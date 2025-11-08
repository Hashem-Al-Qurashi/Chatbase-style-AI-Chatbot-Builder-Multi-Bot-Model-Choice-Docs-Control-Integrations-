"""
RAG Pipeline - Complete orchestration of privacy-first RAG system.

This module orchestrates the entire RAG pipeline with strict privacy enforcement
across all three layers of protection:

Layer 1: Database-level privacy filtering (VectorSearchService)
Layer 2: LLM prompt-level privacy enforcement (LLMService)  
Layer 3: Response post-processing and sanitization (PrivacyFilter)

CRITICAL: This pipeline enforces ZERO tolerance for privacy leaks.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from .vector_search_service import VectorSearchService, get_vector_search_service
from .context_builder import ContextBuilder, ContextData, RankingStrategy
from .llm_service import LLMService, GenerationResult, ChatbotConfig, get_llm_service
from .privacy_filter import PrivacyFilter, FilterResult, get_privacy_filter

from apps.core.embedding_service import OpenAIEmbeddingService
from apps.core.monitoring import track_metric
# Note: Using conversation models directly from their apps
from apps.chatbots.models import Chatbot
from apps.conversations.models import Conversation as ConversationModel
from django.utils import timezone

logger = logging.getLogger(__name__)


class RAGStage(Enum):
    """RAG pipeline stages for tracking."""
    EMBEDDING_GENERATION = "embedding_generation"
    VECTOR_SEARCH = "vector_search" 
    CONTEXT_BUILDING = "context_building"
    LLM_GENERATION = "llm_generation"
    PRIVACY_FILTERING = "privacy_filtering"
    CONVERSATION_SAVING = "conversation_saving"


@dataclass
class RAGResponse:
    """Complete RAG response with metadata."""
    content: str
    citations: List[str]
    
    # Privacy and compliance
    privacy_compliant: bool
    privacy_violations: int
    
    # Performance metrics
    total_time: float
    stage_times: Dict[str, float]
    
    # Usage metrics
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    
    # Context metadata
    sources_used: int
    citable_sources: int
    private_sources: int
    context_score: float
    
    # Quality metrics
    response_quality_score: float
    user_satisfaction_predicted: float


@dataclass
class RAGMetadata:
    """Extended metadata for RAG operations."""
    query: str
    chatbot_id: str
    user_id: str
    conversation_id: Optional[str]
    
    # Search metadata
    search_results_count: int
    search_time: float
    
    # Context metadata
    context_token_count: int
    ranking_strategy: str
    
    # Generation metadata
    model_used: str
    generation_time: float
    
    # Privacy metadata
    privacy_filter_passed: bool
    privacy_violations: List[str]
    
    # Performance metadata
    total_pipeline_time: float
    cache_hits: int


class ConversationManager:
    """Manage conversation history and context."""
    
    @staticmethod
    async def create_conversation(chatbot_id: str, session_id: str, user_id: str) -> str:
        """
        Create new conversation.
        
        Args:
            chatbot_id: Chatbot ID
            session_id: Session ID
            user_id: User ID
            
        Returns:
            str: Conversation ID
        """
        from asgiref.sync import sync_to_async
        
        try:
            # Use async database operations
            chatbot = await sync_to_async(Chatbot.objects.get)(id=chatbot_id)
            
            conversation = await sync_to_async(ConversationModel.objects.create)(
                chatbot=chatbot,
                session_id=session_id,
                user_identifier=user_id,
                created_at=timezone.now()
            )
            
            logger.info(f"Created conversation {conversation.id} for chatbot {chatbot_id}")
            return str(conversation.id)
            
        except Exception as e:
            logger.error(f"Failed to create conversation: {str(e)}")
            raise
    
    @staticmethod
    def add_message(
        conversation_id: str,
        role: str,
        content: str,
        sources_used: List[str] = None,
        metadata: Dict[str, Any] = None
    ):
        """
        Add message to conversation.
        
        Args:
            conversation_id: Conversation ID
            role: Message role (user/assistant)
            content: Message content
            sources_used: Sources used for the message
            metadata: Additional metadata
        """
        try:
            from apps.conversations.models import Message
            
            conversation = ConversationModel.objects.get(id=conversation_id)
            
            message = Message.objects.create(
                conversation=conversation,
                role=role,
                content=content,
                sources_used=sources_used or [],
                metadata=metadata or {},
                created_at=timezone.now()
            )
            
            logger.debug(f"Added {role} message to conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Failed to add message to conversation: {str(e)}")
            # Don't raise - conversation saving shouldn't break the pipeline
    
    @staticmethod
    def get_conversation_context(conversation_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent conversation context.
        
        Args:
            conversation_id: Conversation ID
            limit: Number of recent messages
            
        Returns:
            List[Dict[str, Any]]: Recent messages
        """
        try:
            from apps.conversations.models import Message
            
            messages = Message.objects.filter(
                conversation_id=conversation_id
            ).order_by('-created_at')[:limit]
            
            context = []
            for message in reversed(messages):  # Reverse to get chronological order
                context.append({
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.created_at.isoformat()
                })
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get conversation context: {str(e)}")
            return []


class RAGMetrics:
    """Track comprehensive RAG pipeline metrics."""
    
    @staticmethod
    def track_query_latency(stage: str, duration_ms: float):
        """Track latency for each pipeline stage."""
        track_metric(f"rag.{stage}.latency", duration_ms)
    
    @staticmethod
    def track_relevance_score(query: str, response: str, context_score: float):
        """Track response relevance metrics."""
        # Simple relevance scoring based on context quality
        track_metric("rag.context_score", context_score)
        track_metric("rag.response_length", len(response))
    
    @staticmethod
    def track_privacy_violations(violation_count: int, violation_types: List[str]):
        """Track privacy filter violations."""
        track_metric("rag.privacy.violations", violation_count)
        for violation_type in violation_types:
            track_metric(f"rag.privacy.{violation_type}", 1)
    
    @staticmethod
    def track_cost_metrics(input_tokens: int, output_tokens: int, cost: float):
        """Track cost metrics."""
        track_metric("rag.cost.input_tokens", input_tokens)
        track_metric("rag.cost.output_tokens", output_tokens)
        track_metric("rag.cost.total_usd", cost)
    
    @staticmethod
    def get_pipeline_analytics() -> Dict[str, Any]:
        """Get comprehensive pipeline analytics."""
        # This would integrate with your monitoring system
        # For now, return basic structure
        return {
            "total_queries": 0,
            "avg_latency": 0.0,
            "privacy_compliance_rate": 1.0,
            "avg_cost_per_query": 0.0,
            "avg_context_score": 0.0
        }


class RAGPipeline:
    """
    Complete RAG pipeline with privacy-first architecture.
    
    This class orchestrates the entire RAG process while enforcing
    strict privacy controls at every layer.
    """
    
    def __init__(self, chatbot_id: str):
        """
        Initialize RAG pipeline for specific chatbot.
        
        Args:
            chatbot_id: Chatbot ID
        """
        self.chatbot_id = chatbot_id
        
        # Initialize services
        self.vector_search = get_vector_search_service(chatbot_id)
        self.context_builder = ContextBuilder(max_context_tokens=3000)
        self.llm_service = get_llm_service()
        self.privacy_filter = get_privacy_filter()
        self.embedding_service = OpenAIEmbeddingService()
        
        # Performance tracking
        self.metrics = RAGMetrics()
        
        logger.info(f"Initialized RAG pipeline for chatbot {chatbot_id}")
    
    async def process_query(
        self,
        user_query: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        chatbot_config: Optional[ChatbotConfig] = None
    ) -> RAGResponse:
        """
        Process user query through complete RAG pipeline.
        
        Args:
            user_query: User's question
            user_id: User ID for privacy filtering
            conversation_id: Optional conversation ID
            session_id: Optional session ID  
            chatbot_config: Optional chatbot configuration
            
        Returns:
            RAGResponse: Complete response with metadata
        """
        start_time = time.time()
        stage_times = {}
        
        try:
            logger.info(f"Processing query for user {user_id}: '{user_query[:100]}...'")
            
            # Create conversation if needed
            if not conversation_id and session_id:
                conversation_id = await ConversationManager.create_conversation(
                    self.chatbot_id, session_id, user_id
                )
            
            # Stage 1: Generate query embedding
            stage_start = time.time()
            query_embedding = await self._generate_embedding(user_query)
            stage_times[RAGStage.EMBEDDING_GENERATION.value] = time.time() - stage_start
            
            # Stage 2: Vector search with privacy filtering (Layer 1)
            stage_start = time.time()
            search_results = await self.vector_search.search(
                query_embedding=query_embedding,
                query_text=user_query,
                user_id=user_id,
                top_k=10,
                filter_citable=False,  # Get both citable and private for context
                score_threshold=0.7
            )
            stage_times[RAGStage.VECTOR_SEARCH.value] = time.time() - stage_start
            
            # Stage 3: Build context with privacy separation
            stage_start = time.time()
            context = self.context_builder.build_context(
                search_results=search_results,
                query=user_query,
                include_private=True,  # Include private for reasoning, not citation
                ranking_strategy=RankingStrategy.HYBRID,
                enable_diversity=True
            )
            stage_times[RAGStage.CONTEXT_BUILDING.value] = time.time() - stage_start
            
            # Validate context privacy before proceeding
            context_validation = self.context_builder.validate_context_privacy(context)
            if not context_validation["valid"]:
                logger.error(f"Context privacy validation failed: {context_validation['issues']}")
                raise ValueError("Context privacy validation failed")
            
            # Stage 4: Generate response with LLM (Layer 2 privacy enforcement)
            stage_start = time.time()
            if not chatbot_config:
                chatbot_config = await self._get_default_chatbot_config()
            
            generation_result = await self.llm_service.generate_response(
                context=context,
                user_query=user_query,
                chatbot_config=chatbot_config
            )
            stage_times[RAGStage.LLM_GENERATION.value] = time.time() - stage_start
            
            # Stage 5: Privacy filtering (Layer 3 protection)
            stage_start = time.time()
            privacy_result = self.privacy_filter.validate_response(
                response=generation_result.content,
                context=context,
                user_id=user_id,
                chatbot_id=self.chatbot_id,
                strict_mode=True
            )
            stage_times[RAGStage.PRIVACY_FILTERING.value] = time.time() - stage_start
            
            # Use sanitized response if privacy filter failed
            final_response = (
                privacy_result.sanitized_response 
                if not privacy_result.passed 
                else generation_result.content
            )
            
            # Stage 6: Save to conversation history
            stage_start = time.time()
            if conversation_id:
                await self._save_conversation_messages(
                    conversation_id, user_query, final_response, context
                )
            stage_times[RAGStage.CONVERSATION_SAVING.value] = time.time() - stage_start
            
            total_time = time.time() - start_time
            
            # Extract citations from context
            citations = self.context_builder.get_citation_list(context)
            
            # Calculate quality scores
            response_quality = self._calculate_response_quality(
                generation_result, context, privacy_result
            )
            
            # Track comprehensive metrics
            self._track_pipeline_metrics(
                context, generation_result, privacy_result, stage_times, total_time
            )
            
            logger.info(
                f"RAG pipeline completed in {total_time:.3f}s: "
                f"privacy_compliant={privacy_result.passed}, "
                f"sources={len(search_results)}, "
                f"cost=${generation_result.estimated_cost:.4f}"
            )
            
            return RAGResponse(
                content=final_response,
                citations=citations,
                privacy_compliant=privacy_result.passed,
                privacy_violations=len(privacy_result.violations),
                total_time=total_time,
                stage_times=stage_times,
                input_tokens=generation_result.input_tokens,
                output_tokens=generation_result.output_tokens,
                estimated_cost=generation_result.estimated_cost,
                sources_used=len(search_results),
                citable_sources=context.citable_count,
                private_sources=context.private_count,
                context_score=context.context_score,
                response_quality_score=response_quality,
                user_satisfaction_predicted=min(response_quality * 1.2, 1.0)
            )
            
        except Exception as e:
            logger.error(f"RAG pipeline failed: {str(e)}")
            
            # Check if it's an OpenAI authentication error for demo mode
            error_str = str(e).lower()
            if (isinstance(e.__class__.__name__, str) and 'embeddinggenerationerror' in e.__class__.__name__.lower()) or \
               any(keyword in error_str for keyword in [
                   'openai authentication failed',
                   'authentication', 
                   'api key',
                   'invalid_api_key',
                   'incorrect api key',
                   '401'
               ]):
                return self._generate_demo_response(user_query, time.time() - start_time)
            
            return self._generate_fallback_response(e, time.time() - start_time)
    
    async def _generate_embedding(self, query: str) -> List[float]:
        """Generate embedding for query."""
        try:
            return await self.embedding_service.generate_embedding(query)
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise
    
    async def _get_default_chatbot_config(self) -> ChatbotConfig:
        """Get default chatbot configuration."""
        from asgiref.sync import sync_to_async
        
        try:
            chatbot = await sync_to_async(Chatbot.objects.get)(id=self.chatbot_id)
            return ChatbotConfig(
                name=chatbot.name,
                description=chatbot.description or "AI Assistant",
                company_name=getattr(chatbot.user, 'organization', {}).get('name', 'our company'),
                temperature=0.7,
                max_response_tokens=500,
                strict_citation_mode=True,
                allow_private_reasoning=True
            )
        except Exception as e:
            logger.warning(f"Failed to get chatbot config: {str(e)}")
            return ChatbotConfig(
                name="AI Assistant",
                description="Helpful AI Assistant",
                company_name="our company"
            )
    
    async def _save_conversation_messages(
        self,
        conversation_id: str,
        user_query: str,
        response: str,
        context: ContextData
    ):
        """Save messages to conversation history."""
        try:
            # Save user message
            ConversationManager.add_message(
                conversation_id=conversation_id,
                role="user",
                content=user_query
            )
            
            # Save assistant response with source metadata
            sources_metadata = [
                {
                    "source_id": source.source_id,
                    "document_id": source.document_id,
                    "citation_text": source.citation_text,
                    "is_citable": source.is_citable
                }
                for source in context.citable_sources
            ]
            
            ConversationManager.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=response,
                sources_used=[s["source_id"] for s in sources_metadata],
                metadata={
                    "sources": sources_metadata,
                    "context_score": context.context_score,
                    "token_count": context.token_count
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to save conversation: {str(e)}")
            # Don't raise - conversation saving shouldn't break pipeline
    
    def _calculate_response_quality(
        self,
        generation_result: GenerationResult,
        context: ContextData,
        privacy_result: FilterResult
    ) -> float:
        """Calculate overall response quality score."""
        # Factors: context quality, privacy compliance, generation success
        context_factor = min(context.context_score, 1.0)
        privacy_factor = 1.0 if privacy_result.passed else 0.5
        generation_factor = 1.0 if generation_result.finish_reason == "stop" else 0.8
        
        # Weighted combination
        quality_score = (
            context_factor * 0.4 +
            privacy_factor * 0.4 +
            generation_factor * 0.2
        )
        
        return min(max(quality_score, 0.0), 1.0)
    
    def _track_pipeline_metrics(
        self,
        context: ContextData,
        generation_result: GenerationResult, 
        privacy_result: FilterResult,
        stage_times: Dict[str, float],
        total_time: float
    ):
        """Track comprehensive pipeline metrics."""
        # Track stage times
        for stage, duration in stage_times.items():
            self.metrics.track_query_latency(stage, duration * 1000)  # Convert to ms
        
        # Track relevance and quality
        self.metrics.track_relevance_score(
            context.search_metadata.get("query", ""),
            generation_result.content,
            context.context_score
        )
        
        # Track privacy metrics
        violation_types = [v.violation_type.value for v in privacy_result.violations]
        self.metrics.track_privacy_violations(len(privacy_result.violations), violation_types)
        
        # Track cost metrics
        self.metrics.track_cost_metrics(
            generation_result.input_tokens,
            generation_result.output_tokens,
            generation_result.estimated_cost
        )
        
        # Track overall pipeline metrics
        track_metric("rag.pipeline.total_time", total_time)
        track_metric("rag.pipeline.success", 1)
        track_metric("rag.pipeline.privacy_compliant", 1 if privacy_result.passed else 0)
    
    def _generate_fallback_response(self, error: Exception, elapsed_time: float) -> RAGResponse:
        """Generate fallback response when pipeline fails."""
        track_metric("rag.pipeline.failure", 1)
        track_metric("rag.pipeline.total_time", elapsed_time)
        
        return RAGResponse(
            content="I apologize, but I'm having trouble generating a response right now. Please try again.",
            citations=[],
            privacy_compliant=True,
            privacy_violations=0,
            total_time=elapsed_time,
            stage_times={},
            input_tokens=0,
            output_tokens=0,
            estimated_cost=0.0,
            sources_used=0,
            citable_sources=0,
            private_sources=0,
            context_score=0.0,
            response_quality_score=0.0,
            user_satisfaction_predicted=0.0
        )
    
    def _generate_demo_response(self, user_query: str, elapsed_time: float) -> RAGResponse:
        """Generate demo response when OpenAI API is not available."""
        track_metric("rag.pipeline.demo_mode", 1)
        track_metric("rag.pipeline.total_time", elapsed_time)
        
        demo_content = (
            f"🤖 **Demo Mode Response**\n\n"
            f"Hello! I received your message: \"{user_query}\"\n\n"
            f"I'm currently running in demo mode because OpenAI API is not configured. "
            f"In a full deployment, I would:\n\n"
            f"• Search through your knowledge base for relevant information\n"
            f"• Use AI to generate a contextual response based on your content\n"
            f"• Provide citations and sources for my answers\n"
            f"• Maintain conversation history and context\n\n"
            f"To enable full functionality, please configure a valid OpenAI API key in your environment settings.\n\n"
            f"*This is a demonstration of the chatbot interface and conversation flow.*"
        )
        
        return RAGResponse(
            content=demo_content,
            citations=[],
            privacy_compliant=True,
            privacy_violations=0,
            total_time=elapsed_time,
            stage_times={"demo_mode": elapsed_time},
            input_tokens=len(user_query.split()),
            output_tokens=len(demo_content.split()),
            estimated_cost=0.0,
            sources_used=0,
            citable_sources=0,
            private_sources=0,
            context_score=1.0,  # Perfect score for demo
            response_quality_score=0.8,  # Good demo quality
            user_satisfaction_predicted=0.7
        )


# Cache for RAG pipeline instances
_rag_pipeline_cache: Dict[str, RAGPipeline] = {}


def get_rag_pipeline(chatbot_id: str) -> RAGPipeline:
    """
    Get or create RAG pipeline for chatbot.
    
    Args:
        chatbot_id: Chatbot ID
        
    Returns:
        RAGPipeline: Pipeline instance
    """
    if chatbot_id not in _rag_pipeline_cache:
        _rag_pipeline_cache[chatbot_id] = RAGPipeline(chatbot_id)
    
    return _rag_pipeline_cache[chatbot_id]


def clear_rag_pipeline_cache():
    """Clear RAG pipeline cache."""
    global _rag_pipeline_cache
    _rag_pipeline_cache.clear()
    logger.info("Cleared RAG pipeline cache")