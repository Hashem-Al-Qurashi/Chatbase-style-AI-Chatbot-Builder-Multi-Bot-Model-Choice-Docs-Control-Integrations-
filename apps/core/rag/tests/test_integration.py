"""
Integration tests for RAG Pipeline.

Tests the complete RAG pipeline with privacy enforcement
to ensure all components work together correctly.

CRITICAL: These tests validate privacy leak prevention.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from ..vector_search_service import VectorSearchService, SearchResult
from ..context_builder import ContextBuilder, ContextData, RankingStrategy
from ..llm_service import LLMService, GenerationResult, ChatbotConfig
from ..privacy_filter import PrivacyFilter, FilterResult, ViolationType
from ..pipeline import RAGPipeline, RAGResponse


class TestRAGIntegration:
    """Integration tests for RAG pipeline."""
    
    @pytest.fixture
    def mock_search_results(self):
        """Mock search results with citable and private sources."""
        return [
            SearchResult(
                content="This is citable content from a public document.",
                score=0.95,
                chunk_id="citable_1",
                document_id="doc_1",
                knowledge_base_id="kb_1",
                is_citable=True,
                citation_text="Public Document, Page 1",
                metadata={"privacy_level": "citable"}
            ),
            SearchResult(
                content="This is private confidential content that should not be cited.",
                score=0.85,
                chunk_id="private_1", 
                document_id="doc_2",
                knowledge_base_id="kb_1",
                is_citable=False,
                citation_text=None,
                metadata={"privacy_level": "private"}
            ),
            SearchResult(
                content="Another citable source with important information.",
                score=0.80,
                chunk_id="citable_2",
                document_id="doc_3",
                knowledge_base_id="kb_1",
                is_citable=True,
                citation_text="Reference Manual, Section 5",
                metadata={"privacy_level": "citable"}
            )
        ]
    
    @pytest.fixture
    def mock_chatbot_config(self):
        """Mock chatbot configuration."""
        return ChatbotConfig(
            name="Test Chatbot",
            description="Test chatbot for integration testing",
            company_name="Test Company",
            temperature=0.7,
            max_response_tokens=200,
            strict_citation_mode=True
        )
    
    @pytest.mark.asyncio
    async def test_complete_rag_pipeline_privacy_compliant(
        self, 
        mock_search_results, 
        mock_chatbot_config
    ):
        """Test complete RAG pipeline with privacy-compliant response."""
        
        # Mock external dependencies
        with patch('apps.core.rag.vector_search_service.get_vector_storage'), \
             patch('apps.core.rag.vector_search_service.EmbeddingService'), \
             patch('apps.core.rag.llm_service.AsyncOpenAI') as mock_openai:
            
            # Mock OpenAI response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Based on the available sources, here is the information you requested. According to the Public Document, this explains the topic clearly."
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage = Mock()
            mock_response.usage.prompt_tokens = 150
            mock_response.usage.completion_tokens = 50
            mock_response.usage.total_tokens = 200
            
            mock_openai.return_value.chat.completions.create = AsyncMock(return_value=mock_response)
            
            # Initialize pipeline
            pipeline = RAGPipeline("test_chatbot_id")
            
            # Mock vector search to return our test results
            with patch.object(pipeline.vector_search, 'search', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = mock_search_results
                
                # Mock embedding generation
                with patch.object(pipeline.embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_embedding:
                    mock_embedding.return_value = [0.1] * 1536  # Mock embedding vector
                    
                    # Process query
                    response = await pipeline.process_query(
                        user_query="What information do you have about the topic?",
                        user_id="test_user",
                        chatbot_config=mock_chatbot_config
                    )
                    
                    # Validate response
                    assert isinstance(response, RAGResponse)
                    assert response.privacy_compliant == True
                    assert response.privacy_violations == 0
                    assert len(response.citations) > 0
                    assert response.citable_sources > 0
                    assert response.total_time > 0
                    assert response.estimated_cost > 0
    
    @pytest.mark.asyncio
    async def test_privacy_filter_catches_violations(self, mock_search_results):
        """Test that privacy filter catches privacy violations."""
        
        # Response that violates privacy by mentioning private content
        violating_response = "Based on the private confidential content that should not be cited, here is the answer."
        
        # Create context with private sources
        context_builder = ContextBuilder()
        context = context_builder.build_context(
            search_results=mock_search_results,
            query="test query",
            include_private=True
        )
        
        # Test privacy filter
        privacy_filter = PrivacyFilter()
        result = privacy_filter.validate_response(
            response=violating_response,
            context=context,
            user_id="test_user",
            strict_mode=True
        )
        
        # Should detect violation
        assert result.passed == False
        assert len(result.violations) > 0
        assert result.sanitized_response != violating_response
        assert any(v.violation_type == ViolationType.PRIVATE_CONTENT_LEAK for v in result.violations)
    
    @pytest.mark.asyncio 
    async def test_context_builder_privacy_separation(self, mock_search_results):
        """Test context builder properly separates citable and private sources."""
        
        context_builder = ContextBuilder()
        context = context_builder.build_context(
            search_results=mock_search_results,
            query="test query",
            include_private=True,
            ranking_strategy=RankingStrategy.SIMILARITY
        )
        
        # Validate privacy separation
        assert context.citable_count == 2  # Two citable sources
        assert context.private_count == 1   # One private source
        assert context.total_sources == 3
        
        # Check that citable sources are marked correctly
        for source in context.citable_sources:
            assert source.is_citable == True
            assert source.citation_text is not None
        
        # Check that private sources are marked correctly
        for source in context.private_sources:
            assert source.is_citable == False
        
        # Check context formatting includes privacy markers
        assert "CITABLE SOURCES" in context.full_context
        assert "PRIVATE SOURCES" in context.full_context
        assert "[CITABLE-" in context.full_context
        assert "[PRIVATE]" in context.full_context
    
    @pytest.mark.asyncio
    async def test_vector_search_privacy_filtering(self):
        """Test vector search service privacy filtering."""
        
        with patch('apps.core.rag.vector_search_service.get_vector_storage'), \
             patch('apps.core.rag.vector_search_service.EmbeddingService'):
            
            search_service = VectorSearchService("test_chatbot")
            
            # Mock the underlying search service
            mock_results = [
                Mock(
                    content="Citable content",
                    score=0.9,
                    chunk_id="c1",
                    document_id="d1", 
                    knowledge_base_id="kb1",
                    can_cite=True,
                    citation_text="Source 1",
                    metadata={}
                ),
                Mock(
                    content="Private content", 
                    score=0.8,
                    chunk_id="p1",
                    document_id="d2",
                    knowledge_base_id="kb1", 
                    can_cite=False,
                    citation_text=None,
                    metadata={}
                )
            ]
            
            with patch.object(search_service.rag_search_service, 'search_for_rag', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = (mock_results, {})
                
                # Test with citable filtering
                results = await search_service.search(
                    query_embedding=[0.1] * 1536,
                    query_text="test query",
                    user_id="test_user",
                    filter_citable=True
                )
                
                # Should only return citable results
                assert len(results) == 1
                assert results[0].is_citable == True
                
                # Test without citable filtering  
                results = await search_service.search(
                    query_embedding=[0.1] * 1536,
                    query_text="test query", 
                    user_id="test_user",
                    filter_citable=False
                )
                
                # Should return both citable and private
                assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_llm_service_privacy_prompts(self, mock_search_results, mock_chatbot_config):
        """Test LLM service enforces privacy through prompts."""
        
        context_builder = ContextBuilder()
        context = context_builder.build_context(
            search_results=mock_search_results,
            query="test query",
            include_private=True
        )
        
        with patch('apps.core.rag.llm_service.AsyncOpenAI') as mock_openai:
            # Mock OpenAI response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Privacy-compliant response"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage = Mock()
            mock_response.usage.prompt_tokens = 100
            mock_response.usage.completion_tokens = 30
            
            mock_openai.return_value.chat.completions.create = AsyncMock(return_value=mock_response)
            
            llm_service = LLMService()
            result = await llm_service.generate_response(
                context=context,
                user_query="test query",
                chatbot_config=mock_chatbot_config
            )
            
            # Check that call was made with privacy rules
            call_args = mock_openai.return_value.chat.completions.create.call_args[1]
            system_message = call_args['messages'][0]['content']
            
            assert "CRITICAL PRIVACY RULES" in system_message
            assert "NEVER VIOLATE THESE" in system_message
            assert "Only cite sources marked as [CITABLE" in system_message
            assert "NEVER mention or reference [PRIVATE] sources" in system_message
    
    def test_privacy_filter_validation_comprehensive(self):
        """Test comprehensive privacy filter validation."""
        
        privacy_filter = PrivacyFilter()
        
        # Test cases for different violation types
        test_cases = [
            {
                "response": "According to [PRIVATE] sources, this information...",
                "should_fail": True,
                "violation_type": ViolationType.PRIVATE_SOURCE_REFERENCE
            },
            {
                "response": "Based on citable sources, here is the information.",
                "should_fail": False,
                "violation_type": None
            },
            {
                "response": "The private confidential content shows that...",
                "should_fail": True,
                "violation_type": ViolationType.PRIVATE_SOURCE_REFERENCE
            }
        ]
        
        # Mock context with private sources
        mock_context = Mock()
        mock_context.private_sources = [
            Mock(
                content="private confidential content",
                source_id="private_1",
                is_citable=False
            )
        ]
        mock_context.citable_sources = []
        
        for test_case in test_cases:
            result = privacy_filter.validate_response(
                response=test_case["response"],
                context=mock_context,
                strict_mode=True
            )
            
            if test_case["should_fail"]:
                assert result.passed == False, f"Should have failed for: {test_case['response']}"
                assert len(result.violations) > 0
            else:
                assert result.passed == True, f"Should have passed for: {test_case['response']}"
    
    @pytest.mark.asyncio
    async def test_pipeline_fallback_on_errors(self, mock_chatbot_config):
        """Test pipeline provides fallback responses on errors."""
        
        with patch('apps.core.rag.vector_search_service.get_vector_storage'), \
             patch('apps.core.rag.vector_search_service.EmbeddingService'):
            
            pipeline = RAGPipeline("test_chatbot")
            
            # Mock embedding service to fail
            with patch.object(pipeline.embedding_service, 'generate_embedding', side_effect=Exception("API Error")):
                
                response = await pipeline.process_query(
                    user_query="test query",
                    user_id="test_user",
                    chatbot_config=mock_chatbot_config
                )
                
                # Should return fallback response
                assert isinstance(response, RAGResponse)
                assert "having trouble" in response.content.lower() or "try again" in response.content.lower()
                assert response.privacy_compliant == True  # Fallback is always safe
                assert response.estimated_cost == 0.0
    
    def test_cost_tracking_accuracy(self):
        """Test cost tracking calculates correctly."""
        from ..llm_service import CostTracker
        
        # Test GPT-3.5-turbo pricing
        cost = CostTracker.calculate_cost(
            model="gpt-3.5-turbo",
            input_tokens=1000,
            output_tokens=500
        )
        
        expected_cost = (1000 * 0.0015/1000) + (500 * 0.002/1000)
        assert abs(cost - expected_cost) < 0.0001
        
        # Test GPT-4 pricing
        cost = CostTracker.calculate_cost(
            model="gpt-4",
            input_tokens=1000,
            output_tokens=500
        )
        
        expected_cost = (1000 * 0.03/1000) + (500 * 0.06/1000)
        assert abs(cost - expected_cost) < 0.0001


class TestPrivacyLeakPrevention:
    """Specific tests for privacy leak prevention."""
    
    def test_unique_keywords_not_leaked(self):
        """Test that unique keywords from private sources don't leak."""
        
        # Create private source with unique identifier
        private_source = Mock()
        private_source.content = "The secret project ALPHA-BRAVO-123 is confidential and contains sensitive data about our internal operations."
        private_source.source_id = "private_test"
        private_source.is_citable = False
        
        mock_context = Mock()
        mock_context.private_sources = [private_source]
        mock_context.citable_sources = []
        
        # Response that leaks the unique identifier
        leaking_response = "According to our records, project ALPHA-BRAVO-123 shows interesting results."
        
        privacy_filter = PrivacyFilter()
        result = privacy_filter.validate_response(
            response=leaking_response,
            context=mock_context,
            strict_mode=True
        )
        
        # Should detect the leak
        assert result.passed == False
        assert len(result.violations) > 0
        assert "ALPHA-BRAVO-123" not in result.sanitized_response
    
    def test_pii_detection_and_removal(self):
        """Test detection and removal of PII from responses."""
        
        # Create private source with PII
        private_source = Mock()
        private_source.content = "Contact John Smith at john.smith@company.com or call 555-123-4567"
        private_source.source_id = "private_pii"
        private_source.is_citable = False
        
        mock_context = Mock()
        mock_context.private_sources = [private_source]
        mock_context.citable_sources = []
        
        # Response that leaks PII
        pii_response = "You can reach out to john.smith@company.com for more information."
        
        privacy_filter = PrivacyFilter()
        result = privacy_filter.validate_response(
            response=pii_response,
            context=mock_context,
            strict_mode=True
        )
        
        # Should detect PII leak
        assert result.passed == False
        assert "john.smith@company.com" not in result.sanitized_response
    
    def test_zero_tolerance_policy(self):
        """Test zero tolerance policy for any privacy violations."""
        
        privacy_filter = PrivacyFilter()
        
        # Even minor references should fail in strict mode
        minor_violation_response = "As mentioned in private sources..."
        
        mock_context = Mock()
        mock_context.private_sources = [Mock(content="private data", source_id="p1", is_citable=False)]
        mock_context.citable_sources = []
        
        result = privacy_filter.validate_response(
            response=minor_violation_response,
            context=mock_context,
            strict_mode=True
        )
        
        # Zero tolerance - any reference to private sources should fail
        assert result.passed == False


# Performance benchmarks
class TestPerformanceBenchmarks:
    """Performance tests to ensure pipeline meets latency requirements."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_latency_under_threshold(self, mock_search_results, mock_chatbot_config):
        """Test that end-to-end latency is under 2.5 seconds."""
        
        with patch('apps.core.rag.vector_search_service.get_vector_storage'), \
             patch('apps.core.rag.vector_search_service.EmbeddingService'), \
             patch('apps.core.rag.llm_service.AsyncOpenAI') as mock_openai:
            
            # Mock fast responses
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Fast response"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage = Mock()
            mock_response.usage.prompt_tokens = 50
            mock_response.usage.completion_tokens = 20
            
            mock_openai.return_value.chat.completions.create = AsyncMock(return_value=mock_response)
            
            pipeline = RAGPipeline("test_chatbot")
            
            with patch.object(pipeline.vector_search, 'search', new_callable=AsyncMock) as mock_search, \
                 patch.object(pipeline.embedding_service, 'generate_embedding', new_callable=AsyncMock) as mock_embedding:
                
                mock_search.return_value = mock_search_results[:2]  # Limit results for speed
                mock_embedding.return_value = [0.1] * 1536
                
                response = await pipeline.process_query(
                    user_query="Quick test query",
                    user_id="test_user", 
                    chatbot_config=mock_chatbot_config
                )
                
                # Performance requirement: < 2.5 seconds
                assert response.total_time < 2.5, f"Pipeline took {response.total_time}s, should be < 2.5s"
                
                # Individual stage requirements
                assert response.stage_times.get('vector_search', 0) < 0.2  # < 200ms
                assert response.stage_times.get('context_building', 0) < 0.1  # < 100ms
                assert response.stage_times.get('privacy_filtering', 0) < 0.05  # < 50ms