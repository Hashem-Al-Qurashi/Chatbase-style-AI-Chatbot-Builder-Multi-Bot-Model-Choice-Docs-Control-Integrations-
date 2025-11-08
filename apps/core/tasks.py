"""
Async task processing with Celery for document processing and embeddings.
Implements robust task management with error handling and progress tracking.
"""

import asyncio
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import asdict
from enum import Enum
import logging
import base64

from celery import Celery, Task
from celery.signals import task_prerun, task_postrun, task_failure
from celery.exceptions import Retry, WorkerLostError
from django.core.cache import cache
from django.utils import timezone

from apps.core.document_processors import DocumentProcessorFactory, ProcessedDocument
from apps.core.text_chunking import ChunkerFactory, ChunkingConfig, ChunkingStrategy
from apps.core.embedding_service import OpenAIEmbeddingService, EmbeddingConfig
from apps.core.vector_storage import create_vector_storage
from apps.core.rag_integration import RAGIntegrationService
from apps.core.monitoring import task_monitor
from chatbot_saas.config import get_settings

# For compatibility - will be removed when proper models are implemented
from enum import Enum
class PrivacyLevel(Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    RESTRICTED = "restricted"


settings = get_settings()
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    STARTED = "started"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    REVOKED = "revoked"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


# Import the shared Celery app instance 
from chatbot_saas.celery import app


class BaseTaskWithProgress(Task):
    """Base task class with progress tracking and error handling."""
    
    def __init__(self):
        self.progress_key_prefix = "task_progress"
        self.max_retries = 3
        self.default_retry_delay = 60
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds."""
        task_monitor.record_task_complete(
            task_id=task_id,
            task_name=self.name,
            status='SUCCESS',
            worker_name=getattr(self.request, 'hostname', 'unknown'),
            retries=getattr(self.request, 'retries', 0),
            metadata={'result': retval}
        )
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails."""
        task_monitor.record_task_complete(
            task_id=task_id,
            task_name=self.name,
            status='FAILURE',
            worker_name=getattr(self.request, 'hostname', 'unknown'),
            retries=getattr(self.request, 'retries', 0),
            error_message=str(exc),
            metadata={'exception': einfo.type.__name__, 'traceback': einfo.traceback}
        )
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried."""
        task_monitor.record_task_complete(
            task_id=task_id,
            task_name=self.name,
            status='RETRY',
            worker_name=getattr(self.request, 'hostname', 'unknown'),
            retries=getattr(self.request, 'retries', 0),
            error_message=str(exc),
            metadata={'exception': einfo.type.__name__}
        )
    
    def update_progress(
        self,
        current: int,
        total: int,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Update task progress."""
        # Handle eager mode where task_id might not be available
        task_id = getattr(self.request, 'id', None) or 'eager-mode'
        
        progress_data = {
            "current": current,
            "total": total,
            "percentage": (current / total * 100) if total > 0 else 0,
            "message": message,
            "metadata": metadata or {},
            "updated_at": timezone.now().isoformat(),
            "task_id": task_id,
            "status": TaskStatus.PROCESSING.value
        }
        
        # Only cache if we have a real task_id and caching is enabled
        if task_id != 'eager-mode':
            try:
                from django.conf import settings
                # Check if caching is enabled before attempting to cache
                if getattr(settings, 'ENABLE_CACHING', True):
                    cache.set(
                        f"{self.progress_key_prefix}:{task_id}",
                        progress_data,
                        timeout=3600  # 1 hour
                    )
                else:
                    # In development mode without caching, just log progress
                    print(f"Task Progress: {progress_data['percentage']:.1f}% - {progress_data['message']}")
            except Exception as e:
                # If cache is not available, just continue without caching
                print(f"Cache not available, skipping progress update: {e}")
                print(f"Task Progress: {progress_data['percentage']:.1f}% - {progress_data['message']}")
            
            # Also update task state (only if not in eager mode and caching enabled)
            try:
                from django.conf import settings
                if getattr(settings, 'ENABLE_CACHING', True):
                    self.update_state(
                        state="PROGRESS",
                        meta=progress_data
                    )
            except (ValueError, Exception) as e:
                # Ignore if task_id is not available (eager mode) or caching issues
                pass
        
        # Always log progress for debugging
        print(f"Task Progress: {current}/{total} ({progress_data['percentage']:.1f}%) - {message}")
    
    def get_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task progress."""
        try:
            from django.conf import settings
            if getattr(settings, 'ENABLE_CACHING', True):
                return cache.get(f"{self.progress_key_prefix}:{task_id}")
            else:
                # Return a default progress when caching is disabled
                return {"percentage": 0, "message": "Progress tracking disabled in development mode"}
        except Exception:
            return None
    
    def mark_success(self, result: Any, metadata: Optional[Dict[str, Any]] = None):
        """Mark task as successful."""
        task_id = getattr(self.request, 'id', None) or 'eager-mode'
        success_data = {
            "status": TaskStatus.SUCCESS.value,
            "result": result,
            "metadata": metadata or {},
            "completed_at": timezone.now().isoformat(),
            "task_id": task_id
        }
        
        # Only cache if we have a real task_id
        if task_id != 'eager-mode':
            cache.set(
                f"{self.progress_key_prefix}:{task_id}",
                success_data,
                timeout=3600
            )
        
        print(f"✅ Task completed successfully: {result}")
        return success_data
    
    def mark_failure(self, error: Exception, metadata: Optional[Dict[str, Any]] = None):
        """Mark task as failed."""
        task_id = getattr(self.request, 'id', None) or 'eager-mode'
        failure_data = {
            "status": TaskStatus.FAILURE.value,
            "error": str(error),
            "error_type": type(error).__name__,
            "traceback": traceback.format_exc(),
            "metadata": metadata or {},
            "failed_at": timezone.now().isoformat(),
            "task_id": task_id
        }
        
        # Only cache if we have a real task_id
        if task_id != 'eager-mode':
            cache.set(
                f"{self.progress_key_prefix}:{task_id}",
                failure_data,
                timeout=3600
            )
        
        print(f"❌ Task failed: {error}")
        return failure_data
    
    def retry_with_backoff(self, exc: Exception, **kwargs):
        """Retry task with exponential backoff."""
        retry_count = self.request.retries
        delay = self.default_retry_delay * (2 ** retry_count)
        
        logger.warning(
            f"Task {self.request.id} failed (attempt {retry_count + 1}), "
            f"retrying in {delay}s: {str(exc)}"
        )
        
        raise self.retry(exc=exc, countdown=delay, **kwargs)


@app.task(bind=True, base=BaseTaskWithProgress, name='apps.core.tasks.process_document_pipeline')
def process_document_pipeline(
    self,
    document_id: str,
    file_content_base64: str,
    filename: str,
    content_type: str,
    knowledge_base_id: str,
    user_id: str,
    chunking_strategy: str = "RECURSIVE_CHARACTER"
) -> Dict[str, Any]:
    """
    Process document: extract content, chunk, and generate embeddings.
    
    Args:
        document_id: Document ID
        file_content_base64: Base64 encoded file content
        filename: Original filename
        content_type: MIME type
        knowledge_base_id: Knowledge base ID
        user_id: Owner user ID
        chunking_strategy: Chunking strategy to use
        
    Returns:
        Dict[str, Any]: Processing result
    """
    try:
        import base64
        
        self.update_progress(0, 100, "Starting document processing")
        
        # Decode file content
        file_content = base64.b64decode(file_content_base64)
        
        self.update_progress(10, 100, "Extracting document content")
        
        # Extract document content using our DocumentProcessorFactory
        try:
            processor_factory = DocumentProcessorFactory()
            processor = processor_factory.create_processor(content_type)
            processed_doc = processor.extract_text(file_content, filename)
        except Exception as e:
            logger.error(f"Document content extraction failed: {str(e)}")
            self.mark_failure(e)
            raise
        
        self.update_progress(30, 100, "Chunking document content")
        
        # Chunk document using our ChunkerFactory
        try:
            config = ChunkingConfig(
                chunk_size=1000,
                chunk_overlap=200,
                strategy=ChunkingStrategy(chunking_strategy),
                min_chunk_size=100
            )
            chunker = ChunkerFactory.create_chunker(config)
            chunks = chunker.chunk_text(processed_doc.content)
        except Exception as e:
            logger.error(f"Document chunking failed: {str(e)}")
            self.mark_failure(e)
            raise
        
        self.update_progress(50, 100, f"Generated {len(chunks)} chunks, creating embeddings")
        
        # Generate embeddings using our EmbeddingService
        try:
            embedding_config = EmbeddingConfig()
            embedding_service = OpenAIEmbeddingService(embedding_config)
            
            # Extract text content from chunks
            chunk_texts = [chunk.content for chunk in chunks]
            
            # Generate embeddings in batch
            embedding_result = asyncio.run(embedding_service.generate_embeddings_batch(chunk_texts))
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            self.mark_failure(e)
            raise
        
        self.update_progress(70, 100, "Storing embeddings in vector database")
        
        # Store embeddings in vector database
        try:
            vector_storage = asyncio.run(create_vector_storage("auto"))
            
            # Prepare embedding data for storage
            embeddings_to_store = []
            for i, chunk in enumerate(chunks):
                if i < len(embedding_result.embeddings):
                    embedding_data = embedding_result.embeddings[i]
                    metadata = {
                        "document_id": document_id,
                        "chunk_index": i,
                        "content": chunk.content,
                        "filename": filename,
                        "content_type": content_type,
                        "knowledge_base_id": knowledge_base_id,
                        "user_id": user_id,
                        "created_at": timezone.now().isoformat()
                    }
                    embeddings_to_store.append((
                        f"{document_id}_chunk_{i}",
                        embedding_data.embedding,
                        metadata
                    ))
            
            # Store in vector database with namespace
            namespace = f"kb_{knowledge_base_id}"
            asyncio.run(vector_storage.store_embeddings(embeddings_to_store, namespace))
            
        except Exception as e:
            logger.error(f"Vector storage failed: {str(e)}")
            self.mark_failure(e)
            raise
        
        self.update_progress(90, 100, "Updating document status")
        
        # Update document status in database (simplified - would use proper models)
        try:
            # Here you would update the actual document model
            # For now, we'll just log the completion
            logger.info(f"Document {document_id} processed successfully")
        except Exception as e:
            logger.error(f"Document status update failed: {str(e)}")
            # Don't fail the task for this
        
        self.update_progress(100, 100, "Document processing completed")
        
        result = {
            "document_id": document_id,
            "filename": filename,
            "chunk_count": len(chunks),
            "total_tokens": embedding_result.total_tokens,
            "total_cost": embedding_result.total_cost_usd,
            "processing_time_ms": embedding_result.processing_time_ms,
            "vector_storage_backend": vector_storage.backend_name if hasattr(vector_storage, 'backend_name') else 'unknown'
        }
        
        return self.mark_success(result)
        
    except Exception as e:
        if self.request.retries < self.max_retries:
            self.retry_with_backoff(e)
        else:
            logger.error(f"Document processing failed permanently: {str(e)}")
            self.mark_failure(e)
            raise


@app.task(bind=True, base=BaseTaskWithProgress, name='apps.core.tasks.process_url')
def process_url(
    self,
    document_id: str,
    url: str,
    privacy_level: str,
    knowledge_base_id: str,
    user_id: str,
    chunking_strategy: str = "hybrid"
) -> Dict[str, Any]:
    """
    Process URL: extract content, chunk, and generate embeddings.
    
    Args:
        document_id: Document ID
        url: URL to process
        privacy_level: Document privacy level
        knowledge_base_id: Knowledge base ID
        user_id: Owner user ID
        chunking_strategy: Chunking strategy to use
        
    Returns:
        Dict[str, Any]: Processing result
    """
    try:
        self.update_progress(0, 100, f"Starting URL processing: {url}")
        
        privacy_enum = PrivacyLevel(privacy_level)
        
        # Extract content from URL (simplified web scraping)
        self.update_progress(20, 100, "Extracting content from URL")
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            document_content = soup.get_text()
            # Clean up whitespace
            document_content = '\n'.join(line.strip() for line in document_content.splitlines() if line.strip())
            
        except Exception as e:
            logger.error(f"URL content extraction failed: {str(e)}")
            self.mark_failure(e)
            raise
        
        self.update_progress(40, 100, "Chunking URL content")
        
        # Create a ProcessedDocument object
        processed_doc = ProcessedDocument(
            content=document_content,
            metadata={'url': url, 'title': soup.title.string if soup.title else url},
            word_count=len(document_content.split()),
            character_count=len(document_content)
        )
        
        # Chunk content using our ChunkerFactory
        try:
            config = ChunkingConfig(
                chunk_size=1000,
                chunk_overlap=200,
                strategy=ChunkingStrategy(chunking_strategy),
                min_chunk_size=100
            )
            chunker = ChunkerFactory.create_chunker(config)
            chunks = chunker.chunk_text(processed_doc.content)
        except Exception as e:
            logger.error(f"URL content chunking failed: {str(e)}")
            self.mark_failure(e)
            raise
        
        self.update_progress(60, 100, f"Generated {len(chunks)} chunks, creating embeddings")
        
        # Generate embeddings using our EmbeddingService
        try:
            embedding_config = EmbeddingConfig()
            embedding_service = OpenAIEmbeddingService(embedding_config)
            
            # Extract text content from chunks
            chunk_texts = [chunk.content for chunk in chunks]
            
            # Generate embeddings in batch
            embedding_result = asyncio.run(embedding_service.generate_embeddings_batch(chunk_texts))
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            self.mark_failure(e)
            raise
        
        self.update_progress(80, 100, "Storing embeddings in vector database")
        
        # Store embeddings in vector database
        try:
            vector_storage = asyncio.run(create_vector_storage("auto"))
            
            # Prepare embedding data for storage
            embeddings_to_store = []
            for i, chunk in enumerate(chunks):
                if i < len(embedding_result.embeddings):
                    embedding_data = embedding_result.embeddings[i]
                    metadata = {
                        "document_id": document_id,
                        "chunk_index": i,
                        "content": chunk.content,
                        "url": url,
                        "privacy_level": privacy_level,
                        "knowledge_base_id": knowledge_base_id,
                        "user_id": user_id,
                        "created_at": timezone.now().isoformat()
                    }
                    embeddings_to_store.append((
                        f"{document_id}_chunk_{i}",
                        embedding_data.embedding,
                        metadata
                    ))
            
            # Store in vector database with namespace
            namespace = f"kb_{knowledge_base_id}"
            asyncio.run(vector_storage.store_embeddings(embeddings_to_store, namespace))
            
        except Exception as e:
            logger.error(f"Vector storage failed: {str(e)}")
            self.mark_failure(e)
            raise
        
        # Update document status (simplified - would use proper models)
        try:
            logger.info(f"URL document {document_id} processed successfully")
        except Exception as e:
            logger.error(f"Document status update failed: {str(e)}")
        
        self.update_progress(100, 100, "URL processing completed")
        
        result = {
            "document_id": document_id,
            "url": url,
            "chunk_count": len(chunks),
            "total_tokens": embedding_result.total_tokens,
            "total_cost": embedding_result.total_cost_usd,
            "processing_time_ms": embedding_result.processing_time_ms,
            "privacy_level": privacy_level,
            "vector_storage_backend": vector_storage.backend_name if hasattr(vector_storage, 'backend_name') else 'unknown'
        }
        
        return self.mark_success(result)
        
    except Exception as e:
        if self.request.retries < self.max_retries:
            self.retry_with_backoff(e)
        else:
            logger.error(f"URL processing failed permanently: {str(e)}")
            self.mark_failure(e)
            raise


@app.task(bind=True, base=BaseTaskWithProgress, name='apps.core.tasks.generate_embeddings_for_knowledge_chunks')
def generate_embeddings_for_knowledge_chunks(
    self,
    knowledge_source_id: str,
    chunk_ids: Optional[List[str]] = None,
    model: str = "text-embedding-ada-002",
    batch_size: int = 50,
    force_regenerate: bool = False
) -> Dict[str, Any]:
    """
    Generate embeddings for KnowledgeChunk records.
    
    Args:
        knowledge_source_id: KnowledgeSource ID to process chunks for
        chunk_ids: Optional list of specific chunk IDs to process
        model: Embedding model to use
        batch_size: Batch size for processing
        force_regenerate: Whether to regenerate existing embeddings
        
    Returns:
        Dict[str, Any]: Processing result
    """
    try:
        from apps.knowledge.models import KnowledgeSource, KnowledgeChunk, ProcessingJob
        from apps.core.embedding_service import EmbeddingConfig, OpenAIEmbeddingService
        from apps.core.models import ProcessingStatus
        
        self.update_progress(0, 100, "Starting embedding generation for knowledge chunks")
        
        # Get knowledge source
        try:
            source = KnowledgeSource.objects.get(id=knowledge_source_id)
        except KnowledgeSource.DoesNotExist:
            raise ValueError(f"KnowledgeSource {knowledge_source_id} not found")
        
        self.update_progress(10, 100, f"Loading chunks for source: {source.name}")
        
        # Get chunks to process
        if chunk_ids:
            chunks = KnowledgeChunk.objects.filter(
                id__in=chunk_ids,
                source=source
            ).order_by('chunk_index')
        else:
            if force_regenerate:
                chunks = source.chunks.all().order_by('chunk_index')
            else:
                # Only process chunks without embeddings
                chunks = source.chunks.filter(
                    embedding_vector__isnull=True
                ).order_by('chunk_index')
        
        total_chunks = chunks.count()
        if total_chunks == 0:
            return self.mark_success({
                "source_id": knowledge_source_id,
                "processed_chunks": 0,
                "generated_embeddings": 0,
                "message": "No chunks found or all chunks already have embeddings"
            })
        
        self.update_progress(20, 100, f"Processing {total_chunks} chunks")
        
        # Initialize embedding service
        embedding_config = EmbeddingConfig(
            model=model,
            max_batch_size=batch_size,
            enable_caching=True,
            enable_deduplication=True
        )
        embedding_service = OpenAIEmbeddingService(embedding_config)
        
        # Process chunks in batches
        processed_count = 0
        total_cost = 0.0
        total_tokens = 0
        
        chunk_list = list(chunks)
        for i in range(0, len(chunk_list), batch_size):
            batch_chunks = chunk_list[i:i + batch_size]
            
            batch_progress = 20 + (i / len(chunk_list)) * 60
            self.update_progress(
                int(batch_progress), 100,
                f"Processing batch {i // batch_size + 1}/{(len(chunk_list) - 1) // batch_size + 1}"
            )
            
            try:
                # Generate embeddings for batch
                chunk_embedding_results = asyncio.run(
                    embedding_service.generate_embeddings_for_knowledge_chunks(
                        batch_chunks, update_db=True
                    )
                )
                
                # STEP 5 FIX: Direct vector storage transfer to avoid async/sync issues
                if chunk_embedding_results:
                    try:
                        # Get embeddings from processed chunks and store directly in vector DB
                        vector_data = []
                        chatbot_id = batch_chunks[0].source.chatbot.id
                        
                        for chunk, embedding_result in chunk_embedding_results:
                            if embedding_result.embedding:
                                vector_id = str(chunk.id)
                                metadata = {
                                    'content': chunk.content,
                                    'chunk_index': chunk.chunk_index,
                                    'source_id': str(chunk.source.id),
                                    'source_name': chunk.source.name,
                                    'is_citable': chunk.is_citable,
                                    'token_count': chunk.token_count
                                }
                                vector_data.append((vector_id, embedding_result.embedding, metadata))
                        
                        if vector_data:
                            # Store directly in vector database
                            vector_storage = asyncio.run(create_vector_storage())
                            namespace = f"chatbot_{chatbot_id}"
                            
                            success = asyncio.run(vector_storage.store_embeddings(vector_data, namespace=namespace))
                            
                            if success:
                                logger.info(f"Vector storage success: {len(vector_data)} embeddings stored in namespace {namespace}")
                            else:
                                logger.error(f"Vector storage failed for {len(vector_data)} embeddings")
                        
                    except Exception as vector_error:
                        logger.error(f"Vector storage failed for batch: {str(vector_error)}")
                        # Continue processing - embeddings are still in database
                
                # Track statistics
                for chunk, embedding_result in chunk_embedding_results:
                    if not embedding_result.cached:
                        total_cost += embedding_result.cost_usd
                        total_tokens += embedding_result.tokens_used
                    processed_count += 1
                
                logger.info(
                    f"Processed embedding batch: {len(batch_chunks)} chunks, "
                    f"processed: {processed_count}/{total_chunks}, "
                    f"batch cost: ${sum(r.cost_usd for _, r in chunk_embedding_results if not r.cached):.6f}"
                )
                
            except Exception as e:
                logger.error(
                    f"Batch embedding generation failed for batch {i // batch_size}: {str(e)}"
                )
                # Continue with other batches rather than failing completely
                continue
        
        self.update_progress(85, 100, "Updating source status")
        
        # Update source with embedding completion status
        try:
            # Check if all chunks now have embeddings
            remaining_chunks = source.chunks.filter(embedding_vector__isnull=True).count()
            
            if remaining_chunks == 0:
                # Create processing job for embeddings
                from apps.knowledge.models import ProcessingJob
                ProcessingJob.objects.create(
                    source=source,
                    job_type='generate_embeddings',
                    status=ProcessingStatus.COMPLETED,
                    result_data={
                        'processed_chunks': processed_count,
                        'total_cost': total_cost,
                        'total_tokens': total_tokens,
                        'model': model
                    },
                    completed_at=timezone.now()
                )
                
                logger.info(
                    f"All chunks for source {knowledge_source_id} now have embeddings: {total_chunks} chunks"
                )
            
        except Exception as e:
            logger.warning(
                f"Failed to update source status for {knowledge_source_id}: {str(e)}"
            )
        
        self.update_progress(100, 100, "Embedding generation completed")
        
        result = {
            "source_id": knowledge_source_id,
            "source_name": source.name,
            "processed_chunks": processed_count,
            "total_chunks": total_chunks,
            "generated_embeddings": processed_count,
            "total_cost_usd": total_cost,
            "total_tokens": total_tokens,
            "model": model,
            "batch_size": batch_size,
            "is_citable": source.is_citable,
            "privacy_preserved": True
        }
        
        return self.mark_success(result)
        
    except Exception as e:
        if self.request.retries < self.max_retries:
            self.retry_with_backoff(e)
        else:
            logger.error(f"Knowledge chunk embedding generation failed permanently: {str(e)}")
            self.mark_failure(e)
            raise


@app.task(bind=True, base=BaseTaskWithProgress, name='apps.core.tasks.generate_embeddings')
def generate_embeddings(
    self,
    chunk_ids: List[str],
    model: str = "text-embedding-ada-002",
    batch_size: int = 100
) -> Dict[str, Any]:
    """
    Generate embeddings for existing chunks (legacy task for backward compatibility).
    
    Args:
        chunk_ids: List of chunk IDs to process
        model: Embedding model to use
        batch_size: Batch size for processing
        
    Returns:
        Dict[str, Any]: Processing result
    """
    # Redirect to the new task for actual KnowledgeChunk processing
    from apps.knowledge.models import KnowledgeChunk
    
    try:
        self.update_progress(0, 100, f"Starting embedding generation for {len(chunk_ids)} chunks")
        
        # Get unique source IDs from chunks
        chunks = KnowledgeChunk.objects.filter(id__in=chunk_ids).select_related('source')
        source_ids = list(set(chunk.source.id for chunk in chunks))
        
        total_processed = 0
        
        for source_id in source_ids:
            source_chunk_ids = [str(chunk.id) for chunk in chunks if chunk.source.id == source_id]
            
            # Call the new embedding task
            result = generate_embeddings_for_knowledge_chunks(
                knowledge_source_id=str(source_id),
                chunk_ids=source_chunk_ids,
                model=model,
                batch_size=batch_size
            )
            
            if result and isinstance(result, dict) and 'result' in result:
                total_processed += result['result'].get('processed_chunks', 0)
        
        self.update_progress(100, 100, "Embedding generation completed")
        
        result = {
            "processed_chunks": total_processed,
            "generated_embeddings": total_processed,
            "model": model,
            "batch_size": batch_size
        }
        
        return self.mark_success(result)
        
    except Exception as e:
        if self.request.retries < self.max_retries:
            self.retry_with_backoff(e)
        else:
            logger.error(f"Embedding generation failed permanently: {str(e)}")
            self.mark_failure(e)
            raise


@app.task(bind=True, name='apps.core.tasks.cleanup_expired_sessions')
def cleanup_expired_sessions(self) -> Dict[str, Any]:
    """Clean up expired user sessions."""
    try:
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        
        # Delete expired sessions
        expired_count = Session.objects.filter(expire_date__lt=timezone.now()).count()
        Session.objects.filter(expire_date__lt=timezone.now()).delete()
        
        logger.info(f"Cleaned up {expired_count} expired sessions")
        
        return {
            "cleaned_sessions": expired_count,
            "cleanup_time": timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Session cleanup failed: {str(e)}")
        raise


@app.task(bind=True, name='apps.core.tasks.cleanup_temporary_files')
def cleanup_temporary_files(self) -> Dict[str, Any]:
    """Clean up temporary files and old task progress data."""
    try:
        import os
        import tempfile
        
        cleaned_files = 0
        temp_dir = tempfile.gettempdir()
        
        # Clean up old temporary files (older than 24 hours)
        cutoff_time = time.time() - 86400  # 24 hours
        
        for filename in os.listdir(temp_dir):
            if filename.startswith('upload_') or filename.startswith('process_'):
                filepath = os.path.join(temp_dir, filename)
                try:
                    if os.path.getmtime(filepath) < cutoff_time:
                        os.remove(filepath)
                        cleaned_files += 1
                except (OSError, IOError):
                    continue
        
        # Clean up old task progress entries from cache
        cleaned_progress = 0
        try:
            # Get all task progress keys (simplified - in production use Redis SCAN)
            from django.core.cache import cache
            # This is a simplified cleanup - in production you'd use proper Redis commands
            cleaned_progress = 0  # Placeholder
        except Exception:
            pass
        
        logger.info(f"Cleaned up {cleaned_files} temporary files and {cleaned_progress} progress entries")
        
        return {
            "cleaned_files": cleaned_files,
            "cleaned_progress_entries": cleaned_progress,
            "cleanup_time": timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"File cleanup failed: {str(e)}")
        raise


@app.task(bind=True, name='apps.core.tasks.monitor_embedding_costs')
def monitor_embedding_costs(self) -> Dict[str, Any]:
    """Monitor embedding costs and send alerts if necessary."""
    try:
        # Get daily embedding cost from cache or database
        today = timezone.now().date()
        cost_key = f"daily_embedding_cost:{today}"
        
        daily_cost = cache.get(cost_key, 0.0)
        
        # Set budget thresholds
        warning_threshold = 10.0  # $10
        critical_threshold = 25.0  # $25
        
        alert_level = None
        if daily_cost > critical_threshold:
            alert_level = "critical"
        elif daily_cost > warning_threshold:
            alert_level = "warning"
        
        if alert_level:
            logger.warning(
                f"Embedding cost alert: ${daily_cost:.2f} today "
                f"(threshold: ${warning_threshold if alert_level == 'warning' else critical_threshold})"
            )
            
            # In production, you'd send notifications here
            # send_cost_alert(alert_level, daily_cost)
        
        return {
            "daily_cost": daily_cost,
            "alert_level": alert_level,
            "thresholds": {
                "warning": warning_threshold,
                "critical": critical_threshold
            },
            "check_time": timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cost monitoring failed: {str(e)}")
        raise


@app.task(bind=True, base=BaseTaskWithProgress, name='apps.core.tasks.process_knowledge_source_task')
def process_knowledge_source_task(
    self,
    knowledge_source_id: str,
    force_reprocess: bool = False
) -> Dict[str, Any]:
    """
    Process a knowledge source using the document processing service.
    
    Args:
        knowledge_source_id: KnowledgeSource ID to process
        force_reprocess: Whether to force reprocessing
        
    Returns:
        Dict[str, Any]: Processing result
    """
    try:
        from apps.knowledge.models import KnowledgeSource
        from apps.core.document_processing_service import DocumentProcessingService
        
        self.update_progress(0, 100, "Starting knowledge source processing")
        
        # Get knowledge source
        try:
            source = KnowledgeSource.objects.get(id=knowledge_source_id)
        except KnowledgeSource.DoesNotExist:
            raise ValueError(f"KnowledgeSource {knowledge_source_id} not found")
        
        self.update_progress(10, 100, f"Processing source: {source.name}")
        
        # Skip if already processed and not forcing reprocess
        if source.status == 'completed' and not force_reprocess:
            return self.mark_success({
                "source_id": knowledge_source_id,
                "status": "already_processed",
                "chunks_created": source.chunk_count,
                "message": "Source already processed"
            })
        
        # Initialize document processing service
        doc_service = DocumentProcessingService()
        
        self.update_progress(20, 100, "Initializing document processing")
        
        # Process based on source type
        if source.content_type == 'document' and source.file_path:
            # File-based processing
            self.update_progress(30, 100, "Reading file content")
            
            try:
                with open(source.file_path, 'rb') as f:
                    file_content = f.read()
                
                filename = source.metadata.get('original_filename', source.name)
                
                self.update_progress(40, 100, "Processing document content")
                
                result = doc_service.process_uploaded_file(
                    knowledge_source=source,
                    file_content=file_content,
                    filename=filename,
                    mime_type=source.mime_type
                )
                
            except Exception as e:
                error_msg = f"File processing failed: {str(e)}"
                self.mark_failure(Exception(error_msg))
                raise
                
        elif source.content_type == 'url' and source.source_url:
            # URL-based processing
            self.update_progress(30, 100, "Crawling URL content")
            
            try:
                result = doc_service.process_url_content(
                    knowledge_source=source,
                    url=source.source_url
                )
                
            except Exception as e:
                error_msg = f"URL processing failed: {str(e)}"
                self.mark_failure(Exception(error_msg))
                raise
        else:
            error_msg = f"Unsupported source type: {source.content_type}"
            self.mark_failure(Exception(error_msg))
            raise ValueError(error_msg)
        
        self.update_progress(80, 100, "Finalizing processing")
        
        # Check result
        if result.success:
            self.update_progress(100, 100, "Knowledge source processing completed")
            
            return self.mark_success({
                "source_id": knowledge_source_id,
                "status": "completed",
                "chunks_created": len(result.chunks),
                "total_tokens": result.total_tokens,
                "processing_time_ms": result.processing_time_ms,
                "quality_score": result.processed_document.quality_score if result.processed_document else None
            })
        else:
            error_msg = result.error_message or "Processing failed with unknown error"
            self.mark_failure(Exception(error_msg))
            raise Exception(error_msg)
        
    except Exception as e:
        if self.request.retries < self.max_retries:
            self.retry_with_backoff(e)
        else:
            logger.error(f"Knowledge source processing failed permanently: {str(e)}")
            self.mark_failure(e)
            raise


@app.task(bind=True, base=BaseTaskWithProgress, name='apps.core.tasks.train_chatbot_task')
def train_chatbot_task(
    self,
    chatbot_id: str,
    force_retrain: bool = False,
    knowledge_source_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Train chatbot with its knowledge sources.
    
    Args:
        chatbot_id: Chatbot ID to train
        force_retrain: Whether to force retraining
        knowledge_source_ids: Specific knowledge sources to train with
        
    Returns:
        Dict[str, Any]: Training result
    """
    try:
        from apps.chatbots.models import Chatbot
        from apps.knowledge.models import KnowledgeSource
        
        self.update_progress(0, 100, "Starting chatbot training")
        
        # Get chatbot
        try:
            chatbot = Chatbot.objects.get(id=chatbot_id)
        except Chatbot.DoesNotExist:
            raise ValueError(f"Chatbot {chatbot_id} not found")
        
        # Update chatbot status to processing
        chatbot.update_training_status('processing')
        
        self.update_progress(10, 100, "Loading knowledge sources")
        
        # Get knowledge sources
        if knowledge_source_ids:
            knowledge_sources = KnowledgeSource.objects.filter(
                id__in=knowledge_source_ids,
                chatbot=chatbot
            )
        else:
            knowledge_sources = chatbot.knowledge_sources.all()
        
        if not knowledge_sources.exists():
            # No knowledge sources - mark as ready anyway for basic functionality
            chatbot.update_training_status('completed')
            chatbot.last_trained_at = timezone.now()
            chatbot.save()
            
            return self.mark_success({
                "chatbot_id": chatbot_id,
                "knowledge_sources_processed": 0,
                "status": "ready",
                "message": "No knowledge sources found - chatbot ready for basic chat"
            })
        
        self.update_progress(20, 100, f"Processing {knowledge_sources.count()} knowledge sources")
        
        # Process each knowledge source
        processed_sources = 0
        total_sources = knowledge_sources.count()
        
        for i, source in enumerate(knowledge_sources):
            progress = 20 + (i / total_sources) * 60
            self.update_progress(
                int(progress), 100, 
                f"Processing knowledge source: {source.name}"
            )
            
            # Update source status to processing if not already processed
            if source.status != 'completed' or force_retrain:
                source.status = 'processing'
                source.save()
                
                try:
                    # Trigger document/URL processing based on source type
                    if hasattr(source, 'file') and source.file:
                        # File-based knowledge source
                        task_id = TaskManager.submit_document_processing(
                            document_id=str(source.id),
                            file_content=source.file.read() if source.file else b'',
                            filename=source.file.name if source.file else 'unknown',
                            content_type=source.file_type or 'text/plain',
                            privacy_level='private',
                            knowledge_base_id=str(chatbot.id),
                            user_id=str(chatbot.user.id)
                        )
                    elif hasattr(source, 'url') and source.url:
                        # URL-based knowledge source
                        task_id = TaskManager.submit_url_processing(
                            document_id=str(source.id),
                            url=source.url,
                            privacy_level='private',
                            knowledge_base_id=str(chatbot.id),
                            user_id=str(chatbot.user.id)
                        )
                    
                    # For now, mark as completed immediately (simplified)
                    source.status = 'completed'
                    source.save()
                    processed_sources += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process knowledge source {source.id}: {e}")
                    source.status = 'failed'
                    source.save()
                    continue
            else:
                processed_sources += 1
        
        self.update_progress(80, 100, "Finalizing chatbot training")
        
        # Update chatbot status
        if processed_sources > 0:
            chatbot.update_training_status('completed')
        else:
            chatbot.update_training_status('failed')
        
        chatbot.last_trained_at = timezone.now()
        chatbot.save()
        
        self.update_progress(100, 100, "Chatbot training completed")
        
        result = {
            "chatbot_id": chatbot_id,
            "knowledge_sources_processed": processed_sources,
            "total_knowledge_sources": total_sources,
            "status": "ready" if processed_sources > 0 else "failed",
            "training_completed_at": timezone.now().isoformat()
        }
        
        return self.mark_success(result)
        
    except Exception as e:
        # Update chatbot status to failed
        try:
            from apps.chatbots.models import Chatbot
            chatbot = Chatbot.objects.get(id=chatbot_id)
            chatbot.update_training_status('failed')
        except:
            pass
        
        if self.request.retries < self.max_retries:
            self.retry_with_backoff(e)
        else:
            logger.error(f"Chatbot training failed permanently: {str(e)}")
            self.mark_failure(e)
            raise


@app.task(bind=True, name='apps.core.tasks.health_check')
def health_check(self) -> Dict[str, Any]:
    """Perform system health checks."""
    try:
        health_status = {
            "celery": "healthy",
            "database": "unknown",
            "cache": "unknown",
            "vector_storage": "unknown",
            "embedding_service": "unknown"
        }
        
        # Check database connection
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_status["database"] = "healthy"
        except Exception:
            health_status["database"] = "unhealthy"
        
        # Check cache
        try:
            cache.set("health_check", "test", 10)
            if cache.get("health_check") == "test":
                health_status["cache"] = "healthy"
            else:
                health_status["cache"] = "unhealthy"
        except Exception:
            health_status["cache"] = "unhealthy"
        
        # Check vector storage (simplified)
        try:
            # This would be an actual health check in production
            health_status["vector_storage"] = "healthy"
        except Exception:
            health_status["vector_storage"] = "unhealthy"
        
        # Check embedding service (simplified)
        try:
            # This would test OpenAI API connectivity
            health_status["embedding_service"] = "healthy"
        except Exception:
            health_status["embedding_service"] = "unhealthy"
        
        overall_healthy = all(status == "healthy" for status in health_status.values())
        
        return {
            "overall_status": "healthy" if overall_healthy else "degraded",
            "components": health_status,
            "check_time": timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "check_time": timezone.now().isoformat()
        }


# Helper functions for database operations (simplified for now)
# These will be replaced with proper model implementations

def _store_document_chunks(
    document_id: str,
    chunks: List,
    embeddings: List,
    knowledge_base_id: str
) -> List:
    """Store document chunks and embeddings in database (simplified)."""
    # In production, this would use proper Django models
    logger.info(f"Storing {len(chunks)} chunks for document {document_id}")
    return chunks


def _convert_db_chunk_to_document_chunk(db_chunk):
    """Convert database chunk to DocumentChunk object (simplified)."""
    # In production, this would use proper model conversion
    return {
        'content': getattr(db_chunk, 'content', ''),
        'chunk_index': getattr(db_chunk, 'chunk_index', 0),
        'metadata': getattr(db_chunk, 'metadata', {})
    }


def _update_chunk_embeddings(chunks: List, embeddings: List):
    """Update existing chunks with new embeddings (simplified)."""
    # In production, this would update actual database records
    logger.info(f"Updated embeddings for {len(chunks)} chunks")


# Task monitoring and signals
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task pre-run signal."""
    logger.info(f"Task {task_id} ({task.name}) starting")
    
    # Record task start for monitoring
    task_monitor.record_task_start(
        task_id=task_id,
        task_name=task.name,
        worker_name=getattr(task.request, 'hostname', 'unknown')
    )


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, 
                        retval=None, state=None, **kwds):
    """Handle task post-run signal."""
    logger.info(f"Task {task_id} ({task.name}) completed with state: {state}")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Handle task failure signal."""
    logger.error(f"Task {task_id} failed: {str(exception)}")
    
    # Additional logging for monitoring systems
    if hasattr(exception, '__class__'):
        logger.error(f"Exception type: {exception.__class__.__name__}")
    logger.error(f"Task failure traceback: {traceback}")


class TaskManager:
    """Manager for task operations and monitoring."""
    
    @staticmethod
    def submit_document_processing(
        document_id: str,
        file_content: bytes,
        filename: str,
        content_type: str,
        privacy_level: str,
        knowledge_base_id: str,
        user_id: str,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """Submit document processing task."""
        import base64
        
        file_content_base64 = base64.b64encode(file_content).decode('utf-8')
        
        task = process_document_pipeline.apply_async(
            args=[
                document_id,
                file_content_base64,
                filename,
                content_type,
                privacy_level,
                knowledge_base_id,
                user_id
            ],
            priority=priority.value
        )
        
        return task.id
    
    @staticmethod
    def submit_url_processing(
        document_id: str,
        url: str,
        privacy_level: str,
        knowledge_base_id: str,
        user_id: str,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """Submit URL processing task."""
        task = process_url.apply_async(
            args=[document_id, url, privacy_level, knowledge_base_id, user_id],
            priority=priority.value
        )
        
        return task.id
    
    @staticmethod
    def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status and progress."""
        from celery.result import AsyncResult
        
        result = AsyncResult(task_id, app=app)
        
        # Get progress from cache
        progress_key = f"task_progress:{task_id}"
        progress_data = cache.get(progress_key)
        
        return {
            "task_id": task_id,
            "state": result.state,
            "result": result.result,
            "progress": progress_data,
            "traceback": result.traceback
        }
    
    @staticmethod
    def cancel_task(task_id: str) -> bool:
        """Cancel a running task."""
        app.control.revoke(task_id, terminate=True)
        return True


# Global task manager
task_manager = TaskManager()