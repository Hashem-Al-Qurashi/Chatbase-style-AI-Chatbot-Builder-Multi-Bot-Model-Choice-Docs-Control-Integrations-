"""
Vector Search Service for RAG Pipeline.

Integrates with the existing comprehensive vector search implementation
in apps.core.vector_search to provide privacy-aware search for RAG.

CRITICAL: This service enforces privacy filtering at multiple layers.
"""

import time
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from apps.core.vector_search import (
    VectorSearchEngine, 
    RAGSearchService,
    SearchContext,
    SearchConfig,
    SearchScope,
    SearchResultWithCitation
)
from apps.core.vector_storage import create_vector_storage
from apps.core.embedding_service import OpenAIEmbeddingService
from apps.core.document_processing import PrivacyLevel
from apps.core.monitoring import track_metric
from chatbot_saas.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Simplified search result for RAG pipeline."""
    content: str
    score: float
    chunk_id: str
    document_id: str
    knowledge_base_id: str
    is_citable: bool
    citation_text: Optional[str] = None
    metadata: Dict[str, Any] = None


class VectorSearchService:
    """
    Privacy-aware vector search service for RAG pipeline.
    
    This service wraps the existing VectorSearchEngine with RAG-specific
    functionality and ensures privacy filtering is always applied.
    
    CRITICAL PRIVACY REQUIREMENTS:
    - Only citable sources are returned for citation
    - Private sources can be used for context but never cited
    - User access controls enforced at database level
    """
    
    def __init__(self, chatbot_id: str):
        """
        Initialize vector search service for a specific chatbot.
        
        Args:
            chatbot_id: Chatbot ID for filtering searches
        """
        self.chatbot_id = chatbot_id
        self.vector_storage = None  # Will be initialized async
        self.embedding_service = OpenAIEmbeddingService()
        
        # Initialize the existing search service
        self.rag_search_service = RAGSearchService(
            vector_store=self.vector_storage,
            embedding_service=self.embedding_service
        )
        
        logger.info(f"Initialized VectorSearchService for chatbot {chatbot_id}")
    
    async def search(
        self,
        query_embedding: List[float],
        query_text: str,
        user_id: str,
        top_k: int = 5,
        filter_citable: bool = True,
        score_threshold: float = 0.7,
        enable_reranking: bool = True
    ) -> List[SearchResult]:
        """
        Search for similar vectors with privacy filtering.
        
        Args:
            query_embedding: Query embedding vector
            query_text: Original query text for reranking  
            user_id: User ID for privacy filtering
            top_k: Number of results to return
            filter_citable: If True, only return citable sources
            score_threshold: Minimum similarity score
            enable_reranking: Whether to enable semantic reranking
            
        Returns:
            List[SearchResult]: Privacy-filtered search results
            
        Raises:
            ValueError: If privacy requirements are violated
        """
        start_time = time.time()
        
        try:
            # Create search context with privacy controls
            search_context = SearchContext(
                user_id=user_id,
                knowledge_base_ids=[self.chatbot_id],
                privacy_level=PrivacyLevel.CITABLE if filter_citable else PrivacyLevel.PRIVATE,
                search_intent="answer"  # For RAG responses
            )
            
            # Configure search with privacy scope
            search_scope = SearchScope.CITABLE_AND_PRIVATE if not filter_citable else SearchScope.PUBLIC_ONLY
            
            search_config = SearchConfig(
                top_k=top_k,
                score_threshold=score_threshold,
                search_scope=search_scope,
                enable_reranking=enable_reranking,
                rerank_top_k=min(top_k * 3, 50),  # Get more for reranking
                require_citations=filter_citable
            )
            
            # Perform search using existing service
            detailed_results, search_metadata = await self.rag_search_service.search_for_rag(
                query=query_text,
                context=search_context,
                config=search_config
            )
            
            # Convert to simplified results for RAG pipeline
            simple_results = []
            for result in detailed_results:
                # CRITICAL: Enforce privacy filtering
                if filter_citable and not result.can_cite:
                    logger.warning(f"Filtered non-citable result: {result.chunk_id}")
                    continue
                
                simple_result = SearchResult(
                    content=result.content,
                    score=result.score,
                    chunk_id=result.chunk_id,
                    document_id=result.document_id,
                    knowledge_base_id=result.knowledge_base_id,
                    is_citable=result.can_cite,
                    citation_text=result.citation_text,
                    metadata=result.metadata
                )
                simple_results.append(simple_result)
            
            search_time = time.time() - start_time
            
            # Track metrics
            track_metric("vector_search.latency", search_time)
            track_metric("vector_search.results_count", len(simple_results))
            track_metric("vector_search.citable_count", sum(1 for r in simple_results if r.is_citable))
            
            logger.info(
                f"Vector search completed in {search_time:.3f}s: "
                f"{len(simple_results)} results ({sum(1 for r in simple_results if r.is_citable)} citable)"
            )
            
            return simple_results
            
        except Exception as e:
            logger.error(f"Vector search failed for chatbot {self.chatbot_id}: {str(e)}")
            raise
    
    async def search_with_query_text(
        self,
        query_text: str,
        user_id: str,
        top_k: int = 5,
        filter_citable: bool = True,
        score_threshold: float = 0.7
    ) -> List[SearchResult]:
        """
        Search using query text (will generate embedding automatically).
        
        Args:
            query_text: Search query text
            user_id: User ID for privacy filtering
            top_k: Number of results to return
            filter_citable: If True, only return citable sources
            score_threshold: Minimum similarity score
            
        Returns:
            List[SearchResult]: Privacy-filtered search results
        """
        # Generate query embedding
        query_embedding = await self.embedding_service.generate_embedding(query_text)
        
        return await self.search(
            query_embedding=query_embedding,
            query_text=query_text,
            user_id=user_id,
            top_k=top_k,
            filter_citable=filter_citable,
            score_threshold=score_threshold
        )
    
    async def hybrid_search(
        self,
        query_text: str,
        user_id: str,
        top_k: int = 5,
        filter_citable: bool = True,
        keyword_weight: float = 0.3
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining vector and keyword search.
        
        Args:
            query_text: Search query
            user_id: User ID for privacy filtering
            top_k: Number of results to return
            filter_citable: If True, only return citable sources
            keyword_weight: Weight for keyword search (0.0-1.0)
            
        Returns:
            List[SearchResult]: Hybrid search results
        """
        # Generate query embedding
        query_embedding = await self.embedding_service.generate_embedding(query_text)
        
        # Create search context
        search_context = SearchContext(
            user_id=user_id,
            knowledge_base_ids=[self.chatbot_id],
            privacy_level=PrivacyLevel.CITABLE if filter_citable else PrivacyLevel.PRIVATE,
            search_intent="answer"
        )
        
        # Configure search
        search_scope = SearchScope.CITABLE_AND_PRIVATE if not filter_citable else SearchScope.PUBLIC_ONLY
        search_config = SearchConfig(
            top_k=top_k,
            search_scope=search_scope,
            require_citations=filter_citable
        )
        
        # Perform hybrid search using existing engine
        search_engine = VectorSearchEngine(self.vector_storage)
        detailed_results = await search_engine.hybrid_search(
            query_vector=query_embedding,
            query_text=query_text,
            context=search_context,
            config=search_config,
            keyword_weight=keyword_weight
        )
        
        # Convert to simplified results
        simple_results = []
        for result in detailed_results:
            if filter_citable and not result.can_cite:
                continue
                
            simple_result = SearchResult(
                content=result.content,
                score=result.score,
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                knowledge_base_id=result.knowledge_base_id,
                is_citable=result.can_cite,
                citation_text=result.citation_text,
                metadata=result.metadata
            )
            simple_results.append(simple_result)
        
        return simple_results
    
    def get_backend_info(self) -> Dict[str, Any]:
        """
        Get information about the vector storage backend.
        
        Returns:
            Dict[str, Any]: Backend information
        """
        return {
            "backend_type": type(self.vector_storage).__name__,
            "chatbot_id": self.chatbot_id,
            "settings": {
                "caching_enabled": settings.ENABLE_CACHING,
                "default_top_k": 5,
                "default_score_threshold": 0.7
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of vector search service.
        
        Returns:
            Dict[str, Any]: Health status
        """
        try:
            # Test with a simple query
            test_embedding = [0.1] * 1536  # Test vector
            
            start_time = time.time()
            await self.search(
                query_embedding=test_embedding,
                query_text="health check",
                user_id="system",
                top_k=1,
                filter_citable=False
            )
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time": response_time,
                "backend": type(self.vector_storage).__name__,
                "chatbot_id": self.chatbot_id
            }
            
        except Exception as e:
            logger.error(f"Vector search health check failed: {str(e)}")
            return {
                "status": "unhealthy", 
                "error": str(e),
                "chatbot_id": self.chatbot_id
            }


# Cache for vector search services per chatbot
_search_service_cache: Dict[str, VectorSearchService] = {}


def get_vector_search_service(chatbot_id: str) -> VectorSearchService:
    """
    Get or create vector search service for chatbot.
    
    Args:
        chatbot_id: Chatbot ID
        
    Returns:
        VectorSearchService: Search service instance
    """
    if chatbot_id not in _search_service_cache:
        _search_service_cache[chatbot_id] = VectorSearchService(chatbot_id)
    
    return _search_service_cache[chatbot_id]


def clear_search_service_cache():
    """Clear vector search service cache."""
    global _search_service_cache
    _search_service_cache.clear()
    logger.info("Cleared vector search service cache")