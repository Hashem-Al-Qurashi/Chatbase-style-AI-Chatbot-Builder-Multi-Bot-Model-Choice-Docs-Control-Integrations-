"""
Widget API Views - Public endpoints for embeddable chat widgets
These endpoints do not require authentication for public chatbots
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.http import JsonResponse

from apps.chatbots.models import Chatbot
from apps.conversations.models import Conversation, Message
from apps.core.rag.pipeline import RAGPipeline
from apps.core.exceptions import ServiceError

import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_widget_config(request, slug):
    """
    Get public configuration for a chatbot widget
    
    GET /api/v1/widget/config/{slug}/
    """
    try:
        # Find chatbot by public slug - allow ready or completed status
        chatbot = get_object_or_404(
            Chatbot.objects.filter(
                public_url_slug=slug, 
                status__in=['ready', 'completed']
            )
        )
        
        # Return public configuration
        config = {
            'id': str(chatbot.id),
            'name': chatbot.name,
            'description': chatbot.description,
            'welcome_message': getattr(chatbot, 'welcome_message', None) or f"Hi! I'm {chatbot.name}. How can I help you today?",
            'theme': {
                'primary_color': getattr(chatbot, 'primary_color', None) or '#007bff',
                'background_color': getattr(chatbot, 'background_color', None) or '#ffffff',
                'text_color': getattr(chatbot, 'text_color', None) or '#333333',
            },
            'settings': {
                'show_powered_by': True,
                'enable_file_upload': False,  # Not supported in widget yet
                'max_message_length': 500,
            }
        }
        
        logger.info(f"Widget config requested for chatbot: {chatbot.name} (slug: {slug})")
        return Response(config)
        
    except Chatbot.DoesNotExist:
        logger.warning(f"Widget config requested for non-existent chatbot slug: {slug}")
        return Response(
            {'error': 'Chatbot not found or not available for public use'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error getting widget config for {slug}: {str(e)}")
        return Response(
            {'error': 'Internal server error'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def widget_chat(request, slug):
    """
    Handle chat messages for widget
    
    POST /api/v1/widget/chat/{slug}/
    Body: {
        "message": "user message",
        "conversation_id": "optional existing conversation id"
    }
    """
    try:
        # Get chatbot - allow ready or completed status
        chatbot = get_object_or_404(
            Chatbot.objects.filter(
                public_url_slug=slug, 
                status__in=['ready', 'completed']
            )
        )
        
        # Get message from request
        message_text = request.data.get('message', '').strip()
        if not message_text:
            return Response(
                {'error': 'Message is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate message length
        if len(message_text) > 500:
            return Response(
                {'error': 'Message too long (max 500 characters)'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create conversation
        conversation_id = request.data.get('conversation_id')
        if conversation_id:
            try:
                conversation = Conversation.objects.get(
                    id=conversation_id, 
                    chatbot=chatbot
                )
            except Conversation.DoesNotExist:
                # Create new conversation if specified ID doesn't exist
                conversation = Conversation.objects.create(
                    chatbot=chatbot,
                    metadata={
                        'source': 'widget',
                        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                        'ip_address': request.META.get('REMOTE_ADDR', ''),
                        'widget_session': f"widget_{uuid.uuid4().hex[:12]}"
                    }
                )
        else:
            # Create new conversation
            conversation = Conversation.objects.create(
                chatbot=chatbot,
                metadata={
                    'source': 'widget',
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'ip_address': request.META.get('REMOTE_ADDR', ''),
                    'widget_session': f"widget_{uuid.uuid4().hex[:12]}"
                }
            )
        
        # Save user message
        user_message = Message.objects.create(
            conversation=conversation,
            content=message_text,
            role='user',
            metadata={'source': 'widget'}
        )
        
        # Generate AI response using RAG Pipeline - Same as main chat
        try:
            # Import RAG components
            from apps.core.rag.pipeline import get_rag_pipeline
            from apps.core.rag.llm_service import ChatbotConfig
            from asgiref.sync import async_to_sync
            
            # Get RAG pipeline for this chatbot
            rag_pipeline = get_rag_pipeline(str(chatbot.id))
            
            # Create chatbot configuration for widget (public mode)
            chatbot_config = ChatbotConfig(
                name=chatbot.name,
                description=chatbot.description or "AI Assistant",
                company_name="Widget User",  # Generic for public widget
                temperature=getattr(chatbot, 'temperature', 0.7),
                max_response_tokens=300,  # Shorter responses for widget
                strict_citation_mode=True,
                allow_private_reasoning=False  # Public widget mode
            )
            
            # Process query through RAG pipeline (public access)
            # Convert async call to sync for compatibility
            rag_response = async_to_sync(rag_pipeline.process_query)(
                user_query=message_text,
                user_id=f"widget_{conversation.id}",  # Anonymous widget user
                conversation_id=str(conversation.id),
                chatbot_config=chatbot_config
            )
            
            response_content = rag_response.content
            
            # Extract sources for widget display (limit to 3 for brevity)
            sources = []
            if hasattr(rag_response, 'citable_sources') and rag_response.citable_sources:
                sources = rag_response.citable_sources[:3]
            elif hasattr(rag_response, 'citations') and rag_response.citations:
                sources = [cite for cite in rag_response.citations[:3] if cite]
            
            logger.info(f"Generated RAG response for widget chat: {chatbot.name}, sources: {len(sources)}")
            
        except Exception as e:
            logger.error(f"RAG pipeline error for widget chat: {str(e)}")
            # Fallback to simple response if RAG fails
            response_content = f"Hello! I'm {chatbot.name}. I'm having trouble accessing my knowledge base right now, but I'm here to help. Could you please try rephrasing your question?"
            sources = []
        
        # Save AI response with enhanced metadata
        try:
            ai_message = Message.objects.create(
                conversation=conversation,
                content=response_content,
                role='assistant',
                metadata={
                    'source': 'widget',
                    'sources': sources,
                    'rag_pipeline_version': '1.0',
                    'widget_session': True,
                    'public_access': True
                }
            )
        except Exception as e:
            logger.error(f"Error saving AI message for widget: {str(e)}")
            # Fallback message creation
            ai_message = Message.objects.create(
                conversation=conversation,
                content=response_content,
                role='assistant',
                metadata={'source': 'widget', 'error': 'metadata_save_failed'}
            )
        
        # Prepare response
        response_data = {
            'response': response_content,
            'message': response_content,  # Alternative field name for compatibility
            'conversation_id': str(conversation.id),
            'message_id': str(ai_message.id),
            'sources': sources[:3] if sources else [],  # Limit sources for widget
            'timestamp': ai_message.created_at.isoformat()
        }
        
        # Check for CRM integration - Send to CRM if email detected
        try:
            from apps.core.crm_service import CRMService
            CRMService.process_conversation_for_crm(conversation, chatbot)
        except Exception as e:
            logger.warning(f"CRM integration failed for conversation {conversation.id}: {str(e)}")
            # Don't fail the chat response if CRM fails
        
        logger.info(f"Widget chat response generated for chatbot {chatbot.name}, conversation {conversation.id}")
        return Response(response_data)
        
    except Chatbot.DoesNotExist:
        return Response(
            {'error': 'Chatbot not found or not available'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error in widget chat for {slug}: {str(e)}")
        return Response(
            {'error': 'Internal server error'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def widget_health(request):
    """
    Health check endpoint for widget services
    
    GET /api/v1/widget/health/
    """
    return Response({
        'status': 'ok',
        'service': 'widget_api',
        'timestamp': datetime.now().isoformat()
    })