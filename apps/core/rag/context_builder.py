"""
Context Builder for RAG Pipeline.

Builds context from search results for LLM generation while maintaining
strict privacy separation between citable and private sources.

CRITICAL: This module enforces privacy at the context level - 
citable and private sources are clearly separated.
"""

import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .vector_search_service import SearchResult
from apps.core.monitoring import track_metric

logger = logging.getLogger(__name__)


class RankingStrategy(Enum):
    """Ranking strategies for context building."""
    SIMILARITY = "similarity"           # Rank by vector similarity score
    RECENCY = "recency"                # Boost recent documents
    KEYWORD_MATCH = "keyword_match"    # Boost exact keyword matches
    HYBRID = "hybrid"                  # Combine multiple strategies
    SOURCE_DIVERSITY = "source_diversity"  # Maximize source diversity


@dataclass
class ContextSource:
    """Source information for context with privacy controls."""
    content: str
    source_id: str
    document_id: str
    knowledge_base_id: str
    score: float
    is_citable: bool
    citation_text: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass 
class ContextData:
    """Context data with privacy separation."""
    # Context for LLM (clearly marked citable vs private)
    full_context: str
    
    # Separate tracking
    citable_sources: List[ContextSource]
    private_sources: List[ContextSource]
    
    # Metadata
    token_count: int
    total_sources: int
    citable_count: int
    private_count: int
    context_score: float
    
    # For audit logging
    search_metadata: Dict[str, Any]


class TokenCounter:
    """Simple token counter for context management."""
    
    @staticmethod
    def count_tokens(text: str) -> int:
        """
        Count approximate tokens in text.
        
        Args:
            text: Text to count
            
        Returns:
            int: Approximate token count
        """
        # Simple approximation: ~4 characters per token
        # This is conservative for GPT models
        return len(text) // 4
    
    @staticmethod
    def truncate_to_token_limit(text: str, max_tokens: int) -> str:
        """
        Truncate text to fit within token limit.
        
        Args:
            text: Text to truncate
            max_tokens: Maximum tokens allowed
            
        Returns:
            str: Truncated text
        """
        if TokenCounter.count_tokens(text) <= max_tokens:
            return text
        
        # Approximate character limit
        char_limit = max_tokens * 4
        
        # Truncate at word boundary
        if len(text) <= char_limit:
            return text
        
        truncated = text[:char_limit].rsplit(' ', 1)[0]
        return truncated + "..."


class RelevanceRanker:
    """Ranking strategies for search results."""
    
    @staticmethod
    def rank_by_similarity(results: List[SearchResult]) -> List[SearchResult]:
        """
        Rank by vector similarity score.
        
        Args:
            results: Search results to rank
            
        Returns:
            List[SearchResult]: Ranked results
        """
        return sorted(results, key=lambda x: x.score, reverse=True)
    
    @staticmethod
    def rank_by_recency(results: List[SearchResult]) -> List[SearchResult]:
        """
        Boost recent documents.
        
        Args:
            results: Search results to rank
            
        Returns:
            List[SearchResult]: Ranked results with recency boost
        """
        current_time = time.time()
        
        for result in results:
            # Get document timestamp from metadata
            doc_timestamp = result.metadata.get('created_at', current_time) if result.metadata else current_time
            
            # Calculate age in days
            age_days = (current_time - doc_timestamp) / (24 * 3600)
            
            # Apply recency boost (newer documents get higher scores)
            recency_boost = max(0.1, 1.0 - (age_days / 365))  # Boost degrades over a year
            result.score = result.score * recency_boost
        
        return sorted(results, key=lambda x: x.score, reverse=True)
    
    @staticmethod
    def rank_by_keyword_match(results: List[SearchResult], query: str) -> List[SearchResult]:
        """
        Boost results with exact keyword matches.
        
        Args:
            results: Search results to rank
            query: Original search query
            
        Returns:
            List[SearchResult]: Ranked results with keyword boost
        """
        query_words = set(query.lower().split())
        
        for result in results:
            content_words = set(result.content.lower().split())
            
            # Calculate keyword overlap
            overlap = len(query_words.intersection(content_words))
            overlap_ratio = overlap / len(query_words) if query_words else 0
            
            # Apply keyword boost
            keyword_boost = 1.0 + (overlap_ratio * 0.5)  # Up to 50% boost
            result.score = result.score * keyword_boost
        
        return sorted(results, key=lambda x: x.score, reverse=True)
    
    @staticmethod
    def hybrid_rank(results: List[SearchResult], query: str) -> List[SearchResult]:
        """
        Combine multiple ranking strategies.
        
        Args:
            results: Search results to rank
            query: Original search query
            
        Returns:
            List[SearchResult]: Hybrid ranked results
        """
        # Apply keyword ranking first
        results = RelevanceRanker.rank_by_keyword_match(results, query)
        
        # Then apply recency boost
        results = RelevanceRanker.rank_by_recency(results)
        
        # Final sort by combined score
        return sorted(results, key=lambda x: x.score, reverse=True)


class DiversityOptimizer:
    """Optimize diversity in search results."""
    
    @staticmethod
    def maximize_coverage(results: List[SearchResult], max_per_source: int = 2) -> List[SearchResult]:
        """
        Ensure diverse sources in results.
        
        Args:
            results: Search results
            max_per_source: Maximum results per document/source
            
        Returns:
            List[SearchResult]: Diversified results
        """
        source_counts = {}
        diversified_results = []
        
        for result in results:
            source_key = result.document_id
            
            if source_counts.get(source_key, 0) < max_per_source:
                diversified_results.append(result)
                source_counts[source_key] = source_counts.get(source_key, 0) + 1
        
        return diversified_results
    
    @staticmethod
    def remove_redundancy(results: List[SearchResult], similarity_threshold: float = 0.9) -> List[SearchResult]:
        """
        Remove highly similar chunks.
        
        Args:
            results: Search results
            similarity_threshold: Similarity threshold for redundancy
            
        Returns:
            List[SearchResult]: Deduplicated results
        """
        if len(results) <= 1:
            return results
        
        unique_results = [results[0]]  # Always keep the top result
        
        for result in results[1:]:
            is_redundant = False
            
            for unique_result in unique_results:
                # Simple similarity check based on content overlap
                content1_words = set(result.content.lower().split())
                content2_words = set(unique_result.content.lower().split())
                
                if content1_words and content2_words:
                    overlap = len(content1_words.intersection(content2_words))
                    union = len(content1_words.union(content2_words))
                    jaccard_similarity = overlap / union if union > 0 else 0
                    
                    if jaccard_similarity > similarity_threshold:
                        is_redundant = True
                        break
            
            if not is_redundant:
                unique_results.append(result)
        
        return unique_results


class ContextBuilder:
    """
    Build context from search results with privacy controls.
    
    CRITICAL: This class maintains strict separation between citable 
    and private sources for privacy compliance.
    """
    
    def __init__(self, max_context_tokens: int = 3000):
        """
        Initialize context builder.
        
        Args:
            max_context_tokens: Maximum tokens for context
        """
        self.max_tokens = max_context_tokens
        self.token_counter = TokenCounter()
        
        logger.info(f"Initialized ContextBuilder with max_tokens={max_context_tokens}")
    
    def build_context(
        self,
        search_results: List[SearchResult],
        query: str,
        include_private: bool = True,
        ranking_strategy: RankingStrategy = RankingStrategy.HYBRID,
        max_sources: int = 10,
        enable_diversity: bool = True
    ) -> ContextData:
        """
        Build context with clear separation of citable/private sources.
        
        Args:
            search_results: Search results from vector search
            query: Original query for ranking
            include_private: Whether to include private sources for context
            ranking_strategy: Strategy for ranking results
            max_sources: Maximum number of sources to include
            enable_diversity: Whether to optimize for source diversity
            
        Returns:
            ContextData: Built context with privacy separation
        """
        start_time = time.time()
        
        try:
            # Apply ranking strategy
            ranked_results = self._apply_ranking(search_results, query, ranking_strategy)
            
            # Apply diversity optimization if enabled
            if enable_diversity:
                ranked_results = DiversityOptimizer.maximize_coverage(ranked_results)
                ranked_results = DiversityOptimizer.remove_redundancy(ranked_results)
            
            # Limit number of sources
            ranked_results = ranked_results[:max_sources]
            
            # Separate citable and private sources
            citable_sources = []
            private_sources = []
            
            for result in ranked_results:
                context_source = ContextSource(
                    content=result.content,
                    source_id=result.chunk_id,
                    document_id=result.document_id,
                    knowledge_base_id=result.knowledge_base_id,
                    score=result.score,
                    is_citable=result.is_citable,
                    citation_text=result.citation_text,
                    metadata=result.metadata
                )
                
                if result.is_citable:
                    citable_sources.append(context_source)
                else:
                    private_sources.append(context_source)
            
            # Build context string with clear separation
            context_parts = []
            
            # Add citable sources (these can be referenced in responses)
            if citable_sources:
                context_parts.append("CITABLE SOURCES (can be referenced):")
                for i, source in enumerate(citable_sources, 1):
                    # Truncate content for cleaner context (full content in citation)
                    truncated_content = source.content[:500] + "..." if len(source.content) > 500 else source.content
                    context_parts.append(f"[CITABLE-{i}] {truncated_content}")
            
            # Add private sources (for reasoning only, not citation)
            if include_private and private_sources:
                context_parts.append("\nPRIVATE SOURCES (for reasoning only, do not reference):")
                for source in private_sources:
                    context_parts.append(f"[PRIVATE] {source.content}")
            
            # Combine all context
            full_context = "\n\n".join(context_parts)
            
            # Check token limit and truncate if necessary
            token_count = self.token_counter.count_tokens(full_context)
            
            if token_count > self.max_tokens:
                logger.warning(f"Context exceeds token limit ({token_count} > {self.max_tokens}), truncating")
                full_context = self.token_counter.truncate_to_token_limit(full_context, self.max_tokens)
                token_count = self.token_counter.count_tokens(full_context)
            
            # Calculate context quality score
            context_score = self._calculate_context_score(citable_sources + private_sources)
            
            build_time = time.time() - start_time
            
            # Track metrics
            track_metric("context_builder.build_time", build_time)
            track_metric("context_builder.token_count", token_count)
            track_metric("context_builder.citable_count", len(citable_sources))
            track_metric("context_builder.private_count", len(private_sources))
            
            logger.info(
                f"Built context in {build_time:.3f}s: {token_count} tokens, "
                f"{len(citable_sources)} citable, {len(private_sources)} private sources"
            )
            
            return ContextData(
                full_context=full_context,
                citable_sources=citable_sources,
                private_sources=private_sources,
                token_count=token_count,
                total_sources=len(citable_sources) + len(private_sources),
                citable_count=len(citable_sources),
                private_count=len(private_sources),
                context_score=context_score,
                search_metadata={
                    "query": query,
                    "ranking_strategy": ranking_strategy.value,
                    "diversity_enabled": enable_diversity,
                    "max_sources": max_sources,
                    "build_time": build_time
                }
            )
            
        except Exception as e:
            logger.error(f"Context building failed: {str(e)}")
            raise
    
    def _apply_ranking(
        self,
        results: List[SearchResult],
        query: str,
        strategy: RankingStrategy
    ) -> List[SearchResult]:
        """Apply ranking strategy to search results."""
        if strategy == RankingStrategy.SIMILARITY:
            return RelevanceRanker.rank_by_similarity(results)
        elif strategy == RankingStrategy.RECENCY:
            return RelevanceRanker.rank_by_recency(results)
        elif strategy == RankingStrategy.KEYWORD_MATCH:
            return RelevanceRanker.rank_by_keyword_match(results, query)
        elif strategy == RankingStrategy.HYBRID:
            return RelevanceRanker.hybrid_rank(results, query)
        elif strategy == RankingStrategy.SOURCE_DIVERSITY:
            return DiversityOptimizer.maximize_coverage(results)
        else:
            return results  # No ranking
    
    def _calculate_context_score(self, sources: List[ContextSource]) -> float:
        """
        Calculate overall context quality score.
        
        Args:
            sources: Context sources
            
        Returns:
            float: Context quality score (0-1)
        """
        if not sources:
            return 0.0
        
        # Average of source scores, weighted by citability
        total_score = 0.0
        total_weight = 0.0
        
        for source in sources:
            weight = 1.2 if source.is_citable else 1.0  # Boost citable sources
            total_score += source.score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def get_citation_list(self, context_data: ContextData) -> List[str]:
        """
        Get list of citations from context data.
        
        Args:
            context_data: Context data
            
        Returns:
            List[str]: Citation texts
        """
        citations = []
        
        for source in context_data.citable_sources:
            if source.citation_text:
                # Truncate citation text to first 200 chars for readability
                citation = source.citation_text[:200] + "..." if len(source.citation_text) > 200 else source.citation_text
                citations.append(citation)
            else:
                # Generate concise citation from content
                content_preview = source.content[:150] + "..." if len(source.content) > 150 else source.content
                # Clean up whitespace
                content_preview = ' '.join(content_preview.split())
                citations.append(content_preview)
        
        return citations
    
    def validate_context_privacy(self, context_data: ContextData) -> Dict[str, Any]:
        """
        Validate that context maintains privacy separation.
        
        Args:
            context_data: Context data to validate
            
        Returns:
            Dict[str, Any]: Validation results
        """
        issues = []
        
        # Check that private sources are marked as such
        for source in context_data.private_sources:
            if source.is_citable:
                issues.append(f"Private source {source.source_id} marked as citable")
        
        # Check that citable sources are marked correctly
        for source in context_data.citable_sources:
            if not source.is_citable:
                issues.append(f"Citable source {source.source_id} marked as non-citable")
        
        # Check context formatting
        if "PRIVATE" in context_data.full_context and context_data.private_count == 0:
            issues.append("Context contains PRIVATE markers but no private sources tracked")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "citable_count": context_data.citable_count,
            "private_count": context_data.private_count,
            "token_count": context_data.token_count
        }