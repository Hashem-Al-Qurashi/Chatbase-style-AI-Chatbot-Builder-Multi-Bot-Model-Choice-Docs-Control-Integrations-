"""
Simple RAG Component Validation Tests.

Tests core RAG components with minimal dependencies to validate
functionality without complex setup requirements.

CRITICAL: Tests privacy filtering and basic functionality.
"""

import pytest
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.test_settings')
django.setup()

from unittest.mock import Mock, patch, AsyncMock
import asyncio


def test_privacy_filter_basic_validation():
    """Test basic privacy filter validation."""
    
    print("\n🧪 Testing Privacy Filter Basic Validation")
    
    # Mock context with private and citable sources
    mock_context = Mock()
    mock_context.private_sources = [
        Mock(
            content="This is private confidential content with SECRET-CODE-123",
            source_id="private_1",
            is_citable=False
        )
    ]
    mock_context.citable_sources = [
        Mock(
            content="This is citable public content",
            source_id="citable_1", 
            is_citable=True
        )
    ]
    
    # Import and test privacy filter
    try:
        from apps.core.rag.privacy_filter import PrivacyFilter
        
        privacy_filter = PrivacyFilter()
        
        # Test 1: Response that violates privacy
        violating_response = "According to SECRET-CODE-123, this information shows..."
        
        result = privacy_filter.validate_response(
            response=violating_response,
            context=mock_context,
            strict_mode=True
        )
        
        # Should detect violation
        assert result.passed == False, "Privacy filter should detect violation"
        assert len(result.violations) > 0, "Should have violations detected"
        assert "SECRET-CODE-123" not in result.sanitized_response, "Should sanitize secret code"
        
        print("✅ PASS: Privacy filter detects and sanitizes violations")
        
        # Test 2: Response that is privacy compliant
        clean_response = "Based on the available public information, here is the answer."
        
        result = privacy_filter.validate_response(
            response=clean_response,
            context=mock_context,
            strict_mode=True
        )
        
        # Should pass
        assert result.passed == True, "Clean response should pass privacy filter"
        assert len(result.violations) == 0, "Should have no violations"
        
        print("✅ PASS: Privacy filter allows clean responses")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Privacy filter test failed: {str(e)}")
        return False


def test_context_builder_privacy_separation():
    """Test context builder separates citable and private sources."""
    
    print("\n🧪 Testing Context Builder Privacy Separation")
    
    try:
        # Mock search results 
        mock_results = [
            Mock(
                content="Citable content",
                score=0.9,
                chunk_id="c1", 
                document_id="d1",
                knowledge_base_id="kb1",
                is_citable=True,
                citation_text="Source 1",
                metadata={}
            ),
            Mock(
                content="Private content",
                score=0.8,
                chunk_id="p1",
                document_id="d2", 
                knowledge_base_id="kb1",
                is_citable=False,
                citation_text=None,
                metadata={}
            )
        ]
        
        from apps.core.rag.context_builder import ContextBuilder
        
        context_builder = ContextBuilder(max_context_tokens=1000)
        
        # Build context
        context = context_builder.build_context(
            search_results=mock_results,
            query="test query",
            include_private=True
        )
        
        # Validate separation
        assert context.citable_count == 1, f"Expected 1 citable, got {context.citable_count}"
        assert context.private_count == 1, f"Expected 1 private, got {context.private_count}" 
        assert context.total_sources == 2, f"Expected 2 total, got {context.total_sources}"
        
        # Check context formatting
        assert "CITABLE SOURCES" in context.full_context, "Missing citable sources section"
        assert "PRIVATE SOURCES" in context.full_context, "Missing private sources section"
        assert "[CITABLE-" in context.full_context, "Missing citable markers"
        assert "[PRIVATE]" in context.full_context, "Missing private markers"
        
        print("✅ PASS: Context builder properly separates source types")
        
        # Test privacy validation
        validation = context_builder.validate_context_privacy(context)
        assert validation["valid"] == True, f"Context validation failed: {validation['issues']}"
        
        print("✅ PASS: Context privacy validation works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Context builder test failed: {str(e)}")
        return False


def test_llm_service_cost_tracking():
    """Test LLM service cost tracking accuracy."""
    
    print("\n🧪 Testing LLM Service Cost Tracking")
    
    try:
        from apps.core.rag.llm_service import CostTracker
        
        # Test GPT-3.5-turbo pricing
        cost = CostTracker.calculate_cost(
            model="gpt-3.5-turbo",
            input_tokens=1000,
            output_tokens=500
        )
        
        # Expected: (1000 * 0.0015/1000) + (500 * 0.002/1000) = 0.0015 + 0.001 = 0.0025
        expected_cost = 0.0025
        assert abs(cost - expected_cost) < 0.0001, f"Wrong cost calculation: {cost} != {expected_cost}"
        
        print("✅ PASS: GPT-3.5-turbo cost calculation accurate")
        
        # Test GPT-4 pricing
        cost = CostTracker.calculate_cost(
            model="gpt-4",
            input_tokens=1000,
            output_tokens=500  
        )
        
        # Expected: (1000 * 0.03/1000) + (500 * 0.06/1000) = 0.03 + 0.03 = 0.06
        expected_cost = 0.06
        assert abs(cost - expected_cost) < 0.0001, f"Wrong GPT-4 cost: {cost} != {expected_cost}"
        
        print("✅ PASS: GPT-4 cost calculation accurate")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Cost tracking test failed: {str(e)}")
        return False


def test_rag_pipeline_initialization():
    """Test RAG pipeline can be initialized correctly."""
    
    print("\n🧪 Testing RAG Pipeline Initialization")
    
    try:
        # Mock all external dependencies
        with patch('apps.core.rag.pipeline.get_vector_search_service') as mock_vector, \
             patch('apps.core.rag.pipeline.get_llm_service') as mock_llm, \
             patch('apps.core.rag.pipeline.get_privacy_filter') as mock_privacy, \
             patch('apps.core.rag.pipeline.OpenAIEmbeddingService') as mock_embedding:
            
            # Setup mocks
            mock_vector.return_value = Mock()
            mock_llm.return_value = Mock()
            mock_privacy.return_value = Mock()
            mock_embedding.return_value = Mock()
            
            from apps.core.rag.pipeline import RAGPipeline
            
            # Test pipeline initialization
            pipeline = RAGPipeline("test_chatbot")
            
            assert pipeline.chatbot_id == "test_chatbot", "Wrong chatbot ID"
            assert hasattr(pipeline, 'vector_search'), "Missing vector_search"
            assert hasattr(pipeline, 'context_builder'), "Missing context_builder"
            assert hasattr(pipeline, 'llm_service'), "Missing llm_service"
            assert hasattr(pipeline, 'privacy_filter'), "Missing privacy_filter"
            
            print("✅ PASS: RAG pipeline initializes all components correctly")
            
            return True
            
    except Exception as e:
        print(f"❌ FAIL: RAG pipeline initialization failed: {str(e)}")
        return False


def test_token_counter_accuracy():
    """Test token counting accuracy for context management."""
    
    print("\n🧪 Testing Token Counter Accuracy")
    
    try:
        from apps.core.rag.context_builder import TokenCounter
        
        # Test simple text
        text = "This is a test sentence with some words."
        token_count = TokenCounter.count_tokens(text)
        
        # Should be approximately 10 tokens (40 chars / 4 chars per token)
        expected_approx = len(text) // 4
        assert abs(token_count - expected_approx) <= 2, f"Token count {token_count} not close to expected {expected_approx}"
        
        print("✅ PASS: Token counting approximation reasonable")
        
        # Test truncation
        long_text = "word " * 100  # 500 characters
        truncated = TokenCounter.truncate_to_token_limit(long_text, max_tokens=50)  # ~200 chars
        
        assert len(truncated) < len(long_text), "Text should be truncated"
        assert TokenCounter.count_tokens(truncated) <= 50, "Truncated text exceeds token limit"
        
        print("✅ PASS: Token truncation works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Token counter test failed: {str(e)}")
        return False


def run_all_simple_tests():
    """Run all simple validation tests."""
    
    print("🎯 EXECUTING SIMPLE RAG VALIDATION TESTS")
    print("=" * 60)
    
    test_results = []
    
    # Execute each test
    test_results.append(("Privacy Filter", test_privacy_filter_basic_validation()))
    test_results.append(("Context Builder", test_context_builder_privacy_separation()))
    test_results.append(("Cost Tracking", test_llm_service_cost_tracking()))
    test_results.append(("Pipeline Init", test_rag_pipeline_initialization()))
    test_results.append(("Token Counter", test_token_counter_accuracy()))
    
    # Report results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<20} | {status}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"TOTAL: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED! RAG components validated successfully.")
        return True
    else:
        print(f"⚠️  {failed} tests failed. Issues need to be resolved.")
        return False


if __name__ == "__main__":
    success = run_all_simple_tests()
    exit(0 if success else 1)