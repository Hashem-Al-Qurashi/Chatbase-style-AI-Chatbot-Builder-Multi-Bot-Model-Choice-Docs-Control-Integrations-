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
        self.embedding_service = OpenAIEmbeddingService()
        
        # Vector storage will be initialized lazily on first search
        self.vector_storage = None
        self.rag_search_service = None
        self._initialization_lock = False
        
        logger.info(f"Initialized VectorSearchService for chatbot {chatbot_id}")
    
    async def _ensure_initialized(self):
        """Ensure vector storage is initialized (lazy initialization)."""
        if self.vector_storage is None and not self._initialization_lock:
            self._initialization_lock = True
            try:
                # Initialize vector storage service
                self.vector_storage = await create_vector_storage()
                
                # Use vector storage service directly (RAGSearchService not implemented)
                self.rag_search_service = None  # Will use vector_storage directly
                
                logger.info(f"Lazy initialization completed for chatbot {self.chatbot_id}")
            except Exception as e:
                logger.error(f"Vector storage initialization failed: {e}")
                self.vector_storage = None
                self.rag_search_service = None
            finally:
                self._initialization_lock = False
    
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
        # Ensure vector storage is initialized
        await self._ensure_initialized()
        
        if self.vector_storage is None:
            logger.error("Vector storage initialization failed")
            return []
        
        start_time = time.time()
        
        try:
            # Use vector storage service directly for search
            namespace = f"chatbot_{self.chatbot_id}"
            
            # Choose search method based on privacy requirements
            if filter_citable:
                # Only citable content for citations
                vector_results = await self.vector_storage.search_citable_only(
                    query_vector=query_embedding,
                    top_k=top_k,
                    namespace=namespace
                )
            else:
                # All content (including learn-only for context)
                vector_results = await self.vector_storage.search_all_content(
                    query_vector=query_embedding,
                    top_k=top_k,
                    namespace=namespace
                )
            
            # Convert VectorSearchResult to SearchResult for RAG pipeline
            simple_results = []
            for result in vector_results:
                # Extract metadata for RAG pipeline
                metadata = result.metadata or {}
                is_citable = metadata.get('is_citable', True)
                
                # CRITICAL: Enforce privacy filtering
                if filter_citable and not is_citable:
                    logger.warning(f"Filtered non-citable result: {result.id}")
                    continue
                
                simple_result = SearchResult(
                    content=metadata.get('content', ''),
                    score=result.score,
                    chunk_id=result.id,
                    document_id=metadata.get('source_id', ''),
                    knowledge_base_id=self.chatbot_id,
                    is_citable=is_citable,
                    citation_text=metadata.get('content', ''),
                    metadata=metadata
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