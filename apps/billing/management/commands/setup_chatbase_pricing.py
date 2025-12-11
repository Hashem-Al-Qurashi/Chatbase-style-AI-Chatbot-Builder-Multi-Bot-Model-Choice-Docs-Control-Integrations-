"""
Management command to set up Chatbase-style pricing plans.
"""

from django.core.management.base import BaseCommand
from apps.billing.models import SubscriptionPlan, PlanAddon


class Command(BaseCommand):
    help = 'Set up Chatbase-style pricing plans and add-ons'

    def handle(self, *args, **options):
        self.stdout.write('Setting up Chatbase pricing plans...')
        
        # Clear existing plans
        SubscriptionPlan.objects.all().delete()
        PlanAddon.objects.all().delete()
        
        # Create Chatbase plans
        plans = [
            {
                'name': 'Free',
                'description': 'Perfect for testing and personal projects',
                'price_monthly': 0.00,
                'price_yearly': 0.00,
                'message_credits': 50,
                'max_ai_agents': 1,
                'max_ai_actions': 0,
                'storage_limit_mb': 1,  # ~400KB
                'max_seats': 1,
                'max_training_links': 10,
                'has_api_access': False,
                'has_integrations': False,
                'has_advanced_analytics': False,
                'has_priority_support': False,
                'has_custom_branding': False,
                'agents_persist': False,
                'inactivity_deletion_days': 14,
                'features': {
                    'embed_unlimited_websites': True,
                    'basic_features_only': True,
                    'agents_deleted_after_inactivity': True,
                },
                'sort_order': 1,
                'is_popular': False,
            },
            {
                'name': 'Hobby',
                'description': 'For solo founders and small projects',
                'price_monthly': 40.00,
                'price_yearly': 32.00,  # 20% discount
                'message_credits': 2000,
                'max_ai_agents': 1,
                'max_ai_actions': 5,
                'storage_limit_mb': 40,
                'max_seats': 1,
                'max_training_links': 0,  # Unlimited
                'has_api_access': True,
                'has_integrations': True,
                'has_advanced_analytics': False,
                'has_priority_support': False,
                'has_custom_branding': False,
                'agents_persist': True,
                'inactivity_deletion_days': 0,
                'features': {
                    'api_access': True,
                    'unlimited_training_links': True,
                    'basic_integrations': True,
                    'ai_actions': True,
                },
                'sort_order': 2,
                'is_popular': True,
            },
            {
                'name': 'Standard',
                'description': 'For small teams and growing businesses',
                'price_monthly': 150.00,
                'price_yearly': 120.00,  # 20% discount
                'message_credits': 12000,
                'max_ai_agents': 2,
                'max_ai_actions': 10,
                'storage_limit_mb': 33,
                'max_seats': 3,
                'max_training_links': 0,  # Unlimited
                'has_api_access': True,
                'has_integrations': True,
                'has_advanced_analytics': False,
                'has_priority_support': False,
                'has_custom_branding': False,
                'agents_persist': True,
                'inactivity_deletion_days': 0,
                'features': {
                    'multiple_agents': True,
                    'team_collaboration': True,
                    'more_ai_actions': True,
                },
                'sort_order': 3,
                'is_popular': False,
            },
            {
                'name': 'Pro',
                'description': 'For businesses needing advanced features',
                'price_monthly': 500.00,
                'price_yearly': 400.00,  # 20% discount
                'message_credits': 40000,
                'max_ai_agents': 3,
                'max_ai_actions': 15,
                'storage_limit_mb': 33,
                'max_seats': 5,
                'max_training_links': 0,  # Unlimited
                'has_api_access': True,
                'has_integrations': True,
                'has_advanced_analytics': True,
                'has_priority_support': True,
                'has_custom_branding': False,
                'agents_persist': True,
                'inactivity_deletion_days': 0,
                'features': {
                    'advanced_analytics': True,
                    'priority_features': True,
                    'more_agents': True,
                    'larger_teams': True,
                },
                'sort_order': 4,
                'is_popular': False,
            },
        ]
        
        for plan_data in plans:
            plan = SubscriptionPlan.objects.create(**plan_data)
            self.stdout.write(
                self.style.SUCCESS(f'Created plan: {plan.name} (${plan.price_monthly}/month)')
            )
        
        # Create add-ons
        addons = [
            {
                'name': 'Extra Message Credits (1,000)',
                'description': 'Additional 1,000 message credits per month',
                'price_monthly': 12.00,
                'addon_type': 'credits',
                'credits_amount': 1000,
                'sort_order': 1,
            },
            {
                'name': 'Auto-recharge Credits (1,000)',
                'description': 'Automatically adds credits when you run low',
                'price_monthly': 14.00,
                'addon_type': 'credits',
                'credits_amount': 1000,
                'sort_order': 2,
            },
            {
                'name': 'Additional AI Agent',
                'description': 'Add one more AI agent to your account',
                'price_monthly': 7.00,
                'addon_type': 'agents',
                'agents_amount': 1,
                'sort_order': 3,
            },
            {
                'name': 'Remove Branding',
                'description': 'Remove "Powered by [Your Brand]" from chatbots',
                'price_monthly': 39.00,
                'addon_type': 'branding',
                'sort_order': 4,
            },
            {
                'name': 'Custom Domain',
                'description': 'Use your own domain for chat widgets',
                'price_monthly': 59.00,
                'addon_type': 'domain',
                'sort_order': 5,
            },
        ]
        
        for addon_data in addons:
            addon = PlanAddon.objects.create(**addon_data)
            self.stdout.write(
                self.style.SUCCESS(f'Created add-on: {addon.name} (${addon.price_monthly}/month)')
            )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up Chatbase pricing structure!')
        )
        self.stdout.write(
            self.style.WARNING('Remember to set Stripe price IDs for production!')
        )