"""
API views for billing app.
Handles subscription management and payments.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone
from django.db import models
import stripe
import structlog

from apps.billing.models import Subscription, Payment, UsageTracking
from apps.accounts.models import Organization
from apps.billing.serializers import (
    SubscriptionSerializer, PaymentSerializer,
    UsageTrackingSerializer, CheckoutSessionSerializer,
    BillingPortalSerializer, UsageStatsSerializer
)

logger = structlog.get_logger()

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class SubscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for subscription management.
    """
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter subscriptions by user's organizations."""
        user = self.request.user
        org_ids = user.team_memberships.filter(
            role__in=['owner', 'admin'],
            is_active=True
        ).values_list('organization_id', flat=True)
        
        return Subscription.objects.filter(organization_id__in=org_ids)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel subscription."""
        subscription = self.get_object()
        
        # Check permissions
        membership = subscription.organization.members.filter(
            user=request.user
        ).first()
        
        if not membership or membership.role != 'owner':
            raise ValidationError("Only organization owner can cancel subscription")
        
        try:
            # Cancel in Stripe
            stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            stripe_sub.cancel_at_period_end = True
            stripe_sub.save()
            
            # Update local record
            subscription.status = 'cancelling'
            subscription.cancelled_at = timezone.now()
            subscription.save()
            
            # Update organization
            subscription.organization.subscription_status = 'cancelling'
            subscription.organization.save()
            
            logger.info(
                "Subscription cancelled",
                subscription_id=str(subscription.id),
                organization_id=str(subscription.organization.id),
                user_id=str(request.user.id)
            )
            
            return Response({
                'message': 'Subscription will be cancelled at the end of the billing period',
                'cancel_at': subscription.current_period_end
            })
            
        except stripe.error.StripeError as e:
            logger.error(
                "Failed to cancel subscription",
                subscription_id=str(subscription.id),
                error=str(e)
            )
            raise ValidationError(f"Failed to cancel subscription: {str(e)}")
    
    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        """Reactivate a cancelled subscription."""
        subscription = self.get_object()
        
        # Check permissions
        membership = subscription.organization.members.filter(
            user=request.user
        ).first()
        
        if not membership or membership.role != 'owner':
            raise ValidationError("Only organization owner can reactivate subscription")
        
        if subscription.status != 'cancelling':
            raise ValidationError("Can only reactivate subscriptions pending cancellation")
        
        try:
            # Reactivate in Stripe
            stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            stripe_sub.cancel_at_period_end = False
            stripe_sub.save()
            
            # Update local record
            subscription.status = 'active'
            subscription.cancelled_at = None
            subscription.save()
            
            # Update organization
            subscription.organization.subscription_status = 'active'
            subscription.organization.save()
            
            logger.info(
                "Subscription reactivated",
                subscription_id=str(subscription.id),
                organization_id=str(subscription.organization.id)
            )
            
            return Response({'message': 'Subscription reactivated successfully'})
            
        except stripe.error.StripeError as e:
            logger.error(
                "Failed to reactivate subscription",
                subscription_id=str(subscription.id),
                error=str(e)
            )
            raise ValidationError(f"Failed to reactivate subscription: {str(e)}")
    
    @action(detail=True, methods=['post'])
    def change_plan(self, request, pk=None):
        """Change subscription plan."""
        subscription = self.get_object()
        new_plan = request.data.get('plan')
        
        if new_plan not in ['starter', 'professional', 'enterprise']:
            raise ValidationError("Invalid plan")
        
        # Check permissions
        membership = subscription.organization.members.filter(
            user=request.user
        ).first()
        
        if not membership or membership.role != 'owner':
            raise ValidationError("Only organization owner can change plan")
        
        try:
            # Get price ID for new plan
            price_ids = {
                'starter': settings.STRIPE_PRICE_STARTER,
                'professional': settings.STRIPE_PRICE_PROFESSIONAL,
                'enterprise': settings.STRIPE_PRICE_ENTERPRISE
            }
            
            # Update subscription in Stripe
            stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[{
                    'id': stripe_sub['items']['data'][0]['id'],
                    'price': price_ids[new_plan]
                }],
                proration_behavior='always_invoice'
            )
            
            # Update local record
            subscription.plan_name = new_plan
            subscription.save()
            
            # Update organization tier
            subscription.organization.subscription_tier = new_plan
            subscription.organization.save()
            
            logger.info(
                "Subscription plan changed",
                subscription_id=str(subscription.id),
                old_plan=subscription.plan_name,
                new_plan=new_plan
            )
            
            return Response({
                'message': 'Plan changed successfully',
                'new_plan': new_plan
            })
            
        except stripe.error.StripeError as e:
            logger.error(
                "Failed to change subscription plan",
                subscription_id=str(subscription.id),
                error=str(e)
            )
            raise ValidationError(f"Failed to change plan: {str(e)}")


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing payment history.
    Read-only as payments are managed through Stripe.
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter payments by user's organizations."""
        user = self.request.user
        org_ids = user.team_memberships.filter(
            is_active=True
        ).values_list('organization_id', flat=True)
        
        queryset = Payment.objects.filter(
            subscription__organization_id__in=org_ids
        ).order_by('-created_at')
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Date range filtering
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        return queryset.select_related('subscription')
    
    @action(detail=True, methods=['get'])
    def invoice(self, request, pk=None):
        """Get invoice URL for a payment."""
        payment = self.get_object()
        
        if payment.invoice_url:
            return Response({'invoice_url': payment.invoice_url})
        
        try:
            # Retrieve invoice from Stripe
            payment_intent = stripe.PaymentIntent.retrieve(
                payment.stripe_payment_intent_id
            )
            
            if payment_intent.invoice:
                invoice = stripe.Invoice.retrieve(payment_intent.invoice)
                payment.invoice_url = invoice.hosted_invoice_url
                payment.save()
                
                return Response({'invoice_url': invoice.hosted_invoice_url})
            
            return Response(
                {'error': 'No invoice available for this payment'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        except stripe.error.StripeError as e:
            logger.error(
                "Failed to retrieve invoice",
                payment_id=str(payment.id),
                error=str(e)
            )
            raise ValidationError(f"Failed to retrieve invoice: {str(e)}")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    """
    Create Stripe checkout session for subscription.
    """
    serializer = CheckoutSessionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    plan = serializer.validated_data['plan']
    billing_period = serializer.validated_data.get('billing_period', 'monthly')
    
    # Get organization
    org = request.user.team_memberships.filter(
        role='owner',
        is_active=True
    ).first()
    
    if not org:
        raise ValidationError("No organization found for user")
    
    organization = org.organization
    
    # Check if already has active subscription
    if organization.subscription_status == 'active':
        raise ValidationError("Organization already has an active subscription")
    
    try:
        # Get price ID based on plan and period
        price_ids = {
            ('starter', 'monthly'): settings.STRIPE_PRICE_STARTER_MONTHLY,
            ('starter', 'yearly'): settings.STRIPE_PRICE_STARTER_YEARLY,
            ('professional', 'monthly'): settings.STRIPE_PRICE_PROFESSIONAL_MONTHLY,
            ('professional', 'yearly'): settings.STRIPE_PRICE_PROFESSIONAL_YEARLY,
            ('enterprise', 'monthly'): settings.STRIPE_PRICE_ENTERPRISE_MONTHLY,
            ('enterprise', 'yearly'): settings.STRIPE_PRICE_ENTERPRISE_YEARLY,
        }
        
        price_id = price_ids.get((plan, billing_period))
        if not price_id:
            raise ValidationError("Invalid plan or billing period")
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=serializer.validated_data.get(
                'success_url',
                f"{settings.FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
            ),
            cancel_url=serializer.validated_data.get(
                'cancel_url',
                f"{settings.FRONTEND_URL}/billing/cancel"
            ),
            customer_email=request.user.email,
            metadata={
                'organization_id': str(organization.id),
                'plan_name': plan,
                'billing_period': billing_period
            },
            allow_promotion_codes=True,
            billing_address_collection='required'
        )
        
        logger.info(
            "Checkout session created",
            organization_id=str(organization.id),
            plan=plan,
            billing_period=billing_period,
            session_id=session.id
        )
        
        return Response({
            'checkout_url': session.url,
            'session_id': session.id
        })
        
    except stripe.error.StripeError as e:
        logger.error(
            "Failed to create checkout session",
            organization_id=str(organization.id),
            error=str(e)
        )
        raise ValidationError(f"Failed to create checkout session: {str(e)}")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_billing_portal(request):
    """
    Create Stripe billing portal session.
    """
    serializer = BillingPortalSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # Get organization subscription
    org = request.user.team_memberships.filter(
        role__in=['owner', 'admin'],
        is_active=True
    ).first()
    
    if not org:
        raise ValidationError("No organization found for user")
    
    subscription = Subscription.objects.filter(
        organization=org.organization
    ).first()
    
    if not subscription:
        raise ValidationError("No subscription found")
    
    try:
        # Create billing portal session
        session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=serializer.validated_data.get(
                'return_url',
                f"{settings.FRONTEND_URL}/billing"
            )
        )
        
        logger.info(
            "Billing portal session created",
            organization_id=str(org.organization.id),
            session_id=session.id
        )
        
        return Response({
            'portal_url': session.url
        })
        
    except stripe.error.StripeError as e:
        logger.error(
            "Failed to create billing portal session",
            organization_id=str(org.organization.id),
            error=str(e)
        )
        raise ValidationError(f"Failed to create billing portal: {str(e)}")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def usage_stats(request):
    """
    Get usage statistics for current billing period.
    """
    serializer = UsageStatsSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    
    # Get organization
    org = request.user.team_memberships.filter(
        is_active=True
    ).first()
    
    if not org:
        raise ValidationError("No organization found for user")
    
    organization = org.organization
    period = serializer.validated_data.get('period', 'current')
    
    # Determine date range
    now = timezone.now()
    if period == 'current':
        # Current billing period
        subscription = Subscription.objects.filter(
            organization=organization
        ).first()
        
        if subscription:
            period_start = subscription.current_period_start
            period_end = subscription.current_period_end
        else:
            period_start = now.replace(day=1)
            period_end = (period_start + timezone.timedelta(days=32)).replace(day=1)
    
    elif period == 'last_month':
        period_end = now.replace(day=1)
        period_start = (period_end - timezone.timedelta(days=1)).replace(day=1)
    
    elif period == 'last_quarter':
        period_end = now
        period_start = now - timezone.timedelta(days=90)
    
    elif period == 'last_year':
        period_end = now
        period_start = now - timezone.timedelta(days=365)
    
    # Get or create usage tracking
    usage, created = UsageTracking.objects.get_or_create(
        organization=organization,
        period_start=period_start,
        period_end=period_end,
        defaults={
            'chatbots_created': organization.chatbots.count(),
            'messages_processed': organization.chatbots.aggregate(
                total=models.Sum('total_messages')
            )['total'] or 0,
            'storage_used_mb': 0,  # Would be calculated from actual storage
            'api_calls_made': 0  # Would be tracked separately
        }
    )
    
    # Prepare response
    response_data = UsageTrackingSerializer(usage).data
    
    # Add plan limits
    plan_limits = {
        'starter': {
            'chatbots': 3,
            'messages': 5000,
            'storage_mb': 1024,
            'api_calls': 100
        },
        'professional': {
            'chatbots': 10,
            'messages': 50000,
            'storage_mb': 5120,
            'api_calls': 1000
        },
        'enterprise': {
            'chatbots': None,
            'messages': None,
            'storage_mb': None,
            'api_calls': None
        }
    }
    
    response_data['plan_limits'] = plan_limits.get(
        organization.subscription_tier,
        plan_limits['starter']
    )
    
    # Add detailed breakdown if requested
    if serializer.validated_data.get('detailed', False):
        response_data['detailed'] = {
            'daily_messages': [],  # Would be populated with daily data
            'chatbot_usage': [],  # Usage per chatbot
            'top_features': []  # Most used features
        }
    
    return Response(response_data)