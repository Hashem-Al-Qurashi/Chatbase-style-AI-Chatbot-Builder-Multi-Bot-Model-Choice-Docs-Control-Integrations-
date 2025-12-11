#!/usr/bin/env python3
"""
Manual test of vector similarity search functionality to validate claims.
"""

import os
import sys
import django
import asyncio
import json
import math

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from apps.core.vector_storage import VectorStorageService, VectorStorageConfig

async def test_similarity_search():
    """Test the core similarity search functionality."""
    print("🔍 Testing Vector Similarity Search Implementation")
    print("=" * 60)
    
    # Initialize vector service
    config = VectorStorageConfig(backend="pgvector", vector_dimension=3)  # Small vectors for testing
    service = VectorStorageService(config)
    
    if not await service.initialize():
        print("❌ Failed to initialize vector service")
        return False
    
    print(f"✅ Vector service initialized with {service.backend_name} backend")
    
    # Create test vectors with known relationships
    test_vectors = [
        ("vector_a", [1.0, 0.0, 0.0], {"type": "A", "is_citable": True}),
        ("vector_b", [0.0, 1.0, 0.0], {"type": "B", "is_citable": True}),
        ("vector_c", [0.0, 0.0, 1.0], {"type": "C", "is_citable": False}),
        ("vector_similar_to_a", [0.9, 0.1, 0.0], {"type": "A_similar", "is_citable": True}),
        ("vector_halfway", [0.7, 0.7, 0.0], {"type": "halfway", "is_citable": False}),
    ]
    
    # Store vectors
    await service.store_embeddings(test_vectors, namespace="similarity_test")
    print(f"✅ Stored {len(test_vectors)} test vectors")
    
    # Test 1: Basic similarity search
    print("\n📊 Test 1: Basic Similarity Search")
    query_vector = [1.0, 0.0, 0.0]  # Should match vector_a best
    results = await service.search_similar(
        query_vector=query_vector,
        top_k=5,
        namespace="similarity_test",
        filter_metadata={"include_non_citable": True}
    )
    
    print(f"Query vector: {query_vector}")
    print(f"Results found: {len(results)}")
    for i, result in enumerate(results):
        print(f"  {i+1}. ID: {result.id}, Score: {result.score:.4f}, Type: {result.metadata.get('type')}")
    
    # Validate ordering (vector_a should be first, vector_similar_to_a should be second)
    if len(results) >= 2:
        if results[0].id == "vector_a" and results[1].id == "vector_similar_to_a":
            print("✅ Similarity ordering correct")
        else:
            print("❌ Similarity ordering incorrect")
            print(f"   Expected: vector_a (1st), vector_similar_to_a (2nd)")
            print(f"   Got: {results[0].id} (1st), {results[1].id} (2nd)")
            return False
    else:
        print("❌ Insufficient results returned")
        return False
    
    # Test 2: Privacy filtering
    print("\n🔒 Test 2: Privacy Filtering")
    
    # Citable only
    citable_results = await service.search_citable_only(
        query_vector=query_vector,
        top_k=10,
        namespace="similarity_test"
    )
    
    # All content
    all_results = await service.search_all_content(
        query_vector=query_vector,
        top_k=10,
        namespace="similarity_test"
    )
    
    print(f"Citable-only results: {len(citable_results)}")
    print(f"All results: {len(all_results)}")
    
    # Validate privacy filtering
    citable_ids = {r.id for r in citable_results}
    all_ids = {r.id for r in all_results}
    
    expected_citable = {"vector_a", "vector_b", "vector_similar_to_a"}
    expected_non_citable = {"vector_c", "vector_halfway"}
    
    if citable_ids == expected_citable and all_ids == expected_citable | expected_non_citable:
        print("✅ Privacy filtering working correctly")
    else:
        print("❌ Privacy filtering failed")
        print(f"   Expected citable: {expected_citable}")
        print(f"   Got citable: {citable_ids}")
        print(f"   Expected all: {expected_citable | expected_non_citable}")
        print(f"   Got all: {all_ids}")
        return False
    
    # Test 3: Cosine similarity calculation validation
    print("\n📐 Test 3: Cosine Similarity Validation")
    
    # Manual cosine similarity calculation
    def cosine_similarity(vec1, vec2):
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        return dot_product / (magnitude1 * magnitude2)
    
    # Test against known vectors
    test_cases = [
        ([1.0, 0.0, 0.0], [1.0, 0.0, 0.0], 1.0),      # Identical vectors
        ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0], 0.0),      # Orthogonal vectors
        ([1.0, 0.0, 0.0], [0.9, 0.1, 0.0], None),     # Similar vectors (calculate expected)
    ]
    
    for query_vec, target_vec, expected_sim in test_cases:
        if expected_sim is None:
            expected_sim = cosine_similarity(query_vec, target_vec)
        
        # Search for this specific vector
        results = await service.search_all_content(
            query_vector=query_vec,
            top_k=5,
            namespace="similarity_test"
        )
        
        # Find the target vector in results
        target_result = None
        for result in results:
            stored_embedding = None
            # Extract embedding from database to compare
            # (This is a simplified check since we can't directly get embeddings from search results)
            if (target_vec == [1.0, 0.0, 0.0] and result.id == "vector_a") or \
               (target_vec == [0.0, 1.0, 0.0] and result.id == "vector_b") or \
               (target_vec == [0.9, 0.1, 0.0] and result.id == "vector_similar_to_a"):
                target_result = result
                break
        
        if target_result:
            # Check if similarity score is reasonable (within 5% of expected)
            score_diff = abs(target_result.score - expected_sim)
            if score_diff < 0.05:
                print(f"✅ Similarity calculation accurate for {target_vec}: {target_result.score:.4f} ≈ {expected_sim:.4f}")
            else:
                print(f"❌ Similarity calculation inaccurate for {target_vec}: {target_result.score:.4f} vs {expected_sim:.4f}")
                return False
        else:
            print(f"❌ Target vector {target_vec} not found in results")
            return False
    
    print("\n✅ All vector similarity search tests passed!")
    return True

async def main():
    """Run similarity search tests."""
    success = await test_similarity_search()
    if success:
        print("\n🎯 Vector similarity search implementation validated!")
        sys.exit(0)
    else:
        print("\n💥 Vector similarity search has critical issues!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())