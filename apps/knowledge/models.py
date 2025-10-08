"""
Knowledge source models with multi-layer privacy enforcement.

CRITICAL: This module implements the core privacy controls to prevent
data leaks between "citable" and "learn-only" content. Every query
MUST respect the is_citable flag at multiple layers.
"""

from django.db import models
from django.core.validators import FileExtensionValidator
import structlog
import hashlib

from apps.core.models import BaseModel, ProcessingStatus, ContentType, JSONField

logger = structlog.get_logger()


class KnowledgeSource(BaseModel):
    """
    Knowledge source with CRITICAL privacy controls.
    
    The is_citable field is the foundation of our multi-layer privacy system:
    - is_citable=True: Content can be cited and shown to users
    - is_citable=False: Content used for context only, NEVER shown or referenced
    """
    
    chatbot = models.ForeignKey(
        'chatbots.Chatbot',
        on_delete=models.CASCADE,
        related_name='knowledge_sources'
    )
    
    # Basic info
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Source type and content
    content_type = models.CharField(
        max_length=20,
        choices=ContentType.choices
    )
    
    # File-based sources
    file_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="S3 key or file path"
    )
    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="File size in bytes"
    )
    file_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="SHA-256 hash for deduplication"
    )
    mime_type = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    
    # URL-based sources
    source_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL for web pages or videos"
    )
    
    # CRITICAL PRIVACY CONTROL
    is_citable = models.BooleanField(
        default=True,
        help_text="CRITICAL: Can this source be cited and shown to users?"
    )
    
    # Processing status
    status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Error details if processing failed"
    )
    
    # Processing metadata
    processed_at = models.DateTimeField(null=True, blank=True)
    chunk_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of chunks created from this source"
    )
    token_count = models.PositiveIntegerField(
        default=0,
        help_text="Total tokens in processed content"
    )
    
    # Content preview (first 500 chars for admin)
    content_preview = models.TextField(
        null=True,
        blank=True,
        help_text="First 500 characters for preview"
    )
    
    # Metadata
    metadata = JSONField(
        help_text="Processing metadata and source info"
    )
    
    class Meta:
        db_table = 'knowledge_sources'
        verbose_name = 'Knowledge Source'
        verbose_name_plural = 'Knowledge Sources'
        indexes = [
            models.Index(fields=['chatbot']),
            models.Index(fields=['content_type']),
            models.Index(fields=['status']),
            models.Index(fields=['is_citable']),  # CRITICAL INDEX
            models.Index(fields=['file_hash']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['chatbot', 'file_hash'],
                condition=models.Q(file_hash__isnull=False),
                name='unique_file_per_chatbot'
            )
        ]
    
    def __str__(self):
        privacy_label = "CITABLE" if self.is_citable else "LEARN-ONLY"
        return f"{self.name} [{privacy_label}] ({self.chatbot.name})"
    
    def calculate_file_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of file content."""
        return hashlib.sha256(content).hexdigest()
    
    def update_processing_status(
        self,
        status: str,
        error_message: str = None,
        chunk_count: int = None,
        token_count: int = None
    ) -> None:
        """Update processing status with optional metadata."""
        from django.utils import timezone
        
        self.status = status
        if error_message:
            self.error_message = error_message
        if chunk_count is not None:
            self.chunk_count = chunk_count
        if token_count is not None:
            self.token_count = token_count
        
        if status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
            self.processed_at = timezone.now()
        
        self.save(update_fields=[
            'status',
            'error_message',
            'chunk_count',
            'token_count',
            'processed_at'
        ])
        
        logger.info(
            "Knowledge source processing status updated",
            source_id=str(self.id),
            chatbot_id=str(self.chatbot.id),
            status=status,
            is_citable=self.is_citable,
            error=error_message
        )
    
    @property
    def is_ready(self) -> bool:
        """Check if source is ready for use."""
        return self.status == ProcessingStatus.COMPLETED
    
    @property
    def privacy_label(self) -> str:
        """Get human-readable privacy label."""
        return "Citable" if self.is_citable else "Learn-Only"


class KnowledgeChunk(BaseModel):
    """
    Text chunks from knowledge sources with privacy inheritance.
    
    CRITICAL: Each chunk inherits the is_citable flag from its source.
    This enables database-level filtering to prevent privacy leaks.
    """
    
    source = models.ForeignKey(
        KnowledgeSource,
        on_delete=models.CASCADE,
        related_name='chunks'
    )
    
    # Content
    content = models.TextField(help_text="The actual text content")
    content_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 hash for deduplication"
    )
    
    # Chunk positioning
    chunk_index = models.PositiveIntegerField(
        help_text="Order of this chunk within the source"
    )
    start_char = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Start character position in original content"
    )
    end_char = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="End character position in original content"
    )
    
    # CRITICAL: Privacy flag inherited from source
    is_citable = models.BooleanField(
        help_text="CRITICAL: Inherited from source - can this be cited?"
    )
    
    # Content metadata
    token_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of tokens in this chunk"
    )
    
    # Vector embedding (stored as base64 or JSON)
    embedding_vector = models.JSONField(
        null=True,
        blank=True,
        help_text="Vector embedding for similarity search"
    )
    embedding_model = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Model used to generate embedding"
    )
    
    # Chunk metadata (page numbers, sections, etc.)
    metadata = JSONField(
        help_text="Chunk-specific metadata (page, section, etc.)"
    )
    
    class Meta:
        db_table = 'knowledge_chunks'
        verbose_name = 'Knowledge Chunk'
        verbose_name_plural = 'Knowledge Chunks'
        indexes = [
            models.Index(fields=['source']),
            models.Index(fields=['source', 'chunk_index']),
            models.Index(fields=['is_citable']),  # CRITICAL INDEX
            models.Index(fields=['content_hash']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['source', 'chunk_index'],
                name='unique_chunk_index_per_source'
            ),
            models.UniqueConstraint(
                fields=['source', 'content_hash'],
                name='unique_chunk_content_per_source'
            )
        ]
    
    def __str__(self):
        privacy_label = "CITABLE" if self.is_citable else "LEARN-ONLY"
        preview = self.content[:100] + "..." if len(self.content) > 100 else self.content
        return f"Chunk {self.chunk_index} [{privacy_label}]: {preview}"
    
    def save(self, *args, **kwargs):
        """Auto-inherit privacy setting from source."""
        if not hasattr(self, '_privacy_inherited'):
            self.is_citable = self.source.is_citable
            self._privacy_inherited = True
        
        # Calculate content hash
        if not self.content_hash:
            self.content_hash = hashlib.sha256(
                self.content.encode('utf-8')
            ).hexdigest()
        
        super().save(*args, **kwargs)
    
    @property
    def privacy_label(self) -> str:
        """Get human-readable privacy label."""
        return "Citable" if self.is_citable else "Learn-Only"
    
    def get_citation_info(self) -> dict:
        """
        Get citation information for this chunk.
        ONLY call this for citable chunks!
        """
        if not self.is_citable:
            logger.warning(
                "Attempted to get citation for non-citable chunk",
                chunk_id=str(self.id),
                source_id=str(self.source.id)
            )
            return {}
        
        citation = {
            "source_name": self.source.name,
            "source_type": self.source.content_type,
            "chunk_index": self.chunk_index,
        }
        
        # Add source-specific citation info
        if self.source.source_url:
            citation["url"] = self.source.source_url
        
        # Add page number if available
        if "page" in self.metadata:
            citation["page"] = self.metadata["page"]
        
        return citation


class CitationUsage(BaseModel):
    """
    Track which sources are cited in responses.
    This helps with analytics and compliance.
    """
    
    chatbot = models.ForeignKey(
        'chatbots.Chatbot',
        on_delete=models.CASCADE,
        related_name='citation_usage'
    )
    
    source = models.ForeignKey(
        KnowledgeSource,
        on_delete=models.CASCADE,
        related_name='citations'
    )
    
    chunk = models.ForeignKey(
        KnowledgeChunk,
        on_delete=models.CASCADE,
        related_name='citations'
    )
    
    # Only track citable sources
    conversation_id = models.UUIDField(
        help_text="ID of conversation where this was cited"
    )
    message_id = models.UUIDField(
        help_text="ID of specific message that cited this"
    )
    
    # Usage context
    query = models.TextField(help_text="User query that triggered citation")
    relevance_score = models.FloatField(
        help_text="Similarity score for this citation"
    )
    
    class Meta:
        db_table = 'citation_usage'
        verbose_name = 'Citation Usage'
        verbose_name_plural = 'Citation Usage'
        indexes = [
            models.Index(fields=['chatbot', 'created_at']),
            models.Index(fields=['source', 'created_at']),
            models.Index(fields=['conversation_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Citation: {self.source.name} (Score: {self.relevance_score:.3f})"


class ProcessingJob(BaseModel):
    """
    Track async processing jobs for knowledge sources.
    """
    
    source = models.ForeignKey(
        KnowledgeSource,
        on_delete=models.CASCADE,
        related_name='processing_jobs'
    )
    
    # Job info
    job_type = models.CharField(
        max_length=50,
        choices=[
            ('extract_text', 'Extract Text'),
            ('generate_chunks', 'Generate Chunks'),
            ('generate_embeddings', 'Generate Embeddings'),
            ('url_crawl', 'Crawl URL'),
            ('video_transcribe', 'Transcribe Video'),
        ]
    )
    
    # Celery task info
    celery_task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Celery task ID for tracking"
    )
    
    # Status and progress
    status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING
    )
    progress_percentage = models.FloatField(
        default=0.0,
        help_text="Processing progress (0-100)"
    )
    
    # Results and errors
    result_data = JSONField(
        help_text="Job results and metadata"
    )
    error_details = models.TextField(
        null=True,
        blank=True,
        help_text="Detailed error information"
    )
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'processing_jobs'
        verbose_name = 'Processing Job'
        verbose_name_plural = 'Processing Jobs'
        indexes = [
            models.Index(fields=['source']),
            models.Index(fields=['celery_task_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.job_type} for {self.source.name} ({self.status})"
    
    def update_progress(self, percentage: float, status: str = None) -> None:
        """Update job progress."""
        from django.utils import timezone
        
        self.progress_percentage = percentage
        
        if status:
            self.status = status
            
            if status == ProcessingStatus.PROCESSING and not self.started_at:
                self.started_at = timezone.now()
            elif status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
                self.completed_at = timezone.now()
        
        self.save(update_fields=[
            'progress_percentage',
            'status',
            'started_at',
            'completed_at'
        ])
        
        logger.info(
            "Processing job progress updated",
            job_id=str(self.id),
            source_id=str(self.source.id),
            job_type=self.job_type,
            progress=percentage,
            status=status
        )
