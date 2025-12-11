"""
Plan limits and restriction service (Chatbase style).
"""

from typing import Dict, Any, Optional
import structlog
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import User
from apps.billing.models import SubscriptionPlan
from apps.chatbots.models import Chatbot

logger = structlog.get_logger()


class PlanLimitsService:
    """
    Service for checking and enforcing plan limits (Chatbase style).
    """
    
    @staticmethod
    def get_user_plan_limits(user: User) -> Dict[str, Any]:
        """
        Get plan limits for a user.
        
        Args:
            user: User instance
            
        Returns:
            Dict with plan limits
        """
        return {
            'message_credits': user.message_credits,
            'credits_used': user.credits_used,
            'credits_remaining': user.credits_remaining,
            'max_ai_agents': user.max_ai_agents,
            'storage_limit_mb': user.storage_limit_mb,
            'max_ai_actions': user.max_ai_actions,
            'max_seats': user.max_seats,
            'plan_tier': user.plan_tier,
        }
    
    @staticmethod
    def can_send_message(user: User, credits_needed: int = 1) -> tuple[bool, str]:
        """
        Check if user can send a message (has enough credits).
        
        Args:
            user: User instance
            credits_needed: Number of credits needed
            
        Returns:
            Tuple of (can_send, reason)
        """
        if not user.has_credits_remaining:
            return False, "No message credits remaining"
        
        if user.credits_used + credits_needed > user.message_credits:
            return False, f"Not enough credits (need {credits_needed}, have {user.credits_remaining})"
        
        return True, "OK"
    
    @staticmethod
    def can_create_chatbot(user: User) -> tuple[bool, str]:
        """
        Check if user can create a new chatbot/AI agent.
        
        Args:
            user: User instance
            
        Returns:
            Tuple of (can_create, reason)
        """
        current_count = Chatbot.objects.filter(user=user, deleted_at__isnull=True).count()
        
        if current_count >= user.max_ai_agents:
            return False, f"Maximum AI agents reached ({user.max_ai_agents}). Upgrade plan to create more."
        
        return True, "OK"
    
    @staticmethod
    def can_upload_file(user: User, file_size_mb: float) -> tuple[bool, str]:
        """
        Check if user can upload a file (within storage limits).
        
        Args:
            user: User instance
            file_size_mb: File size in MB
            
        Returns:
            Tuple of (can_upload, reason)
        """
        if file_size_mb > user.storage_limit_mb:
            return False, f"File too large. Max {user.storage_limit_mb}MB per agent."
        
        # Check total storage usage (would need to implement storage tracking)
        # For now, just check file size limit
        return True, "OK"
    
    @staticmethod
    def get_credit_cost_for_model(model_name: str) -> int:
        """
        Get credit cost for different AI models (Chatbase style).
        
        Args:
            model_name: AI model name
            
        Returns:
            Number of credits consumed
        """
        # Chatbase charges different credits based on model
        costs = {
            'gpt-4o-mini': 1,
            'gpt-4o': 10,
            'gpt-4': 20,
            'gpt-3.5-turbo': 2,
            'claude-3-haiku': 1,
            'claude-3-sonnet': 5,
            'claude-3-opus': 15,
        }
        
        return costs.get(model_name.lower(), 2)  # Default to 2 credits
    
    @staticmethod
    def should_delete_inactive_agent(user: User, chatbot: Chatbot) -> bool:
        """
        Check if an AI agent should be deleted due to inactivity (Free plan only).
        
        Args:
            user: User instance
            chatbot: Chatbot instance
            
        Returns:
            True if should be deleted
        """
        # Only free plan has inactivity deletion
        if user.plan_tier != 'free':
            return False
        
        # Check if inactive for 14 days
        if chatbot.updated_at < timezone.now() - timedelta(days=14):
            return True
        
        return False
    
    @staticmethod
    def get_plan_features(user: User) -> Dict[str, bool]:
        """
        Get available features for user's plan.
        
        Args:
            user: User instance
            
        Returns:
            Dict of available features
        """
        # Get plan from database or use defaults based on tier
        try:
            plan = SubscriptionPlan.objects.filter(
                name__iexact=user.plan_tier
            ).first()
            
            if plan:
                return {
                    'api_access': plan.has_api_access,
                    'integrations': plan.has_integrations,
                    'advanced_analytics': plan.has_advanced_analytics,
                    'priority_support': plan.has_priority_support,
                    'custom_branding': plan.has_custom_branding,
                    'unlimited_training_links': plan.max_training_links == 0,
                    'agents_persist': plan.agents_persist,
                }
        except Exception:
            pass
        
        # Default features based on plan tier
        tier_features = {
            'free': {
                'api_access': False,
                'integrations': False,
                'advanced_analytics': False,
                'priority_support': False,
                'custom_branding': False,
                'unlimited_training_links': False,
                'agents_persist': False,
            },
            'hobby': {
                'api_access': True,
                'integrations': True,
                'advanced_analytics': False,
                'priority_support': False,
                'custom_branding': False,
                'unlimited_training_links': True,
                'agents_persist': True,
            },
            'standard': {
                'api_access': True,
                'integrations': True,
                'advanced_analytics': False,
                'priority_support': False,
                'custom_branding': False,
                'unlimited_training_links': True,
                'agents_persist': True,
            },
            'pro': {
                'api_access': True,
                'integrations': True,
                'advanced_analytics': True,
                'priority_support': True,
                'custom_branding': False,
                'unlimited_training_links': True,
                'agents_persist': True,
            },
        }
        
        return tier_features.get(user.plan_tier.lower(), tier_features['free'])
    
    @staticmethod
    def consume_message_credit(user: User, model_name: str = 'gpt-3.5-turbo') -> bool:
        """
        Consume message credits for a chat message.
        
        Args:
            user: User instance
            model_name: AI model used
            
        Returns:
            True if credits were consumed successfully
        """
        credits_needed = PlanLimitsService.get_credit_cost_for_model(model_name)
        
        can_send, reason = PlanLimitsService.can_send_message(user, credits_needed)
        if not can_send:
            logger.warning(
                "Message blocked - insufficient credits",
                user_id=str(user.id),
                credits_needed=credits_needed,
                credits_remaining=user.credits_remaining,
                reason=reason
            )
            return False
        
        # Consume the credits
        success = user.consume_credits(credits_needed)
        if success:
            logger.info(
                "Credits consumed",
                user_id=str(user.id),
                model=model_name,
                credits_consumed=credits_needed,
                credits_remaining=user.credits_remaining
            )
        
        return success
    
    @staticmethod
    def get_upgrade_suggestion(user: User, feature_needed: str) -> Optional[str]:
        """
        Get upgrade suggestion for a blocked feature.
        
        Args:
            user: User instance
            feature_needed: Feature that was blocked
            
        Returns:
            Suggested plan to upgrade to
        """
        current_tier = user.plan_tier.lower()
        
        upgrade_map = {
            'api_access': 'hobby',
            'more_credits': 'hobby' if current_tier == 'free' else 'standard',
            'more_agents': 'standard' if current_tier in ['free', 'hobby'] else 'pro',
            'advanced_analytics': 'pro',
            'priority_support': 'pro',
            'team_seats': 'standard',
        }
        
        suggested_plan = upgrade_map.get(feature_needed)
        if suggested_plan and suggested_plan != current_tier:
            return suggested_plan
        
        return None