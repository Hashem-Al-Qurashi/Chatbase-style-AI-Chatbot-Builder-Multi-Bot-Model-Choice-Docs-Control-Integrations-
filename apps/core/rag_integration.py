"""
RAG Integration Service - Connects embedding generation with vector storage.

This service orchestrates the complete RAG pipeline:
1. Generate embeddings for knowledge chunks
2. Store embeddings in vector database with privacy metadata
3. Enable privacy-aware similarity search for RAG retrieval
4. Maintain chatbot namespace isolation
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import structlog
from django.db import transaction

from apps.knowledge.models import KnowledgeChunk, KnowledgeSource
from .embedding_service import OpenAIEmbeddingService, EmbeddingConfig, EmbeddingResult
from .vector_storage import VectorStorageService, VectorStorageConfig, VectorSearchResult
from .exceptions import RAGIntegrationError

logger = structlog.get_logger()


@dataclass
class RAGProcessingResult:
    """Result of RAG processing operation."""
    processed_chunks: int
    failed_chunks: int
    total_embeddings_generated: int
    total_embeddings_stored: int
    total_cost_usd: float
    processing_time_ms: int
    errors: List[str]


class RAGIntegrationService:
    """
    RAG Integration Service - orchestrates embedding generation and vector storage.
    
    Features:
    - Automatic embedding generation for knowledge chunks
    - Privacy-aware vector storage with chatbot namespace isolation
    - Batch processing for cost optimization
    - Comprehensive error handling and retry logic
    - Database consistency guarantees
    """
    
    def __init__(
        self,
        embedding_config: EmbeddingConfig = None,
        vector_config: VectorStorageConfig = None
    ):
        """Initialize RAG integration service."""
        self.logger = structlog.get_logger().bind(component="RAGIntegrationService")
        
        # Initialize services
        self.embedding_service = OpenAIEmbeddingService(embedding_config)
        self.vector_service = VectorStorageService(vector_config)
        
        self.logger.info(
            "RAG integration service initialized",
            embedding_model=self.embedding_service.config.model,
            vector_backend=self.vector_service.config.backend
        )
    
    async def initialize(self) -> bool:
        """Initialize both embedding and vector storage services."""
        try:
            # Initialize vector storage
            vector_init = await self.vector_service.initialize()
            if not vector_init:
                self.logger.error("Failed to initialize vector storage service")
                return False
            
            self.logger.info(
                "RAG integration service ready",
                vector_backend=self.vector_service.backend_name
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize RAG integration service",
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def process_knowledge_chunks(
        self,
        chunks: List[KnowledgeChunk],
        force_regenerate: bool = False
    ) -> RAGProcessingResult:
        """
        Process knowledge chunks: generate embeddings and store in vector database.
        
        Args:
            chunks: List of KnowledgeChunk instances to process
            force_regenerate: Whether to regenerate existing embeddings
            
        Returns:
            RAGProcessingResult: Processing results and statistics
        """
        start_time = time.time()
        
        if not chunks:
            return RAGProcessingResult(
                processed_chunks=0,
                failed_chunks=0,
                total_embeddings_generated=0,
                total_embeddings_stored=0,
                total_cost_usd=0.0,
                processing_time_ms=0,
                errors=[]
            )
        
        self.logger.info(
            "Starting knowledge chunk processing",
            total_chunks=len(chunks),
            force_regenerate=force_regenerate
        )
        
        # Filter chunks that need processing
        chunks_to_process = []
        existing_embeddings = 0
        
        for chunk in chunks:
            if chunk.embedding_vector and not force_regenerate:
                existing_embeddings += 1
            else:
                chunks_to_process.append(chunk)
        
        self.logger.info(
            "Chunk processing analysis",
            chunks_to_process=len(chunks_to_process),
            existing_embeddings=existing_embeddings,
            force_regenerate=force_regenerate
        )
        
        errors = []
        total_cost = 0.0
        processed_count = 0
        failed_count = 0
        embeddings_generated = 0
        embeddings_stored = 0
        
        if chunks_to_process:
            try:
                # Generate embeddings
                chunk_embeddings = await self.embedding_service.generate_embeddings_for_knowledge_chunks(
                    chunks_to_process,
                    update_db=False  # We'll handle DB updates ourselves for consistency
                )
                
                embeddings_generated = len(chunk_embeddings)
                total_cost = sum(result.cost_usd for _, result in chunk_embeddings)
                
                # Store embeddings in vector database with privacy metadata
                vector_results = await self._store_embeddings_with_metadata(chunk_embeddings)
                embeddings_stored = vector_results['stored_count']
                failed_count = vector_results['failed_count']
                errors.extend(vector_results['errors'])
                
                # Update database with embeddings (if vector storage succeeded)
                if embeddings_stored > 0:
                    db_results = await self._update_chunks_in_database(chunk_embeddings)
                    processed_count = db_results['updated_count']
                    errors.extend(db_results['errors'])
                
            except Exception as e:
                error_msg = f"Failed to process chunks: {str(e)}"
                errors.append(error_msg)
                failed_count = len(chunks_to_process)
                
                self.logger.error(
                    "Chunk processing failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    chunks_to_process=len(chunks_to_process)
                )
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        result = RAGProcessingResult(
            processed_chunks=processed_count,
            failed_chunks=failed_count,
            total_embeddings_generated=embeddings_generated,
            total_embeddings_stored=embeddings_stored,
            total_cost_usd=total_cost,
            processing_time_ms=processing_time_ms,
            errors=errors
        )
        
        self.logger.info(
            "Knowledge chunk processing completed",
            processed_chunks=result.processed_chunks,
            failed_chunks=result.failed_chunks,
            embeddings_generated=result.total_embeddings_generated,
            embeddings_stored=result.total_embeddings_stored,
            cost_usd=result.total_cost_usd,
            processing_time_ms=result.processing_time_ms,
            errors_count=len(result.errors)
        )
        
        return result
    
    async def _store_embeddings_with_metadata(
        self,
        chunk_embeddings: List[Tuple[KnowledgeChunk, EmbeddingResult]]
    ) -> Dict[str, Any]:
        """Store embeddings in vector database with privacy metadata."""
        stored_count = 0
        failed_count = 0
        errors = []
        
        # Group chunks by chatbot for namespace isolation
        chatbot_groups = {}
        for chunk, embedding in chunk_embeddings:
            chatbot_id = str(chunk.source.chatbot.id)
            if chatbot_id not in chatbot_groups:
                chatbot_groups[chatbot_id] = []
            chatbot_groups[chatbot_id].append((chunk, embedding))
        
        # Process each chatbot's chunks separately for namespace isolation
        for chatbot_id, chatbot_chunks in chatbot_groups.items():
            try:
                # Prepare vector data with privacy metadata
                vector_data = []
                for chunk, embedding in chatbot_chunks:
                    vector_id = f"chunk_{chunk.id}"
                    metadata = {
                        "chunk_id": str(chunk.id),
                        "source_id": str(chunk.source.id),
                        "chatbot_id": chatbot_id,
                        "content": chunk.content,
                        "is_citable": chunk.is_citable,  # CRITICAL: Privacy flag
                        "token_count": chunk.token_count,
                        "chunk_index": chunk.chunk_index,
                        "source_name": chunk.source.name,
                        "content_type": chunk.source.content_type,
                    }
                    
                    # Add chunk-specific metadata
                    if chunk.metadata:
                        metadata.update(chunk.metadata)
                    
                    vector_data.append((vector_id, embedding.embedding, metadata))
                
                # Store in vector database with chatbot namespace
                namespace = f"chatbot_{chatbot_id}"
                success = await self.vector_service.store_embeddings(
                    vector_data,
                    namespace=namespace
                )
                
                if success:
                    stored_count += len(chatbot_chunks)
                    self.logger.info(
                        "Stored embeddings for chatbot",
                        chatbot_id=chatbot_id,
                        chunks_stored=len(chatbot_chunks),
                        namespace=namespace
                    )
                else:
                    failed_count += len(chatbot_chunks)
                    error_msg = f"Failed to store embeddings for chatbot {chatbot_id}"
                    errors.append(error_msg)
                    
                    self.logger.error(
                        "Failed to store embeddings for chatbot",
                        chatbot_id=chatbot_id,
                        chunks_failed=len(chatbot_chunks)
                    )
                
            except Exception as e:
                failed_count += len(chatbot_chunks)
                error_msg = f"Error storing embeddings for chatbot {chatbot_id}: {str(e)}"
                errors.append(error_msg)
                
                self.logger.error(
                    "Exception storing embeddings for chatbot",
                    chatbot_id=chatbot_id,
                    error=str(e),
                    error_type=type(e).__name__
                )
        
        return {
            "stored_count": stored_count,
            "failed_count": failed_count,
            "errors": errors
        }
    
    async def _update_chunks_in_database(
        self,
        chunk_embeddings: List[Tuple[KnowledgeChunk, EmbeddingResult]]
    ) -> Dict[str, Any]:
        """Update KnowledgeChunk models with embedding information."""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def update_chunk_batch(chunks_to_update):
            """Update chunks in a database transaction."""
            updated_count = 0
            errors = []
            
            try:
                with transaction.atomic():
                    for chunk, embedding in chunks_to_update:
                        try:
                            chunk.embedding_vector = embedding.embedding
                            chunk.embedding_model = embedding.model
                            chunk.save(update_fields=['embedding_vector', 'embedding_model'])
                            updated_count += 1
                            
                            self.logger.debug(
                                "Updated chunk with embedding",
                                chunk_id=str(chunk.id),
                                source_id=str(chunk.source.id),
                                is_citable=chunk.is_citable
                            )
                            
                        except Exception as e:
                            error_msg = f"Failed to update chunk {chunk.id}: {str(e)}"
                            errors.append(error_msg)
                            
                            self.logger.error(
                                "Failed to update chunk",
                                chunk_id=str(chunk.id),
                                error=str(e)
                            )
                
            except Exception as e:
                error_msg = f"Database transaction failed: {str(e)}"
                errors.append(error_msg)
                
                self.logger.error(
                    "Database update transaction failed",
                    error=str(e),
                    chunks_count=len(chunks_to_update)
                )
            
            return {"updated_count": updated_count, "errors": errors}
        
        return await update_chunk_batch(chunk_embeddings)
    
    async def search_similar_content(
        self,
        query_text: str,
        chatbot_id: str,
        top_k: int = 10,
        citable_only: bool = True
    ) -> List[VectorSearchResult]:
        """
        Search for similar content for a specific chatbot.
        
        Args:
            query_text: Text to search for
            chatbot_id: ID of the chatbot (for namespace isolation)
            top_k: Number of results to return
            citable_only: Whether to return only citable content
            
        Returns:
            List of similar content results
        """
        try:
            # Generate embedding for query
            query_embedding = await self.embedding_service.generate_embedding(query_text)
            
            # Search in chatbot's namespace
            namespace = f"chatbot_{chatbot_id}"
            
            if citable_only:
                results = await self.vector_service.search_citable_only(
                    query_vector=query_embedding.embedding,
                    top_k=top_k,
                    namespace=namespace
                )
            else:
                results = await self.vector_service.search_all_content(
                    query_vector=query_embedding.embedding,
                    top_k=top_k,
                    namespace=namespace
                )
            
            self.logger.info(
                "Similar content search completed",
                chatbot_id=chatbot_id,
                query_length=len(query_text),
                results_count=len(results),
                citable_only=citable_only,
                top_k=top_k
            )
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Failed to search similar content",
                chatbot_id=chatbot_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise RAGIntegrationError(f"Failed to search similar content: {e}")
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        try:
            embedding_stats = self.embedding_service.get_service_stats()
            vector_stats = await self.vector_service.get_storage_stats()
            
            return {
                "rag_integration": {
                    "status": "healthy",
                    "embedding_service_ready": True,
                    "vector_service_ready": self.vector_service.backend is not None,
                    "vector_backend": self.vector_service.backend_name,
                },
                "embedding_service": embedding_stats,
                "vector_storage": vector_stats
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get service stats",
                error=str(e)
            )
            return {
                "rag_integration": {
                    "status": "error",
                    "error": str(e)
                }
            }


# Global service instance
_rag_service = None


async def get_rag_service() -> RAGIntegrationService:
    """Get global RAG integration service instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGIntegrationService()
        await _rag_service.initialize()
    return _rag_service


# Convenience functions
async def process_knowledge_chunks(
    chunks: List[KnowledgeChunk],
    force_regenerate: bool = False
) -> RAGProcessingResult:
    """Process knowledge chunks through the RAG pipeline."""
    service = await get_rag_service()
    return await service.process_knowledge_chunks(chunks, force_regenerate)


async def search_similar_content(
    query_text: str,
    chatbot_id: str,
    top_k: int = 10,
    citable_only: bool = True
) -> List[VectorSearchResult]:
    """Search for similar content for RAG retrieval."""
    service = await get_rag_service()
    return await service.search_similar_content(query_text, chatbot_id, top_k, citable_only)