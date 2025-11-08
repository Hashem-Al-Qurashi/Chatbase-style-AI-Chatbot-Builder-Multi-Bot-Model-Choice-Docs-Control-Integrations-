"""
RAG Orchestration Engine.

Coordinates the complete RAG pipeline with privacy controls, citation tracking,
and enterprise-grade error handling and observability.
"""

import asyncio
import time
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import structlog

from django.core.cache import cache
from django.conf import settings as django_settings

from apps.core.vector_storage import VectorStorageService, VectorStorageConfig
from apps.core.embedding_service import OpenAIEmbeddingService
from apps.core.exceptions import RAGError, VectorStorageError
from chatbot_saas.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


class QueryIntent(Enum):
    """Query intent classification."""
    QUESTION_ANSWER = "qa"
    RESEARCH = "research" 
    SUMMARIZATION = "summary"
    COMPARISON = "comparison"
    GENERATION = "generation"


class PrivacyMode(Enum):
    """Privacy mode for RAG responses."""
    STRICT = "strict"          # Only citable content in responses
    CONTEXTUAL = "contextual"  # Use private for context, cite only public
    INTERNAL = "internal"      # All content available (admin only)


@dataclass
class RAGQuery:
    """RAG query with metadata."""
    text: str
    user_id: str
    chatbot_id: str
    session_id: Optional[str] = None
    knowledge_base_ids: Optional[List[str]] = None
    privacy_mode: PrivacyMode = PrivacyMode.STRICT
    intent: Optional[QueryIntent] = None
    max_context_tokens: int = 4000
    temperature: float = 0.7
    top_k_results: int = 10
    
    # Query metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    request_id: str = field(default_factory=lambda: hashlib.md5(str(time.time()).encode()).hexdigest()[:8])


@dataclass
class RAGContext:
    """RAG context with sources and citations."""
    citable_sources: List[Dict[str, Any]]
    private_sources: List[Dict[str, Any]]
    total_tokens: int
    truncated: bool
    query_embedding: List[float]
    
    # Context assembly metadata
    assembly_time: float
    source_count: Dict[str, int]  # {'citable': N, 'private': N}
    knowledge_bases: List[str]
    
    def get_formatted_context(self, include_private: bool = True) -> str:
        """Get formatted context for LLM."""
        parts = []
        
        if self.citable_sources:
            parts.append("CITABLE SOURCES (can be referenced in response):")
            for i, source in enumerate(self.citable_sources, 1):
                citation = source.get('citation', f'Source {i}')
                content = source.get('content', '')
                parts.append(f"[CITE-{i}] {content}\nCitation: {citation}")
        
        if include_private and self.private_sources:
            parts.append("\nPRIVATE SOURCES (for context only, do not reference directly):")
            for source in self.private_sources:
                content = source.get('content', '')
                parts.append(f"[CONTEXT] {content}")
        
        return "\n\n".join(parts)


@dataclass
class RAGResponse:
    """RAG response with metadata."""
    text: str
    citations: List[Dict[str, Any]]
    context_used: RAGContext
    metadata: Dict[str, Any]
    
    # Response metadata
    generation_time: float
    token_usage: Dict[str, int]
    cost_estimate: float
    privacy_validated: bool
    
    # Quality metrics
    confidence_score: Optional[float] = None
    relevance_score: Optional[float] = None


class QueryProcessor:
    """Processes and analyzes queries."""
    
    def __init__(self):
        self.logger = structlog.get_logger().bind(component="QueryProcessor")
    
    def analyze_query(self, query: RAGQuery) -> Dict[str, Any]:
        """Analyze query for intent, complexity, and requirements."""
        analysis = {
            'intent': self._classify_intent(query.text),
            'complexity': self._assess_complexity(query.text),
            'keywords': self._extract_keywords(query.text),
            'requires_citations': True,  # Default to requiring citations
            'estimated_response_length': self._estimate_response_length(query.text)
        }
        
        self.logger.info(
            "Query analyzed",
            query_id=query.request_id,
            intent=analysis['intent'].value if analysis['intent'] else None,
            complexity=analysis['complexity'],
            keywords_count=len(analysis['keywords'])
        )
        
        return analysis
    
    def _classify_intent(self, text: str) -> QueryIntent:
        """Classify query intent using simple heuristics."""
        text_lower = text.lower()
        
        # Question words indicate Q&A
        if any(word in text_lower for word in ['what', 'how', 'why', 'when', 'where', 'who']):
            return QueryIntent.QUESTION_ANSWER
        
        # Comparison indicators
        if any(word in text_lower for word in ['compare', 'versus', 'vs', 'difference', 'similar']):
            return QueryIntent.COMPARISON
        
        # Summary indicators
        if any(word in text_lower for word in ['summarize', 'summary', 'overview', 'explain']):
            return QueryIntent.SUMMARIZATION
        
        # Research indicators
        if any(word in text_lower for word in ['research', 'analyze', 'investigate', 'study']):
            return QueryIntent.RESEARCH
        
        # Generation indicators
        if any(word in text_lower for word in ['create', 'generate', 'write', 'draft']):
            return QueryIntent.GENERATION
        
        # Default to Q&A
        return QueryIntent.QUESTION_ANSWER
    
    def _assess_complexity(self, text: str) -> str:
        """Assess query complexity."""
        word_count = len(text.split())
        
        if word_count < 5:
            return "simple"
        elif word_count < 15:
            return "moderate"
        else:
            return "complex"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract key terms from query."""
        # Simple keyword extraction - in production, use NLP libraries
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = text.lower().split()
        keywords = [word.strip('.,!?') for word in words if word not in stop_words and len(word) > 2]
        return keywords[:10]  # Limit to top 10
    
    def _estimate_response_length(self, text: str) -> str:
        """Estimate appropriate response length."""
        if any(word in text.lower() for word in ['brief', 'short', 'quick']):
            return "short"
        elif any(word in text.lower() for word in ['detailed', 'comprehensive', 'thorough']):
            return "detailed"
        else:
            return "medium"


class ContextAssembler:
    """Assembles context from search results."""
    
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.logger = structlog.get_logger().bind(component="ContextAssembler")
    
    def assemble_context(
        self,
        search_results: List[Dict[str, Any]],
        query_embedding: List[float],
        privacy_mode: PrivacyMode = PrivacyMode.STRICT
    ) -> RAGContext:
        """Assemble context from search results with privacy controls."""
        start_time = time.time()
        
        # Separate sources by privacy level
        citable_sources = []
        private_sources = []
        
        for result in search_results:
            metadata = result.get('metadata', {})
            is_citable = metadata.get('is_citable', True)
            
            source_data = {
                'content': result.get('content', ''),
                'score': result.get('score', 0.0),
                'chunk_id': result.get('id', ''),
                'document_id': metadata.get('document_id', ''),
                'knowledge_base_id': metadata.get('knowledge_base_id', ''),
                'citation': self._generate_citation(metadata)
            }
            
            if is_citable:
                citable_sources.append(source_data)
            else:
                private_sources.append(source_data)
        
        # Apply privacy mode filtering
        if privacy_mode == PrivacyMode.STRICT:
            # Only use citable sources
            final_citable = citable_sources
            final_private = []
        elif privacy_mode == PrivacyMode.CONTEXTUAL:
            # Use both but prioritize citable
            final_citable = citable_sources
            final_private = private_sources
        else:  # INTERNAL
            # All sources treated as citable for internal use
            final_citable = citable_sources + private_sources
            final_private = []
        
        # Fit within token limits
        final_citable, final_private, total_tokens, truncated = self._fit_within_token_limit(
            final_citable, final_private
        )
        
        assembly_time = time.time() - start_time
        
        context = RAGContext(
            citable_sources=final_citable,
            private_sources=final_private,
            total_tokens=total_tokens,
            truncated=truncated,
            query_embedding=query_embedding,
            assembly_time=assembly_time,
            source_count={
                'citable': len(final_citable),
                'private': len(final_private)
            },
            knowledge_bases=list(set(
                source.get('knowledge_base_id', '') 
                for source in final_citable + final_private
                if source.get('knowledge_base_id')
            ))
        )
        
        self.logger.info(
            "Context assembled",
            citable_sources=len(final_citable),
            private_sources=len(final_private),
            total_tokens=total_tokens,
            truncated=truncated,
            assembly_time=assembly_time
        )
        
        return context
    
    def _generate_citation(self, metadata: Dict[str, Any]) -> str:
        """Generate citation text from metadata."""
        title = metadata.get('document_title', 'Untitled')
        author = metadata.get('document_author')
        url = metadata.get('document_url')
        page = metadata.get('page_number')
        
        citation_parts = [title]
        
        if author:
            citation_parts.append(f"by {author}")
        
        if page:
            citation_parts.append(f"page {page}")
        
        if url:
            citation_parts.append(f"({url})")
        
        return ", ".join(citation_parts)
    
    def _fit_within_token_limit(
        self,
        citable_sources: List[Dict[str, Any]],
        private_sources: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int, bool]:
        """Fit sources within token limit, prioritizing citable sources."""
        # Simple token estimation: 4 characters per token
        def estimate_tokens(text: str) -> int:
            return len(text) // 4
        
        final_citable = []
        final_private = []
        total_tokens = 0
        truncated = False
        
        # Add citable sources first (higher priority)
        for source in citable_sources:
            content = source['content']
            tokens = estimate_tokens(content)
            
            if total_tokens + tokens <= self.max_tokens:
                final_citable.append(source)
                total_tokens += tokens
            else:
                truncated = True
                break
        
        # Add private sources if space remains
        for source in private_sources:
            content = source['content']
            tokens = estimate_tokens(content)
            
            if total_tokens + tokens <= self.max_tokens:
                final_private.append(source)
                total_tokens += tokens
            else:
                truncated = True
                break
        
        return final_citable, final_private, total_tokens, truncated


class LLMService:
    """Handles LLM interactions with cost tracking."""
    
    def __init__(self):
        self.logger = structlog.get_logger().bind(component="LLMService")
        self.cost_tracker = CostTracker()
    
    async def generate_response(
        self,
        query: RAGQuery,
        context: RAGContext,
        query_analysis: Dict[str, Any]
    ) -> RAGResponse:
        """Generate response using LLM with context."""
        start_time = time.time()
        
        # Build prompt
        prompt = self._build_prompt(query, context, query_analysis)
        
        # Call LLM (mock implementation for now)
        response_text, token_usage = await self._call_llm(prompt, query.temperature)
        
        # Extract citations from response
        citations = self._extract_citations(response_text, context)
        
        # Calculate costs
        cost = self.cost_tracker.calculate_cost(
            model="gpt-3.5-turbo",  # Default model
            input_tokens=token_usage['input'],
            output_tokens=token_usage['output']
        )
        
        generation_time = time.time() - start_time
        
        response = RAGResponse(
            text=response_text,
            citations=citations,
            context_used=context,
            metadata={
                'query_id': query.request_id,
                'model': 'gpt-3.5-turbo',
                'prompt_tokens': len(prompt) // 4,  # Rough estimate
                'query_analysis': query_analysis
            },
            generation_time=generation_time,
            token_usage=token_usage,
            cost_estimate=cost,
            privacy_validated=False  # Will be validated by privacy filter
        )
        
        self.logger.info(
            "Response generated",
            query_id=query.request_id,
            generation_time=generation_time,
            input_tokens=token_usage['input'],
            output_tokens=token_usage['output'],
            cost=cost
        )
        
        return response
    
    def _build_prompt(
        self,
        query: RAGQuery,
        context: RAGContext,
        query_analysis: Dict[str, Any]
    ) -> str:
        """Build prompt for LLM."""
        include_private = query.privacy_mode != PrivacyMode.STRICT
        context_text = context.get_formatted_context(include_private=include_private)
        
        intent_instructions = {
            QueryIntent.QUESTION_ANSWER: "Provide a clear, accurate answer to the question.",
            QueryIntent.RESEARCH: "Provide a comprehensive analysis with multiple perspectives.",
            QueryIntent.SUMMARIZATION: "Provide a concise summary of the key points.",
            QueryIntent.COMPARISON: "Compare and contrast the different aspects systematically.",
            QueryIntent.GENERATION: "Create original content based on the provided information."
        }
        
        intent = query_analysis.get('intent', QueryIntent.QUESTION_ANSWER)
        instruction = intent_instructions.get(intent, intent_instructions[QueryIntent.QUESTION_ANSWER])
        
        privacy_instruction = ""
        if query.privacy_mode == PrivacyMode.STRICT:
            privacy_instruction = "\nIMPORTANT: Only reference information from [CITE-N] sources in your response. Do not reference [CONTEXT] sources."
        elif query.privacy_mode == PrivacyMode.CONTEXTUAL:
            privacy_instruction = "\nIMPORTANT: You may use [CONTEXT] sources for understanding, but only cite [CITE-N] sources in your response."
        
        prompt = f"""Based on the following sources, {instruction.lower()}

{context_text}

Query: {query.text}

{privacy_instruction}

Please provide a response with proper citations using the format [CITE-N] where N is the source number.

Response:"""
        
        return prompt
    
    async def _call_llm(self, prompt: str, temperature: float) -> Tuple[str, Dict[str, int]]:
        """Call LLM API (mock implementation)."""
        # Mock implementation - in production, use OpenAI API
        await asyncio.sleep(0.1)  # Simulate API delay
        
        # Estimate token usage
        input_tokens = len(prompt) // 4
        output_tokens = min(500, max(50, input_tokens // 3))  # Reasonable output length
        
        # Mock response
        response_text = f"""Based on the provided sources, I can help answer your question.

This is a mock response that would normally be generated by the LLM using the provided context and following the privacy guidelines.

[CITE-1] This reference would cite the first source.

The response would be tailored to the query intent and privacy mode specified."""
        
        return response_text, {
            'input': input_tokens,
            'output': output_tokens
        }
    
    def _extract_citations(self, response_text: str, context: RAGContext) -> List[Dict[str, Any]]:
        """Extract citation information from response."""
        import re
        
        citations = []
        cite_pattern = r'\[CITE-(\d+)\]'
        
        for match in re.finditer(cite_pattern, response_text):
            cite_num = int(match.group(1))
            if cite_num <= len(context.citable_sources):
                source = context.citable_sources[cite_num - 1]
                citations.append({
                    'cite_number': cite_num,
                    'citation_text': source.get('citation', ''),
                    'document_id': source.get('document_id', ''),
                    'chunk_id': source.get('chunk_id', ''),
                    'score': source.get('score', 0.0)
                })
        
        return citations


class CostTracker:
    """Track and calculate API costs."""
    
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
    def calculate_cost(cls, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for API usage."""
        if model not in cls.PRICING:
            return 0.0
        
        pricing = cls.PRICING[model]
        input_cost = input_tokens * pricing["input"]
        output_cost = output_tokens * pricing["output"]
        
        return input_cost + output_cost


class PrivacyValidator:
    """Validates responses for privacy compliance."""
    
    def __init__(self):
        self.logger = structlog.get_logger().bind(component="PrivacyValidator")
    
    def validate_response(self, response: RAGResponse, query: RAGQuery) -> bool:
        """Validate response meets privacy requirements."""
        # Check for private content leakage
        private_content_snippets = []
        for source in response.context_used.private_sources:
            content = source.get('content', '')
            # Extract key phrases that shouldn't appear in responses
            words = content.split()
            if len(words) > 3:
                # Sample 3-word phrases as potential leakage indicators
                for i in range(len(words) - 2):
                    phrase = ' '.join(words[i:i+3])
                    private_content_snippets.append(phrase)
        
        # Check if response contains private content
        response_lower = response.text.lower()
        violations = []
        
        for snippet in private_content_snippets:
            if len(snippet) > 10 and snippet.lower() in response_lower:
                violations.append(f"Private content detected: {snippet}")
        
        if violations:
            self.logger.warning(
                "Privacy violations detected",
                query_id=query.request_id,
                violations=violations
            )
            return False
        
        # Validate citations are only from citable sources
        valid_citations = True
        for citation in response.citations:
            cite_num = citation.get('cite_number', 0)
            if cite_num > len(response.context_used.citable_sources):
                valid_citations = False
                break
        
        if not valid_citations:
            self.logger.warning(
                "Invalid citations detected",
                query_id=query.request_id
            )
            return False
        
        self.logger.info(
            "Privacy validation passed",
            query_id=query.request_id,
            citations_count=len(response.citations)
        )
        
        return True


class RAGOrchestrator:
    """Main RAG orchestration service."""
    
    def __init__(self):
        self.logger = structlog.get_logger().bind(component="RAGOrchestrator")
        
        # Initialize components
        self.query_processor = QueryProcessor()
        self.context_assembler = ContextAssembler()
        self.llm_service = LLMService()
        self.privacy_validator = PrivacyValidator()
        
        # Initialize storage services
        self.vector_service = None
        self.embedding_service = None
        
        # Cache settings
        self.cache_ttl = 300  # 5 minutes
    
    async def initialize(self) -> bool:
        """Initialize the orchestrator."""
        try:
            # Initialize vector storage
            vector_config = VectorStorageConfig()
            self.vector_service = VectorStorageService(vector_config)
            vector_init = await self.vector_service.initialize()
            
            if not vector_init:
                raise RAGError("Failed to initialize vector storage")
            
            # Initialize embedding service
            self.embedding_service = OpenAIEmbeddingService()
            
            self.logger.info("RAG Orchestrator initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize RAG Orchestrator",
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def process_query(self, query: RAGQuery) -> RAGResponse:
        """Process a complete RAG query pipeline."""
        self.logger.info(
            "Processing RAG query",
            query_id=query.request_id,
            user_id=query.user_id,
            chatbot_id=query.chatbot_id,
            privacy_mode=query.privacy_mode.value
        )
        
        # Check cache first
        cache_key = self._generate_cache_key(query)
        if settings.ENABLE_CACHING:
            cached_response = cache.get(cache_key)
            if cached_response:
                self.logger.info("Returning cached response", query_id=query.request_id)
                return cached_response
        
        try:
            # Step 1: Analyze query
            query_analysis = self.query_processor.analyze_query(query)
            
            # Step 2: Generate embedding
            embedding_result = await self.embedding_service.generate_embeddings_batch([query.text])
            query_vector = embedding_result.embeddings[0].embedding if embedding_result.embeddings else None
            
            if not query_vector:
                raise RAGError("Failed to generate query embedding")
            
            # Step 3: Search for relevant content
            search_results = await self._search_relevant_content(
                query_vector, query.knowledge_base_ids, query.top_k_results
            )
            
            # Step 4: Assemble context
            context = self.context_assembler.assemble_context(
                search_results, query_vector, query.privacy_mode
            )
            
            # Step 5: Generate response
            response = await self.llm_service.generate_response(
                query, context, query_analysis
            )
            
            # Step 6: Validate privacy
            privacy_valid = self.privacy_validator.validate_response(response, query)
            response.privacy_validated = privacy_valid
            
            if not privacy_valid and query.privacy_mode == PrivacyMode.STRICT:
                raise RAGError("Response failed privacy validation")
            
            # Cache the response
            if settings.ENABLE_CACHING:
                cache.set(cache_key, response, timeout=self.cache_ttl)
            
            self.logger.info(
                "RAG query processed successfully",
                query_id=query.request_id,
                response_length=len(response.text),
                citations_count=len(response.citations),
                generation_time=response.generation_time,
                cost=response.cost_estimate
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                "RAG query processing failed",
                query_id=query.request_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise RAGError(f"RAG processing failed: {e}")
    
    async def _search_relevant_content(
        self,
        query_vector: List[float],
        knowledge_base_ids: Optional[List[str]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Search for relevant content."""
        # Build filter for knowledge bases
        filter_metadata = {}
        if knowledge_base_ids:
            filter_metadata['knowledge_base_id'] = knowledge_base_ids
        
        # Allow non-citable content for internal context
        filter_metadata['include_non_citable'] = True
        
        # Search using vector service
        search_results = await self.vector_service.search_similar(
            query_vector=query_vector,
            top_k=top_k,
            filter_metadata=filter_metadata
        )
        
        # Convert to dict format
        results = []
        for result in search_results:
            results.append({
                'id': result.id,
                'content': result.content,
                'score': result.score,
                'metadata': result.metadata
            })
        
        return results
    
    def _generate_cache_key(self, query: RAGQuery) -> str:
        """Generate cache key for query."""
        cache_data = {
            'query': query.text,
            'user_id': query.user_id,
            'chatbot_id': query.chatbot_id,
            'knowledge_bases': sorted(query.knowledge_base_ids or []),
            'privacy_mode': query.privacy_mode.value,
            'top_k': query.top_k_results,
            'temperature': query.temperature
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.md5(cache_string.encode()).hexdigest()[:16]
        
        return f"rag_query:{cache_hash}"


# Global orchestrator instance
rag_orchestrator = RAGOrchestrator()


# Convenience function for quick RAG queries
async def query_rag(
    text: str,
    user_id: str,
    chatbot_id: str,
    privacy_mode: PrivacyMode = PrivacyMode.STRICT,
    **kwargs
) -> RAGResponse:
    """Convenience function for RAG queries."""
    query = RAGQuery(
        text=text,
        user_id=user_id,
        chatbot_id=chatbot_id,
        privacy_mode=privacy_mode,
        **kwargs
    )
    
    return await rag_orchestrator.process_query(query)