"""
WebSocket consumers for real-time chat functionality.
Handles both authenticated and anonymous chat sessions.
"""

import json
import uuid
import asyncio
import structlog
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist

from apps.chatbots.models import Chatbot
from apps.conversations.models import Conversation, Message
from apps.core.rate_limiting import rate_limiter, RateLimitType

logger = structlog.get_logger()


class BaseChatConsumer(AsyncWebsocketConsumer):
    """Base consumer with common chat functionality."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chatbot = None
        self.conversation = None
        self.room_group_name = None
        self.user_identifier = None
    
    async def connect(self):
        """Handle WebSocket connection."""
        try:
            await self.validate_and_setup()
            
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            await self.accept()
            
            # Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'chatbot_id': str(self.chatbot.id),
                'conversation_id': str(self.conversation.id) if self.conversation else None,
                'message': 'Connected successfully'
            }))
            
            logger.info(
                "WebSocket connection established",
                chatbot_id=str(self.chatbot.id),
                user_identifier=self.user_identifier,
                room=self.room_group_name
            )
            
        except Exception as e:
            logger.error(
                "WebSocket connection failed",
                error=str(e),
                path=self.scope['path']
            )
            await self.close(code=4000)
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        
        logger.info(
            "WebSocket connection closed",
            close_code=close_code,
            chatbot_id=str(self.chatbot.id) if self.chatbot else None,
            user_identifier=self.user_identifier
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing_indicator':
                await self.handle_typing_indicator(data)
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            else:
                await self.send_error(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(
                "Error processing WebSocket message",
                error=str(e),
                user_identifier=self.user_identifier
            )
            await self.send_error("Failed to process message")
    
    async def handle_chat_message(self, data):
        """Process chat message and generate response."""
        message_content = data.get('message', '').strip()
        if not message_content:
            await self.send_error("Message content is required")
            return
        
        # Check rate limits
        if not await self.check_rate_limits():
            await self.send_error("Rate limit exceeded")
            return
        
        try:
            # Save user message
            user_message = await self.save_user_message(message_content)
            
            # Broadcast user message to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message_broadcast',
                    'message': {
                        'id': str(user_message.id),
                        'role': 'user',
                        'content': message_content,
                        'timestamp': user_message.created_at.isoformat(),
                    }
                }
            )
            
            # Generate AI response
            await self.generate_ai_response(message_content)
            
        except Exception as e:
            logger.error(
                "Error handling chat message",
                error=str(e),
                user_identifier=self.user_identifier,
                message=message_content
            )
            await self.send_error("Failed to process chat message")
    
    async def handle_typing_indicator(self, data):
        """Handle typing indicator."""
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator_broadcast',
                'user_identifier': self.user_identifier,
                'is_typing': is_typing
            }
        )
    
    async def chat_message_broadcast(self, event):
        """Send chat message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            **event['message']
        }))
    
    async def typing_indicator_broadcast(self, event):
        """Send typing indicator to WebSocket."""
        # Don't send typing indicator back to sender
        if event['user_identifier'] != self.user_identifier:
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'user_identifier': event['user_identifier'],
                'is_typing': event['is_typing']
            }))
    
    async def send_error(self, error_message):
        """Send error message to client."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': error_message
        }))
    
    async def validate_and_setup(self):
        """Validate request and set up consumer state. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement validate_and_setup")
    
    async def check_rate_limits(self):
        """Check rate limits. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement check_rate_limits")
    
    async def save_user_message(self, content):
        """Save user message to database. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement save_user_message")
    
    async def generate_ai_response(self, user_message):
        """Generate AI response. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement generate_ai_response")


class PrivateChatConsumer(BaseChatConsumer):
    """WebSocket consumer for authenticated private chat."""
    
    async def validate_and_setup(self):
        """Validate authenticated user and chatbot ownership."""
        # Get chatbot ID from URL
        chatbot_id = self.scope['url_route']['kwargs']['chatbot_id']
        
        # Check authentication
        user = self.scope.get('user')
        if not user or isinstance(user, AnonymousUser):
            raise Exception("Authentication required for private chat")
        
        # Get chatbot and verify ownership
        self.chatbot = await database_sync_to_async(
            Chatbot.objects.get
        )(id=chatbot_id, user=user)
        
        # Set user identifier and room name
        self.user_identifier = str(user.id)
        self.room_group_name = f"private_chat_{chatbot_id}_{self.user_identifier}"
        
        # Get or create conversation
        self.conversation = await self.get_or_create_private_conversation(user)
    
    @database_sync_to_async
    def get_or_create_private_conversation(self, user):
        """Get or create conversation for authenticated user."""
        conversation, created = Conversation.objects.get_or_create(
            chatbot=self.chatbot,
            user_id=str(user.id),
            is_active=True,
            defaults={
                'session_id': uuid.uuid4(),
                'user_identifier': str(user.id)
            }
        )
        return conversation
    
    async def check_rate_limits(self):
        """Check rate limits for authenticated users."""
        # Authenticated users get higher rate limits
        rate_limit_key = f"private_chat_{self.user_identifier}"
        return await database_sync_to_async(
            rate_limiter.check_limit
        )(rate_limit_key, RateLimitType.CHAT_MESSAGE)
    
    @database_sync_to_async
    def save_user_message(self, content):
        """Save user message for private chat."""
        return Message.objects.create(
            conversation=self.conversation,
            role='user',
            content=content
        )
    
    async def generate_ai_response(self, user_message):
        """Generate AI response using RAG pipeline with real-time streaming."""
        try:
            # Import here to avoid circular imports
            from apps.core.rag.pipeline import get_rag_pipeline
            from apps.core.rag.llm_service import ChatbotConfig
            
            # Send typing indicator
            await self.send(text_data=json.dumps({
                'type': 'typing_start',
                'message': 'AI is thinking...'
            }))
            
            # Get RAG pipeline
            rag_pipeline = get_rag_pipeline(str(self.chatbot.id))
            
            # Create chatbot configuration
            chatbot_config = ChatbotConfig(
                name=self.chatbot.name,
                description=self.chatbot.description or "AI Assistant",
                company_name="Company",  # Could be enhanced with user org
                temperature=0.7,
                max_response_tokens=500,
                strict_citation_mode=True,
                allow_private_reasoning=True
            )
            
            # Start streaming response
            await self.process_streaming_rag_query(
                user_message=user_message,
                rag_pipeline=rag_pipeline,
                chatbot_config=chatbot_config
            )
            
        except Exception as e:
            logger.error(
                "Failed to generate AI response",
                error=str(e),
                chatbot_id=str(self.chatbot.id),
                user_identifier=self.user_identifier
            )
            await self.send_error("Failed to generate response")
    
    async def process_streaming_rag_query(self, user_message, rag_pipeline, chatbot_config):
        """Process RAG query with real-time streaming response."""
        import time
        start_time = time.time()
        response_buffer = ""
        
        try:
            # Step 1: Generate query embedding
            query_embedding = await rag_pipeline._generate_embedding(user_message)
            
            # Step 2: Vector search with privacy filtering
            search_results = await rag_pipeline.vector_search.search(
                query_embedding=query_embedding,
                query_text=user_message,
                user_id=self.user_identifier,
                top_k=10,
                filter_citable=False,  # Get both for context
                score_threshold=0.7
            )
            
            # Step 3: Build context
            context = rag_pipeline.context_builder.build_context(
                search_results=search_results,
                query=user_message,
                include_private=True,
                ranking_strategy=rag_pipeline.context_builder.RankingStrategy.HYBRID
            )
            
            # Validate privacy
            context_validation = rag_pipeline.context_builder.validate_context_privacy(context)
            if not context_validation["valid"]:
                await self.send_error("Privacy validation failed")
                return
            
            # Step 4: Stream LLM response
            message_id = str(uuid.uuid4())
            
            # Send stream start
            await self.send(text_data=json.dumps({
                'type': 'stream_start',
                'message_id': message_id,
                'sources_found': len(search_results)
            }))
            
            # Stream response chunks
            async for chunk in rag_pipeline.llm_service.generate_streaming_response(
                context=context,
                user_query=user_message,
                chatbot_config=chatbot_config
            ):
                response_buffer += chunk
                
                # Send real-time chunk
                await self.send(text_data=json.dumps({
                    'type': 'stream_chunk',
                    'message_id': message_id,
                    'content': chunk
                }))
                
                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.01)
            
            # Step 5: Privacy filtering on complete response
            privacy_result = rag_pipeline.privacy_filter.validate_response(
                response=response_buffer,
                context=context,
                user_id=self.user_identifier,
                chatbot_id=str(self.chatbot.id),
                strict_mode=True
            )
            
            final_response = (
                privacy_result.sanitized_response 
                if not privacy_result.passed 
                else response_buffer
            )
            
            # Step 6: Save to database
            assistant_message = await database_sync_to_async(
                Message.objects.create
            )(
                conversation=self.conversation,
                role='assistant',
                content=final_response,
                model_used=chatbot_config.model.value,
                temperature=chatbot_config.temperature,
                generation_time_ms=(time.time() - start_time) * 1000,
                metadata={
                    'privacy_compliant': privacy_result.passed,
                    'sources_used': len(search_results),
                    'streaming_enabled': True
                }
            )
            
            # Extract citations
            citations = rag_pipeline.context_builder.get_citation_list(context)
            
            # Send stream completion
            await self.send(text_data=json.dumps({
                'type': 'stream_complete',
                'message_id': message_id,
                'final_message_id': str(assistant_message.id),
                'citations': citations,
                'metadata': {
                    'privacy_compliant': privacy_result.passed,
                    'processing_time': time.time() - start_time,
                    'sources_used': len(search_results)
                }
            }))
            
            # Broadcast complete message to group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message_broadcast',
                    'message': {
                        'id': str(assistant_message.id),
                        'role': 'assistant',
                        'content': final_response,
                        'timestamp': assistant_message.created_at.isoformat(),
                        'citations': citations,
                        'streaming': True
                    }
                }
            )
            
        except Exception as e:
            logger.error(
                "Streaming RAG processing failed",
                error=str(e),
                user_message=user_message
            )
            await self.send(text_data=json.dumps({
                'type': 'stream_error',
                'message': f"Streaming failed: {str(e)}"
            }))


class PublicChatConsumer(BaseChatConsumer):
    """WebSocket consumer for anonymous public chat via widget."""
    
    async def validate_and_setup(self):
        """Validate chatbot slug and setup for anonymous users."""
        # Get chatbot slug from URL
        slug = self.scope['url_route']['kwargs']['slug']
        
        # Get chatbot by slug
        try:
            self.chatbot = await database_sync_to_async(
                Chatbot.objects.get
            )(public_url_slug=slug, status='completed')
        except ObjectDoesNotExist:
            raise Exception(f"Chatbot not found: {slug}")
        
        # Set user identifier (IP-based for anonymous users)
        ip_address = self.get_client_ip()
        self.user_identifier = ip_address
        self.room_group_name = f"public_chat_{slug}_{ip_address}"
        
        # Get or create conversation
        self.conversation = await self.get_or_create_public_conversation(ip_address)
    
    def get_client_ip(self):
        """Get client IP address from WebSocket headers."""
        headers = dict(self.scope.get('headers', []))
        x_forwarded_for = headers.get(b'x-forwarded-for')
        if x_forwarded_for:
            return x_forwarded_for.decode('utf-8').split(',')[0].strip()
        return self.scope.get('client', ['unknown'])[0]
    
    @database_sync_to_async 
    def get_or_create_public_conversation(self, ip_address):
        """Get or create conversation for anonymous user."""
        # Check for existing active conversation
        conversation = Conversation.objects.filter(
            chatbot=self.chatbot,
            user_identifier=ip_address,
            is_active=True
        ).first()
        
        if not conversation:
            conversation = Conversation.objects.create(
                chatbot=self.chatbot,
                session_id=uuid.uuid4(),
                user_identifier=ip_address,
                ip_address=ip_address,
                user_agent=self.scope.get('headers', {}).get('user-agent', '')
            )
        
        return conversation
    
    async def check_rate_limits(self):
        """Check rate limits for anonymous users."""
        # More restrictive rate limits for anonymous users
        rate_limit_key = f"public_chat_{self.user_identifier}"
        return await database_sync_to_async(
            rate_limiter.check_limit
        )(rate_limit_key, RateLimitType.CHAT_MESSAGE)
    
    @database_sync_to_async
    def save_user_message(self, content):
        """Save user message for public chat."""
        return Message.objects.create(
            conversation=self.conversation,
            role='user', 
            content=content
        )
    
    async def generate_ai_response(self, user_message):
        """Generate AI response for public chat."""
        try:
            # Import here to avoid circular imports
            from apps.core.rag.pipeline import get_rag_pipeline
            from apps.core.rag.llm_service import ChatbotConfig
            
            # Get RAG pipeline
            rag_pipeline = get_rag_pipeline(str(self.chatbot.id))
            
            # Create chatbot configuration (more restrictive for public)
            chatbot_config = ChatbotConfig(
                name=self.chatbot.name,
                description=self.chatbot.description or "AI Assistant",
                company_name="Company",
                temperature=0.7,
                max_response_tokens=500,
                strict_citation_mode=True,
                allow_private_reasoning=False  # No private reasoning for public chats
            )
            
            # Process query  
            rag_response = await rag_pipeline.process_query(
                user_query=user_message,
                user_id=self.user_identifier,
                conversation_id=str(self.conversation.id),
                session_id=str(self.conversation.session_id),
                chatbot_config=chatbot_config
            )
            
            # Save assistant message
            assistant_message = await database_sync_to_async(
                Message.objects.create
            )(
                conversation=self.conversation,
                role='assistant',
                content=rag_response.content,
                model_used=chatbot_config.model.value,
                temperature=chatbot_config.temperature,
                token_usage={
                    'input_tokens': rag_response.input_tokens,
                    'output_tokens': rag_response.output_tokens,
                    'total_tokens': rag_response.input_tokens + rag_response.output_tokens
                },
                generation_time_ms=rag_response.total_time * 1000
            )
            
            # Broadcast AI response (simplified for public)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message_broadcast',
                    'message': {
                        'id': str(assistant_message.id),
                        'role': 'assistant',
                        'content': rag_response.content,
                        'timestamp': assistant_message.created_at.isoformat(),
                        'citations': rag_response.citations
                    }
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to generate AI response for public chat",
                error=str(e),
                chatbot_slug=self.chatbot.public_url_slug,
                user_identifier=self.user_identifier
            )
            await self.send_error("Failed to generate response")