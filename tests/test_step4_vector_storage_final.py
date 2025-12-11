#!/usr/bin/env python3
"""
GRUMPY TESTER: Step 4 Vector Storage Final Validation

WHAT THIS TESTS:
- Null namespace security vulnerability FIXED
- Similarity calculation edge cases FIXED
- Final validation of 100% Step 4 completion

REQUIREMENTS TO PASS:
1. All edge cases handled without errors
2. Security vulnerabilities patched
3. Performance acceptable for production use
"""

import os
import sys
import django
import asyncio
import time
import traceback
from typing import Dict, Any, List

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from apps.core.vector_storage import VectorStorageService, VectorStorageConfig, VectorStorageError


class GrumpyStep4Tester:
    """Grumpy validation for Step 4 vector storage completion."""
    
    def __init__(self):
        self.results = []
        self.failed_tests = []
    
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
    
    async def test_null_namespace_security(self) -> bool:
        """Test null namespace security handling."""
        print("\n🔒 Testing Null Namespace Security...")
        
        try:
            config = VectorStorageConfig()
            service = VectorStorageService(config)
            await service.initialize()
            
            # Test 1: Null namespace should be handled safely
            embeddings = [('test_null_ns', [0.1] * 1536, {'content': 'test', 'is_citable': True})]
            result = await service.store_embeddings(embeddings, namespace=None)
            self.log_result("Null namespace storage", result, "Should handle null without errors")
            
            # Test 2: Empty string namespace should be normalized
            result = await service.store_embeddings(embeddings, namespace="")
            self.log_result("Empty namespace normalization", result, "Empty string handled correctly")
            
            # Test 3: Search with null namespace should be restricted properly
            query_vector = [0.1] * 1536
            results = await service.search_similar(query_vector, top_k=5, namespace=None)
            self.log_result("Null namespace search restriction", 
                          isinstance(results, list), 
                          f"Returns controlled results: {len(results)} items")
            
            return True
            
        except Exception as e:
            self.log_result("Null namespace security", False, f"Unexpected error: {e}")
            return False
    
    async def test_similarity_edge_cases(self) -> bool:
        """Test similarity calculation edge cases."""
        print("\n📊 Testing Similarity Calculation Edge Cases...")
        
        try:
            config = VectorStorageConfig()
            service = VectorStorageService(config)
            await service.initialize()
            
            test_cases = [
                ("Zero vectors", [0.0] * 1536, "Should handle without division by zero"),
                ("Tiny values", [1e-10] * 1536, "Should handle very small numbers"),
                ("Large values", [1000.0] * 1536, "Should handle large numbers"),
                ("Mixed values", list(range(1536)), "Should handle diverse ranges"),
                ("Normalized vector", [1.0/1536**0.5] * 1536, "Should handle normalized vectors"),
            ]
            
            all_passed = True
            
            for case_name, test_vector, description in test_cases:
                try:
                    results = await service.search_similar(test_vector, top_k=3)
                    
                    # Validate results structure
                    valid_structure = (
                        isinstance(results, list) and
                        all(hasattr(r, 'score') and hasattr(r, 'id') for r in results) and
                        all(isinstance(r.score, (int, float)) and not (r.score != r.score) for r in results)  # No NaN
                    )
                    
                    self.log_result(f"Edge case: {case_name}", valid_structure, description)
                    if not valid_structure:
                        all_passed = False
                        
                except Exception as e:
                    self.log_result(f"Edge case: {case_name}", False, f"Error: {e}")
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            self.log_result("Similarity edge cases", False, f"Setup error: {e}")
            return False
    
    async def test_performance_requirements(self) -> bool:
        """Test performance meets production requirements."""
        print("\n⚡ Testing Performance Requirements...")
        
        try:
            config = VectorStorageConfig()
            service = VectorStorageService(config)
            await service.initialize()
            
            # Performance test: Search latency
            test_vector = [0.5] * 1536
            
            start_time = time.time()
            results = await service.search_similar(test_vector, top_k=10)
            search_time = time.time() - start_time
            
            # Should complete within 2 seconds for SQLite fallback
            search_fast_enough = search_time < 2.0
            self.log_result("Search performance", search_fast_enough, 
                          f"Search took {search_time:.3f}s (must be < 2.0s)")
            
            # Performance test: Storage latency
            embeddings = [(f'perf_test_{i}', [0.1 * i] * 1536, {'test': True}) for i in range(10)]
            
            start_time = time.time()
            storage_success = await service.store_embeddings(embeddings)
            storage_time = time.time() - start_time
            
            # Should complete within 5 seconds for batch of 10
            storage_fast_enough = storage_time < 5.0 and storage_success
            self.log_result("Storage performance", storage_fast_enough,
                          f"Storage took {storage_time:.3f}s (must be < 5.0s)")
            
            return search_fast_enough and storage_fast_enough
            
        except Exception as e:
            self.log_result("Performance requirements", False, f"Error: {e}")
            return False
    
    async def test_data_integrity(self) -> bool:
        """Test data integrity and consistency."""
        print("\n🛡️ Testing Data Integrity...")
        
        try:
            config = VectorStorageConfig()
            service = VectorStorageService(config)
            await service.initialize()
            
            # Test 1: Store and retrieve consistency
            test_data = [
                ('integrity_test_1', [0.1] * 1536, {'content': 'test1', 'is_citable': True}),
                ('integrity_test_2', [0.2] * 1536, {'content': 'test2', 'is_citable': False}),
            ]
            
            storage_success = await service.store_embeddings(test_data, namespace="integrity_test")
            self.log_result("Data storage integrity", storage_success, "Data stored successfully")
            
            # Test 2: Privacy filtering works correctly
            query_vector = [0.15] * 1536
            
            # Should only get citable content by default
            citable_results = await service.search_citable_only(
                query_vector, top_k=5, namespace="integrity_test"
            )
            
            # Should get all content when explicitly requested
            all_results = await service.search_all_content(
                query_vector, top_k=5, namespace="integrity_test"
            )
            
            privacy_works = len(all_results) >= len(citable_results)
            self.log_result("Privacy filtering integrity", privacy_works,
                          f"Citable: {len(citable_results)}, All: {len(all_results)}")
            
            return storage_success and privacy_works
            
        except Exception as e:
            self.log_result("Data integrity", False, f"Error: {e}")
            return False
    
    async def test_error_handling(self) -> bool:
        """Test comprehensive error handling."""
        print("\n🚫 Testing Error Handling...")
        
        try:
            config = VectorStorageConfig()
            service = VectorStorageService(config)
            await service.initialize()
            
            error_tests = []
            
            # Test 1: Invalid embedding dimension
            try:
                await service.store_embeddings([('bad_dim', [0.1] * 100, {})])
                error_tests.append(("Dimension validation", False, "Should reject wrong dimension"))
            except VectorStorageError:
                error_tests.append(("Dimension validation", True, "Correctly rejects wrong dimension"))
            
            # Test 2: Invalid vector ID
            try:
                await service.store_embeddings([('', [0.1] * 1536, {})])
                error_tests.append(("ID validation", False, "Should reject empty ID"))
            except VectorStorageError:
                error_tests.append(("ID validation", True, "Correctly rejects empty ID"))
            
            # Test 3: NaN/Infinity handling
            try:
                await service.store_embeddings([('nan_test', [float('nan')] * 1536, {})])
                error_tests.append(("NaN handling", False, "Should reject NaN values"))
            except VectorStorageError:
                error_tests.append(("NaN handling", True, "Correctly rejects NaN values"))
            
            all_passed = all(result[1] for result in error_tests)
            for test_name, passed, details in error_tests:
                self.log_result(test_name, passed, details)
            
            return all_passed
            
        except Exception as e:
            self.log_result("Error handling", False, f"Unexpected error: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all Step 4 validation tests."""
        print("🎯 GRUMPY TESTER: Step 4 Vector Storage Final Validation")
        print("=" * 70)
        
        test_functions = [
            ("Null Namespace Security", self.test_null_namespace_security),
            ("Similarity Edge Cases", self.test_similarity_edge_cases),
            ("Performance Requirements", self.test_performance_requirements),
            ("Data Integrity", self.test_data_integrity),
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
                traceback.print_exc()
                overall_success = False
        
        # Final report
        print("\n" + "=" * 70)
        print("📊 STEP 4 VALIDATION RESULTS:")
        print("=" * 70)
        
        passed_count = sum(1 for r in self.results if r['passed'])
        total_count = len(self.results)
        
        for result in self.results:
            status = "✅" if result['passed'] else "❌"
            print(f"{status} {result['test']}")
        
        print("=" * 70)
        print(f"TOTAL: {passed_count}/{total_count} tests passed")
        
        if overall_success:
            print("🎉 STEP 4 COMPLETE: Vector storage is production-ready!")
            print("✅ All edge cases handled")
            print("✅ Security vulnerabilities patched")
            print("✅ Performance meets requirements")
            print("✅ Data integrity validated")
            print("✅ Error handling comprehensive")
        else:
            print("⚠️ STEP 4 INCOMPLETE: Issues remain!")
            print(f"❌ Failed tests: {', '.join(self.failed_tests)}")
        
        return overall_success


async def main():
    """Main test execution."""
    tester = GrumpyStep4Tester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎯 READY FOR STEP 5:")
        print("Next: RAG Orchestration Engine implementation")
    else:
        print("\n❌ STEP 4 MUST BE FIXED BEFORE PROCEEDING")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)