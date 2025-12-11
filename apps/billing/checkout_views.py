"""
Stripe checkout API views.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import structlog

from .stripe_service import StripeService
from apps.accounts.models import User

logger = structlog.get_logger()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    """
    Create Stripe checkout session for plan upgrade.
    
    Expected payload:
    {
        "plan": "hobby|standard|pro",
        "billing_cycle": "monthly|yearly"
    }
    """
    try:
        plan_name = request.data.get('plan', '').lower()
        billing_cycle = request.data.get('billing_cycle', 'monthly').lower()
        
        # Validate inputs
        valid_plans = ['hobby', 'standard', 'pro']
        valid_cycles = ['monthly', 'yearly']
        
        if plan_name not in valid_plans:
            return Response({
                'error': 'Invalid plan',
                'valid_plans': valid_plans
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if billing_cycle not in valid_cycles:
            return Response({
                'error': 'Invalid billing cycle',
                'valid_cycles': valid_cycles
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize Stripe service
        stripe_service = StripeService()
        
        # Get price ID for the plan
        price_id = stripe_service.get_plan_price_id(plan_name, billing_cycle)
        if not price_id:
            return Response({
                'error': f'Price ID not found for {plan_name} {billing_cycle}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Create checkout session
        result = stripe_service.create_checkout_session(
            price_id=price_id,
            customer_email=request.user.email,
            success_url=f'http://localhost:3005/success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'http://localhost:3005/pricing',
            metadata={
                'user_id': str(request.user.id),
                'plan_name': plan_name,
                'billing_cycle': billing_cycle,
                'current_plan': request.user.plan_tier,
            }
        )
        
        if result['success']:
            logger.info(
                "Checkout session created for user",
                user_id=str(request.user.id),
                plan=plan_name,
                billing_cycle=billing_cycle,
                session_id=result['session_id']
            )
            
            return Response({
                'checkout_url': result['checkout_url'],
                'session_id': result['session_id'],
                'plan': plan_name,
                'billing_cycle': billing_cycle,
                'test_mode': stripe_service.test_mode,
            })
        else:
            return Response({
                'error': result['error'],
                'error_type': result.get('error_type')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        logger.error(
            "Checkout session creation failed",
            user_id=str(request.user.id),
            error=str(e)
        )
        
        return Response({
            'error': 'Failed to create checkout session',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_checkout_plans(request):
    """
    Get available plans with Stripe price IDs for checkout.
    """
    try:
        stripe_service = StripeService()
        
        plans = [
            {
                'name': 'hobby',
                'display_name': 'Hobby',
                'description': 'For solo founders and small projects',
                'monthly_price': 40,
                'yearly_price': 32,
                'monthly_price_id': stripe_service.get_plan_price_id('hobby', 'monthly'),
                'yearly_price_id': stripe_service.get_plan_price_id('hobby', 'yearly'),
                'features': ['2,000 message credits', '1 AI agent', '40MB storage', 'API access']
            },
            {
                'name': 'standard',
                'display_name': 'Standard', 
                'description': 'For small teams and growing businesses',
                'monthly_price': 150,
                'yearly_price': 120,
                'monthly_price_id': stripe_service.get_plan_price_id('standard', 'monthly'),
                'yearly_price_id': stripe_service.get_plan_price_id('standard', 'yearly'),
                'features': ['12,000 message credits', '2 AI agents', '33MB storage', '3 team seats']
            },
            {
                'name': 'pro',
                'display_name': 'Pro',
                'description': 'For businesses needing advanced features', 
                'monthly_price': 500,
                'yearly_price': 400,
                'monthly_price_id': stripe_service.get_plan_price_id('pro', 'monthly'),
                'yearly_price_id': stripe_service.get_plan_price_id('pro', 'yearly'),
                'features': ['40,000 message credits', '3 AI agents', '33MB storage', '5 team seats', 'Advanced analytics']
            }
        ]
        
        return Response({
            'plans': plans,
            'test_mode': stripe_service.test_mode,
            'current_user_plan': request.user.plan_tier
        })
        
    except Exception as e:
        logger.error("Failed to get checkout plans", error=str(e))
        return Response({
            'error': 'Failed to load plans'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)