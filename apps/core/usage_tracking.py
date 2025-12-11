"""
Usage tracking service for analytics and billing (Chatbase style).
"""

from typing import Dict, Any, Optional
from datetime import datetime, date
from django.utils import timezone
from django.db.models import Sum, Count, Q
import structlog

from apps.accounts.models import User
from apps.billing.models import UsageRecord
from apps.chatbots.models import Chatbot
from apps.conversations.models import Conversation, Message

logger = structlog.get_logger()


class UsageTrackingService:
    """
    Service for tracking usage and generating analytics (Chatbase style).
    """
    
    @staticmethod
    def record_message_usage(
        user: User,
        model_name: str = 'gpt-3.5-turbo',
        tokens_used: int = 0,
        chatbot_id: Optional[str] = None
    ) -> bool:
        """
        Record message usage for billing and analytics.
        
        Args:
            user: User who sent the message
            model_name: AI model used
            tokens_used: Number of tokens consumed
            chatbot_id: ID of chatbot used (optional)
            
        Returns:
            True if recorded successfully
        """
        try:
            # Calculate credits used based on model
            from apps.core.plan_limits import PlanLimitsService
            credits_used = PlanLimitsService.get_credit_cost_for_model(model_name)
            
            # Get or create today's usage record
            today = timezone.now().date()
            usage_record, created = UsageRecord.objects.get_or_create(
                user=user,
                date=today,
                defaults={
                    'message_credits_used': 0,
                    'messages_sent': 0,
                    'tokens_used': 0,
                    'ai_actions_used': 0,
                }
            )
            
            # Update usage record
            usage_record.message_credits_used += credits_used
            usage_record.messages_sent += 1
            usage_record.tokens_used += tokens_used
            usage_record.save()
            
            logger.info(
                "Message usage recorded",
                user_id=str(user.id),
                model=model_name,
                credits_used=credits_used,
                tokens_used=tokens_used,
                chatbot_id=chatbot_id,
                date=today
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to record message usage",
                user_id=str(user.id),
                error=str(e)
            )
            return False
    
    @staticmethod
    def record_ai_action_usage(
        user: User,
        action_type: str,
        chatbot_id: Optional[str] = None
    ) -> bool:
        """
        Record AI Action usage (Chatbase feature).
        
        Args:
            user: User who triggered the action
            action_type: Type of AI action
            chatbot_id: ID of chatbot used
            
        Returns:
            True if recorded successfully
        """
        try:
            # Get or create today's usage record
            today = timezone.now().date()
            usage_record, created = UsageRecord.objects.get_or_create(
                user=user,
                date=today,
                defaults={
                    'message_credits_used': 0,
                    'messages_sent': 0,
                    'tokens_used': 0,
                    'ai_actions_used': 0,
                }
            )
            
            # Update AI actions usage
            usage_record.ai_actions_used += 1
            usage_record.save()
            
            logger.info(
                "AI Action usage recorded",
                user_id=str(user.id),
                action_type=action_type,
                chatbot_id=chatbot_id,
                date=today
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to record AI action usage",
                user_id=str(user.id),
                error=str(e)
            )
            return False
    
    @staticmethod
    def get_usage_analytics(
        user: User,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get usage analytics for a user (Chatbase style).
        
        Args:
            user: User to get analytics for
            period_days: Number of days to analyze
            
        Returns:
            Dict with analytics data
        """
        try:
            # Calculate date range
            end_date = timezone.now().date()
            start_date = end_date - timezone.timedelta(days=period_days)
            
            # Get usage records for period
            usage_records = UsageRecord.objects.filter(
                user=user,
                date__gte=start_date,
                date__lte=end_date
            ).order_by('date')
            
            # Aggregate totals
            totals = usage_records.aggregate(
                total_credits=Sum('message_credits_used'),
                total_messages=Sum('messages_sent'),
                total_tokens=Sum('tokens_used'),
                total_actions=Sum('ai_actions_used'),
                total_storage=Sum('storage_used_mb')
            )
            
            # Get chatbot analytics
            chatbot_stats = []
            for chatbot in user.chatbots.filter(is_deleted=False):
                conversations_count = chatbot.conversations.count()
                messages_count = Message.objects.filter(
                    conversation__chatbot=chatbot
                ).count()
                
                chatbot_stats.append({
                    'id': str(chatbot.id),
                    'name': chatbot.name,
                    'conversations': conversations_count,
                    'messages': messages_count,
                    'last_activity': chatbot.updated_at,
                    'created_at': chatbot.created_at,
                })
            
            # Get daily usage for charts
            daily_usage = []
            for record in usage_records:
                daily_usage.append({
                    'date': record.date,
                    'credits_used': record.message_credits_used,
                    'messages_sent': record.messages_sent,
                    'ai_actions_used': record.ai_actions_used,
                })
            
            # Calculate usage trends
            current_period_credits = totals['total_credits'] or 0
            
            # Get previous period for comparison
            prev_start = start_date - timezone.timedelta(days=period_days)
            prev_end = start_date
            
            prev_totals = UsageRecord.objects.filter(
                user=user,
                date__gte=prev_start,
                date__lt=prev_end
            ).aggregate(
                total_credits=Sum('message_credits_used'),
                total_messages=Sum('messages_sent')
            )
            
            prev_period_credits = prev_totals['total_credits'] or 0
            
            # Calculate growth rate
            if prev_period_credits > 0:
                credits_growth = ((current_period_credits - prev_period_credits) / prev_period_credits) * 100
            else:
                credits_growth = 100 if current_period_credits > 0 else 0
            
            analytics = {
                'period': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'days': period_days,
                },
                'totals': {
                    'credits_used': totals['total_credits'] or 0,
                    'messages_sent': totals['total_messages'] or 0,
                    'tokens_used': totals['total_tokens'] or 0,
                    'ai_actions_used': totals['total_actions'] or 0,
                    'storage_used_mb': totals['total_storage'] or 0,
                },
                'averages': {
                    'credits_per_day': round((totals['total_credits'] or 0) / period_days, 2),
                    'messages_per_day': round((totals['total_messages'] or 0) / period_days, 2),
                },
                'trends': {
                    'credits_growth_percent': round(credits_growth, 2),
                    'period_comparison': {
                        'current_credits': current_period_credits,
                        'previous_credits': prev_period_credits,
                    }
                },
                'plan_usage': {
                    'credits_limit': user.message_credits,
                    'credits_used': user.credits_used,
                    'credits_remaining': user.credits_remaining,
                    'usage_percentage': user.credits_percentage_used,
                    'agents_limit': user.max_ai_agents,
                    'agents_used': user.chatbots.filter(is_deleted=False).count(),
                },
                'chatbot_analytics': chatbot_stats,
                'daily_usage': daily_usage,
                'top_usage_days': sorted(
                    daily_usage, 
                    key=lambda x: x['credits_used'], 
                    reverse=True
                )[:5],
            }
            
            return analytics
            
        except Exception as e:
            logger.error(
                "Failed to get usage analytics",
                user_id=str(user.id),
                error=str(e)
            )
            return {
                'error': 'Failed to load analytics',
                'totals': {
                    'credits_used': 0,
                    'messages_sent': 0,
                    'tokens_used': 0,
                    'ai_actions_used': 0,
                }
            }
    
    @staticmethod
    def get_plan_recommendations(user: User) -> Dict[str, Any]:
        """
        Get plan upgrade recommendations based on usage patterns.
        
        Args:
            user: User to analyze
            
        Returns:
            Dict with recommendations
        """
        try:
            # Get recent usage analytics
            analytics = UsageTrackingService.get_usage_analytics(user, period_days=30)
            
            recommendations = {
                'should_upgrade': False,
                'reasons': [],
                'suggested_plan': None,
                'potential_savings': 0,
                'usage_insights': [],
            }
            
            # Check if user is hitting limits
            if user.credits_percentage_used >= 80:
                recommendations['should_upgrade'] = True
                recommendations['reasons'].append(
                    f"Using {user.credits_percentage_used:.0f}% of message credits"
                )
                recommendations['suggested_plan'] = 'hobby' if user.plan_tier == 'free' else 'standard'
            
            # Check chatbot limit
            chatbots_count = user.chatbots.filter(is_deleted=False).count()
            if chatbots_count >= user.max_ai_agents:
                recommendations['should_upgrade'] = True
                recommendations['reasons'].append(
                    f"Using all {user.max_ai_agents} AI agents"
                )
                recommendations['suggested_plan'] = 'standard' if user.plan_tier in ['free', 'hobby'] else 'pro'
            
            # Usage insights
            avg_daily_credits = analytics['averages']['credits_per_day']
            if avg_daily_credits > 0:
                days_remaining = user.credits_remaining / avg_daily_credits if avg_daily_credits > 0 else 30
                
                if days_remaining < 7:
                    recommendations['usage_insights'].append(
                        f"At current usage rate, credits will run out in {days_remaining:.0f} days"
                    )
                
                if avg_daily_credits > user.message_credits / 30:
                    recommendations['usage_insights'].append(
                        "Daily usage exceeds sustainable rate for current plan"
                    )
            
            # Calculate potential overage costs (if we had pay-per-use)
            overage_credits = max(0, user.credits_used - user.message_credits)
            if overage_credits > 0:
                overage_cost = overage_credits * 0.012  # $12 per 1000 credits
                recommendations['potential_savings'] = overage_cost
                recommendations['usage_insights'].append(
                    f"Potential overage cost: ${overage_cost:.2f}"
                )
            
            return recommendations
            
        except Exception as e:
            logger.error(
                "Failed to get plan recommendations",
                user_id=str(user.id),
                error=str(e)
            )
            return {
                'should_upgrade': False,
                'reasons': [],
                'suggested_plan': None,
                'error': 'Failed to analyze usage'
            }
    
    @staticmethod
    def reset_monthly_usage(user: User) -> bool:
        """
        Reset user's monthly usage (called by billing cycle).
        
        Args:
            user: User to reset
            
        Returns:
            True if reset successfully
        """
        try:
            # Reset user credits
            user.reset_credits()
            
            # Log the reset
            logger.info(
                "Monthly usage reset",
                user_id=str(user.id),
                plan_tier=user.plan_tier,
                new_credits=user.message_credits
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to reset monthly usage",
                user_id=str(user.id),
                error=str(e)
            )
            return False