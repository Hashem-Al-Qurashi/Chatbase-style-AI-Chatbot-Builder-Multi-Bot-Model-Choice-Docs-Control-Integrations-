"""
LLM Service for RAG Pipeline with Privacy Enforcement.

Integrates with OpenAI GPT-3.5-turbo to generate responses with strict privacy controls.
This service implements Layer 2 of the privacy protection system through prompt engineering.

CRITICAL: This service enforces privacy rules at the LLM level to prevent 
private content leakage in responses.
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional, AsyncIterator, List
from dataclasses import dataclass
from enum import Enum

import openai
from openai import AsyncOpenAI

from .context_builder import ContextData
from apps.core.circuit_breaker import CircuitBreaker
from apps.core.monitoring import track_metric
from chatbot_saas.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI_GPT35_TURBO = "gpt-3.5-turbo"
    OPENAI_GPT4 = "gpt-4"
    OPENAI_GPT4_TURBO = "gpt-4-turbo-preview"


@dataclass
class ChatbotConfig:
    """Configuration for chatbot behavior."""
    name: str
    description: str
    personality: str = "helpful and professional"
    temperature: float = 0.7
    max_response_tokens: int = 500
    model: LLMProvider = LLMProvider.OPENAI_GPT35_TURBO
    company_name: str = "our company"
    
    # Privacy settings
    allow_private_reasoning: bool = True
    strict_citation_mode: bool = True
    privacy_protection_level: str = "high"


@dataclass
class GenerationResult:
    """Result from LLM generation."""
    content: str
    usage: Dict[str, int]
    model: str
    finish_reason: str
    
    # Cost tracking
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    
    # Privacy tracking
    privacy_compliant: bool
    citations_extracted: List[str]
    
    # Performance
    generation_time: float


class CostTracker:
    """Track OpenAI API costs."""
    
    # OpenAI pricing (as of December 2024)
    PRICING = {
        "gpt-3.5-turbo": {
            "input": 0.0015 / 1000,   # $0.0015 per 1K input tokens
            "output": 0.002 / 1000,   # $0.002 per 1K output tokens
        },
        "gpt-4": {
            "input": 0.03 / 1000,     # $0.03 per 1K input tokens
            "output": 0.06 / 1000,    # $0.06 per 1K output tokens
        },
        "gpt-4-turbo-preview": {
            "input": 0.01 / 1000,     # $0.01 per 1K input tokens
            "output": 0.03 / 1000,    # $0.03 per 1K output tokens
        }
    }
    
    @classmethod
    def calculate_cost(
        cls,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate cost for API usage.
        
        Args:
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            
        Returns:
            float: Estimated cost in USD
        """
        if model not in cls.PRICING:
            logger.warning(f"Unknown model for cost calculation: {model}")
            return 0.0
        
        pricing = cls.PRICING[model]
        input_cost = input_tokens * pricing["input"]
        output_cost = output_tokens * pricing["output"]
        
        return input_cost + output_cost
    
    @classmethod
    def track_generation(
        cls,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Track generation cost and metrics.
        
        Args:
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            
        Returns:
            float: Cost in USD
        """
        cost = cls.calculate_cost(model, input_tokens, output_tokens)
        
        # Track metrics
        track_metric("llm.cost", cost)
        track_metric("llm.input_tokens", input_tokens)
        track_metric("llm.output_tokens", output_tokens)
        track_metric(f"llm.{model}.usage", 1)
        
        logger.info(f"LLM usage: {input_tokens} in + {output_tokens} out = ${cost:.4f}")
        
        return cost


class PromptTemplates:
    """Template system for privacy-enforcing prompts."""
    
    @staticmethod
    def get_system_prompt(
        chatbot_config: ChatbotConfig,
        privacy_mode: str = "strict"
    ) -> str:
        """
        Get system prompt with privacy enforcement.
        
        Args:
            chatbot_config: Chatbot configuration
            privacy_mode: Privacy enforcement level
            
        Returns:
            str: System prompt with privacy rules
        """
        base_prompt = f"""You are a helpful AI assistant for {chatbot_config.company_name}.

Your personality: {chatbot_config.personality}

Answer questions based ONLY on the provided context. Be helpful, accurate, and concise."""
        
        if privacy_mode == "strict":
            privacy_rules = """
CRITICAL PRIVACY RULES - NEVER VIOLATE THESE:

1. CITATION RULES:
   - Only cite and reference sources marked as [CITABLE-X]
   - NEVER mention, quote, or reference [PRIVATE] sources in your response
   - If you see [PRIVATE] content, you may use it for understanding but must NOT mention it

2. CONTENT RESTRICTIONS:
   - If asked about information that only appears in [PRIVATE] sources, say "I don't have information about that in my available sources"
   - Never reveal that private sources exist or that you have access to private information
   - Do not mention the concept of "private" or "citable" sources to the user

3. RESPONSE REQUIREMENTS:
   - Always provide citations for factual claims using [CITABLE-X] sources
   - Format citations as: "According to [Source Title], ..."
   - If no citable sources support an answer, say "I don't have enough information to answer that question"

4. FORBIDDEN ACTIONS:
   - Do not mention seeing private or restricted content
   - Do not reference private source IDs or content
   - Do not acknowledge the existence of multiple content access levels
"""
        else:
            privacy_rules = """
PRIVACY GUIDELINES:
- Cite your sources when making factual claims
- Only reference sources marked as [CITABLE-X] in your responses
- Use context responsibly and accurately
"""
        
        return base_prompt + privacy_rules
    
    @staticmethod
    def format_query_with_context(
        user_query: str,
        context: ContextData
    ) -> str:
        """
        Format user query with context.
        
        Args:
            user_query: User's query
            context: Context data with sources
            
        Returns:
            str: Formatted query with context
        """
        return f"""Context:
{context.full_context}

User Question: {user_query}

Please answer the question based on the provided context. Remember to follow all citation and privacy rules."""


class LLMService:
    """
    LLM service with privacy enforcement and cost tracking.
    
    This service implements Layer 2 of privacy protection through
    carefully crafted prompts that prevent private content leakage.
    """
    
    def __init__(self):
        """Initialize LLM service."""
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key or api_key.startswith('sk-your'):
            logger.warning("OpenAI API key not configured, running in demo mode")
            self.openai_client = None
            self.demo_mode = True
        else:
            self.openai_client = AsyncOpenAI(api_key=api_key)
            self.demo_mode = False
        
        # Circuit breaker for OpenAI API (following CircuitBreaker interface)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60,
            expected_exception=Exception  # Single exception type as required by interface
        )
        
        self.cost_tracker = CostTracker()
        
        mode = "demo mode" if self.demo_mode else "OpenAI GPT-3.5-turbo"
        logger.info(f"Initialized LLMService with {mode}")
    
    async def generate_response(
        self,
        context: ContextData,
        user_query: str,
        chatbot_config: ChatbotConfig
    ) -> GenerationResult:
        """
        Generate response with privacy enforcement.
        
        Args:
            context: Context data with sources
            user_query: User's query
            chatbot_config: Chatbot configuration
            
        Returns:
            GenerationResult: Generated response with metadata
        """
        start_time = time.time()
        
        try:
            # Build privacy-enforcing system prompt
            system_prompt = PromptTemplates.get_system_prompt(
                chatbot_config,
                privacy_mode="strict" if chatbot_config.strict_citation_mode else "normal"
            )
            
            # Format user query with context
            formatted_query = PromptTemplates.format_query_with_context(
                user_query, context
            )
            
            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": formatted_query}
            ]
            
            # In demo mode, generate a mock response
            if self.demo_mode:
                # Generate a demo response based on the context
                if context.citable_sources:
                    first_source = context.citable_sources[0]
                    message_content = (
                        f"Based on the document provided, I can see it contains information about "
                        f"{first_source.content[:100]}... "
                        f"\n\nThe document appears to be related to the topics you've uploaded. "
                        f"I found {len(context.citable_sources)} relevant sections that match your query."
                    )
                else:
                    message_content = (
                        "I understand you're asking about the PDF content. However, I need to have "
                        "the document properly processed first to provide accurate information. "
                        "Please ensure the document has been uploaded and indexed."
                    )
                
                # Create mock response object
                class MockResponse:
                    class Choice:
                        class Message:
                            content = message_content
                        message = Message()
                        finish_reason = "stop"
                    class Usage:
                        prompt_tokens = 100
                        completion_tokens = 50
                        total_tokens = 150
                    choices = [Choice()]
                    usage = Usage()
                
                response = MockResponse()
            else:
                # Generate response with circuit breaker protection
                async def _generate():
                    return await self.openai_client.chat.completions.create(
                        model=chatbot_config.model.value,
                        messages=messages,
                        temperature=chatbot_config.temperature,
                        max_tokens=chatbot_config.max_response_tokens,
                        timeout=30.0
                    )
                
                response = await self.circuit_breaker.call(_generate)
            
            generation_time = time.time() - start_time
            
            # Extract response data
            message_content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            usage = response.usage
            
            # Calculate cost
            estimated_cost = self.cost_tracker.track_generation(
                chatbot_config.model.value,
                usage.prompt_tokens,
                usage.completion_tokens
            )
            
            # Extract citations (simple implementation)
            citations = self._extract_citations(message_content, context)
            
            # Basic privacy compliance check
            privacy_compliant = self._check_privacy_compliance(
                message_content, context
            )
            
            # Track metrics
            track_metric("llm.generation_time", generation_time)
            track_metric("llm.response_length", len(message_content))
            track_metric("llm.privacy_compliant", 1 if privacy_compliant else 0)
            
            logger.info(
                f"Generated response in {generation_time:.3f}s: "
                f"{len(message_content)} chars, ${estimated_cost:.4f}, "
                f"privacy_compliant={privacy_compliant}"
            )
            
            return GenerationResult(
                content=message_content,
                usage={
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens
                },
                model=chatbot_config.model.value,
                finish_reason=finish_reason,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                estimated_cost=estimated_cost,
                privacy_compliant=privacy_compliant,
                citations_extracted=citations,
                generation_time=generation_time
            )
            
        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {str(e)}")
            raise
        except openai.APITimeoutError as e:
            logger.error(f"OpenAI API timeout: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            raise
    
    async def generate_streaming_response(
        self,
        context: ContextData,
        user_query: str,
        chatbot_config: ChatbotConfig
    ) -> AsyncIterator[str]:
        """
        Generate streaming response with privacy checks.
        
        Args:
            context: Context data with sources
            user_query: User's query
            chatbot_config: Chatbot configuration
            
        Yields:
            str: Response chunks
        """
        try:
            # Build system prompt
            system_prompt = PromptTemplates.get_system_prompt(
                chatbot_config, privacy_mode="strict"
            )
            
            # Format query
            formatted_query = PromptTemplates.format_query_with_context(
                user_query, context
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": formatted_query}
            ]
            
            # Stream response
            stream = await self.openai_client.chat.completions.create(
                model=chatbot_config.model.value,
                messages=messages,
                temperature=chatbot_config.temperature,
                max_tokens=chatbot_config.max_response_tokens,
                stream=True,
                timeout=30.0
            )
            
            full_response = ""
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content_chunk = chunk.choices[0].delta.content
                    full_response += content_chunk
                    
                    # Basic privacy check on accumulating content
                    if not self._contains_private_leak(full_response, context):
                        yield content_chunk
                    else:
                        logger.warning("Privacy leak detected in streaming response")
                        yield "[Response filtered for privacy protection]"
                        break
            
        except Exception as e:
            logger.error(f"Streaming generation failed: {str(e)}")
            yield f"Error generating response: {str(e)}"
    
    def _extract_citations(
        self,
        response: str,
        context: ContextData
    ) -> List[str]:
        """
        Extract citations from response.
        
        Args:
            response: Generated response
            context: Context data
            
        Returns:
            List[str]: Extracted citations
        """
        citations = []
        
        # Look for citation patterns in response
        import re
        
        # Find references to citable sources
        for i, source in enumerate(context.citable_sources, 1):
            pattern = f"\\[CITABLE-{i}\\]"
            if re.search(pattern, response):
                if source.citation_text:
                    citations.append(source.citation_text)
        
        return citations
    
    def _check_privacy_compliance(
        self,
        response: str,
        context: ContextData
    ) -> bool:
        """
        Check if response complies with privacy rules.
        
        Args:
            response: Generated response
            context: Context data
            
        Returns:
            bool: True if privacy compliant
        """
        # Check for private source references
        if "[PRIVATE]" in response:
            logger.warning("Response contains private source markers")
            return False
        
        # Check for mentions of private content
        for source in context.private_sources:
            # Look for unique phrases from private content
            if source.content and len(source.content) > 50:
                # Check for longer phrases that might be quoted
                words = source.content.split()
                if len(words) >= 5:
                    phrase = " ".join(words[:5])
                    if phrase.lower() in response.lower():
                        logger.warning(f"Response may contain private content: {phrase}")
                        return False
        
        return True
    
    def _contains_private_leak(
        self,
        partial_response: str,
        context: ContextData
    ) -> bool:
        """
        Check if partial response contains privacy leaks.
        
        Args:
            partial_response: Partial response being generated
            context: Context data
            
        Returns:
            bool: True if private leak detected
        """
        # Simple check for private markers
        if "[PRIVATE]" in partial_response:
            return True
        
        # Check against private source content
        for source in context.private_sources:
            if source.content and len(source.content) > 20:
                # Check for exact matches of longer phrases
                if source.content[:20].lower() in partial_response.lower():
                    return True
        
        return False


class LLMFallbackStrategy:
    """Fallback strategies for LLM failures."""
    
    @staticmethod
    def handle_rate_limit() -> str:
        """Return graceful message when rate limited."""
        return "I'm currently experiencing high demand. Please try again in a moment."
    
    @staticmethod
    def handle_context_too_long(context: str) -> str:
        """Return message when context is too long."""
        return "The information you're asking about is quite extensive. Could you please ask a more specific question?"
    
    @staticmethod
    def handle_timeout() -> str:
        """Return message when generation times out."""
        return "I'm having trouble generating a response right now. Please try again."
    
    @staticmethod
    def handle_privacy_violation() -> str:
        """Return message when privacy violation is detected."""
        return "I apologize, but I cannot provide that information based on my available sources."
    
    @staticmethod
    def handle_no_context() -> str:
        """Return message when no relevant context is found."""
        return "I don't have enough information in my knowledge base to answer that question. Could you provide more context or ask about something else?"


# Global LLM service instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    Get or create global LLM service instance.
    
    Returns:
        LLMService: LLM service instance
    """
    global _llm_service
    
    if _llm_service is None:
        _llm_service = LLMService()
    
    return _llm_service