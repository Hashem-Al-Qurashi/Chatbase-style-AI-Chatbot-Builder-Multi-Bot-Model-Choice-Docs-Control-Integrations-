"""
Embedding generation with caching and privacy controls.
Implements multi-provider support and efficient batch processing.
"""

import asyncio
import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import logging

import numpy as np
from django.core.cache import cache
from django.utils import timezone

from apps.core.interfaces import LLMProvider, EmbeddingResult
from apps.core.document_processing import DocumentChunk, PrivacyLevel
from apps.core.circuit_breaker import CircuitBreaker
from chatbot_saas.config import get_settings


settings = get_settings()
logger = logging.getLogger(__name__)


class EmbeddingProvider(Enum):
    """Available embedding providers."""
    OPENAI = "openai"
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    HUGGINGFACE = "huggingface"


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""
    provider: EmbeddingProvider
    model: str
    dimension: int
    batch_size: int = 100
    cache_ttl: int = 86400  # 24 hours
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_caching: bool = True


@dataclass
class EmbeddingBatch:
    """Batch of embeddings with metadata."""
    embeddings: List[List[float]]
    chunks: List[DocumentChunk]
    metadata: Dict[str, Any]
    processing_time: float
    provider: str
    model: str


class EmbeddingCache:
    """Cache layer for embeddings with privacy controls."""
    
    def __init__(self, ttl: int = 86400):
        self.ttl = ttl
        self.cache_prefix = "embedding"
    
    def get_cache_key(
        self,
        content: str,
        model: str,
        privacy_level: PrivacyLevel
    ) -> str:
        """Generate cache key for embedding."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        return f"{self.cache_prefix}:{model}:{privacy_level.value}:{content_hash}"
    
    def get_embedding(
        self,
        content: str,
        model: str,
        privacy_level: PrivacyLevel
    ) -> Optional[List[float]]:
        """Get cached embedding."""
        if not settings.ENABLE_CACHING:
            return None
        
        cache_key = self.get_cache_key(content, model, privacy_level)
        cached_result = cache.get(cache_key)
        
        if cached_result:
            logger.debug(f"Cache hit for embedding: {cache_key[:50]}...")
            return cached_result["embedding"]
        
        return None
    
    def set_embedding(
        self,
        content: str,
        model: str,
        privacy_level: PrivacyLevel,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Cache embedding with metadata."""
        if not settings.ENABLE_CACHING:
            return
        
        cache_key = self.get_cache_key(content, model, privacy_level)
        cache_data = {
            "embedding": embedding,
            "model": model,
            "privacy_level": privacy_level.value,
            "cached_at": timezone.now().isoformat(),
            "metadata": metadata or {}
        }
        
        cache.set(cache_key, cache_data, timeout=self.ttl)
        logger.debug(f"Cached embedding: {cache_key[:50]}...")
    
    def invalidate_document_embeddings(self, document_hash: str) -> None:
        """Invalidate all embeddings for a document."""
        # Note: This is a simplified implementation
        # In production, you might want to track cache keys per document
        logger.info(f"Invalidating embeddings for document: {document_hash}")


class OpenAIEmbeddingProvider:
    """OpenAI embedding provider implementation."""
    
    def __init__(self, api_key: str, model: str = "text-embedding-ada-002"):
        self.api_key = api_key
        self.model = model
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception
        )
    
    async def generate_embeddings(
        self,
        texts: List[str],
        **kwargs
    ) -> List[EmbeddingResult]:
        """Generate embeddings using OpenAI API."""
        try:
            import openai
            
            client = openai.AsyncClient(api_key=self.api_key)
            
            @self.circuit_breaker
            async def _call_api():
                response = await client.embeddings.create(
                    input=texts,
                    model=self.model,
                    **kwargs
                )
                return response
            
            response = await _call_api()
            
            results = []
            for i, embedding_data in enumerate(response.data):
                result = EmbeddingResult(
                    embedding=embedding_data.embedding,
                    token_count=response.usage.total_tokens // len(texts),  # Approximate
                    model=self.model,
                    metadata={
                        "provider": "openai",
                        "total_tokens": response.usage.total_tokens,
                        "index": i
                    }
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {str(e)}")
            raise


class SentenceTransformerProvider:
    """Sentence Transformers embedding provider."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the sentence transformer model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded SentenceTransformer model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer model: {str(e)}")
            self.model = None
    
    async def generate_embeddings(
        self,
        texts: List[str],
        **kwargs
    ) -> List[EmbeddingResult]:
        """Generate embeddings using SentenceTransformers."""
        if not self.model:
            raise RuntimeError("SentenceTransformer model not loaded")
        
        try:
            # Generate embeddings (this is synchronous, but we'll run it in executor)
            embeddings = await asyncio.get_event_loop().run_in_executor(
                None, self.model.encode, texts
            )
            
            results = []
            for i, embedding in enumerate(embeddings):
                # Estimate token count (rough approximation)
                token_count = len(texts[i].split()) * 1.3  # Rough token estimation
                
                result = EmbeddingResult(
                    embedding=embedding.tolist(),
                    token_count=int(token_count),
                    model=self.model_name,
                    metadata={
                        "provider": "sentence_transformers",
                        "dimension": len(embedding),
                        "index": i
                    }
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"SentenceTransformer embedding generation failed: {str(e)}")
            raise


class EmbeddingGenerator:
    """Main embedding generator with multi-provider support."""
    
    def __init__(self):
        self.cache = EmbeddingCache(ttl=settings.CACHE_TTL_SECONDS)
        self.providers = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available embedding providers."""
        # OpenAI provider
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            self.providers[EmbeddingProvider.OPENAI] = OpenAIEmbeddingProvider(
                api_key=settings.OPENAI_API_KEY
            )
        
        # SentenceTransformers provider
        try:
            self.providers[EmbeddingProvider.SENTENCE_TRANSFORMERS] = SentenceTransformerProvider()
        except Exception as e:
            logger.warning(f"SentenceTransformers provider not available: {str(e)}")
    
    async def generate_chunk_embeddings(
        self,
        chunks: List[DocumentChunk],
        config: EmbeddingConfig
    ) -> EmbeddingBatch:
        """
        Generate embeddings for document chunks.
        
        Args:
            chunks: List of document chunks
            config: Embedding configuration
            
        Returns:
            EmbeddingBatch: Generated embeddings with metadata
        """
        start_time = time.time()
        
        # Check if provider is available
        if config.provider not in self.providers:
            raise ValueError(f"Embedding provider {config.provider} not available")
        
        provider = self.providers[config.provider]
        
        # Prepare texts and check cache
        texts_to_embed = []
        cached_embeddings = []
        chunk_indices = []
        
        for i, chunk in enumerate(chunks):
            # Check cache first
            cached_embedding = self.cache.get_embedding(
                chunk.content, config.model, chunk.privacy_level
            )
            
            if cached_embedding:
                cached_embeddings.append((i, cached_embedding))
            else:
                texts_to_embed.append(chunk.content)
                chunk_indices.append(i)
        
        # Generate embeddings for non-cached texts
        embeddings = [None] * len(chunks)
        
        # Fill in cached embeddings
        for chunk_idx, embedding in cached_embeddings:
            embeddings[chunk_idx] = embedding
        
        # Generate missing embeddings in batches
        if texts_to_embed:
            for batch_start in range(0, len(texts_to_embed), config.batch_size):
                batch_end = min(batch_start + config.batch_size, len(texts_to_embed))
                batch_texts = texts_to_embed[batch_start:batch_end]
                batch_indices = chunk_indices[batch_start:batch_end]
                
                # Generate embeddings for batch
                embedding_results = await self._generate_with_retry(
                    provider, batch_texts, config
                )
                
                # Store results and cache
                for j, result in enumerate(embedding_results):
                    chunk_idx = batch_indices[j]
                    chunk = chunks[chunk_idx]
                    
                    embeddings[chunk_idx] = result.embedding
                    
                    # Cache the embedding
                    self.cache.set_embedding(
                        chunk.content,
                        config.model,
                        chunk.privacy_level,
                        result.embedding,
                        metadata=result.metadata
                    )
        
        processing_time = time.time() - start_time
        
        # Create batch result
        batch = EmbeddingBatch(
            embeddings=embeddings,
            chunks=chunks,
            metadata={
                "total_chunks": len(chunks),
                "cached_chunks": len(cached_embeddings),
                "generated_chunks": len(texts_to_embed),
                "batch_count": (len(texts_to_embed) + config.batch_size - 1) // config.batch_size,
                "model": config.model,
                "dimension": config.dimension
            },
            processing_time=processing_time,
            provider=config.provider.value,
            model=config.model
        )
        
        logger.info(
            f"Generated embeddings for {len(chunks)} chunks "
            f"({len(cached_embeddings)} cached, {len(texts_to_embed)} generated) "
            f"in {processing_time:.2f}s"
        )
        
        return batch
    
    async def _generate_with_retry(
        self,
        provider: Union[OpenAIEmbeddingProvider, SentenceTransformerProvider],
        texts: List[str],
        config: EmbeddingConfig
    ) -> List[EmbeddingResult]:
        """Generate embeddings with retry logic."""
        last_exception = None
        
        for attempt in range(config.max_retries):
            try:
                return await provider.generate_embeddings(texts)
                
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Embedding generation attempt {attempt + 1} failed: {str(e)}"
                )
                
                if attempt < config.max_retries - 1:
                    await asyncio.sleep(config.retry_delay * (2 ** attempt))
        
        logger.error(f"All embedding generation attempts failed: {str(last_exception)}")
        raise last_exception
    
    def get_available_providers(self) -> List[EmbeddingProvider]:
        """Get list of available embedding providers."""
        return list(self.providers.keys())
    
    def get_provider_info(self, provider: EmbeddingProvider) -> Dict[str, Any]:
        """Get information about a provider."""
        if provider not in self.providers:
            return {"available": False}
        
        provider_obj = self.providers[provider]
        
        if isinstance(provider_obj, OpenAIEmbeddingProvider):
            return {
                "available": True,
                "type": "openai",
                "model": provider_obj.model,
                "dimension": 1536,  # Ada-002 dimension
                "max_tokens": 8192
            }
        elif isinstance(provider_obj, SentenceTransformerProvider):
            return {
                "available": bool(provider_obj.model),
                "type": "sentence_transformers",
                "model": provider_obj.model_name,
                "dimension": 384,  # MiniLM dimension
                "max_tokens": 512
            }
        
        return {"available": False}


class PrivacyAwareEmbeddingService:
    """Service for generating embeddings with privacy controls."""
    
    def __init__(self):
        self.generator = EmbeddingGenerator()
        self.default_configs = {
            PrivacyLevel.PRIVATE: EmbeddingConfig(
                provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
                model="all-MiniLM-L6-v2",
                dimension=384,
                cache_ttl=3600  # Shorter cache for private content
            ),
            PrivacyLevel.CITABLE: EmbeddingConfig(
                provider=EmbeddingProvider.OPENAI,
                model="text-embedding-ada-002",
                dimension=1536,
                cache_ttl=86400
            ),
            PrivacyLevel.PUBLIC: EmbeddingConfig(
                provider=EmbeddingProvider.OPENAI,
                model="text-embedding-ada-002",
                dimension=1536,
                cache_ttl=86400
            )
        }
    
    async def process_document_chunks(
        self,
        chunks: List[DocumentChunk],
        override_config: Optional[EmbeddingConfig] = None
    ) -> Dict[PrivacyLevel, EmbeddingBatch]:
        """
        Process chunks grouped by privacy level.
        
        Args:
            chunks: Document chunks to process
            override_config: Optional config override
            
        Returns:
            Dict[PrivacyLevel, EmbeddingBatch]: Embeddings grouped by privacy level
        """
        # Group chunks by privacy level
        chunks_by_privacy = {}
        for chunk in chunks:
            if chunk.privacy_level not in chunks_by_privacy:
                chunks_by_privacy[chunk.privacy_level] = []
            chunks_by_privacy[chunk.privacy_level].append(chunk)
        
        # Process each privacy level separately
        results = {}
        
        for privacy_level, privacy_chunks in chunks_by_privacy.items():
            config = override_config or self.default_configs[privacy_level]
            
            logger.info(
                f"Processing {len(privacy_chunks)} chunks with privacy level: {privacy_level.value}"
            )
            
            batch = await self.generator.generate_chunk_embeddings(privacy_chunks, config)
            results[privacy_level] = batch
        
        return results
    
    def validate_privacy_compliance(
        self,
        chunks: List[DocumentChunk],
        target_privacy_level: PrivacyLevel
    ) -> bool:
        """
        Validate that all chunks comply with target privacy level.
        
        Args:
            chunks: Chunks to validate
            target_privacy_level: Required privacy level
            
        Returns:
            bool: True if all chunks comply
        """
        privacy_hierarchy = {
            PrivacyLevel.PRIVATE: 0,
            PrivacyLevel.CITABLE: 1,
            PrivacyLevel.PUBLIC: 2
        }
        
        target_level = privacy_hierarchy[target_privacy_level]
        
        for chunk in chunks:
            chunk_level = privacy_hierarchy[chunk.privacy_level]
            if chunk_level < target_level:
                logger.warning(
                    f"Privacy violation: chunk {chunk.chunk_index} has level "
                    f"{chunk.privacy_level.value} but target requires {target_privacy_level.value}"
                )
                return False
        
        return True


# Global embedding service
embedding_service = PrivacyAwareEmbeddingService()