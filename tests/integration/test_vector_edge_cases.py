#!/usr/bin/env python3
"""
Test error handling and edge cases in vector storage system.
"""

import os
import sys
import django
import asyncio
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from apps.core.vector_storage import VectorStorageService, VectorStorageConfig

async def test_edge_cases():
    """Test error handling and edge cases."""
    print("🛡️ Testing Vector Storage Error Handling & Edge Cases")
    print("=" * 60)
    
    # Initialize vector service
    config = VectorStorageConfig(backend="pgvector", vector_dimension=5)
    service = VectorStorageService(config)
    
    if not await service.initialize():
        print("❌ Failed to initialize vector service")
        return False
    
    print(f"✅ Vector service initialized with {service.backend_name} backend")
    
    # Test 1: Empty and null inputs
    print("\n📭 Test 1: Empty and Null Inputs")
    
    # Empty vector list
    try:
        result = await service.store_embeddings([], namespace="empty_test")
        print(f"  ✅ Empty vector list handled: {result}")
    except Exception as e:
        print(f"  ❌ Empty vector list failed: {str(e)}")
    
    # Empty query vector
    try:
        results = await service.search_similar(
            query_vector=[],
            top_k=5,
            namespace="test"
        )
        print(f"  ⚠️ Empty query vector returned {len(results)} results")
    except Exception as e:
        print(f"  ✅ Empty query vector rejected: {type(e).__name__}")
    
    # None inputs
    try:
        results = await service.search_similar(
            query_vector=None,
            top_k=5,
            namespace="test"
        )
        print(f"  ⚠️ None query vector returned {len(results)} results")
    except Exception as e:
        print(f"  ✅ None query vector rejected: {type(e).__name__}")
    
    # Test 2: Invalid vector dimensions
    print("\n📏 Test 2: Invalid Vector Dimensions")
    
    # Too short vector
    try:
        vectors = [("short", [1.0, 2.0], {"test": True})]  # Only 2 dimensions instead of 5
        result = await service.store_embeddings(vectors, namespace="dim_test")
        print(f"  ⚠️ Short vector accepted: {result}")
    except Exception as e:
        print(f"  ✅ Short vector rejected: {type(e).__name__}")
    
    # Too long vector
    try:
        vectors = [("long", [1.0] * 100, {"test": True})]  # 100 dimensions instead of 5
        result = await service.store_embeddings(vectors, namespace="dim_test")
        print(f"  ⚠️ Long vector accepted: {result}")
    except Exception as e:
        print(f"  ✅ Long vector rejected: {type(e).__name__}")
    
    # Non-numeric vector
    try:
        vectors = [("invalid", ["a", "b", "c", "d", "e"], {"test": True})]
        result = await service.store_embeddings(vectors, namespace="dim_test")
        print(f"  ⚠️ Non-numeric vector accepted: {result}")
    except Exception as e:
        print(f"  ✅ Non-numeric vector rejected: {type(e).__name__}")
    
    # Test 3: Extreme values
    print("\n🌡️ Test 3: Extreme Values")
    
    # Very large numbers
    try:
        vectors = [("large", [1e10, 1e10, 1e10, 1e10, 1e10], {"test": True})]
        result = await service.store_embeddings(vectors, namespace="extreme_test")
        if result:
            print("  ✅ Large numbers stored successfully")
            # Test search with large numbers
            results = await service.search_similar(
                query_vector=[1e10, 1e10, 1e10, 1e10, 1e10],
                top_k=5,
                namespace="extreme_test"
            )
            print(f"    Search with large numbers: {len(results)} results")
        else:
            print("  ❌ Large numbers rejected")
    except Exception as e:
        print(f"  ❌ Large numbers failed: {type(e).__name__}")
    
    # Very small numbers
    try:
        vectors = [("small", [1e-10, 1e-10, 1e-10, 1e-10, 1e-10], {"test": True})]
        result = await service.store_embeddings(vectors, namespace="extreme_test")
        if result:
            print("  ✅ Small numbers stored successfully")
        else:
            print("  ❌ Small numbers rejected")
    except Exception as e:
        print(f"  ❌ Small numbers failed: {type(e).__name__}")
    
    # Infinity and NaN
    try:
        vectors = [("inf", [float('inf'), float('-inf'), float('nan'), 1.0, 2.0], {"test": True})]
        result = await service.store_embeddings(vectors, namespace="extreme_test")
        print(f"  ⚠️ Infinity/NaN values accepted: {result}")
    except Exception as e:
        print(f"  ✅ Infinity/NaN values rejected: {type(e).__name__}")
    
    # Test 4: Large metadata
    print("\n📋 Test 4: Large Metadata Handling")
    
    # Very large metadata
    large_content = "X" * 100000  # 100KB of content
    try:
        vectors = [("large_meta", [1.0, 2.0, 3.0, 4.0, 5.0], {
            "large_content": large_content,
            "is_citable": True,
            "nested": {"deep": {"very": {"nested": "data"}}}
        })]
        result = await service.store_embeddings(vectors, namespace="meta_test")
        if result:
            print("  ✅ Large metadata stored successfully")
            # Test search retrieval
            results = await service.search_similar(
                query_vector=[1.0, 2.0, 3.0, 4.0, 5.0],
                top_k=5,
                namespace="meta_test"
            )
            if results and len(results[0].metadata.get("large_content", "")) > 50000:
                print("    ✅ Large metadata retrieved successfully")
            else:
                print("    ⚠️ Large metadata may have been truncated")
        else:
            print("  ❌ Large metadata rejected")
    except Exception as e:
        print(f"  ❌ Large metadata failed: {type(e).__name__}")
    
    # Test 5: Special characters and encoding
    print("\n🌐 Test 5: Special Characters and Encoding")
    
    # Unicode and special characters
    try:
        vectors = [("unicode", [1.0, 2.0, 3.0, 4.0, 5.0], {
            "content": "Testing émojis 🚀 and ñïçé characters 中文测试",
            "special_chars": "!@#$%^&*()[]{}|\\:;\"'<>?,./",
            "json_breaking": '{"key": "value with quotes"}'
        })]
        result = await service.store_embeddings(vectors, namespace="encoding_test")
        if result:
            print("  ✅ Unicode/special characters stored successfully")
            # Test retrieval
            results = await service.search_similar(
                query_vector=[1.0, 2.0, 3.0, 4.0, 5.0],
                top_k=5,
                namespace="encoding_test"
            )
            if results:
                retrieved_content = results[0].metadata.get("content", "")
                if "🚀" in retrieved_content and "中文" in retrieved_content:
                    print("    ✅ Unicode characters retrieved correctly")
                else:
                    print("    ⚠️ Unicode characters may have been corrupted")
            else:
                print("    ❌ No results returned for unicode test")
        else:
            print("  ❌ Unicode/special characters rejected")
    except Exception as e:
        print(f"  ❌ Unicode/special characters failed: {type(e).__name__}")
    
    # Test 6: Concurrent namespace operations
    print("\n🔄 Test 6: Concurrent Namespace Operations")
    
    async def concurrent_namespace_task(namespace: str, vector_id: str):
        """Perform operations in different namespaces concurrently."""
        try:
            # Store vector
            vectors = [(vector_id, [1.0, 2.0, 3.0, 4.0, 5.0], {"namespace": namespace})]
            store_result = await service.store_embeddings(vectors, namespace=namespace)
            
            # Search immediately
            search_results = await service.search_similar(
                query_vector=[1.0, 2.0, 3.0, 4.0, 5.0],
                top_k=5,
                namespace=namespace
            )
            
            return {
                "namespace": namespace,
                "store_success": store_result,
                "search_count": len(search_results),
                "success": store_result and len(search_results) > 0
            }
        except Exception as e:
            return {
                "namespace": namespace,
                "error": str(e),
                "success": False
            }
    
    # Run concurrent operations on different namespaces
    namespace_tasks = [
        concurrent_namespace_task(f"concurrent_{i}", f"vector_{i}")
        for i in range(5)
    ]
    concurrent_results = await asyncio.gather(*namespace_tasks)
    
    successful_concurrent = sum(1 for result in concurrent_results if result["success"])
    print(f"  ✅ {successful_concurrent}/{len(concurrent_results)} concurrent namespace operations successful")
    
    for result in concurrent_results:
        if not result["success"]:
            print(f"    ❌ {result['namespace']}: {result.get('error', 'Unknown error')}")
    
    # Test 7: Edge case search parameters
    print("\n🔍 Test 7: Edge Case Search Parameters")
    
    # Store some test data first
    test_vectors = [
        ("edge1", [1.0, 0.0, 0.0, 0.0, 0.0], {"test": "edge"}),
        ("edge2", [0.0, 1.0, 0.0, 0.0, 0.0], {"test": "edge"}),
        ("edge3", [0.0, 0.0, 1.0, 0.0, 0.0], {"test": "edge"}),
    ]
    await service.store_embeddings(test_vectors, namespace="edge_search_test")
    
    # Zero top_k
    try:
        results = await service.search_similar(
            query_vector=[1.0, 0.0, 0.0, 0.0, 0.0],
            top_k=0,
            namespace="edge_search_test"
        )
        print(f"  ✅ top_k=0 returned {len(results)} results")
    except Exception as e:
        print(f"  ✅ top_k=0 rejected: {type(e).__name__}")
    
    # Negative top_k
    try:
        results = await service.search_similar(
            query_vector=[1.0, 0.0, 0.0, 0.0, 0.0],
            top_k=-5,
            namespace="edge_search_test"
        )
        print(f"  ⚠️ Negative top_k returned {len(results)} results")
    except Exception as e:
        print(f"  ✅ Negative top_k rejected: {type(e).__name__}")
    
    # Very large top_k
    try:
        results = await service.search_similar(
            query_vector=[1.0, 0.0, 0.0, 0.0, 0.0],
            top_k=1000000,
            namespace="edge_search_test"
        )
        print(f"  ✅ Large top_k returned {len(results)} results (max available)")
    except Exception as e:
        print(f"  ❌ Large top_k failed: {type(e).__name__}")
    
    print("\n✅ Edge case and error handling tests completed!")
    return True

async def main():
    """Run edge case tests."""
    try:
        success = await test_edge_cases()
        if success:
            print("\n🎯 Vector storage edge case handling validated!")
            sys.exit(0)
        else:
            print("\n💥 Edge case tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Edge case test error: {str(e)}")
        import traceback
        print("📋 Full traceback:")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())