"""
Webhook endpoints for external integrations.
Handles Stripe payments and CRM webhooks.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import stripe
import hmac
import hashlib
import json
import structlog

from apps.billing.models import Subscription, Payment
from apps.webhooks.models import WebhookEvent, WebhookDelivery
from apps.accounts.models import Organization

logger = structlog.get_logger()


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def stripe_webhook(request):
    """
    Handle Stripe webhook events.
    Processes payment events and subscription updates.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        logger.error("Invalid Stripe payload")
        return Response(
            {'error': 'Invalid payload'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid Stripe signature")
        return Response(
            {'error': 'Invalid signature'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Log webhook event
    webhook_event = WebhookEvent.objects.create(
        provider='stripe',
        event_type=event['type'],
        event_id=event['id'],
        payload=event,
        status='processing'
    )
    
    try:
        # Handle different event types
        if event['type'] == 'checkout.session.completed':
            handle_checkout_completed(event)
        
        elif event['type'] == 'invoice.payment_succeeded':
            handle_payment_succeeded(event)
        
        elif event['type'] == 'invoice.payment_failed':
            handle_payment_failed(event)
        
        elif event['type'] == 'customer.subscription.created':
            handle_subscription_created(event)
        
        elif event['type'] == 'customer.subscription.updated':
            handle_subscription_updated(event)
        
        elif event['type'] == 'customer.subscription.deleted':
            handle_subscription_cancelled(event)
        
        else:
            logger.info(
                f"Unhandled Stripe event type",
                event_type=event['type'],
                event_id=event['id']
            )
        
        # Mark event as processed
        webhook_event.status = 'processed'
        webhook_event.save()
        
        return Response({'status': 'success'})
        
    except Exception as e:
        logger.error(
            "Error processing Stripe webhook",
            event_type=event['type'],
            event_id=event['id'],
            error=str(e)
        )
        
        webhook_event.status = 'failed'
        webhook_event.error_message = str(e)
        webhook_event.save()
        
        return Response(
            {'error': 'Processing failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def handle_checkout_completed(event):
    """Handle successful checkout session."""
    session = event['data']['object']
    
    # Get organization from metadata
    org_id = session['metadata'].get('organization_id')
    if not org_id:
        logger.error("No organization_id in checkout session metadata")
        return
    
    try:
        organization = Organization.objects.get(id=org_id)
        
        # Update subscription
        organization.subscription_status = 'active'
        organization.stripe_customer_id = session['customer']
        organization.stripe_subscription_id = session['subscription']
        organization.save()
        
        # Create subscription record
        Subscription.objects.create(
            organization=organization,
            stripe_subscription_id=session['subscription'],
            stripe_customer_id=session['customer'],
            status='active',
            current_period_start=session.get('current_period_start'),
            current_period_end=session.get('current_period_end'),
            plan_name=session['metadata'].get('plan_name', 'professional'),
            price_amount=session['amount_total'] / 100,
            currency=session['currency']
        )
        
        logger.info(
            "Checkout completed",
            organization_id=str(organization.id),
            subscription_id=session['subscription']
        )
        
    except Organization.DoesNotExist:
        logger.error(
            "Organization not found for checkout",
            organization_id=org_id
        )


def handle_payment_succeeded(event):
    """Handle successful payment."""
    invoice = event['data']['object']
    
    # Find subscription
    subscription = Subscription.objects.filter(
        stripe_subscription_id=invoice['subscription']
    ).first()
    
    if subscription:
        # Create payment record
        Payment.objects.create(
            subscription=subscription,
            stripe_payment_intent_id=invoice['payment_intent'],
            amount=invoice['amount_paid'] / 100,
            currency=invoice['currency'],
            status='succeeded',
            description=f"Payment for {invoice['period_start']} to {invoice['period_end']}"
        )
        
        # Update subscription period
        subscription.current_period_end = invoice['period_end']
        subscription.save()
        
        logger.info(
            "Payment succeeded",
            subscription_id=subscription.id,
            amount=invoice['amount_paid'] / 100
        )


def handle_payment_failed(event):
    """Handle failed payment."""
    invoice = event['data']['object']
    
    # Find subscription
    subscription = Subscription.objects.filter(
        stripe_subscription_id=invoice['subscription']
    ).first()
    
    if subscription:
        # Create failed payment record
        Payment.objects.create(
            subscription=subscription,
            stripe_payment_intent_id=invoice['payment_intent'],
            amount=invoice['amount_due'] / 100,
            currency=invoice['currency'],
            status='failed',
            description=f"Failed payment for {invoice['period_start']} to {invoice['period_end']}"
        )
        
        # Update subscription status
        subscription.status = 'past_due'
        subscription.save()
        
        # Update organization
        subscription.organization.subscription_status = 'past_due'
        subscription.organization.save()
        
        logger.warning(
            "Payment failed",
            subscription_id=subscription.id,
            amount=invoice['amount_due'] / 100
        )


def handle_subscription_created(event):
    """Handle new subscription creation."""
    subscription = event['data']['object']
    
    # Find or create subscription record
    sub, created = Subscription.objects.get_or_create(
        stripe_subscription_id=subscription['id'],
        defaults={
            'stripe_customer_id': subscription['customer'],
            'status': subscription['status'],
            'current_period_start': subscription['current_period_start'],
            'current_period_end': subscription['current_period_end']
        }
    )
    
    if created:
        logger.info(
            "Subscription created",
            subscription_id=subscription['id']
        )


def handle_subscription_updated(event):
    """Handle subscription updates."""
    subscription = event['data']['object']
    
    # Update subscription record
    sub = Subscription.objects.filter(
        stripe_subscription_id=subscription['id']
    ).first()
    
    if sub:
        sub.status = subscription['status']
        sub.current_period_start = subscription['current_period_start']
        sub.current_period_end = subscription['current_period_end']
        sub.save()
        
        # Update organization
        sub.organization.subscription_status = subscription['status']
        sub.organization.save()
        
        logger.info(
            "Subscription updated",
            subscription_id=subscription['id'],
            status=subscription['status']
        )


def handle_subscription_cancelled(event):
    """Handle subscription cancellation."""
    subscription = event['data']['object']
    
    # Update subscription record
    sub = Subscription.objects.filter(
        stripe_subscription_id=subscription['id']
    ).first()
    
    if sub:
        sub.status = 'cancelled'
        sub.cancelled_at = subscription['canceled_at']
        sub.save()
        
        # Update organization
        sub.organization.subscription_status = 'cancelled'
        sub.organization.save()
        
        logger.info(
            "Subscription cancelled",
            subscription_id=subscription['id']
        )


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def crm_webhook(request):
    """
    Generic CRM webhook endpoint.
    Can handle webhooks from various CRM systems.
    """
    # Get webhook signature if present
    signature = request.META.get('HTTP_X_WEBHOOK_SIGNATURE')
    
    # Log webhook event
    webhook_event = WebhookEvent.objects.create(
        provider='crm',
        event_type=request.data.get('event_type', 'unknown'),
        event_id=request.data.get('event_id', ''),
        payload=request.data,
        status='processing'
    )
    
    try:
        # Verify signature if configured
        if signature and settings.CRM_WEBHOOK_SECRET:
            expected_signature = hmac.new(
                settings.CRM_WEBHOOK_SECRET.encode(),
                request.body,
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                webhook_event.status = 'failed'
                webhook_event.error_message = 'Invalid signature'
                webhook_event.save()
                
                return Response(
                    {'error': 'Invalid signature'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        
        # Process different event types
        event_type = request.data.get('event_type')
        
        if event_type == 'contact.created':
            handle_crm_contact_created(request.data)
        
        elif event_type == 'contact.updated':
            handle_crm_contact_updated(request.data)
        
        elif event_type == 'deal.created':
            handle_crm_deal_created(request.data)
        
        elif event_type == 'deal.updated':
            handle_crm_deal_updated(request.data)
        
        else:
            logger.info(
                f"Unhandled CRM event type",
                event_type=event_type
            )
        
        # Mark event as processed
        webhook_event.status = 'processed'
        webhook_event.save()
        
        return Response({'status': 'success'})
        
    except Exception as e:
        logger.error(
            "Error processing CRM webhook",
            event_type=request.data.get('event_type'),
            error=str(e)
        )
        
        webhook_event.status = 'failed'
        webhook_event.error_message = str(e)
        webhook_event.save()
        
        return Response(
            {'error': 'Processing failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def handle_crm_contact_created(data):
    """Handle new contact creation in CRM."""
    # This would be implemented based on specific CRM requirements
    logger.info(
        "CRM contact created",
        contact_id=data.get('contact_id'),
        email=data.get('email')
    )


def handle_crm_contact_updated(data):
    """Handle contact update in CRM."""
    logger.info(
        "CRM contact updated",
        contact_id=data.get('contact_id')
    )


def handle_crm_deal_created(data):
    """Handle new deal creation in CRM."""
    logger.info(
        "CRM deal created",
        deal_id=data.get('deal_id'),
        amount=data.get('amount')
    )


def handle_crm_deal_updated(data):
    """Handle deal update in CRM."""
    logger.info(
        "CRM deal updated",
        deal_id=data.get('deal_id'),
        status=data.get('status')
    )


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def lead_delivery_webhook(request):
    """
    Webhook for lead delivery confirmation.
    Called by external systems to confirm lead receipt.
    """
    # Log delivery
    delivery = WebhookDelivery.objects.create(
        webhook_url=request.data.get('webhook_url'),
        payload=request.data,
        status_code=200,
        response_body={'status': 'received'},
        delivered_at=timezone.now()
    )
    
    # Find related conversation
    conversation_id = request.data.get('conversation_id')
    if conversation_id:
        from apps.conversations.models import Conversation
        conversation = Conversation.objects.filter(id=conversation_id).first()
        if conversation:
            # Update metadata
            if not conversation.metadata:
                conversation.metadata = {}
            conversation.metadata['lead_delivered'] = True
            conversation.metadata['lead_delivery_confirmed_at'] = timezone.now().isoformat()
            conversation.save()
    
    logger.info(
        "Lead delivery confirmed",
        conversation_id=conversation_id
    )
    
    return Response({'status': 'confirmed'})