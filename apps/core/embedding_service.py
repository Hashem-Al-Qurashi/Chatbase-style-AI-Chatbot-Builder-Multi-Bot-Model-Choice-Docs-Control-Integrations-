"""
OpenAI embedding service with enterprise-grade cost optimization and monitoring.
Implements batching, caching, deduplication, and comprehensive error handling.
"""

import hashlib
import time
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import structlog

import openai
from openai import OpenAI
from django.core.cache import cache
from django.utils import timezone
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from chatbot_saas.config import get_settings
from .exceptions import EmbeddingGenerationError
from .circuit_breaker import CircuitBreaker
from .text_chunking import TextChunk
from apps.knowledge.models import KnowledgeChunk

settings = get_settings()
logger = structlog.get_logger()


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    embedding: List[float]
    text_hash: str
    model: str
    dimensions: int
    tokens_used: int
    cached: bool = False
    cost_usd: float = 0.0
    processing_time_ms: int = 0


@dataclass
class BatchEmbeddingResult:
    """Result of batch embedding generation."""
    embeddings: List[EmbeddingResult]
    total_tokens: int
    total_cost_usd: float
    processing_time_ms: int
    cache_hits: int
    api_calls: int
    failed_items: List[Tuple[int, str]] = field(default_factory=list)


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""
    model: str = "text-embedding-ada-002"
    max_batch_size: int = 100  # OpenAI limit for ada-002
    cache_ttl_hours: int = 24 * 7  # 1 week
    enable_caching: bool = True
    enable_deduplication: bool = True
    max_retries: int = 3
    timeout_seconds: int = 30
    cost_per_1k_tokens: float = 0.0001  # ada-002 pricing
    daily_budget_usd: float = 100.0
    enable_circuit_breaker: bool = True
    
    def __post_init__(self):
        """Validate configuration."""
        if self.max_batch_size <= 0 or self.max_batch_size > 2048:
            raise ValueError("Batch size must be between 1 and 2048")
        if self.cost_per_1k_tokens <= 0:
            raise ValueError("Cost per 1k tokens must be positive")


class EmbeddingCache:
    """Intelligent caching for embeddings with deduplication."""
    
    def __init__(self, config: EmbeddingConfig):
        """Initialize cache with configuration."""
        self.config = config
        self.logger = structlog.get_logger().bind(component="EmbeddingCache")
    
    def _get_text_hash(self, text: str, model: str) -> str:
        """Generate hash for text and model combination."""
        content = f"{text}:{model}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get_cached_embedding(self, text: str, model: str) -> Optional[EmbeddingResult]:
        """
        Get cached embedding if available.
        
        Args:
            text: Text to get embedding for
            model: Model used for embedding
            
        Returns:
            EmbeddingResult or None if not cached
        """
        if not self.config.enable_caching:
            return None
        
        text_hash = self._get_text_hash(text, model)
        cache_key = f"embedding:{text_hash}"
        
        try:
            cached_data = cache.get(cache_key)
            if cached_data:
                self.logger.debug(
                    "Embedding cache hit",
                    text_hash=text_hash,
                    model=model
                )
                
                return EmbeddingResult(
                    embedding=cached_data['embedding'],
                    text_hash=text_hash,
                    model=model,
                    dimensions=len(cached_data['embedding']),
                    tokens_used=cached_data['tokens_used'],
                    cached=True,
                    cost_usd=0.0,  # No cost for cached items
                    processing_time_ms=0
                )
        except Exception as e:
            self.logger.warning(
                "Cache retrieval failed",
                error=str(e),
                text_hash=text_hash
            )
        
        return None
    
    def cache_embedding(self, text: str, result: EmbeddingResult) -> None:
        """
        Cache embedding result.
        
        Args:
            text: Original text
            result: Embedding result to cache
        """
        if not self.config.enable_caching:
            return
        
        text_hash = self._get_text_hash(text, result.model)
        cache_key = f"embedding:{text_hash}"
        
        try:
            cache_data = {
                'embedding': result.embedding,
                'tokens_used': result.tokens_used,
                'model': result.model,
                'cached_at': timezone.now().isoformat(),
            }
            
            # Cache for configured TTL
            cache_timeout = self.config.cache_ttl_hours * 3600
            cache.set(cache_key, cache_data, timeout=cache_timeout)
            
            self.logger.debug(
                "Embedding cached",
                text_hash=text_hash,
                model=result.model,
                ttl_hours=self.config.cache_ttl_hours
            )
            
        except Exception as e:
            self.logger.warning(
                "Embedding caching failed",
                error=str(e),
                text_hash=text_hash
            )
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        # This would require custom cache backend for full stats
        # For now, return basic info
        return {
            "cache_enabled": self.config.enable_caching,
            "ttl_hours": self.config.cache_ttl_hours,
        }


class CostTracker:
    """Track embedding generation costs and enforce budgets."""
    
    def __init__(self, config: EmbeddingConfig):
        """Initialize cost tracker."""
        self.config = config
        self.logger = structlog.get_logger().bind(component="CostTracker")
    
    def calculate_cost(self, tokens_used: int) -> float:
        """
        Calculate cost for token usage.
        
        Args:
            tokens_used: Number of tokens used
            
        Returns:
            float: Cost in USD
        """
        return (tokens_used / 1000.0) * self.config.cost_per_1k_tokens
    
    def check_daily_budget(self, additional_cost: float) -> bool:
        """
        Check if additional cost would exceed daily budget.
        
        Args:
            additional_cost: Additional cost to check
            
        Returns:
            bool: True if within budget
        """
        today = timezone.now().date()
        budget_key = f"embedding_cost:{today}"
        
        try:
            current_cost = cache.get(budget_key, 0.0)
            total_cost = current_cost + additional_cost
            
            if total_cost > self.config.daily_budget_usd:
                self.logger.warning(
                    "Daily budget would be exceeded",
                    current_cost=current_cost,
                    additional_cost=additional_cost,
                    total_cost=total_cost,
                    daily_budget=self.config.daily_budget_usd
                )
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Budget check failed",
                error=str(e),
                additional_cost=additional_cost
            )
            # Fail open to avoid blocking operations
            return True
    
    def record_cost(self, cost: float) -> None:
        """
        Record cost usage for budget tracking.
        
        Args:
            cost: Cost to record in USD
        """
        today = timezone.now().date()
        budget_key = f"embedding_cost:{today}"
        
        try:
            current_cost = cache.get(budget_key, 0.0)
            new_cost = current_cost + cost
            
            # Cache until end of day
            cache.set(budget_key, new_cost, timeout=86400)
            
            self.logger.info(
                "Cost recorded",
                cost=cost,
                daily_total=new_cost,
                budget=self.config.daily_budget_usd,
                budget_used_percent=(new_cost / self.config.daily_budget_usd) * 100
            )
            
        except Exception as e:
            self.logger.error(
                "Cost recording failed",
                error=str(e),
                cost=cost
            )
    
    def get_daily_usage(self) -> Dict[str, float]:
        """Get daily cost usage statistics."""
        today = timezone.now().date()
        budget_key = f"embedding_cost:{today}"
        
        try:
            current_cost = cache.get(budget_key, 0.0)
            return {
                "daily_cost": current_cost,
                "daily_budget": self.config.daily_budget_usd,
                "budget_used_percent": (current_cost / self.config.daily_budget_usd) * 100,
                "budget_remaining": self.config.daily_budget_usd - current_cost,
            }
        except Exception:
            return {
                "daily_cost": 0.0,
                "daily_budget": self.config.daily_budget_usd,
                "budget_used_percent": 0.0,
                "budget_remaining": self.config.daily_budget_usd,
            }


class OpenAIEmbeddingService:
    """
    OpenAI embedding service with enterprise features.
    
    Features:
    - Batch processing for cost optimization
    - Intelligent caching and deduplication
    - Rate limiting and circuit breaker
    - Cost tracking and budget enforcement
    - Comprehensive error handling and retry logic
    """
    
    def __init__(self, config: EmbeddingConfig = None):
        """
        Initialize embedding service.
        
        Args:
            config: Service configuration
        """
        self.config = config or EmbeddingConfig()
        self.logger = structlog.get_logger().bind(component="OpenAIEmbeddingService")
        
        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=self.config.timeout_seconds,
            max_retries=0  # We handle retries ourselves
        )
        
        # Initialize components
        self.cache = EmbeddingCache(self.config)
        self.cost_tracker = CostTracker(self.config)
        
        # Initialize circuit breaker
        if self.config.enable_circuit_breaker:
            self.circuit_breaker = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60,
                expected_exception=openai.RateLimitError
            )
        else:
            self.circuit_breaker = None
        
        self.logger.info(
            "OpenAI embedding service initialized",
            model=self.config.model,
            max_batch_size=self.config.max_batch_size,
            caching_enabled=self.config.enable_caching,
            circuit_breaker_enabled=self.config.enable_circuit_breaker
        )
    
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            EmbeddingResult: Generated embedding
            
        Raises:
            EmbeddingGenerationError: If generation fails
        """
        if not text.strip():
            raise EmbeddingGenerationError("Text cannot be empty")
        
        # Validate text length (OpenAI limit is ~8192 tokens, roughly 32k characters)
        if len(text) > 32000:
            raise EmbeddingGenerationError(
                f"Text too long ({len(text)} chars). Maximum supported: 32,000 characters. "
                "Consider chunking the text into smaller pieces."
            )
        
        # Check cache first
        cached_result = self.cache.get_cached_embedding(text, self.config.model)
        if cached_result:
            return cached_result
        
        # Generate new embedding
        batch_result = await self.generate_embeddings_batch([text])
        
        if not batch_result.embeddings:
            raise EmbeddingGenerationError("Failed to generate embedding")
        
        return batch_result.embeddings[0]
    
    async def generate_embeddings_batch(self, texts: List[str]) -> BatchEmbeddingResult:
        """
        Generate embeddings for multiple texts with optimization.
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            BatchEmbeddingResult: Batch generation results
            
        Raises:
            EmbeddingGenerationError: If batch generation fails
        """
        if not texts:
            return BatchEmbeddingResult(
                embeddings=[],
                total_tokens=0,
                total_cost_usd=0.0,
                processing_time_ms=0,
                cache_hits=0,
                api_calls=0
            )
        
        # Validate text lengths
        for i, text in enumerate(texts):
            if not text.strip():
                raise EmbeddingGenerationError(f"Text at index {i} cannot be empty")
            if len(text) > 32000:
                raise EmbeddingGenerationError(
                    f"Text at index {i} too long ({len(text)} chars). "
                    "Maximum supported: 32,000 characters."
                )
        
        start_time = time.time()
        
        self.logger.info(
            "Starting batch embedding generation",
            batch_size=len(texts),
            model=self.config.model
        )
        
        try:
            # Deduplicate and check cache
            unique_texts, text_mapping = self._deduplicate_texts(texts)
            cached_results, uncached_texts = await self._get_cached_embeddings(unique_texts)
            
            # Process uncached texts in batches
            api_results = []
            actual_api_calls = 0
            if uncached_texts:
                api_results, actual_api_calls = await self._process_uncached_texts(uncached_texts)
                
                # Check if we got results for uncached texts (critical for detecting auth failures)
                if not api_results and uncached_texts:
                    raise EmbeddingGenerationError(
                        f"Failed to generate embeddings for {len(uncached_texts)} texts. "
                        "This likely indicates an authentication or API connectivity issue."
                    )
            
            # Combine cached and new results
            all_results = {**cached_results}
            for result in api_results:
                text_hash = result.text_hash
                all_results[text_hash] = result
                # Cache new results
                # Note: We need the original text to cache, but we have the hash
                # In a real implementation, we'd maintain the text-hash mapping
            
            # Map results back to original order
            final_embeddings = []
            for original_text in texts:
                text_hash = self.cache._get_text_hash(original_text, self.config.model)
                if text_hash in all_results:
                    final_embeddings.append(all_results[text_hash])
                else:
                    # This shouldn't happen, but handle gracefully
                    self.logger.warning(
                        "Missing embedding result for text",
                        text_hash=text_hash
                    )
            
            # Calculate totals
            total_tokens = sum(r.tokens_used for r in final_embeddings)
            total_cost = sum(r.cost_usd for r in final_embeddings)
            cache_hits = sum(1 for r in final_embeddings if r.cached)
            api_calls = actual_api_calls  # Use actual API call count, not result count
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Record costs
            if total_cost > 0:
                self.cost_tracker.record_cost(total_cost)
            
            result = BatchEmbeddingResult(
                embeddings=final_embeddings,
                total_tokens=total_tokens,
                total_cost_usd=total_cost,
                processing_time_ms=processing_time_ms,
                cache_hits=cache_hits,
                api_calls=api_calls
            )
            
            self.logger.info(
                "Batch embedding generation completed",
                total_embeddings=len(final_embeddings),
                total_tokens=total_tokens,
                total_cost_usd=total_cost,
                cache_hits=cache_hits,
                api_calls=api_calls,
                processing_time_ms=processing_time_ms
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Batch embedding generation failed",
                error=str(e),
                error_type=type(e).__name__,
                batch_size=len(texts)
            )
            raise EmbeddingGenerationError(f"Batch embedding generation failed: {str(e)}")
    
    def _deduplicate_texts(self, texts: List[str]) -> Tuple[List[str], Dict[str, List[int]]]:
        """
        Deduplicate texts to avoid generating embeddings for identical content.
        
        Args:
            texts: List of texts to deduplicate
            
        Returns:
            Tuple of unique texts and mapping from text to original indices
        """
        if not self.config.enable_deduplication:
            return texts, {text: [i] for i, text in enumerate(texts)}
        
        text_to_indices = {}
        unique_texts = []
        
        for i, text in enumerate(texts):
            if text not in text_to_indices:
                text_to_indices[text] = []
                unique_texts.append(text)
            text_to_indices[text].append(i)
        
        dedup_savings = len(texts) - len(unique_texts)
        if dedup_savings > 0:
            self.logger.info(
                "Text deduplication applied",
                original_count=len(texts),
                unique_count=len(unique_texts),
                duplicates_removed=dedup_savings
            )
        
        return unique_texts, text_to_indices
    
    async def _get_cached_embeddings(self, texts: List[str]) -> Tuple[Dict[str, EmbeddingResult], List[str]]:
        """
        Check cache for existing embeddings.
        
        Args:
            texts: List of texts to check
            
        Returns:
            Tuple of cached results and uncached texts
        """
        cached_results = {}
        uncached_texts = []
        
        for text in texts:
            cached = self.cache.get_cached_embedding(text, self.config.model)
            if cached:
                text_hash = self.cache._get_text_hash(text, self.config.model)
                cached_results[text_hash] = cached
            else:
                uncached_texts.append(text)
        
        cache_hit_rate = len(cached_results) / len(texts) if texts else 0
        self.logger.info(
            "Cache check completed",
            total_texts=len(texts),
            cache_hits=len(cached_results),
            cache_misses=len(uncached_texts),
            cache_hit_rate=cache_hit_rate
        )
        
        return cached_results, uncached_texts
    
    async def _process_uncached_texts(self, texts: List[str]) -> Tuple[List[EmbeddingResult], int]:
        """
        Process uncached texts through OpenAI API.
        
        Args:
            texts: List of texts to process
            
        Returns:
            Tuple of (embedding results, actual API calls made)
        """
        if not texts:
            return [], 0
        
        # Split into batches
        batches = [
            texts[i:i + self.config.max_batch_size]
            for i in range(0, len(texts), self.config.max_batch_size)
        ]
        
        all_results = []
        api_calls_made = 0
        
        for batch_idx, batch in enumerate(batches):
            self.logger.info(
                "Processing batch",
                batch_index=batch_idx + 1,
                total_batches=len(batches),
                batch_size=len(batch)
            )
            
            try:
                batch_results = await self._call_openai_api(batch)
                all_results.extend(batch_results)
                api_calls_made += 1  # Count actual API calls, not results
                
                # Add small delay between batches to respect rate limits
                if batch_idx < len(batches) - 1:
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                self.logger.error(
                    "Batch processing failed",
                    batch_index=batch_idx + 1,
                    error=str(e)
                )
                
                # For critical errors like authentication, fail immediately
                if (isinstance(e, openai.AuthenticationError) or 
                    "401" in str(e) or 
                    "authentication" in str(e).lower() or
                    "api key" in str(e).lower()):
                    raise EmbeddingGenerationError(f"OpenAI authentication failed: {str(e)}")
                
                # For other errors, continue with other batches
                continue
        
        return all_results, api_calls_made
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError)),
        before_sleep=before_sleep_log(logger, logging.INFO)
    )
    async def _call_openai_api(self, batch: List[str]) -> List[EmbeddingResult]:
        """
        Make API call to OpenAI with retry logic.
        
        Args:
            batch: Batch of texts to process
            
        Returns:
            List of embedding results
        """
        start_time = time.time()
        
        # Check budget before making API call
        estimated_tokens = sum(len(text.split()) * 1.3 for text in batch)  # Rough estimate
        estimated_cost = self.cost_tracker.calculate_cost(estimated_tokens)
        
        if not self.cost_tracker.check_daily_budget(estimated_cost):
            raise EmbeddingGenerationError("Daily budget exceeded")
        
        # Use circuit breaker if enabled
        if self.circuit_breaker:
            response = await self.circuit_breaker.call(
                lambda: self.client.embeddings.create(
                    input=batch,
                    model=self.config.model
                )
            )
        else:
            response = await asyncio.to_thread(
                self.client.embeddings.create,
                input=batch,
                model=self.config.model
            )
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Process response
        results = []
        for i, embedding_data in enumerate(response.data):
            text = batch[i]
            text_hash = self.cache._get_text_hash(text, self.config.model)
            tokens_used = response.usage.total_tokens // len(batch)  # Approximate per item
            cost = self.cost_tracker.calculate_cost(tokens_used)
            
            result = EmbeddingResult(
                embedding=embedding_data.embedding,
                text_hash=text_hash,
                model=self.config.model,
                dimensions=len(embedding_data.embedding),
                tokens_used=tokens_used,
                cached=False,
                cost_usd=cost,
                processing_time_ms=processing_time_ms
            )
            
            # Cache the result
            self.cache.cache_embedding(text, result)
            
            results.append(result)
        
        self.logger.info(
            "OpenAI API call successful",
            batch_size=len(batch),
            total_tokens=response.usage.total_tokens,
            cost_usd=sum(r.cost_usd for r in results),
            processing_time_ms=processing_time_ms
        )
        
        return results
    
    async def generate_embeddings_for_chunks(self, chunks: List[TextChunk]) -> List[Tuple[TextChunk, EmbeddingResult]]:
        """
        Generate embeddings for text chunks.
        
        Args:
            chunks: List of text chunks
            
        Returns:
            List of (chunk, embedding_result) tuples
        """
        if not chunks:
            return []
        
        texts = [chunk.content for chunk in chunks]
        batch_result = await self.generate_embeddings_batch(texts)
        
        # Pair chunks with their embeddings
        chunk_embeddings = []
        for i, chunk in enumerate(chunks):
            if i < len(batch_result.embeddings):
                chunk_embeddings.append((chunk, batch_result.embeddings[i]))
            else:
                self.logger.warning(
                    "Missing embedding for chunk",
                    chunk_id=chunk.chunk_id
                )
        
        return chunk_embeddings
    
    async def generate_embeddings_for_knowledge_chunks(
        self, 
        knowledge_chunks: List[KnowledgeChunk],
        update_db: bool = True
    ) -> List[Tuple[KnowledgeChunk, EmbeddingResult]]:
        """
        Generate embeddings for KnowledgeChunk models.
        
        Args:
            knowledge_chunks: List of KnowledgeChunk instances
            update_db: Whether to update the database with embeddings
            
        Returns:
            List of (chunk, embedding_result) tuples
        """
        if not knowledge_chunks:
            return []
        
        self.logger.info(
            "Generating embeddings for knowledge chunks",
            chunk_count=len(knowledge_chunks),
            update_db=update_db
        )
        
        # Extract texts and check for existing embeddings
        chunks_to_process = []
        existing_embeddings = {}
        
        for chunk in knowledge_chunks:
            # Check if chunk already has an embedding
            if chunk.embedding_vector and not update_db:
                # Create mock EmbeddingResult for existing embedding
                existing_embeddings[chunk.id] = EmbeddingResult(
                    embedding=chunk.embedding_vector,
                    text_hash=chunk.content_hash,
                    model=chunk.embedding_model or self.config.model,
                    dimensions=len(chunk.embedding_vector),
                    tokens_used=chunk.token_count,
                    cached=True,
                    cost_usd=0.0,
                    processing_time_ms=0
                )
            else:
                chunks_to_process.append(chunk)
        
        # Generate embeddings for chunks that need them
        new_embeddings = {}
        if chunks_to_process:
            texts = [chunk.content for chunk in chunks_to_process]
            batch_result = await self.generate_embeddings_batch(texts)
            
            # Map results back to chunks
            for i, chunk in enumerate(chunks_to_process):
                if i < len(batch_result.embeddings):
                    new_embeddings[chunk.id] = batch_result.embeddings[i]
        
        # Update database if requested
        if update_db and new_embeddings:
            await self._update_knowledge_chunks_with_embeddings(
                chunks_to_process, new_embeddings
            )
        
        # Combine results
        results = []
        for chunk in knowledge_chunks:
            if chunk.id in existing_embeddings:
                results.append((chunk, existing_embeddings[chunk.id]))
            elif chunk.id in new_embeddings:
                results.append((chunk, new_embeddings[chunk.id]))
            else:
                self.logger.warning(
                    "Missing embedding for knowledge chunk",
                    chunk_id=str(chunk.id)
                )
        
        return results
    
    async def _update_knowledge_chunks_with_embeddings(
        self,
        chunks: List[KnowledgeChunk],
        embeddings: Dict[str, EmbeddingResult]
    ) -> None:
        """
        Update KnowledgeChunk models with generated embeddings.
        
        Args:
            chunks: List of KnowledgeChunk instances
            embeddings: Mapping of chunk_id to EmbeddingResult
        """
        import asyncio
        from django.db import transaction
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def update_chunk_sync(chunk: KnowledgeChunk, embedding: EmbeddingResult):
            """Update a single chunk in sync context."""
            with transaction.atomic():
                chunk.embedding_vector = embedding.embedding
                chunk.embedding_model = embedding.model
                chunk.save(update_fields=['embedding_vector', 'embedding_model'])
                
                self.logger.debug(
                    "Updated chunk with embedding",
                    chunk_id=str(chunk.id),
                    model=embedding.model,
                    dimensions=embedding.dimensions,
                    is_citable=chunk.is_citable
                )
        
        # Update chunks sequentially to avoid database concurrency issues
        updated_count = 0
        for chunk in chunks:
            if chunk.id in embeddings:
                await update_chunk_sync(chunk, embeddings[chunk.id])
                updated_count += 1
        
        if updated_count > 0:
            self.logger.info(
                "Updated knowledge chunks with embeddings",
                updated_count=updated_count
            )
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics and health information."""
        return {
            "config": {
                "model": self.config.model,
                "max_batch_size": self.config.max_batch_size,
                "caching_enabled": self.config.enable_caching,
                "deduplication_enabled": self.config.enable_deduplication,
                "circuit_breaker_enabled": self.config.enable_circuit_breaker,
            },
            "cost_tracking": self.cost_tracker.get_daily_usage(),
            "cache_stats": self.cache.get_cache_stats(),
            "circuit_breaker": {
                "enabled": self.config.enable_circuit_breaker,
                "state": self.circuit_breaker.state.name if self.circuit_breaker else "N/A",
            } if self.circuit_breaker else {"enabled": False},
        }


# Global service instance
_embedding_service = None


def get_embedding_service() -> OpenAIEmbeddingService:
    """Get global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = OpenAIEmbeddingService()
    return _embedding_service


# Convenience functions
async def generate_embedding(text: str) -> EmbeddingResult:
    """Generate embedding for a single text."""
    service = get_embedding_service()
    return await service.generate_embedding(text)


async def generate_embeddings(texts: List[str]) -> BatchEmbeddingResult:
    """Generate embeddings for multiple texts."""
    service = get_embedding_service()
    return await service.generate_embeddings_batch(texts)


async def generate_embeddings_for_knowledge_chunks(
    knowledge_chunks: List[KnowledgeChunk],
    update_db: bool = True
) -> List[Tuple[KnowledgeChunk, EmbeddingResult]]:
    """Generate embeddings for KnowledgeChunk models."""
    service = get_embedding_service()
    return await service.generate_embeddings_for_knowledge_chunks(knowledge_chunks, update_db)