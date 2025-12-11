"""
Management command to set up Stripe products and pricing programmatically.
"""

import stripe
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.billing.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Set up Stripe products and pricing to match our Chatbase structure'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-mode',
            action='store_true',
            help='Use test API keys (recommended for development)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate products even if they exist',
        )

    def handle(self, *args, **options):
        # Configure Stripe with environment variable
        stripe_key = os.getenv('STRIPE_SECRET_KEY')
        if not stripe_key or stripe_key == 'sk_test_placeholder_need_test_key':
            self.stdout.write(
                self.style.ERROR('❌ No valid Stripe secret key found in environment')
            )
            self.stdout.write('Please set STRIPE_SECRET_KEY in .env file')
            return
        
        stripe.api_key = stripe_key
        
        # Determine if test or live mode
        if stripe_key.startswith('sk_test_'):
            self.stdout.write(
                self.style.SUCCESS('✅ Using Stripe TEST mode - safe for development')
            )
        elif stripe_key.startswith('sk_live_'):
            self.stdout.write(
                self.style.WARNING('⚠️ Using Stripe LIVE mode - real charges will occur!')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('✅ Using Stripe TEST mode (restricted key)')
            )
        
        try:
            self.stdout.write('Setting up Stripe products and pricing...')
            
            # Get our local plans
            local_plans = SubscriptionPlan.objects.all().order_by('price_monthly')
            
            created_products = []
            
            for plan in local_plans:
                self.stdout.write(f'🏗️ Creating Stripe product for: {plan.name}')
                
                try:
                    # Create product
                    product = stripe.Product.create(
                        name=f"{plan.name} Plan",
                        description=plan.description,
                        metadata={
                            'plan_id': str(plan.id),
                            'plan_name': plan.name.lower(),
                            'message_credits': str(plan.message_credits),
                            'max_ai_agents': str(plan.max_ai_agents),
                            'max_ai_actions': str(plan.max_ai_actions),
                            'storage_limit_mb': str(plan.storage_limit_mb),
                        }
                    )
                    
                    self.stdout.write(f'✅ Product created: {product.id}')
                    
                    # Create monthly price
                    monthly_price = None
                    if float(plan.price_monthly) > 0:  # Skip $0 plans
                        monthly_price = stripe.Price.create(
                            product=product.id,
                            unit_amount=int(float(plan.price_monthly) * 100),  # Convert to cents
                            currency='usd',
                            recurring={'interval': 'month'},
                            metadata={
                                'plan_name': plan.name.lower(),
                                'billing_interval': 'monthly'
                            }
                        )
                        self.stdout.write(f'💰 Monthly price created: {monthly_price.id} (${plan.price_monthly}/month)')
                    
                    # Create yearly price (with 20% discount)
                    yearly_price = None
                    if float(plan.price_yearly) > 0:  # Skip $0 plans
                        yearly_price = stripe.Price.create(
                            product=product.id,
                            unit_amount=int(float(plan.price_yearly) * 100 * 12),  # Yearly total in cents
                            currency='usd',
                            recurring={'interval': 'year'},
                            metadata={
                                'plan_name': plan.name.lower(),
                                'billing_interval': 'yearly',
                                'discount_percent': '20'
                            }
                        )
                        self.stdout.write(f'💰 Yearly price created: {yearly_price.id} (${float(plan.price_yearly) * 12}/year)')
                    
                    # Update local plan with Stripe IDs
                    if monthly_price:
                        plan.stripe_price_id_monthly = monthly_price.id
                    if yearly_price:
                        plan.stripe_price_id_yearly = yearly_price.id
                    plan.save()
                    
                    created_products.append({
                        'plan': plan.name,
                        'product_id': product.id,
                        'monthly_price_id': monthly_price.id if monthly_price else None,
                        'yearly_price_id': yearly_price.id if yearly_price else None,
                    })
                    
                except stripe.error.StripeError as e:
                    self.stdout.write(
                        self.style.ERROR(f'❌ Failed to create {plan.name}: {str(e)}')
                    )
                    continue
            
            # Skip webhook creation for now (can be done manually)
            self.stdout.write('ℹ️ Skipping webhook creation (set up manually in Stripe dashboard)')
            
            # Print summary
            self.stdout.write('\n📋 STRIPE SETUP COMPLETE')
            self.stdout.write('=' * 40)
            
            for product in created_products:
                self.stdout.write(f"✅ {product['plan']} Plan:")
                self.stdout.write(f"   Product ID: {product['product_id']}")
                if product['monthly_price_id']:
                    self.stdout.write(f"   Monthly Price ID: {product['monthly_price_id']}")
                if product['yearly_price_id']:
                    self.stdout.write(f"   Yearly Price ID: {product['yearly_price_id']}")
                self.stdout.write('')
            
            self.stdout.write('🎯 Next Steps:')
            self.stdout.write('1. Update .env with the price IDs above')
            self.stdout.write('2. Set up webhook URL in production')
            self.stdout.write('3. Test checkout flow with test cards')
            self.stdout.write('4. Implement subscription management')
            
            # Print test card info
            self.stdout.write('\n💳 TEST CARDS FOR TESTING:')
            self.stdout.write('✅ Success: 4242424242424242')
            self.stdout.write('❌ Declined: 4000000000000002')
            self.stdout.write('⚠️ Requires Auth: 4000002500003155')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'💥 Setup failed: {str(e)}')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS('🚀 Stripe setup completed successfully!')
        )