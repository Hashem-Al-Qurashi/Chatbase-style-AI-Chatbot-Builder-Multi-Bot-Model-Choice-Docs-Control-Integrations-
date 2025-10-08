"""
Webhook tracking and management models.
"""

from django.db import models
import structlog

from apps.core.models import BaseModel, JSONField

logger = structlog.get_logger()


class WebhookEvent(BaseModel):
    """
    Track incoming webhook events from external services.
    """
    
    # Event source
    source = models.CharField(
        max_length=50,
        choices=[
            ('stripe', 'Stripe'),
            ('crm', 'CRM'),
            ('user', 'User Webhook'),
        ]
    )
    
    # Event details
    event_id = models.CharField(
        max_length=255,
        help_text="External event ID"
    )
    event_type = models.CharField(
        max_length=100,
        help_text="Type of webhook event"
    )
    
    # Processing status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    
    # Request data
    payload = JSONField(help_text="Raw webhook payload")
    headers = JSONField(help_text="Request headers")
    
    # Processing results
    result = JSONField(help_text="Processing results")
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Error details if processing failed"
    )
    
    # Timing
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'webhook_events'
        verbose_name = 'Webhook Event'
        verbose_name_plural = 'Webhook Events'
        indexes = [
            models.Index(fields=['source', 'event_type']),
            models.Index(fields=['event_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.source}: {self.event_type} ({self.status})"
