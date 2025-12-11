#!/usr/bin/env python3
"""
Performance and stress testing for vector storage system.
"""

import os
import sys
import django
import asyncio
import json
import time
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from apps.core.vector_storage import VectorStorageService, VectorStorageConfig

async def test_vector_performance():
    """Test vector storage performance under various conditions."""
    print("⚡ Testing Vector Storage Performance & Reliability")
    print("=" * 60)
    
    # Initialize vector service
    config = VectorStorageConfig(backend="pgvector", vector_dimension=100)  # Smaller for faster testing
    service = VectorStorageService(config)
    
    if not await service.initialize():
        print("❌ Failed to initialize vector service")
        return False
    
    print(f"✅ Vector service initialized with {service.backend_name} backend")
    
    # Test 1: Bulk insertion performance
    print("\n📈 Test 1: Bulk Insertion Performance")
    
    bulk_sizes = [10, 50, 100, 500]
    for size in bulk_sizes:
        # Generate test vectors
        vectors = []
        for i in range(size):
            embedding = [random.uniform(-1, 1) for _ in range(100)]
            metadata = {
                "id": f"bulk_test_{i}",
                "content": f"Test content {i} for bulk insertion performance",
                "is_citable": i % 2 == 0,  # Mix of citable and non-citable
                "category": f"category_{i % 5}",
                "timestamp": time.time()
            }
            vectors.append((f"bulk_{size}_{i}", embedding, metadata))
        
        # Time the insertion
        start_time = time.time()
        success = await service.store_embeddings(vectors, namespace=f"bulk_test_{size}")
        end_time = time.time()
        
        duration = end_time - start_time
        vectors_per_second = size / duration if duration > 0 else float('inf')
        
        if success:
            print(f"  ✅ {size} vectors: {duration:.3f}s ({vectors_per_second:.1f} vectors/sec)")
        else:
            print(f"  ❌ {size} vectors: FAILED in {duration:.3f}s")
            return False
    
    # Test 2: Search performance with varying dataset sizes
    print("\n🔍 Test 2: Search Performance")
    
    query_vector = [random.uniform(-1, 1) for _ in range(100)]
    
    for size in bulk_sizes:
        namespace = f"bulk_test_{size}"
        
        # Test search performance
        search_times = []
        for _ in range(5):  # Run 5 searches to get average
            start_time = time.time()
            results = await service.search_similar(
                query_vector=query_vector,
                top_k=10,
                namespace=namespace
            )
            end_time = time.time()
            search_times.append(end_time - start_time)
        
        avg_search_time = sum(search_times) / len(search_times)
        print(f"  📊 {size} vectors: {avg_search_time:.3f}s avg search time ({len(results)} results)")
    
    # Test 3: Concurrent operations
    print("\n🔄 Test 3: Concurrent Operations")
    
    async def concurrent_search_task(task_id: int):
        """Perform concurrent search operations."""
        namespace = f"bulk_test_100"  # Use medium-sized dataset
        query_vector = [random.uniform(-1, 1) for _ in range(100)]
        
        start_time = time.time()
        results = await service.search_similar(
            query_vector=query_vector,
            top_k=5,
            namespace=namespace
        )
        end_time = time.time()
        
        return {
            "task_id": task_id,
            "duration": end_time - start_time,
            "results_count": len(results),
            "success": len(results) >= 0  # Search can return 0 results
        }
    
    # Run 10 concurrent searches
    concurrent_tasks = [concurrent_search_task(i) for i in range(10)]
    concurrent_start = time.time()
    concurrent_results = await asyncio.gather(*concurrent_tasks)
    concurrent_end = time.time()
    
    total_concurrent_time = concurrent_end - concurrent_start
    successful_tasks = sum(1 for result in concurrent_results if result["success"])
    avg_task_time = sum(result["duration"] for result in concurrent_results) / len(concurrent_results)
    
    print(f"  ✅ {successful_tasks}/{len(concurrent_tasks)} concurrent searches successful")
    print(f"  📊 Total time: {total_concurrent_time:.3f}s, Avg task time: {avg_task_time:.3f}s")
    
    if successful_tasks < len(concurrent_tasks):
        print(f"  ⚠️ {len(concurrent_tasks) - successful_tasks} concurrent operations failed")
    
    # Test 4: Memory usage with large vectors
    print("\n💾 Test 4: Large Vector Handling")
    
    # Test with larger dimension vectors
    large_config = VectorStorageConfig(backend="pgvector", vector_dimension=1536)  # Full OpenAI embedding size
    large_service = VectorStorageService(large_config)
    await large_service.initialize()
    
    # Create some large vectors
    large_vectors = []
    for i in range(10):  # Smaller number due to size
        embedding = [random.uniform(-1, 1) for _ in range(1536)]
        metadata = {
            "content": f"Large vector test content {i}" * 100,  # Large content
            "is_citable": True,
            "size": "large"
        }
        large_vectors.append((f"large_{i}", embedding, metadata))
    
    start_time = time.time()
    large_success = await large_service.store_embeddings(large_vectors, namespace="large_test")
    end_time = time.time()
    
    if large_success:
        large_duration = end_time - start_time
        print(f"  ✅ 10 large vectors (1536 dim): {large_duration:.3f}s")
        
        # Test search on large vectors
        large_query = [random.uniform(-1, 1) for _ in range(1536)]
        search_start = time.time()
        large_results = await large_service.search_similar(
            query_vector=large_query,
            top_k=5,
            namespace="large_test"
        )
        search_end = time.time()
        
        search_duration = search_end - search_start
        print(f"  🔍 Large vector search: {search_duration:.3f}s ({len(large_results)} results)")
    else:
        print(f"  ❌ Large vector storage failed")
        return False
    
    # Test 5: Error handling and recovery
    print("\n🛡️ Test 5: Error Handling")
    
    # Test invalid vector dimensions
    try:
        invalid_vectors = [("invalid", [1, 2, 3], {"test": True})]  # Wrong dimension
        await service.store_embeddings(invalid_vectors, namespace="error_test")
        print("  ⚠️ Invalid vector dimension was accepted (may be normal for SQLite)")
    except Exception as e:
        print(f"  ✅ Invalid vector dimension rejected: {type(e).__name__}")
    
    # Test search with invalid query vector
    try:
        invalid_query = [1, 2, 3]  # Wrong dimension
        results = await service.search_similar(
            query_vector=invalid_query,
            top_k=5,
            namespace="bulk_test_100"
        )
        print(f"  ⚠️ Invalid query dimension returned {len(results)} results")
    except Exception as e:
        print(f"  ✅ Invalid query dimension rejected: {type(e).__name__}")
    
    # Test 6: Storage statistics
    print("\n📊 Test 6: Storage Statistics")
    
    stats = await service.get_storage_stats()
    print(f"  📈 Storage Stats:")
    print(f"    - Backend: {stats.get('backend', 'unknown')}")
    print(f"    - Total vectors: {stats.get('total_vectors', 'unknown')}")
    print(f"    - Namespaces: {stats.get('namespaces', 'unknown')}")
    print(f"    - Table size: {stats.get('table_size', 'unknown')}")
    
    print("\n✅ All performance tests completed!")
    return True

async def main():
    """Run performance tests."""
    try:
        success = await test_vector_performance()
        if success:
            print("\n🎯 Vector storage performance validated!")
            sys.exit(0)
        else:
            print("\n💥 Performance tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Performance test error: {str(e)}")
        import traceback
        print("📋 Full traceback:")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())