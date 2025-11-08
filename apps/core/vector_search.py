"""
Vector search with metadata filtering and citation control.
Implements privacy-aware search with multi-layer access controls.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import logging
import json

from django.core.cache import cache

from apps.core.interfaces import VectorStore, SearchResult
from apps.core.document_processing import PrivacyLevel
from apps.core.circuit_breaker import CircuitBreaker
from chatbot_saas.config import get_settings


settings = get_settings()
logger = logging.getLogger(__name__)


class SearchScope(Enum):
    """Search scope for privacy control."""
    PRIVATE_ONLY = "private_only"          # Only private content for training
    CITABLE_AND_PRIVATE = "citable_private"  # Citable content + private for training
    PUBLIC_ONLY = "public_only"            # Only public content
    ALL = "all"                           # All content (admin/owner only)


@dataclass
class SearchFilter:
    """Search filter criteria."""
    field: str
    operator: str  # eq, ne, in, nin, gte, lte, contains
    value: Any


@dataclass
class SearchConfig:
    """Configuration for vector search."""
    top_k: int = 10
    score_threshold: float = 0.0
    include_metadata: bool = True
    include_content: bool = True
    search_scope: SearchScope = SearchScope.CITABLE_AND_PRIVATE
    enable_reranking: bool = False
    rerank_top_k: int = 50
    
    # Privacy controls
    user_id: Optional[str] = None
    allowed_knowledge_bases: Optional[List[str]] = None
    require_citations: bool = True


@dataclass
class SearchContext:
    """Context for search requests."""
    user_id: str
    knowledge_base_ids: List[str]
    privacy_level: PrivacyLevel
    search_intent: str  # "answer", "research", "training"
    session_id: Optional[str] = None


@dataclass
class SearchResultWithCitation:
    """Search result with citation information."""
    content: str
    score: float
    chunk_id: str
    document_id: str
    knowledge_base_id: str
    privacy_level: PrivacyLevel
    
    # Citation metadata
    can_cite: bool
    citation_text: Optional[str]
    source_title: Optional[str]
    source_author: Optional[str]
    source_url: Optional[str]
    page_number: Optional[int]
    
    # Chunk metadata
    chunk_index: int
    start_char: int
    end_char: int
    metadata: Dict[str, Any]


class PrivacyFilter:
    """Filter for enforcing privacy policies in search."""
    
    @staticmethod
    def create_privacy_filters(
        search_scope: SearchScope,
        user_id: Optional[str] = None,
        knowledge_base_ids: Optional[List[str]] = None
    ) -> List[SearchFilter]:
        """
        Create privacy filters based on search scope.
        
        Args:
            search_scope: Search scope level
            user_id: User ID for ownership checks
            knowledge_base_ids: Allowed knowledge base IDs
            
        Returns:
            List[SearchFilter]: Privacy filters
        """
        filters = []
        
        # Privacy level filters
        if search_scope == SearchScope.PRIVATE_ONLY:
            filters.append(SearchFilter("privacy_level", "eq", "private"))
            if user_id:
                filters.append(SearchFilter("user_id", "eq", user_id))
        
        elif search_scope == SearchScope.CITABLE_AND_PRIVATE:
            filters.append(SearchFilter("privacy_level", "in", ["private", "citable"]))
            if user_id:
                # For private content, must be owner
                filters.append(SearchFilter("access_control", "eq", f"owner:{user_id}"))
        
        elif search_scope == SearchScope.PUBLIC_ONLY:
            filters.append(SearchFilter("privacy_level", "eq", "public"))
        
        elif search_scope == SearchScope.ALL:
            # Admin access - no privacy filters
            pass
        
        # Knowledge base filters
        if knowledge_base_ids:
            filters.append(SearchFilter("knowledge_base_id", "in", knowledge_base_ids))
        
        return filters
    
    @staticmethod
    def can_cite_result(result: SearchResult, user_id: str) -> bool:
        """
        Check if search result can be cited by user.
        
        Args:
            result: Search result
            user_id: User ID
            
        Returns:
            bool: True if result can be cited
        """
        metadata = result.metadata
        privacy_level = metadata.get("privacy_level", "private")
        
        if privacy_level == "public":
            return True
        elif privacy_level == "citable":
            return True
        elif privacy_level == "private":
            # Can only cite if user owns the content
            return metadata.get("user_id") == user_id
        
        return False
    
    @staticmethod
    def sanitize_result_for_privacy(
        result: SearchResult,
        user_id: str,
        require_citations: bool = True
    ) -> Optional[SearchResultWithCitation]:
        """
        Sanitize search result based on privacy requirements.
        
        Args:
            result: Raw search result
            user_id: User ID
            require_citations: Whether citations are required
            
        Returns:
            Optional[SearchResultWithCitation]: Sanitized result or None if not allowed
        """
        metadata = result.metadata
        privacy_level = PrivacyLevel(metadata.get("privacy_level", "private"))
        
        # Check access permissions
        if privacy_level == PrivacyLevel.PRIVATE:
            if metadata.get("user_id") != user_id:
                return None  # No access to private content of other users
        
        # Determine citation capability
        can_cite = PrivacyFilter.can_cite_result(result, user_id)
        
        if require_citations and not can_cite:
            # Content can be used for context but not cited
            content = result.content
            citation_text = None
        else:
            content = result.content
            citation_text = PrivacyFilter._generate_citation_text(result)
        
        return SearchResultWithCitation(
            content=content,
            score=result.score,
            chunk_id=result.id,
            document_id=metadata.get("document_id", ""),
            knowledge_base_id=metadata.get("knowledge_base_id", ""),
            privacy_level=privacy_level,
            can_cite=can_cite,
            citation_text=citation_text,
            source_title=metadata.get("document_title"),
            source_author=metadata.get("document_author"),
            source_url=metadata.get("document_url"),
            page_number=metadata.get("page_number"),
            chunk_index=metadata.get("chunk_index", 0),
            start_char=metadata.get("start_char", 0),
            end_char=metadata.get("end_char", 0),
            metadata=metadata
        )
    
    @staticmethod
    def _generate_citation_text(result: SearchResult) -> str:
        """Generate citation text for a search result."""
        metadata = result.metadata
        
        title = metadata.get("document_title", "Untitled")
        author = metadata.get("document_author")
        url = metadata.get("document_url")
        page = metadata.get("page_number")
        
        citation_parts = [title]
        
        if author:
            citation_parts.append(f"by {author}")
        
        if page:
            citation_parts.append(f"page {page}")
        
        if url:
            citation_parts.append(f"({url})")
        
        return ", ".join(citation_parts)


class SemanticReranker:
    """Rerank search results based on semantic similarity."""
    
    def __init__(self):
        self.model = None
        self._load_reranking_model()
    
    def _load_reranking_model(self):
        """Load reranking model."""
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            logger.info("Loaded semantic reranking model")
        except Exception as e:
            logger.warning(f"Failed to load reranking model: {str(e)}")
    
    async def rerank_results(
        self,
        query: str,
        results: List[SearchResultWithCitation],
        top_k: int
    ) -> List[SearchResultWithCitation]:
        """
        Rerank search results using semantic similarity.
        
        Args:
            query: Search query
            results: Initial search results
            top_k: Number of results to return after reranking
            
        Returns:
            List[SearchResultWithCitation]: Reranked results
        """
        if not self.model or len(results) <= 1:
            return results[:top_k]
        
        try:
            # Prepare query-document pairs
            pairs = [(query, result.content) for result in results]
            
            # Get relevance scores
            scores = await asyncio.get_event_loop().run_in_executor(
                None, self.model.predict, pairs
            )
            
            # Combine with original scores (weighted average)
            for i, result in enumerate(results):
                semantic_score = float(scores[i])
                vector_score = result.score
                
                # Weighted combination (70% semantic, 30% vector)
                combined_score = 0.7 * semantic_score + 0.3 * vector_score
                result.score = combined_score
            
            # Sort by combined score and return top_k
            reranked = sorted(results, key=lambda x: x.score, reverse=True)
            
            logger.info(f"Reranked {len(results)} results using semantic similarity")
            return reranked[:top_k]
            
        except Exception as e:
            logger.error(f"Reranking failed: {str(e)}")
            return results[:top_k]


class VectorSearchEngine:
    """Main vector search engine with privacy controls."""
    
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.reranker = SemanticReranker()
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60,
            expected_exception=Exception
        )
        self.search_cache_ttl = 300  # 5 minutes
    
    async def search(
        self,
        query_vector: List[float],
        query_text: str,
        context: SearchContext,
        config: SearchConfig
    ) -> List[SearchResultWithCitation]:
        """
        Perform privacy-aware vector search.
        
        Args:
            query_vector: Query embedding vector
            query_text: Original query text for reranking
            context: Search context with user info
            config: Search configuration
            
        Returns:
            List[SearchResultWithCitation]: Privacy-filtered search results
        """
        # Generate cache key
        cache_key = self._generate_cache_key(query_vector, context, config)
        
        # Check cache
        if settings.ENABLE_CACHING:
            cached_results = cache.get(cache_key)
            if cached_results:
                logger.debug("Returning cached search results")
                return cached_results
        
        # Create privacy filters
        privacy_filters = PrivacyFilter.create_privacy_filters(
            search_scope=config.search_scope,
            user_id=context.user_id,
            knowledge_base_ids=context.knowledge_base_ids
        )
        
        # Convert to vector store filter format
        vector_filters = self._convert_filters_to_vector_store_format(privacy_filters)
        
        # Determine search parameters
        search_top_k = config.rerank_top_k if config.enable_reranking else config.top_k
        
        try:
            # Perform vector search with circuit breaker
            async def _search():
                return await self.vector_store.search(
                    query_vector=query_vector,
                    top_k=search_top_k,
                    filter_criteria=vector_filters,
                    include_metadata=config.include_metadata,
                    score_threshold=config.score_threshold
                )
            
            raw_results = await self.circuit_breaker.call(_search)
            
            # Apply privacy filtering and sanitization
            sanitized_results = []
            for result in raw_results:
                sanitized = PrivacyFilter.sanitize_result_for_privacy(
                    result,
                    context.user_id,
                    config.require_citations
                )
                if sanitized:
                    sanitized_results.append(sanitized)
            
            # Apply semantic reranking if enabled
            if config.enable_reranking and len(sanitized_results) > 1:
                final_results = await self.reranker.rerank_results(
                    query_text, sanitized_results, config.top_k
                )
            else:
                final_results = sanitized_results[:config.top_k]
            
            # Apply additional filtering based on search intent
            final_results = self._apply_intent_filtering(final_results, context)
            
            # Cache results
            if settings.ENABLE_CACHING:
                cache.set(cache_key, final_results, timeout=self.search_cache_ttl)
            
            logger.info(
                f"Search completed: {len(raw_results)} raw -> "
                f"{len(sanitized_results)} sanitized -> {len(final_results)} final results"
            )
            
            return final_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            raise
    
    async def hybrid_search(
        self,
        query_vector: List[float],
        query_text: str,
        context: SearchContext,
        config: SearchConfig,
        keyword_weight: float = 0.3
    ) -> List[SearchResultWithCitation]:
        """
        Perform hybrid search combining vector and keyword search.
        
        Args:
            query_vector: Query embedding vector
            query_text: Query text for keyword search
            context: Search context
            config: Search configuration
            keyword_weight: Weight for keyword search results
            
        Returns:
            List[SearchResultWithCitation]: Hybrid search results
        """
        # Perform vector search
        vector_results = await self.search(query_vector, query_text, context, config)
        
        # Perform keyword search (simplified implementation)
        keyword_results = await self._keyword_search(query_text, context, config)
        
        # Combine and rerank results
        combined_results = self._combine_search_results(
            vector_results, keyword_results, keyword_weight
        )
        
        return combined_results[:config.top_k]
    
    async def _keyword_search(
        self,
        query_text: str,
        context: SearchContext,
        config: SearchConfig
    ) -> List[SearchResultWithCitation]:
        """Perform keyword-based search."""
        # This is a simplified implementation
        # In practice, you would use Elasticsearch, Solr, or similar
        
        # For now, return empty results
        # TODO: Implement actual keyword search
        return []
    
    def _combine_search_results(
        self,
        vector_results: List[SearchResultWithCitation],
        keyword_results: List[SearchResultWithCitation],
        keyword_weight: float
    ) -> List[SearchResultWithCitation]:
        """Combine vector and keyword search results."""
        # Create a mapping of chunk_id to results
        result_map = {}
        
        # Add vector results
        for result in vector_results:
            result.score = result.score * (1 - keyword_weight)
            result_map[result.chunk_id] = result
        
        # Add or merge keyword results
        for result in keyword_results:
            weighted_score = result.score * keyword_weight
            
            if result.chunk_id in result_map:
                # Combine scores
                result_map[result.chunk_id].score += weighted_score
            else:
                # Add new result
                result.score = weighted_score
                result_map[result.chunk_id] = result
        
        # Sort by combined score
        combined_results = sorted(
            result_map.values(),
            key=lambda x: x.score,
            reverse=True
        )
        
        return combined_results
    
    def _apply_intent_filtering(
        self,
        results: List[SearchResultWithCitation],
        context: SearchContext
    ) -> List[SearchResultWithCitation]:
        """Apply filtering based on search intent."""
        if context.search_intent == "training":
            # For training, we can use all content but don't need citations
            for result in results:
                result.can_cite = False
                result.citation_text = None
        
        elif context.search_intent == "research":
            # For research, prioritize citable content
            citable_results = [r for r in results if r.can_cite]
            non_citable_results = [r for r in results if not r.can_cite]
            return citable_results + non_citable_results
        
        # Default: return as-is
        return results
    
    def _convert_filters_to_vector_store_format(
        self,
        filters: List[SearchFilter]
    ) -> Dict[str, Any]:
        """Convert search filters to vector store format."""
        # This depends on the specific vector store implementation
        # For now, return a generic format
        vector_filters = {}
        
        for filter_item in filters:
            if filter_item.operator == "eq":
                vector_filters[filter_item.field] = {"$eq": filter_item.value}
            elif filter_item.operator == "in":
                vector_filters[filter_item.field] = {"$in": filter_item.value}
            elif filter_item.operator == "ne":
                vector_filters[filter_item.field] = {"$ne": filter_item.value}
            elif filter_item.operator == "gte":
                vector_filters[filter_item.field] = {"$gte": filter_item.value}
            elif filter_item.operator == "lte":
                vector_filters[filter_item.field] = {"$lte": filter_item.value}
        
        return vector_filters
    
    def _generate_cache_key(
        self,
        query_vector: List[float],
        context: SearchContext,
        config: SearchConfig
    ) -> str:
        """Generate cache key for search results."""
        import hashlib
        
        # Create a hash of the search parameters
        cache_data = {
            "query_hash": hashlib.sha256(str(query_vector).encode()).hexdigest()[:16],
            "user_id": context.user_id,
            "knowledge_bases": sorted(context.knowledge_base_ids),
            "privacy_level": context.privacy_level.value,
            "search_scope": config.search_scope.value,
            "top_k": config.top_k,
            "score_threshold": config.score_threshold
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.sha256(cache_string.encode()).hexdigest()[:16]
        
        return f"vector_search:{cache_hash}"


class RAGSearchService:
    """High-level RAG search service."""
    
    def __init__(self, vector_store: VectorStore, embedding_service):
        self.search_engine = VectorSearchEngine(vector_store)
        self.embedding_service = embedding_service
    
    async def search_for_rag(
        self,
        query: str,
        context: SearchContext,
        config: Optional[SearchConfig] = None
    ) -> Tuple[List[SearchResultWithCitation], Dict[str, Any]]:
        """
        Perform search for RAG pipeline.
        
        Args:
            query: Search query
            context: Search context
            config: Optional search configuration
            
        Returns:
            Tuple[List[SearchResultWithCitation], Dict[str, Any]]: Results and metadata
        """
        if config is None:
            config = SearchConfig()
        
        start_time = time.time()
        
        # Generate query embedding
        # Note: This is simplified - in practice you'd use the embedding service
        query_vector = await self._generate_query_embedding(query, context)
        
        # Perform search
        results = await self.search_engine.search(
            query_vector=query_vector,
            query_text=query,
            context=context,
            config=config
        )
        
        search_time = time.time() - start_time
        
        # Generate search metadata
        metadata = {
            "query": query,
            "search_time": search_time,
            "total_results": len(results),
            "search_scope": config.search_scope.value,
            "citable_results": sum(1 for r in results if r.can_cite),
            "privacy_levels": list(set(r.privacy_level.value for r in results)),
            "knowledge_bases": list(set(r.knowledge_base_id for r in results if r.knowledge_base_id))
        }
        
        return results, metadata
    
    async def _generate_query_embedding(
        self,
        query: str,
        context: SearchContext
    ) -> List[float]:
        """Generate embedding for search query."""
        # This is a simplified implementation
        # In practice, you'd use the embedding service with appropriate model
        
        # For now, return a dummy vector
        # TODO: Integrate with actual embedding service
        return [0.0] * 1536  # Ada-002 dimension


# Global search service
# This would be initialized with actual vector store in Django apps.py
search_service = None