"""
API views for billing and pricing (Chatbase style).
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
import structlog

from .models import SubscriptionPlan, PlanAddon, UsageRecord
# Create inline serializers to avoid import issues
from rest_framework import serializers
from apps.core.plan_limits import PlanLimitsService

logger = structlog.get_logger()


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans."""
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'description', 'price_monthly', 'price_yearly',
            'message_credits', 'max_ai_agents', 'max_ai_actions', 'storage_limit_mb',
            'max_seats', 'max_training_links', 'has_api_access', 'has_integrations',
            'has_advanced_analytics', 'has_priority_support', 'has_custom_branding',
            'agents_persist', 'inactivity_deletion_days', 'features', 'is_popular'
        ]


class PlanAddonSerializer(serializers.ModelSerializer):
    """Serializer for plan add-ons."""
    
    class Meta:
        model = PlanAddon
        fields = [
            'id', 'name', 'description', 'price_monthly', 'addon_type',
            'credits_amount', 'agents_amount', 'storage_mb_amount'
        ]


class UsageRecordSerializer(serializers.ModelSerializer):
    """Serializer for usage records."""
    
    class Meta:
        model = UsageRecord
        fields = [
            'id', 'date', 'message_credits_used', 'messages_sent',
            'tokens_used', 'ai_actions_used', 'created_at'
        ]


class PricingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API for viewing pricing plans and add-ons (public access).
    """
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Return active plans ordered by price."""
        return SubscriptionPlan.objects.filter(
            is_active=True
        ).order_by('sort_order', 'price_monthly')
    
    @action(detail=False, methods=['get'])
    def addons(self, request):
        """Get available add-ons."""
        addons = PlanAddon.objects.filter(
            is_active=True
        ).order_by('sort_order', 'price_monthly')
        
        serializer = PlanAddonSerializer(addons, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def compare(self, request):
        """Get plan comparison data."""
        plans = self.get_queryset()
        addons = PlanAddon.objects.filter(is_active=True)
        
        comparison_data = {
            'plans': SubscriptionPlanSerializer(plans, many=True).data,
            'addons': PlanAddonSerializer(addons, many=True).data,
            'features_comparison': {
                'message_credits': [plan.message_credits for plan in plans],
                'max_ai_agents': [plan.max_ai_agents for plan in plans],
                'storage_limits': [plan.storage_limit_mb for plan in plans],
                'api_access': [plan.has_api_access for plan in plans],
                'integrations': [plan.has_integrations for plan in plans],
                'advanced_analytics': [plan.has_advanced_analytics for plan in plans],
            }
        }
        
        return Response(comparison_data)


class BillingViewSet(viewsets.ModelViewSet):
    """
    API for user billing and usage information.
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def current_plan(self, request):
        """Get current user's plan and usage."""
        user = request.user
        
        # Get plan limits and usage
        plan_data = PlanLimitsService.get_user_plan_limits(user)
        features = PlanLimitsService.get_plan_features(user)
        
        response_data = {
            'plan': {
                'tier': user.plan_tier,
                'message_credits': user.message_credits,
                'credits_used': user.credits_used,
                'credits_remaining': user.credits_remaining,
                'credits_percentage_used': user.credits_percentage_used,
                'max_ai_agents': user.max_ai_agents,
                'storage_limit_mb': user.storage_limit_mb,
                'max_ai_actions': user.max_ai_actions,
                'max_seats': user.max_seats,
                'credits_reset_date': user.credits_reset_date,
            },
            'features': features,
            'usage_stats': {
                'chatbots_created': user.chatbots.filter(deleted_at__isnull=True).count(),
                'total_conversations': user.conversations.count() if hasattr(user, 'conversations') else 0,
            },
            'billing_info': {
                'stripe_customer_id': user.stripe_customer_id,
                'subscription_id': user.subscription_id,
                'subscription_status': user.subscription_status,
                'subscription_current_period_end': user.subscription_current_period_end,
            }
        }
        
        return Response(response_data)
    
    @action(detail=False, methods=['post'])
    def check_limits(self, request):
        """Check if user can perform an action."""
        action_type = request.data.get('action')
        user = request.user
        
        if action_type == 'send_message':
            model_name = request.data.get('model', 'gpt-3.5-turbo')
            credits_needed = PlanLimitsService.get_credit_cost_for_model(model_name)
            can_proceed, reason = PlanLimitsService.can_send_message(user, credits_needed)
            
            return Response({
                'can_proceed': can_proceed,
                'reason': reason,
                'credits_needed': credits_needed,
                'credits_remaining': user.credits_remaining,
                'suggested_plan': PlanLimitsService.get_upgrade_suggestion(user, 'more_credits') if not can_proceed else None
            })
        
        elif action_type == 'create_chatbot':
            can_proceed, reason = PlanLimitsService.can_create_chatbot(user)
            
            return Response({
                'can_proceed': can_proceed,
                'reason': reason,
                'current_count': user.chatbots.filter(deleted_at__isnull=True).count(),
                'max_allowed': user.max_ai_agents,
                'suggested_plan': PlanLimitsService.get_upgrade_suggestion(user, 'more_agents') if not can_proceed else None
            })
        
        elif action_type == 'upload_file':
            file_size_mb = request.data.get('file_size_mb', 0)
            can_proceed, reason = PlanLimitsService.can_upload_file(user, file_size_mb)
            
            return Response({
                'can_proceed': can_proceed,
                'reason': reason,
                'file_size_mb': file_size_mb,
                'limit_mb': user.storage_limit_mb
            })
        
        else:
            return Response({
                'error': 'Invalid action type'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def consume_credits(self, request):
        """Consume message credits."""
        model_name = request.data.get('model', 'gpt-3.5-turbo')
        user = request.user
        
        success = PlanLimitsService.consume_message_credit(user, model_name)
        
        if success:
            return Response({
                'success': True,
                'credits_consumed': PlanLimitsService.get_credit_cost_for_model(model_name),
                'credits_remaining': user.credits_remaining,
                'credits_percentage_used': user.credits_percentage_used
            })
        else:
            return Response({
                'success': False,
                'error': 'Insufficient credits',
                'credits_remaining': user.credits_remaining,
                'suggested_plan': PlanLimitsService.get_upgrade_suggestion(user, 'more_credits')
            }, status=status.HTTP_402_PAYMENT_REQUIRED)
    
    @action(detail=False, methods=['get'])
    def usage_history(self, request):
        """Get usage history for the user."""
        user = request.user
        
        # Get recent usage records
        usage_records = UsageRecord.objects.filter(
            user=user
        ).order_by('-date')[:30]  # Last 30 days
        
        serializer = UsageRecordSerializer(usage_records, many=True)
        
        return Response({
            'usage_history': serializer.data,
            'current_period': {
                'credits_used': user.credits_used,
                'credits_total': user.message_credits,
                'reset_date': user.credits_reset_date,
            }
        })
    
    @action(detail=False, methods=['post'])
    def upgrade_plan(self, request):
        """Request plan upgrade (would integrate with Stripe)."""
        plan_name = request.data.get('plan')
        billing_cycle = request.data.get('billing_cycle', 'monthly')  # 'monthly' or 'yearly'
        
        # Validate plan exists
        try:
            plan = SubscriptionPlan.objects.get(
                name__iexact=plan_name,
                is_active=True
            )
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'error': 'Invalid plan'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # In production, this would create a Stripe checkout session
        # For now, return plan information for frontend to handle
        
        price = plan.price_yearly if billing_cycle == 'yearly' else plan.price_monthly
        
        return Response({
            'plan': SubscriptionPlanSerializer(plan).data,
            'price': price,
            'billing_cycle': billing_cycle,
            'savings': (plan.price_monthly * 12 - plan.price_yearly) if billing_cycle == 'yearly' else 0,
            'checkout_url': f'/checkout/{plan.id}/?cycle={billing_cycle}',  # Frontend route
            'features_gained': {
                'additional_credits': plan.message_credits - request.user.message_credits,
                'additional_agents': plan.max_ai_agents - request.user.max_ai_agents,
                'new_features': PlanLimitsService.get_plan_features(request.user)
            }
        })