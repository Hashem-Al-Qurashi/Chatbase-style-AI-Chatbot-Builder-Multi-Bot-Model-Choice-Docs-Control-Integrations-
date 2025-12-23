"""
Simple Stripe checkout API for immediate integration.
"""

import stripe
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from chatbot_saas.config import get_settings


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    """
    Create Stripe checkout session for plan upgrade.
    """
    try:
        # Configure Stripe API key at runtime to ensure settings are loaded
        settings = get_settings()
        stripe.api_key = settings.STRIPE_SECRET_KEY

        plan = request.data.get('plan', '').lower()

        # Plan pricing with actual Stripe price IDs
        plan_configs = {
            'hobby': {
                'name': 'Hobby Plan',
                'price_id': 'price_1SdXtbB38w53JGJyp1hyGgGd',  # $40/month
                'description': 'For solo founders and small projects'
            },
            'standard': {
                'name': 'Standard Plan', 
                'price_id': 'price_1Sejb6B38w53JGJyAwxR2GXn',  # $150/month
                'description': 'For small teams and growing businesses'
            },
            'pro': {
                'name': 'Pro Plan',
                'price_id': 'price_1Sejb7B38w53JGJyT66TJbhW',  # $500/month
                'description': 'For businesses needing advanced features'
            }
        }
        
        if plan not in plan_configs:
            return Response({
                'error': 'Invalid plan',
                'valid_plans': list(plan_configs.keys())
            }, status=status.HTTP_400_BAD_REQUEST)

        plan_config = plan_configs[plan]

        # Create checkout session with actual price IDs
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': plan_config['price_id'],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f'http://localhost:3005/dashboard?upgrade_success={plan}',
            cancel_url='http://localhost:3005/#pricing',
            customer_email=request.user.email,
            metadata={
                'user_id': str(request.user.id),
                'plan': plan,
                'upgrade_from': request.user.plan_tier,
            }
        )
        
        # Get price for display
        price_amount = {
            'hobby': 40,
            'standard': 150, 
            'pro': 500
        }[plan]
        
        return Response({
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id,
            'plan': plan,
            'price': price_amount,
            'success': True
        })
        
    except stripe.error.StripeError as e:
        import structlog
        logger = structlog.get_logger()
        logger.error(
            "Stripe checkout error",
            error=str(e),
            error_type=type(e).__name__,
            user_email=request.user.email,
            plan=plan
        )
        return Response({
            'error': f'Stripe error: {str(e)}',
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        import structlog
        import traceback
        logger = structlog.get_logger()
        logger.error(
            "Checkout session creation failed",
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exc(),
            user_email=request.user.email,
            plan=plan
        )
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)