"""
Document Processing Service for RAG Pipeline - Step 2 Implementation.

This service integrates the existing document processors, text chunking, 
and model creation to provide a complete document-to-chunks pipeline.
"""

import os
import hashlib
import mimetypes
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import structlog
from django.utils import timezone
from django.conf import settings

from .document_processors import document_processor_factory, ProcessedDocument
from .text_chunking import ChunkerFactory, ChunkingConfig, ChunkingStrategy, TextChunk
from .exceptions import DocumentProcessingError, TextExtractionError, ChunkingError
from apps.knowledge.models import KnowledgeSource, KnowledgeChunk, ProcessingJob
from apps.core.models import ProcessingStatus

logger = structlog.get_logger()


@dataclass
class DocumentProcessingResult:
    """Result of complete document processing."""
    source: KnowledgeSource
    processed_document: Optional[ProcessedDocument]
    chunks: List[KnowledgeChunk]
    processing_job: Optional[ProcessingJob]
    total_tokens: int
    processing_time_ms: int
    success: bool
    error_message: Optional[str] = None


class DocumentProcessingService:
    """
    Service for processing documents into knowledge chunks.
    
    Integrates document extraction, text chunking, and database storage
    to provide a complete pipeline from file upload to searchable chunks.
    """
    
    def __init__(self):
        """Initialize document processing service."""
        self.logger = structlog.get_logger().bind(service="DocumentProcessingService")
        
        # Default chunking configuration
        self.default_chunking_config = ChunkingConfig(
            chunk_size=1000,
            chunk_overlap=200,
            strategy=ChunkingStrategy.RECURSIVE_CHARACTER,
            min_chunk_size=100,
            max_chunk_size=2000,
            preserve_structure=True
        )
    
    def process_uploaded_file(
        self,
        knowledge_source: KnowledgeSource,
        file_content: bytes,
        filename: str,
        mime_type: str,
        chunking_config: Optional[ChunkingConfig] = None
    ) -> DocumentProcessingResult:
        """
        Process an uploaded file into knowledge chunks.
        
        Args:
            knowledge_source: The KnowledgeSource instance
            file_content: Raw file bytes
            filename: Original filename
            mime_type: MIME type of the file
            chunking_config: Optional chunking configuration
            
        Returns:
            DocumentProcessingResult: Complete processing result
        """
        start_time = timezone.now()
        
        try:
            self.logger.info(
                "Starting document processing",
                source_id=str(knowledge_source.id),
                filename=filename,
                mime_type=mime_type,
                file_size=len(file_content),
                is_citable=knowledge_source.is_citable
            )
            
            # Create processing job
            processing_job = ProcessingJob.objects.create(
                source=knowledge_source,
                job_type='extract_text',
                status=ProcessingStatus.PROCESSING,
                result_data={}
            )
            
            # Update knowledge source status
            knowledge_source.update_processing_status(
                ProcessingStatus.PROCESSING,
                chunk_count=0,
                token_count=0
            )
            
            # Step 1: Extract text content
            self.logger.info("Extracting text content", source_id=str(knowledge_source.id))
            
            try:
                processor = document_processor_factory.create_processor(mime_type)
                processed_doc = processor.extract_text(file_content, filename)
            except Exception as e:
                error_msg = f"Text extraction failed: {str(e)}"
                self._handle_processing_error(knowledge_source, processing_job, error_msg)
                return DocumentProcessingResult(
                    source=knowledge_source,
                    processed_document=None,
                    chunks=[],
                    processing_job=processing_job,
                    total_tokens=0,
                    processing_time_ms=0,
                    success=False,
                    error_message=error_msg
                )
            
            # Update content preview
            preview_text = processed_doc.text_content[:500] if processed_doc.text_content else ""
            knowledge_source.content_preview = preview_text
            knowledge_source.save(update_fields=['content_preview'])
            
            # Step 2: Chunk the text
            self.logger.info(
                "Chunking document text",
                source_id=str(knowledge_source.id),
                text_length=len(processed_doc.text_content),
                word_count=processed_doc.word_count
            )
            
            try:
                config = chunking_config or self.default_chunking_config
                chunker = ChunkerFactory.create_chunker(config)
                
                # Add document metadata for chunking context
                doc_metadata = {
                    'filename': filename,
                    'mime_type': mime_type,
                    'source_id': str(knowledge_source.id),
                    'is_citable': knowledge_source.is_citable,
                    **processed_doc.metadata
                }
                
                text_chunks = chunker.chunk_text(processed_doc.text_content, doc_metadata)
                
            except Exception as e:
                error_msg = f"Text chunking failed: {str(e)}"
                self._handle_processing_error(knowledge_source, processing_job, error_msg)
                return DocumentProcessingResult(
                    source=knowledge_source,
                    processed_document=processed_doc,
                    chunks=[],
                    processing_job=processing_job,
                    total_tokens=0,
                    processing_time_ms=0,
                    success=False,
                    error_message=error_msg
                )
            
            # Step 3: Create KnowledgeChunk records
            self.logger.info(
                "Creating knowledge chunks in database",
                source_id=str(knowledge_source.id),
                chunk_count=len(text_chunks)
            )
            
            try:
                knowledge_chunks = self._create_knowledge_chunks(
                    knowledge_source, text_chunks, processed_doc
                )
            except Exception as e:
                error_msg = f"Database chunk creation failed: {str(e)}"
                self._handle_processing_error(knowledge_source, processing_job, error_msg)
                return DocumentProcessingResult(
                    source=knowledge_source,
                    processed_document=processed_doc,
                    chunks=[],
                    processing_job=processing_job,
                    total_tokens=0,
                    processing_time_ms=0,
                    success=False,
                    error_message=error_msg
                )
            
            # Calculate totals
            total_tokens = sum(chunk.token_count for chunk in knowledge_chunks)
            processing_time_ms = int((timezone.now() - start_time).total_seconds() * 1000)
            
            # Step 4: Trigger embedding generation (async)
            self.logger.info(
                "Triggering embedding generation for chunks",
                source_id=str(knowledge_source.id),
                chunk_count=len(knowledge_chunks)
            )
            
            try:
                from .tasks import generate_embeddings_for_knowledge_chunks
                
                # Trigger embedding generation task
                embedding_task = generate_embeddings_for_knowledge_chunks.apply_async(
                    args=[str(knowledge_source.id)],
                    kwargs={
                        'force_regenerate': False,
                        'batch_size': 50
                    },
                    priority=1  # Normal priority
                )
                
                self.logger.info(
                    "Embedding generation task queued",
                    source_id=str(knowledge_source.id),
                    embedding_task_id=embedding_task.id
                )
                
            except Exception as e:
                self.logger.warning(
                    "Failed to queue embedding generation task",
                    source_id=str(knowledge_source.id),
                    error=str(e)
                )
                # Don't fail the whole process if embedding queueing fails
            
            # Step 5: Update final status
            knowledge_source.update_processing_status(
                ProcessingStatus.COMPLETED,
                chunk_count=len(knowledge_chunks),
                token_count=total_tokens
            )
            
            # Update processing job
            processing_job.status = ProcessingStatus.COMPLETED
            processing_job.result_data = {
                'chunks_created': len(knowledge_chunks),
                'total_tokens': total_tokens,
                'processing_time_ms': processing_time_ms,
                'quality_score': processed_doc.quality_score,
                'metadata': processed_doc.metadata,
                'embedding_task_queued': True
            }
            processing_job.completed_at = timezone.now()
            processing_job.save()
            
            self.logger.info(
                "Document processing completed successfully",
                source_id=str(knowledge_source.id),
                chunks_created=len(knowledge_chunks),
                total_tokens=total_tokens,
                processing_time_ms=processing_time_ms,
                quality_score=processed_doc.quality_score
            )
            
            return DocumentProcessingResult(
                source=knowledge_source,
                processed_document=processed_doc,
                chunks=knowledge_chunks,
                processing_job=processing_job,
                total_tokens=total_tokens,
                processing_time_ms=processing_time_ms,
                success=True
            )
            
        except Exception as e:
            error_msg = f"Unexpected processing error: {str(e)}"
            self.logger.error(
                "Document processing failed with unexpected error",
                source_id=str(knowledge_source.id),
                error=error_msg,
                error_type=type(e).__name__
            )
            
            # Ensure cleanup on any unexpected error
            try:
                processing_job = processing_job if 'processing_job' in locals() else None
                self._handle_processing_error(knowledge_source, processing_job, error_msg)
            except:
                pass  # Don't let cleanup errors mask the original error
            
            return DocumentProcessingResult(
                source=knowledge_source,
                processed_document=None,
                chunks=[],
                processing_job=processing_job if 'processing_job' in locals() else None,
                total_tokens=0,
                processing_time_ms=0,
                success=False,
                error_message=error_msg
            )
    
    def process_url_content(
        self,
        knowledge_source: KnowledgeSource,
        url: str,
        chunking_config: Optional[ChunkingConfig] = None
    ) -> DocumentProcessingResult:
        """
        Process URL content into knowledge chunks.
        
        Args:
            knowledge_source: The KnowledgeSource instance
            url: URL to process
            chunking_config: Optional chunking configuration
            
        Returns:
            DocumentProcessingResult: Complete processing result
        """
        start_time = timezone.now()
        
        try:
            self.logger.info(
                "Starting URL processing",
                source_id=str(knowledge_source.id),
                url=url,
                is_citable=knowledge_source.is_citable
            )
            
            # Create processing job
            processing_job = ProcessingJob.objects.create(
                source=knowledge_source,
                job_type='url_crawl',
                status=ProcessingStatus.PROCESSING,
                result_data={}
            )
            
            # Update knowledge source status
            knowledge_source.update_processing_status(
                ProcessingStatus.PROCESSING,
                chunk_count=0,
                token_count=0
            )
            
            # Step 1: Crawl URL and extract content
            self.logger.info("Crawling URL content", source_id=str(knowledge_source.id), url=url)
            
            try:
                content, metadata = self._crawl_url(url)
                
                # Create a ProcessedDocument object from URL content
                processed_doc = ProcessedDocument(
                    text_content=content,
                    metadata=metadata,
                    word_count=len(content.split()),
                    char_count=len(content),
                    processing_time_ms=0,
                    quality_score=1.0
                )
                
            except Exception as e:
                error_msg = f"URL crawling failed: {str(e)}"
                self._handle_processing_error(knowledge_source, processing_job, error_msg)
                return DocumentProcessingResult(
                    source=knowledge_source,
                    processed_document=None,
                    chunks=[],
                    processing_job=processing_job,
                    total_tokens=0,
                    processing_time_ms=0,
                    success=False,
                    error_message=error_msg
                )
            
            # Continue with same chunking process as files
            return self._process_extracted_content(
                knowledge_source, processed_doc, processing_job, start_time, chunking_config
            )
            
        except Exception as e:
            error_msg = f"Unexpected URL processing error: {str(e)}"
            self.logger.error(
                "URL processing failed with unexpected error",
                source_id=str(knowledge_source.id),
                url=url,
                error=error_msg,
                error_type=type(e).__name__
            )
            
            try:
                processing_job = processing_job if 'processing_job' in locals() else None
                self._handle_processing_error(knowledge_source, processing_job, error_msg)
            except:
                pass
            
            return DocumentProcessingResult(
                source=knowledge_source,
                processed_document=None,
                chunks=[],
                processing_job=processing_job if 'processing_job' in locals() else None,
                total_tokens=0,
                processing_time_ms=0,
                success=False,
                error_message=error_msg
            )
    
    def _process_extracted_content(
        self,
        knowledge_source: KnowledgeSource,
        processed_doc: ProcessedDocument,
        processing_job: ProcessingJob,
        start_time,
        chunking_config: Optional[ChunkingConfig] = None
    ) -> DocumentProcessingResult:
        """Process already extracted content (common for files and URLs)."""
        
        # Update content preview
        preview_text = processed_doc.text_content[:500] if processed_doc.text_content else ""
        knowledge_source.content_preview = preview_text
        knowledge_source.save(update_fields=['content_preview'])
        
        # Step 2: Chunk the text
        self.logger.info(
            "Chunking extracted text",
            source_id=str(knowledge_source.id),
            text_length=len(processed_doc.text_content),
            word_count=processed_doc.word_count
        )
        
        try:
            config = chunking_config or self.default_chunking_config
            chunker = ChunkerFactory.create_chunker(config)
            
            # Add source metadata for chunking context
            doc_metadata = {
                'source_id': str(knowledge_source.id),
                'is_citable': knowledge_source.is_citable,
                **processed_doc.metadata
            }
            
            text_chunks = chunker.chunk_text(processed_doc.text_content, doc_metadata)
            
        except Exception as e:
            error_msg = f"Text chunking failed: {str(e)}"
            self._handle_processing_error(knowledge_source, processing_job, error_msg)
            return DocumentProcessingResult(
                source=knowledge_source,
                processed_document=processed_doc,
                chunks=[],
                processing_job=processing_job,
                total_tokens=0,
                processing_time_ms=0,
                success=False,
                error_message=error_msg
            )
        
        # Step 3: Create KnowledgeChunk records
        self.logger.info(
            "Creating knowledge chunks in database",
            source_id=str(knowledge_source.id),
            chunk_count=len(text_chunks)
        )
        
        try:
            knowledge_chunks = self._create_knowledge_chunks(
                knowledge_source, text_chunks, processed_doc
            )
        except Exception as e:
            error_msg = f"Database chunk creation failed: {str(e)}"
            self._handle_processing_error(knowledge_source, processing_job, error_msg)
            return DocumentProcessingResult(
                source=knowledge_source,
                processed_document=processed_doc,
                chunks=[],
                processing_job=processing_job,
                total_tokens=0,
                processing_time_ms=0,
                success=False,
                error_message=error_msg
            )
        
        # Calculate totals
        total_tokens = sum(chunk.token_count for chunk in knowledge_chunks)
        processing_time_ms = int((timezone.now() - start_time).total_seconds() * 1000)
        
        # Step 4: Trigger embedding generation (async)
        self.logger.info(
            "Triggering embedding generation for chunks",
            source_id=str(knowledge_source.id),
            chunk_count=len(knowledge_chunks)
        )
        
        try:
            from .tasks import generate_embeddings_for_knowledge_chunks
            
            # Trigger embedding generation task
            embedding_task = generate_embeddings_for_knowledge_chunks.apply_async(
                args=[str(knowledge_source.id)],
                kwargs={
                    'force_regenerate': False,
                    'batch_size': 50
                },
                priority=1  # Normal priority
            )
            
            self.logger.info(
                "Embedding generation task queued",
                source_id=str(knowledge_source.id),
                embedding_task_id=embedding_task.id
            )
            
        except Exception as e:
            self.logger.warning(
                "Failed to queue embedding generation task",
                source_id=str(knowledge_source.id),
                error=str(e)
            )
            # Don't fail the whole process if embedding queueing fails
        
        # Step 5: Update final status
        knowledge_source.update_processing_status(
            ProcessingStatus.COMPLETED,
            chunk_count=len(knowledge_chunks),
            token_count=total_tokens
        )
        
        # Update processing job
        processing_job.status = ProcessingStatus.COMPLETED
        processing_job.result_data = {
            'chunks_created': len(knowledge_chunks),
            'total_tokens': total_tokens,
            'processing_time_ms': processing_time_ms,
            'quality_score': processed_doc.quality_score,
            'metadata': processed_doc.metadata,
            'embedding_task_queued': True
        }
        processing_job.completed_at = timezone.now()
        processing_job.save()
        
        self.logger.info(
            "Content processing completed successfully",
            source_id=str(knowledge_source.id),
            chunks_created=len(knowledge_chunks),
            total_tokens=total_tokens,
            processing_time_ms=processing_time_ms,
            quality_score=processed_doc.quality_score
        )
        
        return DocumentProcessingResult(
            source=knowledge_source,
            processed_document=processed_doc,
            chunks=knowledge_chunks,
            processing_job=processing_job,
            total_tokens=total_tokens,
            processing_time_ms=processing_time_ms,
            success=True
        )
    
    def _create_knowledge_chunks(
        self,
        knowledge_source: KnowledgeSource,
        text_chunks: List[TextChunk],
        processed_doc: ProcessedDocument
    ) -> List[KnowledgeChunk]:
        """
        Create KnowledgeChunk records from TextChunk objects.
        
        Args:
            knowledge_source: The source to associate chunks with
            text_chunks: List of TextChunk objects
            processed_doc: The processed document
            
        Returns:
            List[KnowledgeChunk]: Created knowledge chunks
        """
        knowledge_chunks = []
        
        for text_chunk in text_chunks:
            # Create chunk metadata including original document info
            chunk_metadata = {
                'chunk_strategy': str(text_chunk.metadata.get('strategy', 'unknown')),
                'quality_score': text_chunk.quality_score,
                'start_char': text_chunk.start_index,
                'end_char': text_chunk.end_index,
                'overlap_previous': text_chunk.overlap_with_previous,
                'overlap_next': text_chunk.overlap_with_next,
                'document_metadata': processed_doc.metadata,
                **text_chunk.metadata
            }
            
            # Create KnowledgeChunk with privacy inheritance
            knowledge_chunk = KnowledgeChunk.objects.create(
                source=knowledge_source,
                content=text_chunk.content,
                chunk_index=text_chunk.metadata.get('chunk_index', 0),
                start_char=text_chunk.start_index,
                end_char=text_chunk.end_index,
                is_citable=knowledge_source.is_citable,  # Inherit privacy setting
                token_count=text_chunk.token_count,
                metadata=chunk_metadata
            )
            
            knowledge_chunks.append(knowledge_chunk)
            
            self.logger.debug(
                "Created knowledge chunk",
                source_id=str(knowledge_source.id),
                chunk_id=str(knowledge_chunk.id),
                chunk_index=knowledge_chunk.chunk_index,
                token_count=knowledge_chunk.token_count,
                is_citable=knowledge_chunk.is_citable,
                quality_score=text_chunk.quality_score
            )
        
        return knowledge_chunks
    
    def _crawl_url(self, url: str) -> Tuple[str, Dict[str, Any]]:
        """
        Crawl URL and extract text content.
        
        Args:
            url: URL to crawl
            
        Returns:
            Tuple[str, Dict]: (extracted_text, metadata)
        """
        import requests
        from bs4 import BeautifulSoup
        
        try:
            # Make request with reasonable timeout and headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; ChatbotSaaS/1.0; +http://example.com/bot)'
            }
            
            response = requests.get(url, timeout=30, headers=headers)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            # Extract title
            title = soup.title.string.strip() if soup.title else ""
            
            # Extract main content
            content = soup.get_text()
            
            # Clean up whitespace
            content = '\n'.join(line.strip() for line in content.splitlines() if line.strip())
            
            metadata = {
                'url': url,
                'title': title,
                'content_type': response.headers.get('content-type', ''),
                'status_code': response.status_code,
                'content_length': len(content),
                'extracted_at': timezone.now().isoformat()
            }
            
            return content, metadata
            
        except requests.RequestException as e:
            raise DocumentProcessingError(f"Failed to fetch URL {url}: {str(e)}")
        except Exception as e:
            raise DocumentProcessingError(f"Failed to parse URL content: {str(e)}")
    
    def _handle_processing_error(
        self,
        knowledge_source: KnowledgeSource,
        processing_job: Optional[ProcessingJob],
        error_message: str
    ):
        """Handle processing errors by updating statuses."""
        
        # Update knowledge source
        knowledge_source.update_processing_status(
            ProcessingStatus.FAILED,
            error_message=error_message
        )
        
        # Update processing job
        if processing_job:
            processing_job.status = ProcessingStatus.FAILED
            processing_job.error_details = error_message
            processing_job.completed_at = timezone.now()
            processing_job.save()
        
        self.logger.error(
            "Document processing failed",
            source_id=str(knowledge_source.id),
            error=error_message
        )
    
    def get_supported_mime_types(self) -> List[str]:
        """Get list of supported MIME types."""
        return document_processor_factory.get_supported_mime_types()
    
    def cleanup_failed_processing(self, knowledge_source: KnowledgeSource):
        """Clean up after failed processing."""
        try:
            # Delete any chunks that might have been created
            knowledge_source.chunks.all().delete()
            
            # Reset source status
            knowledge_source.chunk_count = 0
            knowledge_source.token_count = 0
            knowledge_source.content_preview = ""
            knowledge_source.save()
            
            self.logger.info(
                "Cleaned up failed processing",
                source_id=str(knowledge_source.id)
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to cleanup after processing error",
                source_id=str(knowledge_source.id),
                cleanup_error=str(e)
            )


# Global service instance
document_processing_service = DocumentProcessingService()