"""
API views for chatbots app.
Provides RESTful endpoints for chatbot management.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.core.cache import cache
import structlog

from apps.chatbots.models import Chatbot, ChatbotSettings, ChatbotAnalytics
from apps.chatbots.serializers import (
    ChatbotSerializer, ChatbotListSerializer, ChatbotSettingsSerializer,
    ChatbotAnalyticsSerializer, ChatbotTrainingSerializer,
    ChatbotTestSerializer, ChatbotCloneSerializer,
    ChatbotExportSerializer, ChatbotImportSerializer
)
from apps.core.tasks import train_chatbot_task
# from apps.core.rate_limiting import rate_limiter, RateLimitType  # TODO: Fix rate limiting import

logger = structlog.get_logger()


class ChatbotViewSet(viewsets.ModelViewSet):
    """
    ViewSet for chatbot CRUD operations.
    Includes training, testing, and management endpoints.
    """
    
    serializer_class = ChatbotSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter chatbots by user/organization."""
        user = self.request.user
        queryset = Chatbot.objects.filter(user=user)
        
        # Add search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Add status filtering
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Add sorting
        ordering = self.request.query_params.get('ordering', '-created_at')
        queryset = queryset.order_by(ordering)
        
        return queryset
    
    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'list':
            return ChatbotListSerializer
        return ChatbotSerializer
    
    def perform_create(self, serializer):
        """Create chatbot with user association."""
        # TODO: Implement rate limiting
        # if not rate_limiter.check_limit(
        #     f"chatbot_create_{self.request.user.id}",
        #     RateLimitType.CHATBOT_CREATION
        # ):
        #     raise ValidationError("Chatbot creation rate limit exceeded")
        
        chatbot = serializer.save(user=self.request.user)
        
        # Create default settings
        ChatbotSettings.objects.create(chatbot=chatbot)
        
        logger.info(
            "Chatbot created",
            chatbot_id=str(chatbot.id),
            user_id=str(self.request.user.id)
        )
    
    @action(detail=True, methods=['post'])
    def train(self, request, pk=None):
        """
        Train or retrain the chatbot.
        Triggers async training task.
        """
        chatbot = self.get_object()
        serializer = ChatbotTrainingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if already training
        if chatbot.status == 'processing':
            return Response(
                {'error': 'Chatbot is already being trained'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Trigger training task with proper eager mode handling
        from django.conf import settings
        
        if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
            # In eager mode: task executes synchronously, don't override status
            task_result = train_chatbot_task.delay(
                chatbot_id=str(chatbot.id),
                force_retrain=serializer.validated_data.get('force_retrain', False),
                knowledge_source_ids=serializer.validated_data.get('knowledge_source_ids')
            )
            # Task already completed, get updated status from DB
            chatbot.refresh_from_db()
        else:
            # In async mode: task runs in background, set processing status
            train_chatbot_task.delay(
                chatbot_id=str(chatbot.id),
                force_retrain=serializer.validated_data.get('force_retrain', False),
                knowledge_source_ids=serializer.validated_data.get('knowledge_source_ids')
            )
            # Update status for async execution
            chatbot.update_training_status('processing')
        
        logger.info(
            "Chatbot training initiated",
            chatbot_id=str(chatbot.id),
            user_id=str(request.user.id)
        )
        
        return Response({
            'message': 'Training initiated' if not getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False) else 'Training completed',
            'status': chatbot.status,
            'estimated_time': '2-5 minutes' if not getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False) else 'Completed instantly'
        })
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """
        Test chatbot response without saving conversation.
        Useful for configuration testing.
        """
        chatbot = self.get_object()
        serializer = ChatbotTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if chatbot is ready
        if not chatbot.is_ready:
            return Response(
                {'error': 'Chatbot is not ready. Please train it first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate test response
        from apps.core.services import ChatService
        chat_service = ChatService()
        
        try:
            response = chat_service.generate_response(
                chatbot=chatbot,
                message=serializer.validated_data['message'],
                include_sources=serializer.validated_data.get('include_sources', True)
            )
            
            return Response({
                'response': response['message'],
                'sources': response.get('sources', []),
                'processing_time': response.get('processing_time')
            })
            
        except Exception as e:
            logger.error(
                "Chatbot test failed",
                chatbot_id=str(chatbot.id),
                error=str(e)
            )
            return Response(
                {'error': 'Failed to generate response'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """
        Clone an existing chatbot.
        Creates a copy with optional settings/knowledge.
        """
        chatbot = self.get_object()
        serializer = ChatbotCloneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create clone
        cloned_chatbot = Chatbot.objects.create(
            user=request.user,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', chatbot.description),
            theme_color=chatbot.theme_color,
            welcome_message=chatbot.welcome_message,
            placeholder_text=chatbot.placeholder_text,
            temperature=chatbot.temperature,
            max_tokens=chatbot.max_tokens,
            model_name=chatbot.model_name,
            enable_citations=chatbot.enable_citations,
            enable_data_collection=chatbot.enable_data_collection,
            metadata=chatbot.metadata
        )
        
        # Clone settings if requested
        if serializer.validated_data.get('include_settings', True):
            original_settings = chatbot.settings
            ChatbotSettings.objects.create(
                chatbot=cloned_chatbot,
                system_prompt=original_settings.system_prompt,
                response_guidelines=original_settings.response_guidelines,
                rate_limit_messages_per_hour=original_settings.rate_limit_messages_per_hour,
                rate_limit_messages_per_day=original_settings.rate_limit_messages_per_day,
                enable_profanity_filter=original_settings.enable_profanity_filter,
                enable_spam_detection=original_settings.enable_spam_detection,
                blocked_words=original_settings.blocked_words,
                enable_sentiment_analysis=original_settings.enable_sentiment_analysis,
                enable_topic_extraction=original_settings.enable_topic_extraction,
                enable_lead_capture=original_settings.enable_lead_capture,
                lead_capture_trigger=original_settings.lead_capture_trigger,
                lead_capture_message=original_settings.lead_capture_message,
                show_powered_by=original_settings.show_powered_by,
                custom_css=original_settings.custom_css
            )
        
        logger.info(
            "Chatbot cloned",
            original_id=str(chatbot.id),
            cloned_id=str(cloned_chatbot.id),
            user_id=str(request.user.id)
        )
        
        return Response(
            ChatbotSerializer(cloned_chatbot, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """
        Get chatbot analytics.
        Returns aggregated metrics for specified period.
        """
        chatbot = self.get_object()
        
        # Get date range from query params
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Default to last 30 days
        if not date_from:
            date_from = timezone.now() - timezone.timedelta(days=30)
        if not date_to:
            date_to = timezone.now()
        
        analytics = ChatbotAnalytics.objects.filter(
            chatbot=chatbot,
            date__gte=date_from,
            date__lte=date_to
        ).order_by('date')
        
        # Aggregate metrics
        aggregated = analytics.aggregate(
            total_visitors=Count('unique_visitors'),
            total_conversations=Count('total_conversations'),
            total_messages=Count('total_messages'),
            avg_satisfaction=Avg('user_satisfaction'),
            total_leads=Count('leads_captured'),
            avg_conversion=Avg('conversion_rate')
        )
        
        serializer = ChatbotAnalyticsSerializer(analytics, many=True)
        
        return Response({
            'period': {
                'from': date_from,
                'to': date_to
            },
            'aggregated': aggregated,
            'daily': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """
        Export chatbot configuration.
        Returns configuration in specified format.
        """
        chatbot = self.get_object()
        serializer = ChatbotExportSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        export_data = {
            'chatbot': ChatbotSerializer(chatbot).data,
            'version': '1.0'
        }
        
        if serializer.validated_data.get('include_settings', True):
            export_data['settings'] = ChatbotSettingsSerializer(chatbot.settings).data
        
        if serializer.validated_data.get('include_knowledge', True):
            # Add knowledge sources export
            from apps.knowledge.serializers import KnowledgeSourceSerializer
            sources = chatbot.knowledge_sources.all()
            export_data['knowledge_sources'] = KnowledgeSourceSerializer(sources, many=True).data
        
        if serializer.validated_data.get('include_analytics', False):
            analytics = ChatbotAnalytics.objects.filter(chatbot=chatbot)
            export_data['analytics'] = ChatbotAnalyticsSerializer(analytics, many=True).data
        
        # Format response based on requested format
        format_type = serializer.validated_data.get('format', 'json')
        if format_type == 'yaml':
            import yaml
            from django.http import HttpResponse
            response = HttpResponse(
                yaml.dump(export_data),
                content_type='application/yaml'
            )
            response['Content-Disposition'] = f'attachment; filename="{chatbot.public_url_slug}_export.yaml"'
            return response
        
        return Response(export_data)
    
    @action(detail=False, methods=['post'])
    def import_config(self, request):
        """
        Import chatbot configuration.
        Creates new chatbot from configuration file.
        """
        serializer = ChatbotImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Parse configuration file
        config_file = serializer.validated_data['config_file']
        
        try:
            if config_file.name.endswith('.yaml') or config_file.name.endswith('.yml'):
                import yaml
                config_data = yaml.safe_load(config_file.read())
            else:
                import json
                config_data = json.loads(config_file.read())
            
            # Create chatbot from config
            chatbot_data = config_data.get('chatbot', {})
            chatbot_data['user'] = request.user
            
            chatbot = Chatbot.objects.create(**chatbot_data)
            
            # Import settings if present
            if 'settings' in config_data:
                settings_data = config_data['settings']
                settings_data['chatbot'] = chatbot
                ChatbotSettings.objects.create(**settings_data)
            
            logger.info(
                "Chatbot imported",
                chatbot_id=str(chatbot.id),
                user_id=str(request.user.id)
            )
            
            return Response(
                ChatbotSerializer(chatbot, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(
                "Chatbot import failed",
                error=str(e),
                user_id=str(request.user.id)
            )
            raise ValidationError(f"Failed to import configuration: {str(e)}")
    
    @action(detail=True, methods=['post'])
    def chat(self, request, pk=None):
        """
        Send a chat message to the chatbot.
        This is the main chat endpoint for the dashboard.
        """
        chatbot = self.get_object()
        
        # Check if chatbot is ready
        if not chatbot.is_ready:
            return Response(
                {'error': 'Chatbot is not ready. Please train it first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get message from request
        message = request.data.get('message')
        if not message:
            return Response(
                {'error': 'Message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Use the chat service to generate response
        from apps.core.services import ServiceRegistry
        
        try:
            # Get or create conversation for this user
            from apps.conversations.models import Conversation, Message
            import uuid
            
            # Create a new conversation for each chat session
            conversation = Conversation.objects.create(
                chatbot=chatbot,
                user_identifier=str(request.user.id),
                metadata={
                    'user_id': str(request.user.id),
                    'authenticated': True
                }
            )
            
            # Save user message
            user_message = Message.objects.create(
                conversation=conversation,
                role='user',
                content=message
            )
            
            # Generate response using RAG pipeline
            from apps.core.rag.pipeline import RAGPipeline
            from asgiref.sync import sync_to_async
            import asyncio
            
            # Initialize RAG pipeline for this chatbot
            rag_pipeline = RAGPipeline(str(chatbot.id))
            
            # Process the query through RAG pipeline (async call)
            async def get_rag_response():
                return await rag_pipeline.process_query(
                    user_query=message,
                    conversation_id=str(conversation.id),
                    user_id=str(request.user.id)
                )
            
            # Run the async function
            rag_result = asyncio.run(get_rag_response())
            
            response_text = rag_result.content
            sources = rag_result.citations if hasattr(rag_result, 'citations') else []
            
            # Save bot response
            bot_message = Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=response_text,
                metadata={'sources': sources}
            )
            
            return Response({
                'response': response_text,
                'conversation_id': str(conversation.id),
                'message_id': str(bot_message.id),
                'sources': sources
            })
            
        except Exception as e:
            logger.error(
                "Chat failed",
                chatbot_id=str(chatbot.id),
                error=str(e)
            )
            return Response(
                {'error': 'Failed to generate response'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def get_settings(self, request, pk=None):
        """Get chatbot settings."""
        chatbot = self.get_object()
        chatbot_settings = chatbot.settings
        serializer = ChatbotSettingsSerializer(chatbot_settings)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def update_settings(self, request, pk=None):
        """Update chatbot settings."""
        chatbot = self.get_object()
        chatbot_settings = chatbot.settings
        serializer = ChatbotSettingsSerializer(chatbot_settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        logger.info(
            "Chatbot settings updated",
            chatbot_id=str(chatbot.id),
            user_id=str(request.user.id)
        )
        
        return Response(serializer.data)