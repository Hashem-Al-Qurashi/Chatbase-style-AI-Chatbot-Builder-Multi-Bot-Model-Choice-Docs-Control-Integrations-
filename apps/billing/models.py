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
    
    # Chatbase-style limits and features
    message_credits = models.PositiveIntegerField(
        default=50,
        help_text="Monthly message credits (Chatbase style)"
    )
    max_ai_agents = models.PositiveIntegerField(
        default=1,
        help_text="Maximum number of AI agents (chatbots)"
    )
    max_ai_actions = models.PositiveIntegerField(
        default=0,
        help_text="Maximum AI Actions per agent"
    )
    storage_limit_mb = models.PositiveIntegerField(
        default=1,
        help_text="Storage limit per AI agent in MB"
    )
    max_seats = models.PositiveIntegerField(
        default=1,
        help_text="Maximum number of team seats"
    )
    max_training_links = models.PositiveIntegerField(
        default=10,
        help_text="Maximum training links (0 = unlimited)"
    )
    
    # Plan features
    has_api_access = models.BooleanField(
        default=False,
        help_text="API access included"
    )
    has_integrations = models.BooleanField(
        default=False,
        help_text="Basic integrations included"
    )
    has_advanced_analytics = models.BooleanField(
        default=False,
        help_text="Advanced analytics included"
    )
    has_priority_support = models.BooleanField(
        default=False,
        help_text="Priority support included"
    )
    has_custom_branding = models.BooleanField(
        default=False,
        help_text="Custom branding options"
    )
    agents_persist = models.BooleanField(
        default=True,
        help_text="Agents persist (false = deleted after inactivity)"
    )
    inactivity_deletion_days = models.PositiveIntegerField(
        default=0,
        help_text="Days before deletion (0 = never delete)"
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
        return f"{self.name} (${self.price_monthly}/month) - {self.message_credits} credits"


class PlanAddon(BaseModel):
    """
    Additional features/resources that can be purchased.
    """
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Pricing
    price_monthly = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Monthly price in USD"
    )
    
    # What this addon provides
    addon_type = models.CharField(
        max_length=50,
        choices=[
            ('credits', 'Extra Message Credits'),
            ('agents', 'Additional AI Agents'),
            ('storage', 'Extra Storage'),
            ('branding', 'Custom Branding'),
            ('domain', 'Custom Domain'),
            ('support', 'Priority Support'),
        ]
    )
    
    # Addon values
    credits_amount = models.PositiveIntegerField(
        default=0,
        help_text="Additional message credits provided"
    )
    agents_amount = models.PositiveIntegerField(
        default=0,
        help_text="Additional agents provided"
    )
    storage_mb_amount = models.PositiveIntegerField(
        default=0,
        help_text="Additional storage in MB"
    )
    
    # Stripe integration
    stripe_price_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    
    # Display
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'plan_addons'
        verbose_name = 'Plan Addon'
        verbose_name_plural = 'Plan Addons'
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
    
    # Usage metrics (Chatbase style)
    message_credits_used = models.PositiveIntegerField(
        default=0,
        help_text="Message credits consumed"
    )
    messages_sent = models.PositiveIntegerField(default=0)
    tokens_used = models.PositiveIntegerField(default=0)
    embeddings_generated = models.PositiveIntegerField(default=0)
    storage_used_mb = models.FloatField(default=0.0)
    ai_actions_used = models.PositiveIntegerField(
        default=0,
        help_text="AI Actions executed"
    )
    
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
