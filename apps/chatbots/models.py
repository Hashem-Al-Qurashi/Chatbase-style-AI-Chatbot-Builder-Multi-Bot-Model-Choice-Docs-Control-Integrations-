"""
Chatbot models with privacy controls and CRM integration.
"""

from django.db import models
from django.core.validators import URLValidator
from django.utils.text import slugify
import structlog
import secrets
import string

from apps.core.models import BaseModel, ProcessingStatus, JSONField

logger = structlog.get_logger()


class Chatbot(BaseModel):
    """
    Main chatbot model with privacy settings and CRM integration.
    Critical: Implements multi-layer privacy enforcement.
    """
    
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='chatbots'
    )
    
    # Basic info
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Public URL and embedding
    public_url_slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Unique slug for public chatbot URL"
    )
    
    # Appearance
    theme_color = models.CharField(
        max_length=7,
        default="#2563EB",
        help_text="Hex color for chat widget theme"
    )
    welcome_message = models.TextField(
        default="Hello! How can I help you today?",
        help_text="Initial message shown to users"
    )
    placeholder_text = models.CharField(
        max_length=255,
        default="Type your message...",
        help_text="Placeholder text for input field"
    )
    
    # Behavior settings
    temperature = models.FloatField(
        default=0.7,
        help_text="LLM temperature for response generation"
    )
    max_tokens = models.PositiveIntegerField(
        default=500,
        help_text="Maximum tokens in response"
    )
    model_name = models.CharField(
        max_length=100,
        default="gpt-3.5-turbo",
        help_text="LLM model to use"
    )
    
    # Privacy and safety
    enable_citations = models.BooleanField(
        default=True,
        help_text="Show source citations for citable content"
    )
    enable_data_collection = models.BooleanField(
        default=False,
        help_text="Collect conversation data for analytics"
    )
    
    # CRM Integration
    crm_webhook_url = models.URLField(
        null=True,
        blank=True,
        validators=[URLValidator()],
        help_text="Webhook URL for pushing leads to CRM"
    )
    crm_webhook_secret = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Secret for webhook authentication"
    )
    
    # Status and metrics
    status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING
    )
    last_trained_at = models.DateTimeField(null=True, blank=True)
    total_conversations = models.PositiveIntegerField(default=0)
    total_messages = models.PositiveIntegerField(default=0)
    
    # Configuration
    metadata = JSONField(
        help_text="Additional chatbot configuration"
    )
    
    class Meta:
        db_table = 'chatbots'
        verbose_name = 'Chatbot'
        verbose_name_plural = 'Chatbots'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['public_url_slug']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_chatbot_name_per_user'
            )
        ]
    
    def __str__(self):
        return f"{self.name} ({self.user.email})"
    
    def save(self, *args, **kwargs):
        """Generate slug if not provided."""
        if not self.public_url_slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            
            while Chatbot.objects.filter(public_url_slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.public_url_slug = slug
        
        # Generate CRM webhook secret if URL is provided but no secret exists
        if self.crm_webhook_url and not self.crm_webhook_secret:
            self.crm_webhook_secret = self._generate_webhook_secret()
        
        super().save(*args, **kwargs)
    
    def _generate_webhook_secret(self) -> str:
        """Generate secure webhook secret."""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(32))
    
    @property
    def public_url(self) -> str:
        """Get full public URL for chatbot."""
        # This would be configured based on your domain
        return f"https://yourdomain.com/chat/{self.public_url_slug}"
    
    @property
    def embed_url(self) -> str:
        """Get embed URL for iframe."""
        return f"https://yourdomain.com/embed/{self.public_url_slug}"
    
    @property
    def embed_script(self) -> str:
        """Generate JavaScript embed script."""
        return f"""
<script>
(function() {{
    var chatbot = document.createElement('iframe');
    chatbot.src = '{self.embed_url}';
    chatbot.style.cssText = 'position:fixed;bottom:20px;right:20px;width:400px;height:600px;border:none;z-index:9999;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.15);';
    chatbot.title = 'Chat with {self.name}';
    document.body.appendChild(chatbot);
}})();
</script>
        """.strip()
    
    @property
    def is_ready(self) -> bool:
        """Check if chatbot is ready for use."""
        return self.status == ProcessingStatus.COMPLETED
    
    @property
    def has_knowledge_sources(self) -> bool:
        """Check if chatbot has any knowledge sources."""
        return self.knowledge_sources.filter(deleted_at__isnull=True).exists()
    
    def increment_conversation_count(self) -> None:
        """Increment conversation counter."""
        self.total_conversations += 1
        self.save(update_fields=['total_conversations'])
    
    def increment_message_count(self, count: int = 1) -> None:
        """Increment message counter."""
        self.total_messages += count
        self.save(update_fields=['total_messages'])
    
    def update_training_status(self, status: str) -> None:
        """Update training status."""
        from django.utils import timezone
        
        self.status = status
        if status == ProcessingStatus.COMPLETED:
            self.last_trained_at = timezone.now()
        
        self.save(update_fields=['status', 'last_trained_at'])
        
        logger.info(
            "Chatbot training status updated",
            chatbot_id=str(self.id),
            status=status,
            user_id=str(self.user.id)
        )


class ChatbotSettings(BaseModel):
    """
    Extended settings for chatbot customization.
    Separate model to avoid bloating main chatbot table.
    """
    
    chatbot = models.OneToOneField(
        Chatbot,
        on_delete=models.CASCADE,
        related_name='settings'
    )
    
    # Advanced behavior
    system_prompt = models.TextField(
        blank=True,
        help_text="Custom system prompt for the chatbot"
    )
    response_guidelines = models.TextField(
        blank=True,
        help_text="Guidelines for how the chatbot should respond"
    )
    
    # Rate limiting
    rate_limit_messages_per_hour = models.PositiveIntegerField(
        default=60,
        help_text="Max messages per hour per user"
    )
    rate_limit_messages_per_day = models.PositiveIntegerField(
        default=500,
        help_text="Max messages per day per user"
    )
    
    # Content filtering
    enable_profanity_filter = models.BooleanField(default=True)
    enable_spam_detection = models.BooleanField(default=True)
    blocked_words = models.JSONField(
        default=list,
        help_text="List of blocked words/phrases"
    )
    
    # Analytics
    enable_sentiment_analysis = models.BooleanField(default=False)
    enable_topic_extraction = models.BooleanField(default=False)
    
    # Lead capture
    enable_lead_capture = models.BooleanField(default=False)
    lead_capture_trigger = models.CharField(
        max_length=50,
        choices=[
            ('immediate', 'Immediately'),
            ('after_messages', 'After N messages'),
            ('keyword', 'On keyword trigger'),
            ('manual', 'Manual trigger only'),
        ],
        default='manual'
    )
    lead_capture_message = models.TextField(
        default="Would you like to leave your contact information for follow-up?",
        help_text="Message shown when capturing leads"
    )
    
    # Branding
    show_powered_by = models.BooleanField(
        default=True,
        help_text="Show 'Powered by Your Platform' branding"
    )
    custom_css = models.TextField(
        blank=True,
        help_text="Custom CSS for widget styling"
    )
    
    class Meta:
        db_table = 'chatbot_settings'
        verbose_name = 'Chatbot Settings'
        verbose_name_plural = 'Chatbot Settings'
    
    def __str__(self):
        return f"Settings for {self.chatbot.name}"


class ChatbotAnalytics(BaseModel):
    """
    Analytics and metrics for chatbot performance.
    """
    
    chatbot = models.ForeignKey(
        Chatbot,
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    
    # Time period
    date = models.DateField()
    hour = models.PositiveSmallIntegerField(null=True, blank=True)
    
    # Metrics
    unique_visitors = models.PositiveIntegerField(default=0)
    total_conversations = models.PositiveIntegerField(default=0)
    total_messages = models.PositiveIntegerField(default=0)
    avg_conversation_length = models.FloatField(default=0.0)
    avg_response_time = models.FloatField(default=0.0)  # in seconds
    
    # Engagement
    bounce_rate = models.FloatField(
        default=0.0,
        help_text="Percentage of users who left after first message"
    )
    user_satisfaction = models.FloatField(
        null=True,
        blank=True,
        help_text="Average user satisfaction score"
    )
    
    # Lead generation
    leads_captured = models.PositiveIntegerField(default=0)
    conversion_rate = models.FloatField(
        default=0.0,
        help_text="Percentage of conversations that captured leads"
    )
    
    # Popular topics/queries
    top_queries = models.JSONField(
        default=list,
        help_text="Most common user queries"
    )
    top_sources_cited = models.JSONField(
        default=list,
        help_text="Most frequently cited knowledge sources"
    )
    
    class Meta:
        db_table = 'chatbot_analytics'
        verbose_name = 'Chatbot Analytics'
        verbose_name_plural = 'Chatbot Analytics'
        indexes = [
            models.Index(fields=['chatbot', 'date']),
            models.Index(fields=['date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['chatbot', 'date', 'hour'],
                name='unique_analytics_per_hour'
            )
        ]
    
    def __str__(self):
        period = f"{self.date}"
        if self.hour is not None:
            period += f" {self.hour}:00"
        return f"{self.chatbot.name} Analytics - {period}"
