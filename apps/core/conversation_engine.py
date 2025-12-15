"""
Core conversation engine with memory and context management.
"""

from typing import Dict, List, Any, Optional
from apps.core.ai_service import get_ai_service
from apps.conversations.models import Conversation, Message
from apps.accounts.models import User
from apps.chatbots.models import Chatbot
from apps.core.plan_limits import PlanLimitsService
from apps.core.usage_tracking import UsageTrackingService
import structlog
import uuid

logger = structlog.get_logger()


class ConversationEngine:
    """
    Advanced conversation engine with memory and context.
    """
    
    def __init__(self, chatbot: Chatbot):
        """Initialize conversation engine for a specific chatbot."""
        self.chatbot = chatbot
        self.ai_service = get_ai_service()
        
    def process_message(
        self,
        user: User,
        message: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process user message and generate intelligent response.
        
        Args:
            user: User sending the message
            message: User's message content
            conversation_id: Optional existing conversation ID
            
        Returns:
            Dict with response, conversation info, and metadata
        """
        try:
            logger.info(
                "Processing conversation message",
                user_id=str(user.id),
                chatbot_id=str(self.chatbot.id),
                message_length=len(message),
                conversation_id=conversation_id
            )
            
            # Step 1: Credit check (no claims without validation)
            model_name = self.chatbot.model_name or 'gpt-3.5-turbo'
            credits_needed = PlanLimitsService.get_credit_cost_for_model(model_name)
            
            can_proceed, reason = PlanLimitsService.can_send_message(user, credits_needed)
            if not can_proceed:
                return {
                    'success': False,
                    'error': 'Insufficient credits',
                    'reason': reason,
                    'credits_remaining': user.credits_remaining,
                    'suggested_plan': PlanLimitsService.get_upgrade_suggestion(user, 'more_credits')
                }
            
            # Step 2: Get or create conversation
            conversation = self._get_or_create_conversation(user, conversation_id)
            
            # Step 3: Build conversation context
            context = self._build_conversation_context(conversation)
            
            # Step 4: Generate AI response
            ai_result = self.ai_service.generate_response(
                message=message,
                conversation_history=context,
                model=model_name,
                max_tokens=self.chatbot.max_tokens or 500,
                temperature=self.chatbot.temperature or 0.7,
                system_prompt=self._build_system_prompt()
            )
            
            if not ai_result['success']:
                return {
                    'success': False,
                    'error': 'AI generation failed',
                    'details': ai_result['error']
                }
            
            # Step 5: Save messages to database
            user_message = self._save_user_message(conversation, message)
            bot_message = self._save_bot_message(conversation, ai_result['response'])
            
            # Step 6: Consume credits and track usage
            credit_consumed = user.consume_credits(credits_needed)
            if credit_consumed:
                UsageTrackingService.record_message_usage(
                    user=user,
                    model_name=model_name,
                    tokens_used=ai_result['total_tokens'],
                    chatbot_id=str(self.chatbot.id)
                )
            
            # Step 7: Return complete response
            result = {
                'success': True,
                'response': ai_result['response'],
                'conversation_id': str(conversation.id),
                'message_id': str(bot_message.id),
                'model_used': model_name,
                'tokens_used': ai_result['total_tokens'],
                'credits_consumed': credits_needed if credit_consumed else 0,
                'credits_remaining': user.credits_remaining,
                'processing_time': ai_result['processing_time'],
                'conversation_length': conversation.messages.count()
            }
            
            logger.info(
                "Message processed successfully",
                user_id=str(user.id),
                conversation_id=str(conversation.id),
                tokens_used=ai_result['total_tokens'],
                credits_consumed=credits_needed,
                processing_time=f"{ai_result['processing_time']:.2f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Message processing failed",
                user_id=str(user.id),
                error=str(e)
            )
            
            return {
                'success': False,
                'error': 'Message processing failed',
                'details': str(e)
            }
    
    def _get_or_create_conversation(self, user: User, conversation_id: Optional[str]) -> Conversation:
        """Get existing conversation or create new one."""
        if conversation_id:
            try:
                conversation = Conversation.objects.get(
                    id=conversation_id,
                    chatbot=self.chatbot
                )
                logger.info("Using existing conversation", conversation_id=conversation_id)
                return conversation
            except Conversation.DoesNotExist:
                logger.warning("Conversation not found, creating new one", conversation_id=conversation_id)
        
        # Create new conversation
        conversation = Conversation.objects.create(
            chatbot=self.chatbot,
            title=f"Chat with {user.first_name or user.email}",
            metadata={'user_email': user.email}
        )
        
        logger.info("New conversation created", conversation_id=str(conversation.id))
        return conversation
    
    def _build_conversation_context(self, conversation: Conversation) -> List[Dict[str, str]]:
        """Build conversation history for AI context."""
        # Get last 20 messages (avoid negative indexing issue)
        all_messages = conversation.messages.order_by('created_at')
        messages = list(all_messages)[-20:] if all_messages.count() > 20 else list(all_messages)
        
        context = []
        for msg in messages:
            context.append({
                'role': msg.role,  # 'user' or 'assistant'
                'content': msg.content
            })
        
        logger.info(
            "Conversation context built",
            conversation_id=str(conversation.id),
            context_messages=len(context)
        )
        
        return context
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for the chatbot."""
        base_prompt = f"""You are {self.chatbot.name}, a helpful AI assistant.

Your personality:
- Friendly and professional
- Concise but thorough
- Helpful and accurate

Your capabilities:
- Answer questions based on your knowledge
- Have conversations and remember context
- Provide helpful suggestions and guidance

Always aim to be helpful while being honest about your limitations."""

        if self.chatbot.welcome_message:
            base_prompt += f"\n\nWelcome message style: {self.chatbot.welcome_message}"
        
        return base_prompt
    
    def _save_user_message(self, conversation: Conversation, content: str) -> Message:
        """Save user message to database."""
        sequence_num = conversation.messages.count() + 1
        message = Message.objects.create(
            conversation=conversation,
            content=content,
            role='user',
            sequence_number=sequence_num,
            metadata={'timestamp': str(sequence_num)}
        )
        return message
    
    def _save_bot_message(self, conversation: Conversation, content: str) -> Message:
        """Save bot response to database."""
        sequence_num = conversation.messages.count() + 1
        message = Message.objects.create(
            conversation=conversation,
            content=content,
            role='assistant',
            sequence_number=sequence_num,
            metadata={'timestamp': str(sequence_num)}
        )
        return message