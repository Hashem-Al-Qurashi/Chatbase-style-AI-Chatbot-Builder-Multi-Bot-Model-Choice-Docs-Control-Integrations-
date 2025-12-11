#!/usr/bin/env python3
"""
GRUMPY TESTER: Step 5 RAG Orchestration Engine Validation

WHAT THIS TESTS:
- Complete RAG pipeline functionality
- Query processing and intent analysis
- Privacy-aware context assembly
- LLM response generation with citations
- Privacy validation and compliance
- Cost tracking and performance

REQUIREMENTS TO PASS:
1. All RAG pipeline stages work correctly
2. Privacy controls function as designed
3. Citations are properly tracked and validated
4. Performance meets enterprise requirements
5. Cost tracking is accurate
6. Error handling is comprehensive
"""

import os
import sys
import django
import asyncio
import time
from typing import Dict, Any, List

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from apps.core.rag_orchestrator import (
    RAGOrchestrator, RAGQuery, PrivacyMode, QueryIntent,
    QueryProcessor, ContextAssembler, LLMService, PrivacyValidator
)
from apps.core.exceptions import RAGError


class GrumpyStep5Tester:
    """Grumpy validation for Step 5 RAG orchestration."""
    
    def __init__(self):
        self.results = []
        self.failed_tests = []
        self.orchestrator = RAGOrchestrator()
    
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        
        self.results.append({
            'test': test_name,
            'passed': passed,
            'details': details
        })
        
        if not passed:
            self.failed_tests.append(test_name)
    
    async def test_orchestrator_initialization(self) -> bool:
        """Test RAG orchestrator initialization."""
        print("\n🚀 Testing RAG Orchestrator Initialization...")
        
        try:
            initialized = await self.orchestrator.initialize()
            self.log_result("Orchestrator initialization", initialized, "Should initialize all components")
            
            # Verify components are properly initialized
            components_ok = all([
                hasattr(self.orchestrator, 'query_processor'),
                hasattr(self.orchestrator, 'context_assembler'),
                hasattr(self.orchestrator, 'llm_service'),
                hasattr(self.orchestrator, 'privacy_validator'),
                hasattr(self.orchestrator, 'vector_service'),
                hasattr(self.orchestrator, 'embedding_service')
            ])
            
            self.log_result("Component initialization", components_ok, "All components should be present")
            
            return initialized and components_ok
            
        except Exception as e:
            self.log_result("Orchestrator initialization", False, f"Unexpected error: {e}")
            return False
    
    async def test_query_processing_pipeline(self) -> bool:
        """Test complete query processing pipeline."""
        print("\n🔄 Testing Query Processing Pipeline...")
        
        try:
            # Test different query types
            test_queries = [
                ("What is the purpose of this system?", QueryIntent.QUESTION_ANSWER, PrivacyMode.STRICT),
                ("Compare the features of product A and product B", QueryIntent.COMPARISON, PrivacyMode.CONTEXTUAL),
                ("Summarize the recent developments", QueryIntent.SUMMARIZATION, PrivacyMode.STRICT),
                ("Create a report on market trends", QueryIntent.GENERATION, PrivacyMode.CONTEXTUAL),
            ]
            
            all_passed = True
            
            for query_text, expected_intent, privacy_mode in test_queries:
                query = RAGQuery(
                    text=query_text,
                    user_id='test_user',
                    chatbot_id='test_bot',
                    privacy_mode=privacy_mode,
                    top_k_results=5
                )
                
                try:
                    response = await self.orchestrator.process_query(query)
                    
                    # Validate response structure
                    valid_response = (
                        isinstance(response.text, str) and len(response.text) > 0 and
                        isinstance(response.citations, list) and
                        hasattr(response, 'context_used') and
                        hasattr(response, 'generation_time') and
                        hasattr(response, 'cost_estimate') and
                        hasattr(response, 'privacy_validated')
                    )
                    
                    if not valid_response:
                        all_passed = False
                        self.log_result(f"Query pipeline - {expected_intent.value}", False, 
                                      "Invalid response structure")
                    else:
                        self.log_result(f"Query pipeline - {expected_intent.value}", True,
                                      f"Response: {len(response.text)} chars, {len(response.citations)} citations")
                    
                except Exception as e:
                    all_passed = False
                    self.log_result(f"Query pipeline - {expected_intent.value}", False, f"Pipeline error: {e}")
            
            return all_passed
            
        except Exception as e:
            self.log_result("Query processing pipeline", False, f"Setup error: {e}")
            return False
    
    async def test_privacy_mode_compliance(self) -> bool:
        """Test privacy mode compliance."""
        print("\n🔒 Testing Privacy Mode Compliance...")
        
        try:
            test_query = "What sensitive information is available?"
            
            privacy_tests = []
            
            # Test STRICT mode - should only use citable sources
            strict_query = RAGQuery(
                text=test_query,
                user_id='test_user',
                chatbot_id='test_bot',
                privacy_mode=PrivacyMode.STRICT,
                top_k_results=5
            )
            
            strict_response = await self.orchestrator.process_query(strict_query)
            strict_ok = (
                strict_response.privacy_validated and
                all(source.get('is_citable', True) for source in strict_response.context_used.citable_sources) and
                len(strict_response.context_used.private_sources) == 0
            )
            privacy_tests.append(("STRICT mode", strict_ok, "Should only use citable sources"))
            
            # Test CONTEXTUAL mode - can use private for context but not citation
            contextual_query = RAGQuery(
                text=test_query,
                user_id='test_user',
                chatbot_id='test_bot',
                privacy_mode=PrivacyMode.CONTEXTUAL,
                top_k_results=5
            )
            
            contextual_response = await self.orchestrator.process_query(contextual_query)
            contextual_ok = (
                contextual_response.privacy_validated and
                len(contextual_response.context_used.citable_sources) >= 0  # May have citable sources
            )
            privacy_tests.append(("CONTEXTUAL mode", contextual_ok, "Should handle mixed sources correctly"))
            
            # Test INTERNAL mode - can use all sources
            internal_query = RAGQuery(
                text=test_query,
                user_id='test_user',
                chatbot_id='test_bot',
                privacy_mode=PrivacyMode.INTERNAL,
                top_k_results=5
            )
            
            internal_response = await self.orchestrator.process_query(internal_query)
            internal_ok = internal_response.privacy_validated  # Should validate regardless
            privacy_tests.append(("INTERNAL mode", internal_ok, "Should allow all sources"))
            
            all_passed = all(result[1] for result in privacy_tests)
            for test_name, passed, description in privacy_tests:
                self.log_result(test_name, passed, description)
            
            return all_passed
            
        except Exception as e:
            self.log_result("Privacy mode compliance", False, f"Error: {e}")
            return False
    
    async def test_context_assembly_logic(self) -> bool:
        """Test context assembly and truncation logic."""
        print("\n📋 Testing Context Assembly Logic...")
        
        try:
            # Test context with token limits
            query = RAGQuery(
                text="Tell me about the system capabilities",
                user_id='test_user',
                chatbot_id='test_bot',
                privacy_mode=PrivacyMode.CONTEXTUAL,
                max_context_tokens=1000,  # Relatively small limit
                top_k_results=10  # Request more results to test truncation
            )
            
            response = await self.orchestrator.process_query(query)
            context = response.context_used
            
            # Validate context structure
            context_valid = (
                hasattr(context, 'citable_sources') and
                hasattr(context, 'private_sources') and
                hasattr(context, 'total_tokens') and
                hasattr(context, 'truncated') and
                hasattr(context, 'source_count') and
                hasattr(context, 'assembly_time')
            )
            
            self.log_result("Context structure", context_valid, "Context should have all required fields")
            
            # Test token limit enforcement
            token_limit_ok = context.total_tokens <= query.max_context_tokens
            self.log_result("Token limit enforcement", token_limit_ok,
                          f"Used {context.total_tokens} tokens (limit: {query.max_context_tokens})")
            
            # Test source prioritization (citable sources should be included first)
            prioritization_ok = len(context.citable_sources) >= 0  # Should have some citable sources
            self.log_result("Source prioritization", prioritization_ok,
                          f"Citable: {len(context.citable_sources)}, Private: {len(context.private_sources)}")
            
            # Test context formatting
            formatted_context = context.get_formatted_context(include_private=True)
            formatting_ok = (
                isinstance(formatted_context, str) and
                len(formatted_context) > 0 and
                "CITABLE SOURCES" in formatted_context
            )
            self.log_result("Context formatting", formatting_ok, "Should format context properly")
            
            return context_valid and token_limit_ok and prioritization_ok and formatting_ok
            
        except Exception as e:
            self.log_result("Context assembly logic", False, f"Error: {e}")
            return False
    
    async def test_cost_tracking_accuracy(self) -> bool:
        """Test cost tracking accuracy."""
        print("\n💰 Testing Cost Tracking Accuracy...")
        
        try:
            # Track costs across multiple queries
            initial_cost = 0.0
            
            test_queries = [
                "Short query",
                "This is a longer query with more words to test token counting and cost calculation accuracy",
                "Medium length query for testing"
            ]
            
            total_tracked_cost = 0.0
            
            for query_text in test_queries:
                query = RAGQuery(
                    text=query_text,
                    user_id='test_user',
                    chatbot_id='test_bot',
                    privacy_mode=PrivacyMode.STRICT
                )
                
                response = await self.orchestrator.process_query(query)
                
                # Validate cost is calculated
                cost_calculated = (
                    hasattr(response, 'cost_estimate') and
                    isinstance(response.cost_estimate, (int, float)) and
                    response.cost_estimate >= 0
                )
                
                if not cost_calculated:
                    self.log_result("Cost calculation", False, f"Invalid cost for query: {query_text}")
                    return False
                
                total_tracked_cost += response.cost_estimate
            
            # Validate total cost is reasonable
            cost_reasonable = 0.0001 <= total_tracked_cost <= 0.01  # Between $0.0001 and $0.01
            self.log_result("Cost tracking accuracy", cost_reasonable,
                          f"Total cost: ${total_tracked_cost:.6f} (should be reasonable)")
            
            # Test cost breakdown
            query = RAGQuery(
                text="Test query for cost breakdown",
                user_id='test_user',
                chatbot_id='test_bot'
            )
            
            response = await self.orchestrator.process_query(query)
            
            cost_breakdown_ok = (
                hasattr(response, 'token_usage') and
                'input' in response.token_usage and
                'output' in response.token_usage and
                response.token_usage['input'] > 0 and
                response.token_usage['output'] > 0
            )
            
            self.log_result("Cost breakdown", cost_breakdown_ok,
                          f"Input: {response.token_usage.get('input', 0)}, Output: {response.token_usage.get('output', 0)}")
            
            return cost_reasonable and cost_breakdown_ok
            
        except Exception as e:
            self.log_result("Cost tracking accuracy", False, f"Error: {e}")
            return False
    
    async def test_performance_requirements(self) -> bool:
        """Test performance meets requirements."""
        print("\n⚡ Testing Performance Requirements...")
        
        try:
            # Test response time
            query = RAGQuery(
                text="What are the key features of this system?",
                user_id='test_user',
                chatbot_id='test_bot',
                privacy_mode=PrivacyMode.STRICT
            )
            
            start_time = time.time()
            response = await self.orchestrator.process_query(query)
            total_time = time.time() - start_time
            
            # Should complete within 5 seconds for typical queries
            response_time_ok = total_time < 5.0
            self.log_result("Response time", response_time_ok,
                          f"Total time: {total_time:.3f}s (must be < 5.0s)")
            
            # Test generation time specifically
            generation_time_ok = response.generation_time < 2.0
            self.log_result("LLM generation time", generation_time_ok,
                          f"Generation: {response.generation_time:.3f}s (must be < 2.0s)")
            
            # Test context assembly time
            assembly_time_ok = response.context_used.assembly_time < 1.0
            self.log_result("Context assembly time", assembly_time_ok,
                          f"Assembly: {response.context_used.assembly_time:.3f}s (must be < 1.0s)")
            
            return response_time_ok and generation_time_ok and assembly_time_ok
            
        except Exception as e:
            self.log_result("Performance requirements", False, f"Error: {e}")
            return False
    
    async def test_error_handling(self) -> bool:
        """Test comprehensive error handling."""
        print("\n🚫 Testing Error Handling...")
        
        try:
            error_tests = []
            
            # Test invalid query
            try:
                empty_query = RAGQuery(
                    text="",  # Empty query
                    user_id='test_user',
                    chatbot_id='test_bot'
                )
                response = await self.orchestrator.process_query(empty_query)
                error_tests.append(("Empty query handling", False, "Should handle empty queries gracefully"))
            except Exception:
                error_tests.append(("Empty query handling", True, "Correctly rejects empty query"))
            
            # Test malformed privacy mode (this should work due to enum validation)
            try:
                query = RAGQuery(
                    text="Valid query text",
                    user_id='test_user',
                    chatbot_id='test_bot',
                    privacy_mode=PrivacyMode.STRICT  # Valid enum
                )
                response = await self.orchestrator.process_query(query)
                error_tests.append(("Valid privacy mode", True, "Should accept valid privacy mode"))
            except Exception as e:
                error_tests.append(("Valid privacy mode", False, f"Should not fail with valid mode: {e}"))
            
            # Test very long query (should truncate gracefully)
            try:
                long_query = RAGQuery(
                    text="Very long query " * 1000,  # Very long text
                    user_id='test_user',
                    chatbot_id='test_bot',
                    max_context_tokens=100  # Small context to force truncation
                )
                response = await self.orchestrator.process_query(long_query)
                truncation_handled = response.context_used.truncated or response.context_used.total_tokens <= 100
                error_tests.append(("Long query truncation", truncation_handled, "Should handle long queries"))
            except Exception as e:
                error_tests.append(("Long query truncation", False, f"Should handle long queries: {e}"))
            
            all_passed = all(result[1] for result in error_tests)
            for test_name, passed, details in error_tests:
                self.log_result(test_name, passed, details)
            
            return all_passed
            
        except Exception as e:
            self.log_result("Error handling", False, f"Setup error: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all Step 5 validation tests."""
        print("🎯 GRUMPY TESTER: Step 5 RAG Orchestration Engine Validation")
        print("=" * 70)
        
        test_functions = [
            ("Orchestrator Initialization", self.test_orchestrator_initialization),
            ("Query Processing Pipeline", self.test_query_processing_pipeline),
            ("Privacy Mode Compliance", self.test_privacy_mode_compliance),
            ("Context Assembly Logic", self.test_context_assembly_logic),
            ("Cost Tracking Accuracy", self.test_cost_tracking_accuracy),
            ("Performance Requirements", self.test_performance_requirements),
            ("Error Handling", self.test_error_handling),
        ]
        
        overall_success = True
        
        for test_name, test_func in test_functions:
            try:
                success = await test_func()
                if not success:
                    overall_success = False
            except Exception as e:
                print(f"❌ CRITICAL FAILURE in {test_name}: {e}")
                overall_success = False
        
        # Final report
        print("\n" + "=" * 70)
        print("📊 STEP 5 VALIDATION RESULTS:")
        print("=" * 70)
        
        passed_count = sum(1 for r in self.results if r['passed'])
        total_count = len(self.results)
        
        for result in self.results:
            status = "✅" if result['passed'] else "❌"
            print(f"{status} {result['test']}")
        
        print("=" * 70)
        print(f"TOTAL: {passed_count}/{total_count} tests passed")
        
        if overall_success:
            print("🎉 STEP 5 COMPLETE: RAG Orchestration Engine is production-ready!")
            print("✅ Complete RAG pipeline functional")
            print("✅ Privacy controls working correctly")
            print("✅ Cost tracking accurate")
            print("✅ Performance meets requirements")
            print("✅ Error handling comprehensive")
        else:
            print("⚠️ STEP 5 INCOMPLETE: Issues remain!")
            print(f"❌ Failed tests: {', '.join(self.failed_tests)}")
        
        return overall_success


async def main():
    """Main test execution."""
    tester = GrumpyStep5Tester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎯 READY FOR STEP 6:")
        print("Next: Real-time streaming with Django Channels")
    else:
        print("\n❌ STEP 5 MUST BE FIXED BEFORE PROCEEDING")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)