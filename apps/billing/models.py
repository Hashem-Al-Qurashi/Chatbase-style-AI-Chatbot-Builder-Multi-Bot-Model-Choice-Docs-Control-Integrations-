"""
Billing and subscription models with Stripe integration.
"""

from django.db import models
from decimal import Decimal
import structlog

from apps.core.models import BaseModel, JSONField

logger = structlog.get_logger()


class SubscriptionPlan(BaseModel):
    """
    Available subscription plans.
    """
    
    # Plan info
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Pricing
    price_monthly = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monthly price in USD"
    )
    price_yearly = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Yearly price in USD (optional)"
    )
    
    # Stripe integration
    stripe_price_id_monthly = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Stripe price ID for monthly billing"
    )
    stripe_price_id_yearly = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Stripe price ID for yearly billing"
    )
    
    # Limits and features
    message_quota = models.PositiveIntegerField(
        help_text="Monthly message quota"
    )
    max_chatbots = models.PositiveIntegerField(
        help_text="Maximum number of chatbots"
    )
    max_knowledge_sources = models.PositiveIntegerField(
        help_text="Maximum knowledge sources per chatbot"
    )
    max_file_size_mb = models.PositiveIntegerField(
        help_text="Maximum file size in MB"
    )
    
    # Features
    features = JSONField(
        help_text="Available features for this plan"
    )
    
    # Display
    is_popular = models.BooleanField(
        default=False,
        help_text="Mark as popular plan"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is plan available for new subscriptions"
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Display order"
    )
    
    class Meta:
        db_table = 'subscription_plans'
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'
        ordering = ['sort_order', 'price_monthly']
    
    def __str__(self):
        return f"{self.name} (${self.price_monthly}/month)"


class UsageRecord(BaseModel):
    """
    Track usage for billing and analytics.
    """
    
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='usage_records'
    )
    
    # Time period
    date = models.DateField()
    hour = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Hour of day (0-23) for hourly tracking"
    )
    
    # Usage metrics
    messages_sent = models.PositiveIntegerField(default=0)
    tokens_used = models.PositiveIntegerField(default=0)
    embeddings_generated = models.PositiveIntegerField(default=0)
    storage_used_mb = models.FloatField(default=0.0)
    
    # Costs (for internal tracking)
    openai_cost = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="OpenAI API costs"
    )
    pinecone_cost = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Pinecone costs"
    )
    storage_cost = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="S3 storage costs"
    )
    
    class Meta:
        db_table = 'usage_records'
        verbose_name = 'Usage Record'
        verbose_name_plural = 'Usage Records'
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'date', 'hour'],
                name='unique_usage_per_hour'
            )
        ]
    
    def __str__(self):
        period = f"{self.date}"
        if self.hour is not None:
            period += f" {self.hour}:00"
        return f"{self.user.email} - {period}"
