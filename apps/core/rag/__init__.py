"""
RAG (Retrieval-Augmented Generation) module for chatbot SaaS.

This module implements a privacy-first RAG pipeline with multi-layer protection:
1. Database-level privacy filtering
2. LLM prompt-level privacy enforcement  
3. Response post-processing and sanitization

Components:
- VectorSearchService: Privacy-aware vector search
- ContextBuilder: Context assembly and ranking
- LLMService: OpenAI GPT-3.5-turbo integration with privacy prompts
- PrivacyFilter: Multi-layer privacy enforcement
- RAGPipeline: End-to-end orchestration

Privacy Policy:
- ZERO tolerance for privacy leaks
- All queries audited and logged
- Citable vs private content strictly separated
- User access controls enforced at all layers
"""

from .vector_search_service import VectorSearchService
from .context_builder import ContextBuilder, ContextData
from .llm_service import LLMService, GenerationResult
from .privacy_filter import PrivacyFilter, FilterResult  
from .pipeline import RAGPipeline, RAGResponse

__all__ = [
    'VectorSearchService',
    'ContextBuilder', 
    'ContextData',
    'LLMService',
    'GenerationResult', 
    'PrivacyFilter',
    'FilterResult',
    'RAGPipeline',
    'RAGResponse'
]