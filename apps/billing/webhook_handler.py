"""
Stripe webhook handler to process subscription events.
"""

import stripe
import json
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from apps.accounts.models import User
import structlog
import os

logger = structlog.get_logger()

# Configure Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Handle Stripe webhook events.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        # For now, skip signature verification in development
        # In production, you'd verify the webhook signature
        event = json.loads(payload)
        
        logger.info(
            "Stripe webhook received",
            event_type=event.get('type'),
            event_id=event.get('id')
        )
        
        # Handle different event types
        if event['type'] == 'checkout.session.completed':
            handle_checkout_completed(event['data']['object'])
        elif event['type'] == 'customer.subscription.created':
            handle_subscription_created(event['data']['object'])
        elif event['type'] == 'customer.subscription.updated':
            handle_subscription_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            handle_subscription_cancelled(event['data']['object'])
        else:
            logger.info(
                "Unhandled webhook event type",
                event_type=event['type']
            )
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(
            "Webhook processing failed",
            error=str(e)
        )
        return HttpResponseBadRequest(f"Webhook error: {str(e)}")


def handle_checkout_completed(session):
    """
    Handle completed checkout session - upgrade user plan.
    """
    try:
        logger.info(
            "Processing checkout completion",
            session_id=session['id'],
            customer_email=session.get('customer_details', {}).get('email')
        )
        
        # Get user from metadata
        metadata = session.get('metadata', {})
        user_id = metadata.get('user_id')
        plan_name = metadata.get('plan')
        
        if not user_id or not plan_name:
            # Try to get user by email
            customer_email = session.get('customer_details', {}).get('email')
            if customer_email:
                try:
                    user = User.objects.get(email=customer_email)
                    user_id = str(user.id)
                except User.DoesNotExist:
                    logger.error(
                        "User not found for checkout session",
                        customer_email=customer_email,
                        session_id=session['id']
                    )
                    return
            else:
                logger.error(
                    "No user identifier in checkout session",
                    session_id=session['id']
                )
                return
        
        # Get user and upgrade plan
        try:
            user = User.objects.get(id=user_id)
            
            # Upgrade user plan
            user.upgrade_plan(plan_name, session.get('subscription'))
            
            logger.info(
                "User plan upgraded via webhook",
                user_id=user_id,
                user_email=user.email,
                old_plan=user.plan_tier,
                new_plan=plan_name,
                session_id=session['id']
            )
            
        except User.DoesNotExist:
            logger.error(
                "User not found for plan upgrade",
                user_id=user_id,
                session_id=session['id']
            )
            
    except Exception as e:
        logger.error(
            "Failed to process checkout completion",
            error=str(e),
            session_id=session.get('id')
        )


def handle_subscription_created(subscription):
    """
    Handle new subscription creation.
    """
    logger.info(
        "Subscription created",
        subscription_id=subscription['id'],
        customer=subscription['customer'],
        status=subscription['status']
    )
    
    # Additional subscription setup if needed


def handle_subscription_updated(subscription):
    """
    Handle subscription updates (upgrades, downgrades, etc.).
    """
    logger.info(
        "Subscription updated",
        subscription_id=subscription['id'],
        status=subscription['status']
    )


def handle_subscription_cancelled(subscription):
    """
    Handle subscription cancellation.
    """
    logger.info(
        "Subscription cancelled",
        subscription_id=subscription['id']
    )
    
    # Could downgrade user to free plan here