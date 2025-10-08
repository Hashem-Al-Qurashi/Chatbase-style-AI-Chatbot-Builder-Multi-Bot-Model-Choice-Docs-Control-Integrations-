"""
Conversation and message models with privacy tracking.
"""

from django.db import models
from django.core.validators import validate_ipv4_address, validate_ipv6_address
import structlog
import uuid

from apps.core.models import BaseModel, MessageRole, JSONField

logger = structlog.get_logger()


class Conversation(BaseModel):
    """
    Chat conversation between user and chatbot.
    """
    
    chatbot = models.ForeignKey(
        'chatbots.Chatbot',
        on_delete=models.CASCADE,
        related_name='conversations'
    )
    
    # Session tracking
    session_id = models.UUIDField(
        default=uuid.uuid4,
        help_text="Unique session identifier"
    )
    
    # User info (anonymous users)
    user_identifier = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Anonymous user identifier (IP hash, fingerprint, etc.)"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="User IP address"
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        help_text="User agent string"
    )
    
    # Lead information (if captured)
    lead_email = models.EmailField(
        null=True,
        blank=True,
        help_text="Email if lead was captured"
    )
    lead_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Name if lead was captured"
    )
    lead_phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Phone if lead was captured"
    )
    lead_captured_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When lead was captured"
    )
    
    # Conversation metadata
    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Auto-generated conversation title"
    )
    language = models.CharField(
        max_length=10,
        default='en',
        help_text="Detected conversation language"
    )
    
    # Analytics
    message_count = models.PositiveIntegerField(
        default=0,
        help_text="Total messages in conversation"
    )
    user_satisfaction = models.FloatField(
        null=True,
        blank=True,
        help_text="User satisfaction rating (1-5)"
    )
    satisfaction_feedback = models.TextField(
        null=True,
        blank=True,
        help_text="User feedback text"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Is conversation still active"
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When conversation ended"
    )
    
    # Privacy and compliance
    data_retention_days = models.PositiveIntegerField(
        default=90,
        help_text="Days to retain conversation data"
    )
    
    # Metadata
    metadata = JSONField(
        help_text="Additional conversation metadata"
    )
    
    class Meta:
        db_table = 'conversations'
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
        indexes = [
            models.Index(fields=['chatbot']),
            models.Index(fields=['session_id']),
            models.Index(fields=['user_identifier']),
            models.Index(fields=['lead_email']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        title = self.title or f"Conversation {self.session_id}"
        return f"{title} - {self.chatbot.name}"
    
    def increment_message_count(self) -> None:
        """Increment message counter."""
        self.message_count += 1
        self.save(update_fields=['message_count'])
        
        # Also update chatbot counter
        self.chatbot.increment_message_count()
    
    def end_conversation(self) -> None:
        """End the conversation."""
        from django.utils import timezone
        
        self.is_active = False
        self.ended_at = timezone.now()
        self.save(update_fields=['is_active', 'ended_at'])
        
        logger.info(
            "Conversation ended",
            conversation_id=str(self.id),
            chatbot_id=str(self.chatbot.id),
            message_count=self.message_count
        )
    
    def capture_lead(
        self,
        email: str,
        name: str = None,
        phone: str = None
    ) -> None:
        """Capture lead information."""
        from django.utils import timezone
        
        self.lead_email = email
        self.lead_name = name
        self.lead_phone = phone
        self.lead_captured_at = timezone.now()
        
        self.save(update_fields=[
            'lead_email',
            'lead_name',
            'lead_phone',
            'lead_captured_at'
        ])
        
        logger.info(
            "Lead captured",
            conversation_id=str(self.id),
            chatbot_id=str(self.chatbot.id),
            email=email,
            name=name
        )
    
    def set_satisfaction(self, rating: float, feedback: str = None) -> None:
        """Set user satisfaction rating."""
        self.user_satisfaction = rating
        self.satisfaction_feedback = feedback
        
        self.save(update_fields=[
            'user_satisfaction',
            'satisfaction_feedback'
        ])
        
        logger.info(
            "Satisfaction rating set",
            conversation_id=str(self.id),
            rating=rating,
            has_feedback=bool(feedback)
        )
    
    @property
    def has_lead(self) -> bool:
        """Check if lead was captured."""
        return bool(self.lead_email)
    
    @property
    def duration_minutes(self) -> float:
        """Get conversation duration in minutes."""
        end_time = self.ended_at or self.updated_at
        duration = end_time - self.created_at
        return duration.total_seconds() / 60


class Message(BaseModel):
    """
    Individual message in a conversation with source tracking.
    """
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    # Message content
    role = models.CharField(
        max_length=20,
        choices=MessageRole.choices
    )
    content = models.TextField(help_text="Message content")
    
    # Message ordering
    sequence_number = models.PositiveIntegerField(
        help_text="Message order in conversation"
    )
    
    # Response generation metadata (for assistant messages)
    model_used = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="LLM model used for response"
    )
    temperature = models.FloatField(
        null=True,
        blank=True,
        help_text="Temperature used for generation"
    )
    token_usage = JSONField(
        help_text="Token usage statistics"
    )
    
    # Response timing
    generation_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Time taken to generate response in milliseconds"
    )
    
    # Sources used (ONLY citable sources)
    sources_cited = models.ManyToManyField(
        'knowledge.KnowledgeChunk',
        through='MessageSource',
        blank=True,
        help_text="Knowledge chunks cited in this message"
    )
    
    # Message flags
    is_helpful = models.BooleanField(
        null=True,
        blank=True,
        help_text="User feedback on message helpfulness"
    )
    is_flagged = models.BooleanField(
        default=False,
        help_text="Message flagged for review"
    )
    flag_reason = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Reason for flagging"
    )
    
    # Metadata
    metadata = JSONField(
        help_text="Additional message metadata"
    )
    
    class Meta:
        db_table = 'messages'
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        indexes = [
            models.Index(fields=['conversation']),
            models.Index(fields=['conversation', 'sequence_number']),
            models.Index(fields=['role']),
            models.Index(fields=['is_flagged']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['conversation', 'sequence_number'],
                name='unique_message_sequence'
            )
        ]
    
    def __str__(self):
        preview = self.content[:100] + "..." if len(self.content) > 100 else self.content
        return f"{self.role.title()} #{self.sequence_number}: {preview}"
    
    def save(self, *args, **kwargs):
        """Auto-set sequence number."""
        if not self.sequence_number:
            last_message = self.conversation.messages.order_by('sequence_number').last()
            self.sequence_number = (last_message.sequence_number + 1) if last_message else 1
        
        super().save(*args, **kwargs)
        
        # Update conversation message count
        if self._state.adding:
            self.conversation.increment_message_count()
    
    def add_source_citation(
        self,
        chunk: 'knowledge.KnowledgeChunk',
        relevance_score: float
    ) -> None:
        """
        Add source citation to message.
        CRITICAL: Only allows citable chunks.
        """
        if not chunk.is_citable:
            logger.warning(
                "Attempted to cite non-citable chunk",
                message_id=str(self.id),
                chunk_id=str(chunk.id),
                source_id=str(chunk.source.id)
            )
            return
        
        MessageSource.objects.create(
            message=self,
            chunk=chunk,
            relevance_score=relevance_score
        )
        
        # Track citation usage
        from apps.knowledge.models import CitationUsage
        CitationUsage.objects.create(
            chatbot=self.conversation.chatbot,
            source=chunk.source,
            chunk=chunk,
            conversation_id=self.conversation.id,
            message_id=self.id,
            query=self._get_user_query(),
            relevance_score=relevance_score
        )
    
    def _get_user_query(self) -> str:
        """Get the user query that triggered this response."""
        if self.role != MessageRole.ASSISTANT:
            return ""
        
        # Get the previous user message
        prev_message = self.conversation.messages.filter(
            sequence_number=self.sequence_number - 1,
            role=MessageRole.USER
        ).first()
        
        return prev_message.content if prev_message else ""
    
    def flag_message(self, reason: str) -> None:
        """Flag message for review."""
        self.is_flagged = True
        self.flag_reason = reason
        self.save(update_fields=['is_flagged', 'flag_reason'])
        
        logger.warning(
            "Message flagged",
            message_id=str(self.id),
            conversation_id=str(self.conversation.id),
            reason=reason
        )
    
    def set_helpfulness(self, is_helpful: bool) -> None:
        """Set user feedback on message helpfulness."""
        self.is_helpful = is_helpful
        self.save(update_fields=['is_helpful'])
        
        logger.info(
            "Message helpfulness feedback",
            message_id=str(self.id),
            is_helpful=is_helpful
        )


class MessageSource(BaseModel):
    """
    Junction table tracking which sources were cited in a message.
    CRITICAL: Only stores citable sources.
    """
    
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='source_citations'
    )
    
    chunk = models.ForeignKey(
        'knowledge.KnowledgeChunk',
        on_delete=models.CASCADE,
        related_name='message_citations'
    )
    
    # Citation metadata
    relevance_score = models.FloatField(
        help_text="Similarity/relevance score for this citation"
    )
    citation_text = models.TextField(
        null=True,
        blank=True,
        help_text="Specific text that was cited"
    )
    
    class Meta:
        db_table = 'message_sources'
        verbose_name = 'Message Source'
        verbose_name_plural = 'Message Sources'
        indexes = [
            models.Index(fields=['message']),
            models.Index(fields=['chunk']),
            models.Index(fields=['relevance_score']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['message', 'chunk'],
                name='unique_message_chunk_citation'
            )
        ]
    
    def __str__(self):
        return f"Citation: {self.chunk.source.name} (Score: {self.relevance_score:.3f})"
    
    def save(self, *args, **kwargs):
        """Ensure only citable chunks are stored."""
        if not self.chunk.is_citable:
            raise ValueError(
                f"Cannot cite non-citable chunk {self.chunk.id} "
                f"from source {self.chunk.source.id}"
            )
        
        super().save(*args, **kwargs)


class ConversationTag(BaseModel):
    """
    Tags for categorizing conversations (auto-generated or manual).
    """
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='tags'
    )
    
    # Tag info
    tag = models.CharField(max_length=100, help_text="Tag name")
    confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="Confidence score for auto-generated tags"
    )
    
    # Tag source
    is_auto_generated = models.BooleanField(
        default=True,
        help_text="Was this tag auto-generated?"
    )
    
    class Meta:
        db_table = 'conversation_tags'
        verbose_name = 'Conversation Tag'
        verbose_name_plural = 'Conversation Tags'
        indexes = [
            models.Index(fields=['conversation']),
            models.Index(fields=['tag']),
            models.Index(fields=['is_auto_generated']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['conversation', 'tag'],
                name='unique_conversation_tag'
            )
        ]
    
    def __str__(self):
        auto_label = " (auto)" if self.is_auto_generated else ""
        return f"{self.tag}{auto_label}"
