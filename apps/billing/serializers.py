"""
Serializers for billing app.
Handles subscriptions and payment management.
"""

from rest_framework import serializers
from apps.billing.models import Subscription, Payment, UsageTracking


class SubscriptionSerializer(serializers.ModelSerializer):
    """Subscription serializer."""
    
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    days_until_renewal = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    
    class Meta:
        model = Subscription
        fields = (
            'id', 'organization', 'organization_name',
            'stripe_subscription_id', 'stripe_customer_id',
            'status', 'plan_name', 'price_amount', 'currency',
            'current_period_start', 'current_period_end',
            'trial_end', 'cancelled_at', 'days_until_renewal',
            'is_active', 'created_at', 'updated_at', 'metadata'
        )
        read_only_fields = (
            'id', 'stripe_subscription_id', 'stripe_customer_id',
            'current_period_start', 'current_period_end',
            'trial_end', 'cancelled_at', 'created_at', 'updated_at'
        )
    
    def get_days_until_renewal(self, obj):
        """Calculate days until renewal."""
        if obj.current_period_end:
            from django.utils import timezone
            delta = obj.current_period_end - timezone.now()
            return max(0, delta.days)
        return None
    
    def get_is_active(self, obj):
        """Check if subscription is active."""
        return obj.status in ['active', 'trialing']


class PaymentSerializer(serializers.ModelSerializer):
    """Payment serializer."""
    
    subscription_plan = serializers.CharField(source='subscription.plan_name', read_only=True)
    
    class Meta:
        model = Payment
        fields = (
            'id', 'subscription', 'subscription_plan',
            'stripe_payment_intent_id', 'amount', 'currency',
            'status', 'description', 'invoice_url',
            'created_at', 'metadata'
        )
        read_only_fields = fields


class UsageTrackingSerializer(serializers.ModelSerializer):
    """Usage tracking serializer."""
    
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    usage_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = UsageTracking
        fields = (
            'id', 'organization', 'organization_name',
            'period_start', 'period_end', 'chatbots_created',
            'messages_processed', 'storage_used_mb',
            'api_calls_made', 'usage_percentage',
            'created_at', 'updated_at'
        )
        read_only_fields = fields
    
    def get_usage_percentage(self, obj):
        """Calculate usage percentage based on plan limits."""
        # This would be calculated based on organization's plan limits
        return {
            'chatbots': min(100, (obj.chatbots_created / 10) * 100),  # Assuming 10 chatbot limit
            'messages': min(100, (obj.messages_processed / 10000) * 100),  # Assuming 10k message limit
            'storage': min(100, (obj.storage_used_mb / 5120) * 100),  # Assuming 5GB limit
            'api_calls': min(100, (obj.api_calls_made / 1000) * 100)  # Assuming 1k API call limit
        }


class CheckoutSessionSerializer(serializers.Serializer):
    """Checkout session creation serializer."""
    
    plan = serializers.ChoiceField(choices=['starter', 'professional', 'enterprise'])
    billing_period = serializers.ChoiceField(choices=['monthly', 'yearly'], default='monthly')
    success_url = serializers.URLField(required=False)
    cancel_url = serializers.URLField(required=False)


class BillingPortalSerializer(serializers.Serializer):
    """Billing portal session serializer."""
    
    return_url = serializers.URLField(required=False)


class UsageStatsSerializer(serializers.Serializer):
    """Usage statistics serializer."""
    
    period = serializers.ChoiceField(
        choices=['current', 'last_month', 'last_quarter', 'last_year'],
        default='current'
    )
    detailed = serializers.BooleanField(default=False)