#!/usr/bin/env python3
"""
Rigorous test of namespace isolation to validate security claims.
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

async def test_namespace_isolation():
    """Test rigorous namespace isolation between chatbots."""
    print("🏢 Testing Namespace Isolation Security")
    print("=" * 60)
    
    # Initialize vector service
    config = VectorStorageConfig(backend="pgvector", vector_dimension=5)
    service = VectorStorageService(config)
    
    if not await service.initialize():
        print("❌ Failed to initialize vector service")
        return False
    
    print(f"✅ Vector service initialized with {service.backend_name} backend")
    
    # Create highly sensitive test data for different "companies"
    company_a_vectors = [
        ("trade_secret_1", [1.0, 0.0, 0.0, 0.0, 0.0], {"company": "A", "sensitivity": "TOP_SECRET", "content": "Company A's proprietary algorithm"}),
        ("financial_data_1", [0.9, 0.1, 0.0, 0.0, 0.0], {"company": "A", "sensitivity": "CONFIDENTIAL", "content": "Company A's Q4 revenue projections"}),
        ("customer_list_1", [0.8, 0.2, 0.0, 0.0, 0.0], {"company": "A", "sensitivity": "RESTRICTED", "content": "Company A's customer database"}),
    ]
    
    company_b_vectors = [
        ("trade_secret_2", [0.0, 1.0, 0.0, 0.0, 0.0], {"company": "B", "sensitivity": "TOP_SECRET", "content": "Company B's proprietary algorithm"}),
        ("financial_data_2", [0.0, 0.9, 0.1, 0.0, 0.0], {"company": "B", "sensitivity": "CONFIDENTIAL", "content": "Company B's Q4 revenue projections"}),
        ("customer_list_2", [0.0, 0.8, 0.2, 0.0, 0.0], {"company": "B", "sensitivity": "RESTRICTED", "content": "Company B's customer database"}),
    ]
    
    company_c_vectors = [
        ("trade_secret_3", [0.0, 0.0, 1.0, 0.0, 0.0], {"company": "C", "sensitivity": "TOP_SECRET", "content": "Company C's proprietary algorithm"}),
        ("financial_data_3", [0.0, 0.0, 0.9, 0.1, 0.0], {"company": "C", "sensitivity": "CONFIDENTIAL", "content": "Company C's Q4 revenue projections"}),
        ("customer_list_3", [0.0, 0.0, 0.8, 0.2, 0.0], {"company": "C", "sensitivity": "RESTRICTED", "content": "Company C's customer database"}),
    ]
    
    # Store data in separate namespaces
    await service.store_embeddings(company_a_vectors, namespace="company_A_tenant")
    await service.store_embeddings(company_b_vectors, namespace="company_B_tenant")
    await service.store_embeddings(company_c_vectors, namespace="company_C_tenant")
    
    print(f"✅ Stored {len(company_a_vectors)} vectors for Company A")
    print(f"✅ Stored {len(company_b_vectors)} vectors for Company B")
    print(f"✅ Stored {len(company_c_vectors)} vectors for Company C")
    
    # Test 1: Company A searches should only see Company A data
    print("\n🔒 Test 1: Company A Isolation")
    a_query = [1.0, 0.0, 0.0, 0.0, 0.0]  # Similar to Company A data
    a_results = await service.search_all_content(
        query_vector=a_query,
        top_k=10,
        namespace="company_A_tenant"
    )
    
    print(f"Company A search results: {len(a_results)}")
    for result in a_results:
        print(f"  - {result.id}: {result.metadata.get('company')} - {result.metadata.get('content')}")
    
    # Validate no cross-contamination
    a_companies = {result.metadata.get('company') for result in a_results}
    if a_companies == {"A"}:
        print("✅ Company A isolation maintained")
    else:
        print(f"❌ Company A isolation breach! Found companies: {a_companies}")
        return False
    
    # Test 2: Company B searches should only see Company B data
    print("\n🔒 Test 2: Company B Isolation")
    b_query = [0.0, 1.0, 0.0, 0.0, 0.0]  # Similar to Company B data
    b_results = await service.search_all_content(
        query_vector=b_query,
        top_k=10,
        namespace="company_B_tenant"
    )
    
    print(f"Company B search results: {len(b_results)}")
    for result in b_results:
        print(f"  - {result.id}: {result.metadata.get('company')} - {result.metadata.get('content')}")
    
    b_companies = {result.metadata.get('company') for result in b_results}
    if b_companies == {"B"}:
        print("✅ Company B isolation maintained")
    else:
        print(f"❌ Company B isolation breach! Found companies: {b_companies}")
        return False
    
    # Test 3: Company C searches should only see Company C data
    print("\n🔒 Test 3: Company C Isolation")
    c_query = [0.0, 0.0, 1.0, 0.0, 0.0]  # Similar to Company C data
    c_results = await service.search_all_content(
        query_vector=c_query,
        top_k=10,
        namespace="company_C_tenant"
    )
    
    print(f"Company C search results: {len(c_results)}")
    for result in c_results:
        print(f"  - {result.id}: {result.metadata.get('company')} - {result.metadata.get('content')}")
    
    c_companies = {result.metadata.get('company') for result in c_results}
    if c_companies == {"C"}:
        print("✅ Company C isolation maintained")
    else:
        print(f"❌ Company C isolation breach! Found companies: {c_companies}")
        return False
    
    # Test 4: Cross-namespace attack test
    print("\n🛡️ Test 4: Cross-Namespace Attack Simulation")
    
    # Try to search Company A namespace with Company B's most similar query
    attack_query = [0.0, 1.0, 0.0, 0.0, 0.0]  # Company B's pattern
    attack_results = await service.search_all_content(
        query_vector=attack_query,
        top_k=10,
        namespace="company_A_tenant"  # But searching A's namespace
    )
    
    print(f"Attack results (B query on A namespace): {len(attack_results)}")
    attack_companies = {result.metadata.get('company') for result in attack_results}
    
    if attack_companies == {"A"} or len(attack_companies) == 0:
        print("✅ Cross-namespace attack prevented")
    else:
        print(f"❌ Cross-namespace attack succeeded! Found companies: {attack_companies}")
        return False
    
    # Test 5: Empty namespace test
    print("\n📭 Test 5: Empty Namespace Isolation")
    empty_results = await service.search_all_content(
        query_vector=[1.0, 1.0, 1.0, 1.0, 1.0],
        top_k=10,
        namespace="empty_namespace_test"
    )
    
    if len(empty_results) == 0:
        print("✅ Empty namespace returns no results")
    else:
        print(f"❌ Empty namespace returned {len(empty_results)} results - data leak!")
        return False
    
    # Test 6: Null namespace test
    print("\n⚠️ Test 6: Null Namespace Behavior")
    try:
        null_results = await service.search_all_content(
            query_vector=[1.0, 1.0, 1.0, 1.0, 1.0],
            top_k=10,
            namespace=None
        )
        
        print(f"Null namespace search returned {len(null_results)} results")
        # This should either work (global search) or be prevented
        print("⚠️ Null namespace search allowed - ensure this is intended behavior")
        
    except Exception as e:
        print(f"✅ Null namespace search prevented: {str(e)}")
    
    print("\n✅ All namespace isolation tests passed!")
    return True

async def main():
    """Run namespace isolation tests."""
    success = await test_namespace_isolation()
    if success:
        print("\n🎯 Namespace isolation validated - No data leaks detected!")
        sys.exit(0)
    else:
        print("\n💥 CRITICAL SECURITY ISSUE: Namespace isolation failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())