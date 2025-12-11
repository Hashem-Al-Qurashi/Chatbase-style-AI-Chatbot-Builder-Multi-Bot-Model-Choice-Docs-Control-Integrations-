#!/usr/bin/env python3
"""
GRUMPY TESTER: Final Integration Validation

WHAT THIS TESTS:
- Complete RAG pipeline end-to-end functionality  
- All components working together seamlessly
- Performance under realistic load
- Error handling across the full stack
- Production readiness assessment

REQUIREMENTS TO PASS:
1. All RAG implementation steps (4-6) working correctly
2. End-to-end query processing pipeline functional
3. Real-time streaming operational
4. Privacy controls enforced throughout
5. Performance meets enterprise requirements
6. System ready for production deployment
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

from apps.core.vector_storage import VectorStorageService, VectorStorageConfig
from apps.core.embedding_service import OpenAIEmbeddingService  
from apps.core.rag_orchestrator import RAGOrchestrator, RAGQuery, PrivacyMode, QueryIntent
from apps.core.streaming_service import (
    RAGStreamingConsumer, RateLimiter, StreamingAuthenticator, 
    streaming_health_checker
)


class GrumpyFinalTester:
    """Grumpy validation for complete RAG implementation."""
    
    def __init__(self):
        self.results = []
        self.failed_tests = []
        self.start_time = time.time()
    
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
    
    async def test_step4_vector_storage(self) -> bool:
        """Validate Step 4: Vector Storage is fully functional."""
        print("\n📊 Validating Step 4: Vector Storage...")
        
        try:
            config = VectorStorageConfig()
            service = VectorStorageService(config)
            
            # Test initialization
            initialized = await service.initialize()
            self.log_result("Vector storage initialization", initialized, "Should initialize successfully")
            
            if not initialized:
                return False
            
            # Test storage and retrieval
            test_embeddings = [
                ('integration_test_1', [0.1] * 1536, {'content': 'Integration test content 1', 'is_citable': True}),
                ('integration_test_2', [0.2] * 1536, {'content': 'Integration test content 2', 'is_citable': True}),
            ]
            
            storage_success = await service.store_embeddings(test_embeddings, namespace="integration_test")
            self.log_result("Vector storage operations", storage_success, "Should store embeddings successfully")
            
            # Test search
            search_results = await service.search_similar([0.15] * 1536, top_k=5, namespace="integration_test")
            search_success = isinstance(search_results, list) and len(search_results) > 0
            self.log_result("Vector search operations", search_success, f"Should return search results: {len(search_results)} found")
            
            # Test stats
            stats = await service.get_storage_stats()
            stats_success = isinstance(stats, dict) and 'backend' in stats
            self.log_result("Vector storage stats", stats_success, "Should return storage statistics")
            
            return initialized and storage_success and search_success and stats_success
            
        except Exception as e:
            self.log_result("Step 4 Vector Storage", False, f"Error: {e}")
            return False
    
    async def test_step5_rag_orchestrator(self) -> bool:
        """Validate Step 5: RAG Orchestration Engine is fully functional."""
        print("\n🤖 Validating Step 5: RAG Orchestration Engine...")
        
        try:
            orchestrator = RAGOrchestrator()
            
            # Test initialization
            initialized = await orchestrator.initialize()
            self.log_result("RAG orchestrator initialization", initialized, "Should initialize all components")
            
            if not initialized:
                return False
            
            # Test different query types and privacy modes
            test_queries = [
                ("What are the main features?", PrivacyMode.STRICT),
                ("Compare the different approaches", PrivacyMode.CONTEXTUAL),
                ("Summarize the key points", PrivacyMode.STRICT),
            ]
            
            all_queries_success = True
            
            for query_text, privacy_mode in test_queries:
                rag_query = RAGQuery(
                    text=query_text,
                    user_id='integration_test_user',
                    chatbot_id='integration_test_bot',
                    privacy_mode=privacy_mode,
                    top_k_results=5
                )
                
                start_time = time.time()
                response = await orchestrator.process_query(rag_query)
                processing_time = time.time() - start_time
                
                # Validate response
                response_valid = (
                    isinstance(response.text, str) and len(response.text) > 0 and
                    isinstance(response.citations, list) and
                    hasattr(response, 'cost_estimate') and
                    hasattr(response, 'privacy_validated') and
                    processing_time < 5.0  # Should complete within 5 seconds
                )
                
                self.log_result(f"RAG query: {privacy_mode.value}", response_valid, 
                              f"Response: {len(response.text)} chars, {len(response.citations)} citations, {processing_time:.3f}s")
                
                if not response_valid:
                    all_queries_success = False
            
            return all_queries_success
            
        except Exception as e:
            self.log_result("Step 5 RAG Orchestrator", False, f"Error: {e}")
            return False
    
    async def test_step6_streaming_service(self) -> bool:
        """Validate Step 6: Real-time Streaming is fully functional."""
        print("\n🔌 Validating Step 6: Real-time Streaming...")
        
        try:
            # Test health check
            health_status = await streaming_health_checker.check_health()
            health_success = health_status.get('status') in ['healthy', 'degraded']  # Degraded is ok for Redis issues
            self.log_result("Streaming service health", health_success, f"Status: {health_status.get('status')}")
            
            # Test authentication
            authenticator = StreamingAuthenticator()
            valid_user = await authenticator.authenticate_token("user_integration_test")
            auth_success = valid_user is not None and valid_user.get('is_authenticated')
            self.log_result("Streaming authentication", auth_success, "Should authenticate valid tokens")
            
            # Test rate limiting
            rate_limiter = RateLimiter(max_requests=10, window_minutes=1)
            rate_limit_ok = rate_limiter.is_allowed("integration_test_user")
            self.log_result("Streaming rate limiting", rate_limit_ok, "Should allow requests within limits")
            
            # Test consumer initialization
            consumer = RAGStreamingConsumer()
            consumer_ok = (
                hasattr(consumer, 'rag_orchestrator') and
                hasattr(consumer, 'query_processor') and
                hasattr(consumer, 'rate_limiter') and
                hasattr(consumer, 'authenticator')
            )
            self.log_result("Streaming consumer setup", consumer_ok, "Should have all required components")
            
            return health_success and auth_success and rate_limit_ok and consumer_ok
            
        except Exception as e:
            self.log_result("Step 6 Streaming Service", False, f"Error: {e}")
            return False
    
    async def test_end_to_end_pipeline(self) -> bool:
        """Test complete end-to-end RAG pipeline."""
        print("\n🔄 Testing End-to-End RAG Pipeline...")
        
        try:
            # Initialize all components
            orchestrator = RAGOrchestrator()
            initialized = await orchestrator.initialize()
            
            if not initialized:
                self.log_result("E2E Pipeline initialization", False, "Failed to initialize orchestrator")
                return False
            
            # Test realistic query scenario
            realistic_query = RAGQuery(
                text="What is the purpose and main functionality of this chatbot system?",
                user_id='e2e_test_user',
                chatbot_id='e2e_test_bot',
                privacy_mode=PrivacyMode.STRICT,
                top_k_results=10,
                temperature=0.7
            )
            
            # Measure full pipeline performance
            start_time = time.time()
            
            # Step 1: Query analysis
            analysis = orchestrator.query_processor.analyze_query(realistic_query)
            analysis_time = time.time() - start_time
            
            # Step 2: Full pipeline processing
            response = await orchestrator.process_query(realistic_query)
            total_time = time.time() - start_time
            
            # Validate complete response
            pipeline_success = (
                isinstance(analysis, dict) and 'intent' in analysis and
                isinstance(response.text, str) and len(response.text) > 50 and
                isinstance(response.citations, list) and
                response.privacy_validated and
                total_time < 10.0  # Should complete within 10 seconds
            )
            
            self.log_result("E2E pipeline execution", pipeline_success, 
                          f"Total time: {total_time:.3f}s, Response: {len(response.text)} chars")
            
            # Test privacy compliance
            privacy_compliant = (
                response.privacy_validated and
                all(source.get('is_citable', True) for source in response.context_used.citable_sources)
            )
            self.log_result("E2E privacy compliance", privacy_compliant, "Privacy controls enforced throughout")
            
            # Test cost tracking
            cost_tracked = (
                hasattr(response, 'cost_estimate') and
                isinstance(response.cost_estimate, (int, float)) and
                response.cost_estimate > 0
            )
            self.log_result("E2E cost tracking", cost_tracked, f"Cost: ${response.cost_estimate:.6f}")
            
            return pipeline_success and privacy_compliant and cost_tracked
            
        except Exception as e:
            self.log_result("End-to-End Pipeline", False, f"Error: {e}")
            return False
    
    async def test_performance_under_load(self) -> bool:
        """Test performance under simulated load."""
        print("\n⚡ Testing Performance Under Load...")
        
        try:
            orchestrator = RAGOrchestrator()
            await orchestrator.initialize()
            
            # Test concurrent queries
            queries = [
                RAGQuery(
                    text=f"Test query number {i} for load testing",
                    user_id=f'load_test_user_{i}',
                    chatbot_id='load_test_bot',
                    privacy_mode=PrivacyMode.STRICT,
                    top_k_results=5
                )
                for i in range(5)  # 5 concurrent queries for load test
            ]
            
            # Execute queries concurrently
            start_time = time.time()
            
            async def process_query(query):
                return await orchestrator.process_query(query)
            
            # Run queries concurrently
            tasks = [process_query(query) for query in queries]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
            
            # Validate results
            successful_responses = [r for r in responses if not isinstance(r, Exception)]
            load_test_success = (
                len(successful_responses) == len(queries) and
                total_time < 15.0 and  # Should complete within 15 seconds
                all(hasattr(r, 'text') and len(r.text) > 0 for r in successful_responses)
            )
            
            self.log_result("Load test execution", load_test_success,
                          f"{len(successful_responses)}/{len(queries)} successful, {total_time:.3f}s total")
            
            # Test average response time
            avg_time = total_time / len(queries) if queries else 0
            avg_time_ok = avg_time < 5.0  # Average should be under 5 seconds
            self.log_result("Load test average response time", avg_time_ok, 
                          f"Average: {avg_time:.3f}s per query")
            
            return load_test_success and avg_time_ok
            
        except Exception as e:
            self.log_result("Performance Under Load", False, f"Error: {e}")
            return False
    
    async def test_error_recovery(self) -> bool:
        """Test error handling and recovery."""
        print("\n🚫 Testing Error Handling and Recovery...")
        
        try:
            orchestrator = RAGOrchestrator()
            await orchestrator.initialize()
            
            error_tests = []
            
            # Test empty query handling
            try:
                empty_query = RAGQuery(
                    text="",
                    user_id='error_test_user',
                    chatbot_id='error_test_bot'
                )
                # Should handle gracefully
                analysis = orchestrator.query_processor.analyze_query(empty_query)
                error_tests.append(("Empty query handling", isinstance(analysis, dict), "Should handle empty queries"))
            except Exception as e:
                error_tests.append(("Empty query handling", False, f"Failed: {e}"))
            
            # Test malformed inputs
            try:
                malformed_query = RAGQuery(
                    text="x" * 2000,  # Very long query
                    user_id='error_test_user',
                    chatbot_id='error_test_bot',
                    top_k_results=1000  # Excessive top_k
                )
                response = await orchestrator.process_query(malformed_query)
                # Should handle gracefully and return reasonable response
                handled_ok = isinstance(response.text, str) and len(response.text) > 0
                error_tests.append(("Malformed input handling", handled_ok, "Should handle excessive inputs"))
            except Exception as e:
                # Should handle gracefully or raise appropriate exception
                handled_ok = "RAGError" in str(type(e)) or "VectorStorageError" in str(type(e))
                error_tests.append(("Malformed input handling", handled_ok, f"Proper exception: {type(e).__name__}"))
            
            # Test rate limiting
            rate_limiter = RateLimiter(max_requests=1, window_minutes=1)
            user_id = "rate_limit_test"
            
            first_allowed = rate_limiter.is_allowed(user_id)
            second_denied = not rate_limiter.is_allowed(user_id)
            rate_limit_works = first_allowed and second_denied
            error_tests.append(("Rate limiting", rate_limit_works, "Should enforce rate limits"))
            
            all_passed = all(result[1] for result in error_tests)
            for test_name, passed, details in error_tests:
                self.log_result(test_name, passed, details)
            
            return all_passed
            
        except Exception as e:
            self.log_result("Error Handling and Recovery", False, f"Error: {e}")
            return False
    
    async def test_production_readiness(self) -> bool:
        """Assess production readiness."""
        print("\n🏭 Assessing Production Readiness...")
        
        try:
            readiness_checks = []
            
            # Check all health endpoints
            health_status = await streaming_health_checker.check_health()
            health_ok = health_status.get('status') in ['healthy', 'degraded']
            readiness_checks.append(("Health monitoring", health_ok, "Health checks functional"))
            
            # Check performance requirements
            orchestrator = RAGOrchestrator()
            await orchestrator.initialize()
            
            test_query = RAGQuery(
                text="Production readiness test query",
                user_id='prod_test_user',
                chatbot_id='prod_test_bot'
            )
            
            start_time = time.time()
            response = await orchestrator.process_query(test_query)
            response_time = time.time() - start_time
            
            performance_ok = response_time < 3.0  # Should be under 3 seconds
            readiness_checks.append(("Response time SLA", performance_ok, f"{response_time:.3f}s < 3.0s"))
            
            # Check cost tracking
            cost_tracking_ok = (
                hasattr(response, 'cost_estimate') and
                response.cost_estimate > 0 and
                response.cost_estimate < 0.01  # Should be reasonable cost
            )
            readiness_checks.append(("Cost tracking", cost_tracking_ok, f"${response.cost_estimate:.6f}"))
            
            # Check privacy validation
            privacy_ok = response.privacy_validated
            readiness_checks.append(("Privacy validation", privacy_ok, "Privacy controls active"))
            
            # Check error handling
            try:
                rate_limiter = RateLimiter()
                error_handling_ok = hasattr(rate_limiter, 'is_allowed')
                readiness_checks.append(("Error handling", error_handling_ok, "Error handling components present"))
            except Exception:
                readiness_checks.append(("Error handling", False, "Error handling issues"))
            
            all_ready = all(check[1] for check in readiness_checks)
            for check_name, passed, details in readiness_checks:
                self.log_result(check_name, passed, details)
            
            return all_ready
            
        except Exception as e:
            self.log_result("Production Readiness", False, f"Error: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run complete final integration validation."""
        print("🎯 GRUMPY TESTER: Final Integration Validation")
        print("🔍 Testing complete RAG implementation (Steps 4-6)")
        print("=" * 70)
        
        test_functions = [
            ("Step 4: Vector Storage", self.test_step4_vector_storage),
            ("Step 5: RAG Orchestrator", self.test_step5_rag_orchestrator),
            ("Step 6: Streaming Service", self.test_step6_streaming_service),
            ("End-to-End Pipeline", self.test_end_to_end_pipeline),
            ("Performance Under Load", self.test_performance_under_load),
            ("Error Recovery", self.test_error_recovery),
            ("Production Readiness", self.test_production_readiness),
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
        total_time = time.time() - self.start_time
        
        print("\n" + "=" * 70)
        print("📊 FINAL INTEGRATION VALIDATION RESULTS:")
        print("=" * 70)
        
        passed_count = sum(1 for r in self.results if r['passed'])
        total_count = len(self.results)
        
        for result in self.results:
            status = "✅" if result['passed'] else "❌"
            print(f"{status} {result['test']}")
        
        print("=" * 70)
        print(f"TOTAL: {passed_count}/{total_count} tests passed")
        print(f"VALIDATION TIME: {total_time:.1f} seconds")
        
        if overall_success:
            print("\n🎉 COMPLETE RAG IMPLEMENTATION VALIDATED!")
            print("✅ Step 4: Vector Storage - PRODUCTION READY")
            print("✅ Step 5: RAG Orchestration Engine - PRODUCTION READY") 
            print("✅ Step 6: Real-time Streaming - PRODUCTION READY")
            print("✅ End-to-end pipeline - FUNCTIONAL")
            print("✅ Performance requirements - MET")
            print("✅ Error handling - COMPREHENSIVE")
            print("✅ Production readiness - VALIDATED")
            print("\n🚀 SYSTEM READY FOR PRODUCTION DEPLOYMENT!")
        else:
            print("\n⚠️ RAG IMPLEMENTATION NOT READY FOR PRODUCTION!")
            print(f"❌ Failed tests: {', '.join(self.failed_tests)}")
            print("🔧 Issues must be resolved before production deployment")
        
        return overall_success


async def main():
    """Main test execution."""
    tester = GrumpyFinalTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎯 RAG IMPLEMENTATION COMPLETE:")
        print("All components validated and ready for production!")
        print("\nDeployment checklist:")
        print("□ Configure production environment variables")  
        print("□ Set up Redis for WebSocket scaling")
        print("□ Configure proper API rate limits")
        print("□ Set up monitoring and alerting")
        print("□ Deploy with proper security configurations")
    else:
        print("\n❌ RAG IMPLEMENTATION INCOMPLETE")
        print("Fix all failing tests before production deployment")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)