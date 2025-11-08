"""
Real-time streaming service for RAG responses using Django Channels.

Provides WebSocket-based streaming of RAG responses with authentication,
rate limiting, and comprehensive error handling.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import structlog

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.utils import timezone

from apps.core.rag_orchestrator import RAGOrchestrator, RAGQuery, PrivacyMode, query_rag
from apps.core.exceptions import RAGError
from chatbot_saas.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


@dataclass
class StreamingSession:
    """WebSocket streaming session data."""
    user_id: str
    chatbot_id: str
    session_id: str
    channel_name: str
    connected_at: datetime
    last_activity: datetime
    message_count: int = 0
    rate_limit_tokens: int = 60  # Default rate limit
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['connected_at'] = self.connected_at.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        return data


class RateLimiter:
    """Rate limiter for WebSocket connections."""
    
    def __init__(self, max_requests: int = 60, window_minutes: int = 1):
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60
        self.logger = structlog.get_logger().bind(component="RateLimiter")
    
    def is_allowed(self, user_id: str) -> bool:
        """Check if user is within rate limits."""
        cache_key = f"rate_limit:{user_id}"
        
        # Get current request count
        current_count = cache.get(cache_key, 0)
        
        if current_count >= self.max_requests:
            self.logger.warning(
                "Rate limit exceeded",
                user_id=user_id,
                current_count=current_count,
                max_requests=self.max_requests
            )
            return False
        
        # Increment counter
        cache.set(cache_key, current_count + 1, timeout=self.window_seconds)
        
        return True
    
    def get_remaining_requests(self, user_id: str) -> int:
        """Get remaining requests for user."""
        cache_key = f"rate_limit:{user_id}"
        current_count = cache.get(cache_key, 0)
        return max(0, self.max_requests - current_count)


class StreamingAuthenticator:
    """Authentication for WebSocket connections."""
    
    def __init__(self):
        self.logger = structlog.get_logger().bind(component="StreamingAuthenticator")
    
    @database_sync_to_async
    def authenticate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Authenticate user token and return user info."""
        try:
            # Simple token-based auth - in production, use proper JWT validation
            if not token or len(token) < 10:
                return None
            
            # Mock authentication - replace with real token validation
            if token.startswith("user_"):
                user_id = token.replace("user_", "")
                return {
                    "user_id": user_id,
                    "is_authenticated": True,
                    "permissions": ["chat", "stream"]
                }
            
            return None
            
        except Exception as e:
            self.logger.error("Authentication error", error=str(e))
            return None
    
    async def authenticate_websocket(self, scope: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Authenticate WebSocket connection."""
        # Extract token from query string or headers
        query_string = scope.get("query_string", b"").decode()
        
        # Parse query parameters
        params = {}
        if query_string:
            for param in query_string.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key] = value
        
        token = params.get("token")
        if not token:
            # Try to get from headers (for browser-based connections)
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
        
        if token:
            return await self.authenticate_token(token)
        
        return None


class RAGStreamingConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for streaming RAG responses."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session: Optional[StreamingSession] = None
        self.rate_limiter = RateLimiter()
        self.authenticator = StreamingAuthenticator()
        self.rag_orchestrator = RAGOrchestrator()
        self.logger = structlog.get_logger().bind(component="RAGStreamingConsumer")
        
        # Initialize individual components for testing
        from apps.core.rag_orchestrator import QueryProcessor
        self.query_processor = QueryProcessor()
        
        # Initialize orchestrator flag
        self.orchestrator_initialized = False
    
    async def connect(self):
        """Handle WebSocket connection."""
        try:
            # Authenticate connection
            user_info = await self.authenticator.authenticate_websocket(self.scope)
            
            if not user_info:
                self.logger.warning("Unauthenticated WebSocket connection attempt")
                await self.close(code=4001)  # Unauthorized
                return
            
            # Check rate limits
            user_id = user_info["user_id"]
            if not self.rate_limiter.is_allowed(user_id):
                self.logger.warning("Rate limit exceeded for WebSocket connection", user_id=user_id)
                await self.close(code=4029)  # Too Many Requests
                return
            
            # Accept connection
            await self.accept()
            
            # Create session
            self.session = StreamingSession(
                user_id=user_id,
                chatbot_id="default",  # Can be customized per connection
                session_id=f"ws_{user_id}_{int(time.time())}",
                channel_name=self.channel_name,
                connected_at=timezone.now(),
                last_activity=timezone.now()
            )
            
            # Initialize RAG orchestrator if needed
            if not self.orchestrator_initialized:
                await self.rag_orchestrator.initialize()
                self.orchestrator_initialized = True
            
            # Send connection confirmation
            await self.send_message({
                "type": "connection_established",
                "session_id": self.session.session_id,
                "user_id": user_id,
                "rate_limit": {
                    "max_requests": self.rate_limiter.max_requests,
                    "window_seconds": self.rate_limiter.window_seconds,
                    "remaining": self.rate_limiter.get_remaining_requests(user_id)
                }
            })
            
            self.logger.info(
                "WebSocket connection established",
                user_id=user_id,
                session_id=self.session.session_id,
                channel_name=self.channel_name
            )
            
        except Exception as e:
            self.logger.error("Error establishing WebSocket connection", error=str(e))
            await self.close(code=4500)  # Internal Server Error
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if self.session:
            session_duration = timezone.now() - self.session.connected_at
            
            self.logger.info(
                "WebSocket connection closed",
                user_id=self.session.user_id,
                session_id=self.session.session_id,
                close_code=close_code,
                session_duration_seconds=session_duration.total_seconds(),
                message_count=self.session.message_count
            )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            if not self.session:
                await self.close(code=4001)
                return
            
            # Update activity timestamp
            self.session.last_activity = timezone.now()
            self.session.message_count += 1
            
            # Check rate limits
            if not self.rate_limiter.is_allowed(self.session.user_id):
                await self.send_error("Rate limit exceeded. Please slow down.")
                return
            
            # Parse message
            try:
                message = json.loads(text_data)
            except json.JSONDecodeError:
                await self.send_error("Invalid JSON format.")
                return
            
            # Handle different message types
            message_type = message.get("type")
            
            if message_type == "query":
                await self.handle_query_message(message)
            elif message_type == "ping":
                await self.handle_ping_message()
            elif message_type == "cancel":
                await self.handle_cancel_message(message)
            else:
                await self.send_error(f"Unknown message type: {message_type}")
            
        except Exception as e:
            self.logger.error(
                "Error handling WebSocket message",
                error=str(e),
                user_id=self.session.user_id if self.session else "unknown"
            )
            await self.send_error("Internal server error.")
    
    async def handle_query_message(self, message: Dict[str, Any]):
        """Handle RAG query messages with streaming response."""
        try:
            # Validate query
            query_text = message.get("query", "").strip()
            if not query_text:
                await self.send_error("Query text is required.")
                return
            
            if len(query_text) > 1000:  # Reasonable limit
                await self.send_error("Query text too long (max 1000 characters).")
                return
            
            # Extract query parameters
            chatbot_id = message.get("chatbot_id", self.session.chatbot_id)
            privacy_mode = message.get("privacy_mode", "strict")
            
            # Validate privacy mode
            try:
                privacy_enum = PrivacyMode(privacy_mode)
            except ValueError:
                await self.send_error(f"Invalid privacy mode: {privacy_mode}")
                return
            
            # Create RAG query
            rag_query = RAGQuery(
                text=query_text,
                user_id=self.session.user_id,
                chatbot_id=chatbot_id,
                session_id=self.session.session_id,
                privacy_mode=privacy_enum,
                top_k_results=message.get("top_k", 10),
                temperature=message.get("temperature", 0.7)
            )
            
            # Send query acknowledgment
            await self.send_message({
                "type": "query_started",
                "query_id": rag_query.request_id,
                "query": query_text,
                "timestamp": timezone.now().isoformat()
            })
            
            # Process query with streaming
            await self.stream_rag_response(rag_query)
            
        except Exception as e:
            self.logger.error(
                "Error handling query message",
                error=str(e),
                user_id=self.session.user_id
            )
            await self.send_error("Failed to process query.")
    
    async def stream_rag_response(self, rag_query: RAGQuery):
        """Stream RAG response in chunks."""
        try:
            # Send processing status updates
            await self.send_message({
                "type": "processing_status",
                "query_id": rag_query.request_id,
                "stage": "analyzing",
                "message": "Analyzing your question..."
            })
            
            # Process the query (this could be made more granular for better streaming)
            start_time = time.time()
            
            # Send embedding status
            await self.send_message({
                "type": "processing_status",
                "query_id": rag_query.request_id,
                "stage": "embedding",
                "message": "Generating query embedding..."
            })
            
            # Send search status
            await self.send_message({
                "type": "processing_status",
                "query_id": rag_query.request_id,
                "stage": "searching",
                "message": "Searching knowledge base..."
            })
            
            # Process the full query
            response = await self.rag_orchestrator.process_query(rag_query)
            
            # Send context assembly status
            await self.send_message({
                "type": "processing_status",
                "query_id": rag_query.request_id,
                "stage": "assembling",
                "message": "Assembling context from sources..."
            })
            
            # Send generation status
            await self.send_message({
                "type": "processing_status",
                "query_id": rag_query.request_id,
                "stage": "generating",
                "message": "Generating response..."
            })
            
            # Stream the response text (simulate streaming by chunking)
            await self.stream_response_text(rag_query.request_id, response.text)
            
            # Send citations
            await self.send_message({
                "type": "citations",
                "query_id": rag_query.request_id,
                "citations": response.citations
            })
            
            # Send final metadata
            processing_time = time.time() - start_time
            await self.send_message({
                "type": "query_completed",
                "query_id": rag_query.request_id,
                "metadata": {
                    "processing_time": processing_time,
                    "generation_time": response.generation_time,
                    "cost_estimate": response.cost_estimate,
                    "privacy_validated": response.privacy_validated,
                    "context_sources": response.context_used.source_count,
                    "total_tokens": response.context_used.total_tokens
                },
                "timestamp": timezone.now().isoformat()
            })
            
        except RAGError as e:
            await self.send_error(f"RAG processing failed: {str(e)}", rag_query.request_id)
        except Exception as e:
            self.logger.error(
                "Error streaming RAG response",
                error=str(e),
                query_id=rag_query.request_id
            )
            await self.send_error("Failed to generate response.", rag_query.request_id)
    
    async def stream_response_text(self, query_id: str, text: str, chunk_size: int = 50):
        """Stream response text in chunks to simulate real-time generation."""
        words = text.split()
        current_chunk = []
        
        await self.send_message({
            "type": "response_start",
            "query_id": query_id,
            "timestamp": timezone.now().isoformat()
        })
        
        for i, word in enumerate(words):
            current_chunk.append(word)
            
            # Send chunk every N words or at the end
            if len(current_chunk) >= chunk_size // 5 or i == len(words) - 1:  # Smaller chunks for demo
                chunk_text = " ".join(current_chunk)
                
                await self.send_message({
                    "type": "response_chunk",
                    "query_id": query_id,
                    "chunk": chunk_text,
                    "chunk_index": i // (chunk_size // 5),
                    "is_final": i == len(words) - 1
                })
                
                current_chunk = []
                
                # Add small delay to simulate streaming
                await asyncio.sleep(0.1)
        
        await self.send_message({
            "type": "response_end",
            "query_id": query_id,
            "timestamp": timezone.now().isoformat()
        })
    
    async def handle_ping_message(self):
        """Handle ping messages for connection health checks."""
        await self.send_message({
            "type": "pong",
            "timestamp": timezone.now().isoformat(),
            "session_id": self.session.session_id if self.session else None
        })
    
    async def handle_cancel_message(self, message: Dict[str, Any]):
        """Handle query cancellation requests."""
        query_id = message.get("query_id")
        
        await self.send_message({
            "type": "query_cancelled",
            "query_id": query_id,
            "timestamp": timezone.now().isoformat()
        })
        
        # Note: In a production system, you'd want to actually cancel the running query
        self.logger.info(
            "Query cancellation requested",
            query_id=query_id,
            user_id=self.session.user_id if self.session else "unknown"
        )
    
    async def send_message(self, message: Dict[str, Any]):
        """Send a message to the WebSocket client."""
        try:
            await self.send(text_data=json.dumps(message))
        except Exception as e:
            self.logger.error("Failed to send WebSocket message", error=str(e))
    
    async def send_error(self, error_message: str, query_id: Optional[str] = None):
        """Send an error message to the client."""
        await self.send_message({
            "type": "error",
            "message": error_message,
            "query_id": query_id,
            "timestamp": timezone.now().isoformat()
        })


class StreamingHealthChecker:
    """Health checker for streaming service."""
    
    def __init__(self):
        self.logger = structlog.get_logger().bind(component="StreamingHealthChecker")
    
    async def check_health(self) -> Dict[str, Any]:
        """Check streaming service health."""
        try:
            components = {}
            overall_status = "healthy"
            
            # Check Redis connection (for Django Channels) - non-critical for basic functionality
            try:
                from channels.layers import get_channel_layer
                channel_layer = get_channel_layer()
                
                if channel_layer is None:
                    components["channel_layer"] = "not_configured"
                else:
                    # Test channel layer
                    test_channel = "test-health-check"
                    await channel_layer.send(test_channel, {"type": "test.message"})
                    components["channel_layer"] = "healthy"
            except Exception as e:
                components["channel_layer"] = f"unhealthy: {str(e)}"
                # Don't fail overall health for Redis issues in development
                if "localhost:6379" not in str(e):
                    overall_status = "degraded"
            
            # Check RAG orchestrator - critical component
            try:
                orchestrator = RAGOrchestrator()
                rag_initialized = await orchestrator.initialize()
                components["rag_orchestrator"] = "healthy" if rag_initialized else "unhealthy"
                if not rag_initialized:
                    overall_status = "unhealthy"
            except Exception as e:
                components["rag_orchestrator"] = f"unhealthy: {str(e)}"
                overall_status = "unhealthy"
            
            # Check basic streaming components
            try:
                rate_limiter = RateLimiter()
                authenticator = StreamingAuthenticator()
                components["rate_limiter"] = "healthy"
                components["authenticator"] = "healthy"
            except Exception as e:
                components["streaming_components"] = f"unhealthy: {str(e)}"
                overall_status = "unhealthy"
            
            return {
                "status": overall_status,
                "components": components,
                "timestamp": timezone.now().isoformat(),
                "notes": "Redis connection issues are non-critical in development"
            }
            
        except Exception as e:
            self.logger.error("Health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": timezone.now().isoformat()
            }


# Global health checker instance
streaming_health_checker = StreamingHealthChecker()


# WebSocket URL routing
def get_websocket_urlpatterns():
    """Get WebSocket URL patterns for routing."""
    from django.urls import path
    
    return [
        path("ws/chat/", RAGStreamingConsumer.as_asgi()),
        path("ws/health/", streaming_health_checker.check_health),
    ]