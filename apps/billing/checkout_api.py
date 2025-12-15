"""
Simple Stripe checkout API for immediate integration.
"""

import stripe
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import os

# Configure Stripe with environment variable
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    """
    Create Stripe checkout session for plan upgrade.
    """
    try:
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
        
        config = plan_configs[plan]
        
        # Create checkout session with actual price IDs
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': config['price_id'],
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
        
    except Exception as e:
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)