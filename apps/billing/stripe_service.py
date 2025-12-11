"""
Stripe integration service for subscription management.
"""

import stripe
import os
from typing import Dict, Any, Optional
from django.conf import settings
import structlog

logger = structlog.get_logger()


class StripeService:
    """Service for Stripe subscription management."""
    
    def __init__(self):
        """Initialize Stripe with API key."""
        # Use environment variable directly for flexibility
        stripe_key = os.getenv('STRIPE_SECRET_KEY')
        if not stripe_key:
            raise ValueError("STRIPE_SECRET_KEY not found in environment")
        
        stripe.api_key = stripe_key
        
        # Determine if test or live mode
        self.test_mode = stripe_key.startswith('sk_test_')
        
        logger.info(
            "Stripe service initialized",
            test_mode=self.test_mode,
            key_prefix=stripe_key[:12] + "..."
        )
    
    def create_checkout_session(
        self,
        price_id: str,
        customer_email: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe checkout session for subscription.
        
        Args:
            price_id: Stripe price ID for the plan
            customer_email: Customer email address
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment is cancelled
            metadata: Additional metadata to store
            
        Returns:
            Dict with checkout session info
        """
        try:
            # Create checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                metadata=metadata or {},
                allow_promotion_codes=True,
                billing_address_collection='required',
                automatic_tax={'enabled': True},
            )
            
            logger.info(
                "Checkout session created",
                session_id=session.id,
                customer_email=customer_email,
                price_id=price_id,
                test_mode=self.test_mode
            )
            
            return {
                'session_id': session.id,
                'checkout_url': session.url,
                'success': True
            }
            
        except stripe.error.StripeError as e:
            logger.error(
                "Stripe checkout session creation failed",
                error=str(e),
                price_id=price_id,
                customer_email=customer_email
            )
            
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def get_plan_price_id(self, plan_name: str, billing_cycle: str = 'monthly') -> Optional[str]:
        """
        Get Stripe price ID for a plan and billing cycle.
        
        Args:
            plan_name: Plan name (hobby, standard, pro)
            billing_cycle: 'monthly' or 'yearly'
            
        Returns:
            Stripe price ID or None
        """
        env_key = f"STRIPE_PRICE_{plan_name.upper()}_{billing_cycle.upper()}"
        price_id = os.getenv(env_key)
        
        if not price_id:
            logger.warning(
                "Price ID not found",
                plan_name=plan_name,
                billing_cycle=billing_cycle,
                env_key=env_key
            )
        
        return price_id
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify Stripe webhook signature.
        
        Args:
            payload: Raw webhook payload
            signature: Stripe signature header
            
        Returns:
            True if signature is valid
        """
        try:
            webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
            if not webhook_secret:
                logger.error("STRIPE_WEBHOOK_SECRET not configured")
                return False
            
            stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
            return True
            
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid webhook signature")
            return False
        except Exception as e:
            logger.error("Webhook verification failed", error=str(e))
            return False
    
    def get_subscription_info(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        Get subscription information from Stripe.
        
        Args:
            subscription_id: Stripe subscription ID
            
        Returns:
            Subscription info dict or None
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            return {
                'id': subscription.id,
                'status': subscription.status,
                'current_period_start': subscription.current_period_start,
                'current_period_end': subscription.current_period_end,
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'customer': subscription.customer,
                'price_id': subscription.items.data[0].price.id if subscription.items.data else None,
                'plan_name': subscription.items.data[0].price.metadata.get('plan_name') if subscription.items.data else None,
            }
            
        except stripe.error.StripeError as e:
            logger.error("Failed to retrieve subscription", error=str(e))
            return None
    
    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> bool:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            at_period_end: Cancel at end of period or immediately
            
        Returns:
            True if cancelled successfully
        """
        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)
            
            logger.info(
                "Subscription cancelled",
                subscription_id=subscription_id,
                at_period_end=at_period_end
            )
            
            return True
            
        except stripe.error.StripeError as e:
            logger.error("Failed to cancel subscription", error=str(e))
            return False