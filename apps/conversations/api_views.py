"""
API views for conversations app.
Provides endpoints for chat conversations and public chat widget.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
import structlog
import uuid

from apps.conversations.models import Conversation, Message, MessageSource
from apps.chatbots.models import Chatbot
from apps.conversations.serializers import (
    ConversationSerializer, ConversationListSerializer,
    MessageSerializer, ChatMessageSerializer,
    ChatResponseSerializer, LeadCaptureSerializer,
    ConversationFeedbackSerializer, MessageFeedbackSerializer,
    ConversationExportSerializer
)
from apps.core.services import ServiceRegistry
from apps.core.rate_limiting import rate_limiter, RateLimitType

logger = structlog.get_logger()


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for conversation management.
    For authenticated users to view their chatbot conversations.
    """
    
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter conversations by user's chatbots."""
        user = self.request.user
        queryset = Conversation.objects.filter(chatbot__user=user)
        
        # Filter by chatbot
        chatbot_id = self.request.query_params.get('chatbot')
        if chatbot_id:
            queryset = queryset.filter(chatbot_id=chatbot_id)
        
        # Filter by status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by lead status
        has_lead = self.request.query_params.get('has_lead')
        if has_lead is not None:
            if has_lead.lower() == 'true':
                queryset = queryset.exclude(lead_email__isnull=True)
            else:
                queryset = queryset.filter(lead_email__isnull=True)
        
        # Date range filtering
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(lead_email__icontains=search) |
                Q(lead_name__icontains=search)
            )
        
        # Ordering
        ordering = self.request.query_params.get('ordering', '-created_at')
        queryset = queryset.order_by(ordering)
        
        return queryset.select_related('chatbot').prefetch_related('messages')
    
    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'list':
            return ConversationListSerializer
        return ConversationSerializer
    
    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        """End an active conversation."""
        conversation = self.get_object()
        
        if not conversation.is_active:
            return Response(
                {'error': 'Conversation is already ended'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        conversation.end_conversation()
        
        return Response({'message': 'Conversation ended successfully'})
    
    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """Export conversation in various formats."""
        conversation = self.get_object()
        serializer = ConversationExportSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        format_type = serializer.validated_data.get('format', 'json')
        
        if format_type == 'json':
            data = ConversationSerializer(conversation).data
            return Response(data)
        
        elif format_type == 'csv':
            import csv
            from django.http import HttpResponse
            
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="conversation_{conversation.id}.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Timestamp', 'Role', 'Message', 'Sources'])
            
            for message in conversation.messages.all():
                sources = ', '.join([s.chunk.source.name for s in message.source_citations.all()])
                writer.writerow([
                    message.created_at,
                    message.role,
                    message.content,
                    sources
                ])
            
            return response
        
        elif format_type == 'pdf':
            # PDF export would require additional library like reportlab
            return Response(
                {'error': 'PDF export not yet implemented'},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get conversation analytics for user's chatbots."""
        user = request.user
        
        # Get date range
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if not date_from:
            date_from = timezone.now() - timezone.timedelta(days=30)
        if not date_to:
            date_to = timezone.now()
        
        # Get conversations
        conversations = Conversation.objects.filter(
            chatbot__user=user,
            created_at__gte=date_from,
            created_at__lte=date_to
        )
        
        # Calculate analytics
        analytics = conversations.aggregate(
            total_conversations=Count('id'),
            total_messages=Count('messages'),
            avg_messages_per_conversation=Avg('message_count'),
            avg_satisfaction=Avg('user_satisfaction'),
            total_leads=Count('lead_email'),
            active_conversations=Count('id', filter=Q(is_active=True))
        )
        
        # Get top chatbots
        top_chatbots = conversations.values('chatbot__name').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        return Response({
            'period': {
                'from': date_from,
                'to': date_to
            },
            'metrics': analytics,
            'top_chatbots': top_chatbots
        })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
async def private_chat_message(request, chatbot_id):
    """
    Private endpoint for authenticated users to chat with their chatbots.
    Uses the complete RAG pipeline with full privacy controls.
    """
    # Get chatbot and verify ownership
    try:
        chatbot = Chatbot.objects.get(id=chatbot_id, user=request.user)
    except Chatbot.DoesNotExist:
        raise NotFound('Chatbot not found or access denied')
    
    # Validate request
    serializer = ChatMessageSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    message = serializer.validated_data['message']
    conversation_id = serializer.validated_data.get('conversation_id')
    
    # Get or create conversation
    conversation = None
    if conversation_id:
        try:
            conversation = Conversation.objects.get(
                id=conversation_id,
                chatbot=chatbot,
                user_id=str(request.user.id)
            )
        except Conversation.DoesNotExist:
            pass
    
    if not conversation:
        # Create new conversation for authenticated user
        conversation = Conversation.objects.create(
            chatbot=chatbot,
            session_id=uuid.uuid4(),
            user_identifier=str(request.user.id),
            user_id=str(request.user.id),
            language=serializer.validated_data.get('language', 'en')
        )
    
    # Save user message
    user_message = Message.objects.create(
        conversation=conversation,
        role='user',
        content=message
    )
    
    # Generate response using RAG Pipeline
    from apps.core.rag.pipeline import get_rag_pipeline
    from apps.core.rag.llm_service import ChatbotConfig
    
    try:
        # Get RAG pipeline for this chatbot
        rag_pipeline = get_rag_pipeline(str(chatbot.id))
        
        # Create chatbot configuration
        chatbot_config = ChatbotConfig(
            name=chatbot.name,
            description=chatbot.description or "AI Assistant",
            company_name=getattr(request.user, 'organization', {}).get('name', 'our company'),
            temperature=getattr(chatbot.settings, 'temperature', 0.7),
            max_response_tokens=getattr(chatbot.settings, 'max_response_tokens', 500),
            strict_citation_mode=True,
            allow_private_reasoning=True
        )
        
        # Process query through RAG pipeline (authenticated users can access private sources)
        rag_response = await rag_pipeline.process_query(
            user_query=message,
            user_id=str(request.user.id),
            conversation_id=str(conversation.id),
            chatbot_config=chatbot_config
        )
        
        # Save assistant message with enhanced metadata
        assistant_message = Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=rag_response.content,
            model_used=chatbot_config.model.value,
            temperature=chatbot_config.temperature,
            token_usage={
                'input_tokens': rag_response.input_tokens,
                'output_tokens': rag_response.output_tokens,
                'total_tokens': rag_response.input_tokens + rag_response.output_tokens,
                'estimated_cost': rag_response.estimated_cost
            },
            generation_time_ms=rag_response.total_time * 1000,
            metadata={
                'privacy_compliant': rag_response.privacy_compliant,
                'privacy_violations': rag_response.privacy_violations,
                'sources_used': rag_response.sources_used,
                'citable_sources': rag_response.citable_sources,
                'private_sources': rag_response.private_sources,
                'context_score': rag_response.context_score,
                'quality_score': rag_response.response_quality_score,
                'stage_times': rag_response.stage_times
            }
        )
        
        # Add source citations
        for i, citation in enumerate(rag_response.citations):
            if citation:  # Only add non-empty citations
                MessageSource.objects.create(
                    message=assistant_message,
                    chunk_id=f"citation_{i}",
                    relevance_score=0.9  # Could be enhanced with actual relevance scores
                )
        
        logger.info(
            "Private chat message processed",
            chatbot_id=str(chatbot.id),
            conversation_id=str(conversation.id),
            user_id=str(request.user.id),
            privacy_compliant=rag_response.privacy_compliant,
            cost=rag_response.estimated_cost
        )
        
        # Prepare detailed response for authenticated users
        response_data = {
            'message': rag_response.content,
            'conversation_id': str(conversation.id),
            'message_id': str(assistant_message.id),
            'citations': rag_response.citations,
            'privacy_status': {
                'compliant': rag_response.privacy_compliant,
                'violations': rag_response.privacy_violations
            },
            'performance': {
                'total_time': rag_response.total_time,
                'stage_times': rag_response.stage_times,
                'quality_score': rag_response.response_quality_score
            },
            'usage': {
                'input_tokens': rag_response.input_tokens,
                'output_tokens': rag_response.output_tokens,
                'estimated_cost': rag_response.estimated_cost
            },
            'sources': {
                'total_used': rag_response.sources_used,
                'citable': rag_response.citable_sources,
                'private': rag_response.private_sources,
                'context_score': rag_response.context_score
            }
        }
        
        return Response(response_data)
        
    except Exception as e:
        logger.error(
            "Failed to generate private chat response",
            chatbot_id=str(chatbot.id),
            conversation_id=str(conversation.id),
            user_id=str(request.user.id),
            error=str(e)
        )
        
        return Response(
            {'error': 'Failed to generate response. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
async def public_chat_message(request, slug):
    """
    Public endpoint for chat widget.
    Handles messages from embedded chatbot.
    """
    # Get chatbot by slug
    try:
        chatbot = Chatbot.objects.get(public_url_slug=slug, status='completed')
    except Chatbot.DoesNotExist:
        raise NotFound('Chatbot not found or not ready')
    
    # Check rate limiting
    ip_address = request.META.get('REMOTE_ADDR')
    rate_limit_key = f"chat_{slug}_{ip_address}"
    
    if not rate_limiter.check_limit(rate_limit_key, RateLimitType.CHAT_MESSAGE):
        return Response(
            {'error': 'Rate limit exceeded. Please wait before sending another message.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    # Validate request
    serializer = ChatMessageSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    message = serializer.validated_data['message']
    session_id = serializer.validated_data.get('session_id')
    
    # Get or create conversation
    if session_id:
        conversation = Conversation.objects.filter(
            session_id=session_id,
            chatbot=chatbot
        ).first()
    else:
        conversation = None
    
    if not conversation:
        # Create new conversation
        session_id = uuid.uuid4()
        conversation = Conversation.objects.create(
            chatbot=chatbot,
            session_id=session_id,
            user_identifier=ip_address,
            ip_address=ip_address,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            language=serializer.validated_data.get('language', 'en')
        )
        
        # Increment chatbot conversation count
        chatbot.increment_conversation_count()
    
    # Check conversation-level rate limits
    if conversation.message_count >= chatbot.settings.rate_limit_messages_per_hour:
        return Response(
            {'error': 'Message limit reached for this conversation'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    # Save user message
    user_message = Message.objects.create(
        conversation=conversation,
        role='user',
        content=message
    )
    
    # Generate response using RAG Pipeline
    from apps.core.rag.pipeline import get_rag_pipeline
    from apps.core.rag.llm_service import ChatbotConfig
    
    try:
        # Get RAG pipeline for this chatbot
        rag_pipeline = get_rag_pipeline(str(chatbot.id))
        
        # Create chatbot configuration
        chatbot_config = ChatbotConfig(
            name=chatbot.name,
            description=chatbot.description or "AI Assistant",
            company_name=getattr(chatbot.user, 'organization', {}).get('name', 'our company'),
            temperature=getattr(chatbot.settings, 'temperature', 0.7),
            max_response_tokens=getattr(chatbot.settings, 'max_response_tokens', 500),
            strict_citation_mode=True,
            allow_private_reasoning=True
        )
        
        # Process query through RAG pipeline
        rag_response = await rag_pipeline.process_query(
            user_query=message,
            user_id=ip_address,  # Use IP as user ID for anonymous users
            conversation_id=str(conversation.id),
            session_id=str(session_id),
            chatbot_config=chatbot_config
        )
        
        # Convert RAG response to expected format
        response_data = {
            'message': rag_response.content,
            'model': chatbot_config.model.value,
            'temperature': chatbot_config.temperature,
            'token_usage': {
                'input_tokens': rag_response.input_tokens,
                'output_tokens': rag_response.output_tokens,
                'total_tokens': rag_response.input_tokens + rag_response.output_tokens
            },
            'processing_time': rag_response.total_time * 1000,  # Convert to ms
            'sources': [
                {
                    'chunk_id': f"citation_{i}",
                    'source_name': citation,
                    'source_type': 'document',
                    'relevance_score': 0.9,
                    'is_citable': True
                }
                for i, citation in enumerate(rag_response.citations)
            ],
            'suggested_followups': [],  # Could be enhanced later
            'privacy_compliant': rag_response.privacy_compliant,
            'cost': rag_response.estimated_cost
        }
        
        # Save assistant message
        assistant_message = Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=response_data['message'],
            model_used=response_data.get('model'),
            temperature=response_data.get('temperature'),
            token_usage=response_data.get('token_usage', {}),
            generation_time_ms=response_data.get('processing_time')
        )
        
        # Add source citations if available
        for source in response_data.get('sources', []):
            if source.get('is_citable'):
                MessageSource.objects.create(
                    message=assistant_message,
                    chunk_id=source['chunk_id'],
                    relevance_score=source['relevance_score']
                )
        
        # Prepare response
        response_serializer = ChatResponseSerializer(data={
            'message': response_data['message'],
            'session_id': session_id,
            'sources': [
                {
                    'name': s['source_name'],
                    'type': s['source_type'],
                    'relevance': s['relevance_score']
                }
                for s in response_data.get('sources', [])
                if s.get('is_citable')
            ],
            'suggested_followups': response_data.get('suggested_followups', [])
        })
        response_serializer.is_valid()
        
        logger.info(
            "Public chat message processed",
            chatbot_id=str(chatbot.id),
            conversation_id=str(conversation.id),
            session_id=str(session_id)
        )
        
        return Response(response_serializer.data)
        
    except Exception as e:
        logger.error(
            "Failed to generate chat response",
            chatbot_id=str(chatbot.id),
            conversation_id=str(conversation.id),
            error=str(e)
        )
        
        return Response(
            {'error': 'Failed to generate response. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def capture_lead(request, slug):
    """
    Capture lead information from chat widget.
    """
    # Get chatbot by slug
    try:
        chatbot = Chatbot.objects.get(public_url_slug=slug)
    except Chatbot.DoesNotExist:
        raise NotFound('Chatbot not found')
    
    serializer = LeadCaptureSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # Find conversation
    conversation = None
    if serializer.validated_data.get('conversation_id'):
        conversation = Conversation.objects.filter(
            id=serializer.validated_data['conversation_id'],
            chatbot=chatbot
        ).first()
    elif serializer.validated_data.get('session_id'):
        conversation = Conversation.objects.filter(
            session_id=serializer.validated_data['session_id'],
            chatbot=chatbot
        ).first()
    
    if not conversation:
        return Response(
            {'error': 'Conversation not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Capture lead
    conversation.capture_lead(
        email=serializer.validated_data['email'],
        name=serializer.validated_data.get('name'),
        phone=serializer.validated_data.get('phone')
    )
    
    # Send to CRM webhook if configured
    if chatbot.crm_webhook_url:
        from apps.core.tasks import send_lead_to_crm_task
        send_lead_to_crm_task.delay(
            chatbot_id=str(chatbot.id),
            conversation_id=str(conversation.id),
            lead_data={
                'email': serializer.validated_data['email'],
                'name': serializer.validated_data.get('name'),
                'phone': serializer.validated_data.get('phone'),
                'conversation_url': f"/conversations/{conversation.id}",
                'captured_at': timezone.now().isoformat()
            }
        )
    
    logger.info(
        "Lead captured",
        chatbot_id=str(chatbot.id),
        conversation_id=str(conversation.id),
        email=serializer.validated_data['email']
    )
    
    return Response({
        'message': 'Lead captured successfully',
        'conversation_id': str(conversation.id)
    })


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def conversation_feedback(request, slug):
    """
    Submit feedback for a conversation.
    """
    # Get chatbot by slug
    try:
        chatbot = Chatbot.objects.get(public_url_slug=slug)
    except Chatbot.DoesNotExist:
        raise NotFound('Chatbot not found')
    
    serializer = ConversationFeedbackSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # Find conversation
    conversation = None
    if serializer.validated_data.get('conversation_id'):
        conversation = Conversation.objects.filter(
            id=serializer.validated_data['conversation_id'],
            chatbot=chatbot
        ).first()
    elif serializer.validated_data.get('session_id'):
        conversation = Conversation.objects.filter(
            session_id=serializer.validated_data['session_id'],
            chatbot=chatbot
        ).first()
    
    if not conversation:
        return Response(
            {'error': 'Conversation not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Set satisfaction rating
    conversation.set_satisfaction(
        rating=serializer.validated_data['rating'],
        feedback=serializer.validated_data.get('feedback')
    )
    
    return Response({'message': 'Feedback submitted successfully'})


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def message_feedback(request, slug):
    """
    Submit feedback for a specific message.
    """
    # Get chatbot by slug
    try:
        chatbot = Chatbot.objects.get(public_url_slug=slug)
    except Chatbot.DoesNotExist:
        raise NotFound('Chatbot not found')
    
    serializer = MessageFeedbackSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # Find message
    message = Message.objects.filter(
        id=serializer.validated_data['message_id'],
        conversation__chatbot=chatbot
    ).first()
    
    if not message:
        return Response(
            {'error': 'Message not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Process feedback
    if serializer.validated_data.get('flag'):
        message.flag_message(serializer.validated_data['flag_reason'])
    else:
        message.set_helpfulness(serializer.validated_data['is_helpful'])
    
    return Response({'message': 'Feedback submitted successfully'})


@api_view(['GET'])
@permission_classes([AllowAny])
def chatbot_widget_config(request, slug):
    """
    Get chatbot configuration for widget initialization.
    """
    try:
        chatbot = Chatbot.objects.get(public_url_slug=slug, status='completed')
    except Chatbot.DoesNotExist:
        raise NotFound('Chatbot not found or not ready')
    
    # Cache widget config
    cache_key = f"widget_config_{slug}"
    config = cache.get(cache_key)
    
    if not config:
        from apps.chatbots.serializers import PublicChatbotSerializer
        config = PublicChatbotSerializer(chatbot).data
        
        # Add settings
        settings = chatbot.settings
        config['settings'] = {
            'rate_limit_messages_per_hour': settings.rate_limit_messages_per_hour,
            'enable_lead_capture': settings.enable_lead_capture,
            'lead_capture_trigger': settings.lead_capture_trigger,
            'lead_capture_message': settings.lead_capture_message,
            'show_powered_by': settings.show_powered_by,
            'custom_css': settings.custom_css
        }
        
        cache.set(cache_key, config, 300)  # Cache for 5 minutes
    
    return Response(config)