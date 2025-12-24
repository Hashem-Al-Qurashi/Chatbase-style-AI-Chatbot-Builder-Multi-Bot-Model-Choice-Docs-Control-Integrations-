#!/usr/bin/env python3
"""
AGGRESSIVE Vector Storage Edge Case Testing - Testing the claimed fixes
This test is designed to break the vector storage with malicious inputs
"""

import os
import sys
import django
import asyncio
import json
import math
from typing import List, Dict, Any

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from apps.core.vector_storage import VectorStorageService, VectorStorageConfig
from apps.core.exceptions import VectorStorageError


class AggressiveVectorStorageTests:
    """Aggressive test suite to validate edge case claims."""
    
    def __init__(self):
        self.config = VectorStorageConfig(
            backend="pgvector",  # Will fallback to SQLite
            vector_dimension=1536,
            batch_size=10,
            enable_caching=True
        )
        self.failures = []
        self.successes = []
    
    async def run_all_tests(self):
        """Run all aggressive edge case tests."""
        print("🔥 AGGRESSIVE VECTOR STORAGE EDGE CASE TESTING")
        print("=" * 60)
        print("Testing claimed fixes: null namespace vulnerability, similarity calculation errors, comprehensive input validation")
        
        # Initialize service once
        self.vector_service = VectorStorageService(self.config)
        await self.vector_service.initialize()
        
        await self.test_null_namespace_vulnerability()
        await self.test_malicious_input_validation()
        await self.test_similarity_calculation_edge_cases()
        await self.test_vector_dimension_attacks()
        await self.test_metadata_injection_attacks()
        await self.test_numeric_overflow_attacks()
        
        self.print_results()
    
    async def test_null_namespace_vulnerability(self):
        """Test the claimed null namespace vulnerability fix."""
        print("\n🎯 Testing Null Namespace Vulnerability Fix")
        
        test_embeddings = [("test_null", [0.1] * 1536, {"content": "test"})]
        
        # Test various null/empty namespace scenarios
        test_cases = [
            (None, "None namespace"),
            ("", "Empty string namespace"),
            ("   ", "Whitespace namespace"),
            ("\x00", "Null byte namespace"),
            ("null", "String 'null'"),
            (0, "Integer 0 as namespace"),
            (False, "Boolean False as namespace"),
            ([], "Empty list as namespace"),
            ({}, "Empty dict as namespace"),
        ]
        
        for namespace, description in test_cases:
            try:
                result = await self.vector_service.store_embeddings(
                    test_embeddings,
                    namespace=namespace
                )
                
                if result:
                    # Try to search with the same namespace
                    search_results = await self.vector_service.search_similar(
                        query_vector=[0.1] * 1536,
                        top_k=5,
                        namespace=namespace
                    )
                    print(f"   ✅ {description}: Stored and searched successfully")
                else:
                    print(f"   ❌ {description}: Storage failed")
                    self.failures.append(f"Namespace test failed: {description}")
                    
            except Exception as e:
                if isinstance(namespace, str) or namespace is None:
                    print(f"   ❌ {description}: Exception - {str(e)}")
                    self.failures.append(f"Namespace validation failed: {description} - {str(e)}")
                else:
                    print(f"   ✅ {description}: Properly rejected with {type(e).__name__}")
                    self.successes.append(f"Invalid namespace type rejected: {description}")
    
    async def test_malicious_input_validation(self):
        """Test comprehensive input validation claims."""
        print("\n🔍 Testing Comprehensive Input Validation")
        
        # Test malicious vector IDs
        malicious_ids = [
            ("", "Empty ID"),
            ("   ", "Whitespace ID"),
            ("../../../etc/passwd", "Path traversal ID"),
            ("'; DROP TABLE vector_embeddings; --", "SQL injection ID"),
            ("\x00\x01\x02", "Binary data ID"),
            ("a" * 10000, "Extremely long ID"),
            (None, "None ID"),
            (123, "Numeric ID"),
        ]
        
        valid_embedding = [0.1] * 1536
        valid_metadata = {"test": "data"}
        
        for vector_id, description in malicious_ids:
            try:
                result = await self.vector_service.store_embeddings(
                    [(vector_id, valid_embedding, valid_metadata)],
                    namespace="test_malicious"
                )
                
                if result:
                    print(f"   ❌ {description}: Accepted malicious input!")
                    self.failures.append(f"Malicious ID accepted: {description}")
                else:
                    print(f"   ✅ {description}: Properly rejected")
                    self.successes.append(f"Malicious ID rejected: {description}")
                    
            except VectorStorageError as e:
                print(f"   ✅ {description}: Validation error - {str(e)}")
                self.successes.append(f"Input validation working: {description}")
            except Exception as e:
                print(f"   ⚠️  {description}: Unexpected error - {str(e)}")
    
    async def test_similarity_calculation_edge_cases(self):
        """Test similarity calculation robustness."""
        print("\n📊 Testing Similarity Calculation Edge Cases")
        
        # Test problematic vectors
        problematic_vectors = [
            ([float('nan')] * 1536, "NaN vector"),
            ([float('inf')] * 1536, "Infinity vector"),
            ([float('-inf')] * 1536, "Negative infinity vector"),
            ([0.0] * 1536, "Zero vector"),
            ([1e308] * 1536, "Overflow vector"),
            ([1e-308] * 1536, "Underflow vector"),
            ([float('nan'), 1.0, float('inf')] + [0.0] * 1533, "Mixed problematic"),
        ]
        
        for vector, description in problematic_vectors:
            try:
                # Try to store the problematic vector
                result = await self.vector_service.store_embeddings(
                    [(f"test_{description}", vector, {"test": True})],
                    namespace="test_similarity"
                )
                
                if result:
                    print(f"   ❌ {description}: Accepted problematic vector!")
                    self.failures.append(f"Problematic vector accepted: {description}")
                    
                    # Try to search with it
                    try:
                        search_results = await self.vector_service.search_similar(
                            query_vector=vector,
                            top_k=5,
                            namespace="test_similarity"
                        )
                        print(f"      Search with {description}: {len(search_results)} results")
                    except Exception as search_e:
                        print(f"      Search failed: {str(search_e)}")
                else:
                    print(f"   ✅ {description}: Storage properly rejected")
                    self.successes.append(f"Problematic vector rejected: {description}")
                    
            except VectorStorageError as e:
                print(f"   ✅ {description}: Validation error - {str(e)}")
                self.successes.append(f"Vector validation working: {description}")
            except Exception as e:
                print(f"   ⚠️  {description}: Unexpected error - {str(e)}")
    
    async def test_vector_dimension_attacks(self):
        """Test vector dimension validation."""
        print("\n📏 Testing Vector Dimension Validation")
        
        dimension_tests = [
            ([], "Empty vector"),
            ([0.1] * 10, "Too short vector"),
            ([0.1] * 3000, "Too long vector"),
            ([0.1] * 1535, "One dimension short"),
            ([0.1] * 1537, "One dimension over"),
            (None, "None vector"),
            ("not_a_list", "String instead of list"),
            ([0.1, "string", 0.3] + [0.1] * 1533, "Mixed types in vector"),
        ]
        
        for vector, description in dimension_tests:
            try:
                result = await self.vector_service.store_embeddings(
                    [(f"test_dim_{description}", vector, {"test": True})],
                    namespace="test_dimensions"
                )
                
                if result:
                    print(f"   ❌ {description}: Accepted invalid dimension!")
                    self.failures.append(f"Invalid dimension accepted: {description}")
                else:
                    print(f"   ✅ {description}: Properly rejected")
                    self.successes.append(f"Invalid dimension rejected: {description}")
                    
            except VectorStorageError as e:
                print(f"   ✅ {description}: Validation error - {str(e)}")
                self.successes.append(f"Dimension validation working: {description}")
            except Exception as e:
                print(f"   ⚠️  {description}: Unexpected error - {str(e)}")
    
    async def test_metadata_injection_attacks(self):
        """Test metadata injection and size attacks."""
        print("\n💉 Testing Metadata Injection Attacks")
        
        # Create oversized metadata
        huge_metadata = {"data": "x" * 200000}  # 200KB
        
        metadata_tests = [
            (huge_metadata, "Oversized metadata (200KB)"),
            ({"key": None}, "None value in metadata"),
            ({"../../../etc": "passwd"}, "Path traversal in metadata key"),
            ({"'; DROP TABLE": "vector_embeddings; --"}, "SQL injection in metadata"),
            ({str(i): f"value_{i}" for i in range(10000)}, "Too many metadata keys"),
            (None, "None metadata"),
            ("string_metadata", "String instead of dict"),
            ([1, 2, 3], "List instead of dict"),
        ]
        
        valid_vector = [0.1] * 1536
        
        for metadata, description in metadata_tests:
            try:
                result = await self.vector_service.store_embeddings(
                    [(f"test_meta_{description}", valid_vector, metadata)],
                    namespace="test_metadata"
                )
                
                if result:
                    if description == "Oversized metadata (200KB)":
                        print(f"   ❌ {description}: Accepted oversized metadata!")
                        self.failures.append(f"Oversized metadata accepted: {description}")
                    else:
                        print(f"   ✅ {description}: Stored successfully")
                        self.successes.append(f"Valid metadata accepted: {description}")
                else:
                    print(f"   ⚠️  {description}: Storage failed")
                    
            except VectorStorageError as e:
                if "too large" in str(e).lower() or "invalid metadata" in str(e).lower():
                    print(f"   ✅ {description}: Validation error - {str(e)}")
                    self.successes.append(f"Metadata validation working: {description}")
                else:
                    print(f"   ⚠️  {description}: Unexpected validation error - {str(e)}")
            except Exception as e:
                print(f"   ⚠️  {description}: Unexpected error - {str(e)}")
    
    async def test_numeric_overflow_attacks(self):
        """Test numeric overflow and precision attacks."""
        print("\n💥 Testing Numeric Overflow Attacks")
        
        overflow_tests = [
            ([1e100] * 1536, "Scientific notation overflow"),
            ([-1e100] * 1536, "Negative scientific notation"),
            ([sys.float_info.max] * 1536, "Float max values"),
            ([sys.float_info.min] * 1536, "Float min values"),
            ([2**1023] * 1536, "Power of 2 overflow"),
            ([1.7976931348623157e+308] * 1536, "Near float limit"),
            ([1] * 1536, "Integer values"),
            ([True, False] * 768, "Boolean values"),
        ]
        
        for vector, description in overflow_tests:
            try:
                result = await self.vector_service.store_embeddings(
                    [(f"test_overflow_{description}", vector, {"test": True})],
                    namespace="test_overflow"
                )
                
                if result:
                    print(f"   ✅ {description}: Handled successfully")
                    self.successes.append(f"Numeric handling working: {description}")
                    
                    # Test similarity calculation with these values
                    try:
                        search_results = await self.vector_service.search_similar(
                            query_vector=[0.1] * 1536,
                            top_k=5,
                            namespace="test_overflow"
                        )
                        print(f"      Similarity search: {len(search_results)} results")
                    except Exception as search_e:
                        print(f"      Similarity search failed: {str(search_e)}")
                        if "overflow" in str(search_e).lower():
                            self.failures.append(f"Similarity calculation overflow: {description}")
                else:
                    print(f"   ⚠️  {description}: Storage failed")
                    
            except VectorStorageError as e:
                print(f"   ✅ {description}: Validation error - {str(e)}")
                self.successes.append(f"Overflow protection working: {description}")
            except Exception as e:
                print(f"   ❌ {description}: Unexpected error - {str(e)}")
                self.failures.append(f"Overflow handling failed: {description} - {str(e)}")
    
    def print_results(self):
        """Print comprehensive test results."""
        print("\n" + "=" * 60)
        print("🔥 AGGRESSIVE EDGE CASE TESTING RESULTS")
        print("=" * 60)
        
        total_tests = len(self.successes) + len(self.failures)
        success_rate = len(self.successes) / total_tests * 100 if total_tests > 0 else 0
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Successes: {len(self.successes)}")
        print(f"   Failures: {len(self.failures)}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if self.failures:
            print(f"\n❌ CRITICAL FAILURES:")
            for i, failure in enumerate(self.failures, 1):
                print(f"   {i}. {failure}")
        
        if self.successes:
            print(f"\n✅ SUCCESSFUL VALIDATIONS:")
            for i, success in enumerate(self.successes[:10], 1):  # Show first 10
                print(f"   {i}. {success}")
            if len(self.successes) > 10:
                print(f"   ... and {len(self.successes) - 10} more")
        
        # Final verdict
        critical_failures = [f for f in self.failures if any(keyword in f.lower() for keyword in ['accepted', 'overflow', 'injection'])]
        
        if critical_failures:
            print(f"\n💥 VERDICT: CRITICAL SECURITY VULNERABILITIES FOUND!")
            print(f"   The claimed 'comprehensive input validation' is NOT working properly.")
            print(f"   Found {len(critical_failures)} critical security issues.")
        elif self.failures:
            print(f"\n⚠️  VERDICT: MINOR ISSUES FOUND")
            print(f"   Some edge cases not handled properly, but no critical security issues.")
        else:
            print(f"\n🎉 VERDICT: ROBUST INPUT VALIDATION")
            print(f"   All edge cases handled properly. Claims validated.")


async def main():
    """Run aggressive edge case tests."""
    test_suite = AggressiveVectorStorageTests()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())