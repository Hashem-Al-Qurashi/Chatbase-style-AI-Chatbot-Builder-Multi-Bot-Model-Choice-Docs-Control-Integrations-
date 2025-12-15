"""
Core AI service for chatbot conversations.
Built for reliability, performance, and validation.
"""

import os
from openai import OpenAI
from typing import Dict, List, Optional, Any
import structlog
import time

logger = structlog.get_logger()


class AIService:
    """Core AI service for generating chatbot responses."""
    
    def __init__(self):
        """Initialize AI service with OpenAI client."""
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=self.api_key)
        
        # Validate connection on startup
        self._validate_connection()
        
        logger.info("AI service initialized successfully")
    
    def _validate_connection(self):
        """Validate OpenAI API connection."""
        try:
            test_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Test connection"}],
                max_tokens=5
            )
            logger.info("OpenAI connection validated successfully")
        except Exception as e:
            logger.error(f"OpenAI connection validation failed: {e}")
            raise
    
    def generate_response(
        self,
        message: str,
        conversation_history: List[Dict[str, str]] = None,
        model: str = "gpt-3.5-turbo",
        max_tokens: int = 500,
        temperature: float = 0.7,
        system_prompt: str = None
    ) -> Dict[str, Any]:
        """
        Generate AI response with full validation.
        
        Args:
            message: User's input message
            conversation_history: Previous messages for context
            model: AI model to use
            max_tokens: Maximum response length
            temperature: Response creativity (0-1)
            system_prompt: Custom system instructions
            
        Returns:
            Dict with response, tokens used, processing time
        """
        start_time = time.time()
        
        try:
            logger.info(
                "Generating AI response",
                model=model,
                message_length=len(message),
                history_length=len(conversation_history or [])
            )
            
            # Build messages array
            messages = []
            
            # Add system prompt
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                messages.append({
                    "role": "system", 
                    "content": "You are a helpful AI assistant. Be friendly, accurate, and concise."
                })
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history[-10:]:  # Last 10 messages for context
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Generate response
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=30
            )
            
            # Extract response data
            response_content = completion.choices[0].message.content
            input_tokens = completion.usage.prompt_tokens
            output_tokens = completion.usage.completion_tokens
            total_tokens = completion.usage.total_tokens
            
            processing_time = time.time() - start_time
            
            result = {
                'response': response_content,
                'model_used': model,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens,
                'processing_time': processing_time,
                'success': True,
                'error': None
            }
            
            logger.info(
                "AI response generated successfully",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                processing_time=f"{processing_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            logger.error(
                "AI response generation failed",
                model=model,
                error=str(e),
                processing_time=f"{processing_time:.2f}s"
            )
            
            return {
                'response': "I apologize, but I'm having trouble processing your message right now. Please try again.",
                'model_used': model,
                'input_tokens': 0,
                'output_tokens': 0,
                'total_tokens': 0,
                'processing_time': processing_time,
                'success': False,
                'error': str(e)
            }
    
    def test_models(self) -> Dict[str, bool]:
        """
        Test all available AI models.
        
        Returns:
            Dict of model_name: working_status
        """
        models_to_test = [
            "gpt-3.5-turbo",
            "gpt-4o-mini", 
            "gpt-4o"
        ]
        
        results = {}
        
        for model in models_to_test:
            try:
                test_result = self.generate_response(
                    message="Test message",
                    model=model,
                    max_tokens=10
                )
                results[model] = test_result['success']
                
                logger.info(
                    "Model test completed",
                    model=model,
                    working=test_result['success']
                )
                
            except Exception as e:
                results[model] = False
                logger.error(f"Model {model} test failed: {e}")
        
        return results


# Global AI service instance
ai_service = None

def get_ai_service() -> AIService:
    """Get or create AI service instance."""
    global ai_service
    if ai_service is None:
        ai_service = AIService()
    return ai_service