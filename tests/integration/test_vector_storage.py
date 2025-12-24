#!/usr/bin/env python3
"""
Test script for vector storage functionality.
Tests both Pinecone and pgvector backends with fallback logic.
"""

import os
import sys
import asyncio
import random
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')

import django
django.setup()

from apps.core.vector_storage import (
    VectorStorageService, VectorStorageConfig, VectorSearchQuery,
    VectorSearchResult, PineconeBackend, PgVectorBackend,
    create_vector_storage
)


def generate_test_embedding(dimension: int = 1536) -> list:
    """Generate a random test embedding vector."""
    return [random.uniform(-1, 1) for _ in range(dimension)]


async def test_pgvector_backend():
    """Test PgVector backend functionality."""
    print("🧪 Testing PgVector Backend")
    print("=" * 40)
    
    try:
        # Create config for pgvector
        config = VectorStorageConfig(
            backend="pgvector",
            vector_dimension=1536,
            batch_size=10,
            enable_caching=True
        )
        
        # Initialize backend
        backend = PgVectorBackend(config)
        initialized = await backend.initialize()
        
        if not initialized:
            print("❌ PgVector backend initialization failed")
            return False
        
        print("✅ PgVector backend initialized successfully")
        
        # Test data
        test_vectors = [
            ("test_doc_1", generate_test_embedding(), {"content": "First test document", "type": "test"}),
            ("test_doc_2", generate_test_embedding(), {"content": "Second test document", "type": "test"}),
            ("test_doc_3", generate_test_embedding(), {"content": "Third test document", "type": "test"}),
        ]
        
        # Test upsert
        print("\n🔄 Testing vector upsert...")
        upsert_success = await backend.upsert_vectors(test_vectors, namespace="test")
        if upsert_success:
            print(f"✅ Successfully upserted {len(test_vectors)} vectors")
        else:
            print("❌ Vector upsert failed")
            return False
        
        # Test search
        print("\n🔄 Testing vector search...")
        query = VectorSearchQuery(
            vector=test_vectors[0][1],  # Use first vector for similarity search
            top_k=2,
            namespace="test"
        )
        
        search_results = await backend.search_vectors(query)
        print(f"✅ Found {len(search_results)} similar vectors")
        
        if search_results:
            best_match = search_results[0]
            print(f"   📊 Best match ID: {best_match.id}")
            print(f"   📊 Similarity score: {best_match.score:.4f}")
            print(f"   📄 Content: {best_match.metadata.get('content', 'N/A')}")
        
        # Test stats
        print("\n🔄 Testing storage stats...")
        stats = await backend.get_stats()
        print(f"✅ Storage stats retrieved:")
        print(f"   📊 Backend: {stats.get('backend')}")
        print(f"   📊 Total vectors: {stats.get('total_vectors')}")
        print(f"   📊 Table size: {stats.get('table_size')}")
        
        # Test deletion
        print("\n🔄 Testing vector deletion...")
        delete_success = await backend.delete_vectors(
            ["test_doc_1", "test_doc_2", "test_doc_3"], 
            namespace="test"
        )
        if delete_success:
            print("✅ Test vectors deleted successfully")
        else:
            print("❌ Vector deletion failed")
        
        return True
        
    except Exception as e:
        print(f"❌ PgVector backend test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_pinecone_backend_mock():
    """Test Pinecone backend with mocked responses."""
    print("\n🧪 Testing Pinecone Backend (Mocked)")
    print("=" * 45)
    
    try:
        # Mock pinecone module
        mock_pinecone = MagicMock()
        mock_pinecone.list_indexes.return_value = ["chatbot-embeddings"]
        
        # Mock index
        mock_index = MagicMock()
        mock_pinecone.Index.return_value = mock_index
        
        # Mock upsert response
        mock_index.upsert.return_value = {"upserted_count": 3}
        
        # Mock search response
        mock_match = MagicMock()
        mock_match.id = "test_doc_1"
        mock_match.score = 0.95
        mock_match.metadata = {"content": "First test document", "type": "test"}
        mock_match.values = None
        
        mock_search_response = MagicMock()
        mock_search_response.matches = [mock_match]
        mock_index.query.return_value = mock_search_response
        
        # Mock delete response
        mock_index.delete.return_value = {"deleted_count": 3}
        
        # Mock stats response  
        mock_stats = MagicMock()
        mock_stats.total_vector_count = 1000
        mock_stats.index_fullness = 0.1
        mock_stats.dimension = 1536
        mock_stats.namespaces = {"test": {"vector_count": 3}}
        mock_index.describe_index_stats.return_value = mock_stats
        
        with patch.dict('sys.modules', {'pinecone': mock_pinecone}):
            # Create config for pinecone
            config = VectorStorageConfig(
                backend="pinecone",
                pinecone_api_key="test-key",
                pinecone_environment="test-env",
                pinecone_index_name="chatbot-embeddings"
            )
            
            # Initialize backend
            backend = PineconeBackend(config)
            initialized = await backend.initialize()
            
            if not initialized:
                print("❌ Pinecone backend initialization failed")
                return False
            
            print("✅ Pinecone backend initialized successfully")
            
            # Test data
            test_vectors = [
                ("test_doc_1", generate_test_embedding(), {"content": "First test document", "type": "test"}),
                ("test_doc_2", generate_test_embedding(), {"content": "Second test document", "type": "test"}),
                ("test_doc_3", generate_test_embedding(), {"content": "Third test document", "type": "test"}),
            ]
            
            # Test upsert
            print("\n🔄 Testing vector upsert...")
            upsert_success = await backend.upsert_vectors(test_vectors, namespace="test")
            if upsert_success:
                print(f"✅ Successfully upserted {len(test_vectors)} vectors")
            else:
                print("❌ Vector upsert failed")
                return False
            
            # Test search
            print("\n🔄 Testing vector search...")
            query = VectorSearchQuery(
                vector=test_vectors[0][1],
                top_k=2,
                namespace="test"
            )
            
            search_results = await backend.search_vectors(query)
            print(f"✅ Found {len(search_results)} similar vectors")
            
            if search_results:
                best_match = search_results[0]
                print(f"   📊 Best match ID: {best_match.id}")
                print(f"   📊 Similarity score: {best_match.score:.4f}")
                print(f"   📄 Content: {best_match.metadata.get('content', 'N/A')}")
            
            # Test stats
            print("\n🔄 Testing storage stats...")
            stats = await backend.get_stats()
            print(f"✅ Storage stats retrieved:")
            print(f"   📊 Backend: {stats.get('backend')}")
            print(f"   📊 Total vectors: {stats.get('total_vectors')}")
            print(f"   📊 Index fullness: {stats.get('index_fullness')}")
            print(f"   📊 Dimension: {stats.get('dimension')}")
            
            # Test deletion
            print("\n🔄 Testing vector deletion...")
            delete_success = await backend.delete_vectors(
                ["test_doc_1", "test_doc_2", "test_doc_3"], 
                namespace="test"
            )
            if delete_success:
                print("✅ Test vectors deleted successfully")
            else:
                print("❌ Vector deletion failed")
            
            return True
        
    except Exception as e:
        print(f"❌ Pinecone backend test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_vector_storage_service():
    """Test the main VectorStorageService with auto-fallback."""
    print("\n🧪 Testing Vector Storage Service")
    print("=" * 45)
    
    try:
        # Create service with auto backend selection
        config = VectorStorageConfig(
            backend="auto",
            pinecone_api_key="",  # No key to force fallback
            enable_caching=True,
            batch_size=5
        )
        
        service = VectorStorageService(config)
        initialized = await service.initialize()
        
        if not initialized:
            print("❌ Vector storage service initialization failed")
            return False
        
        print(f"✅ Vector storage service initialized with {service.backend_name} backend")
        
        # Test embeddings
        test_embeddings = [
            ("doc_1", generate_test_embedding(), {"content": "Vector storage test document 1", "source": "test"}),
            ("doc_2", generate_test_embedding(), {"content": "Vector storage test document 2", "source": "test"}),
            ("doc_3", generate_test_embedding(), {"content": "Vector storage test document 3", "source": "test"}),
            ("doc_4", generate_test_embedding(), {"content": "Vector storage test document 4", "source": "test"}),
            ("doc_5", generate_test_embedding(), {"content": "Vector storage test document 5", "source": "test"}),
        ]
        
        # Test storage
        print("\n🔄 Testing embedding storage...")
        store_success = await service.store_embeddings(test_embeddings, namespace="service_test")
        if store_success:
            print(f"✅ Successfully stored {len(test_embeddings)} embeddings")
        else:
            print("❌ Embedding storage failed")
            return False
        
        # Test search
        print("\n🔄 Testing similarity search...")
        search_results = await service.search_similar(
            query_vector=test_embeddings[0][1],
            top_k=3,
            namespace="service_test"
        )
        
        print(f"✅ Found {len(search_results)} similar embeddings")
        for i, result in enumerate(search_results[:2]):
            print(f"   📊 Result {i+1}: {result.id} (score: {result.score:.4f})")
            print(f"      📄 Content: {result.metadata.get('content', 'N/A')[:50]}...")
        
        # Test cached search (should be faster)
        print("\n🔄 Testing cached search...")
        cached_results = await service.search_similar(
            query_vector=test_embeddings[0][1],
            top_k=3,
            namespace="service_test"
        )
        print(f"✅ Cached search returned {len(cached_results)} results")
        
        # Test stats
        print("\n🔄 Testing service stats...")
        stats = await service.get_storage_stats()
        print(f"✅ Service stats retrieved:")
        print(f"   📊 Backend: {stats.get('config', {}).get('backend')}")
        print(f"   📊 Caching enabled: {stats.get('config', {}).get('caching_enabled')}")
        print(f"   📊 Batch size: {stats.get('config', {}).get('batch_size')}")
        if 'total_vectors' in stats:
            print(f"   📊 Total vectors: {stats.get('total_vectors')}")
        
        # Test deletion
        print("\n🔄 Testing embedding deletion...")
        delete_ids = ["doc_1", "doc_2", "doc_3", "doc_4", "doc_5"]
        delete_success = await service.delete_embeddings(delete_ids, namespace="service_test")
        if delete_success:
            print("✅ Test embeddings deleted successfully")
        else:
            print("❌ Embedding deletion failed")
        
        return True
        
    except Exception as e:
        print(f"❌ Vector storage service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_convenience_function():
    """Test the convenience create_vector_storage function."""
    print("\n🧪 Testing Convenience Function")
    print("=" * 40)
    
    try:
        # Test auto backend
        service = await create_vector_storage("auto")
        print(f"✅ Auto backend created: {service.backend_name}")
        
        # Test pgvector backend
        pgvector_service = await create_vector_storage("pgvector")
        print(f"✅ PgVector backend created: {pgvector_service.backend_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Convenience function test failed: {e}")
        return False


async def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n🧪 Testing Edge Cases")
    print("=" * 30)
    
    try:
        # Test empty embeddings
        service = await create_vector_storage("pgvector")
        
        print("🔄 Testing empty embeddings list...")
        empty_success = await service.store_embeddings([], namespace="empty_test")
        print(f"✅ Empty embeddings handled: {empty_success}")
        
        # Test search with invalid vector
        print("🔄 Testing search with wrong dimension...")
        try:
            wrong_dim_results = await service.search_similar(
                query_vector=[0.1] * 10,  # Wrong dimension
                top_k=5,
                namespace="empty_test"
            )
            print(f"⚠️ Search with wrong dimension returned {len(wrong_dim_results)} results")
        except Exception as e:
            print(f"✅ Correctly handled wrong dimension: {type(e).__name__}")
        
        # Test search in non-existent namespace
        print("🔄 Testing search in non-existent namespace...")
        no_results = await service.search_similar(
            query_vector=generate_test_embedding(),
            top_k=5,
            namespace="nonexistent"
        )
        print(f"✅ Non-existent namespace search returned {len(no_results)} results")
        
        return True
        
    except Exception as e:
        print(f"❌ Edge cases test failed: {e}")
        return False


async def main():
    """Run all vector storage tests."""
    print("🚀 Starting Vector Storage System Tests")
    print("=" * 60)
    
    test_results = []
    
    # Test PgVector backend
    pgvector_result = await test_pgvector_backend()
    test_results.append(("PgVector Backend", pgvector_result))
    
    # Test Pinecone backend (mocked)
    pinecone_result = await test_pinecone_backend_mock()
    test_results.append(("Pinecone Backend (Mocked)", pinecone_result))
    
    # Test main service
    service_result = await test_vector_storage_service()
    test_results.append(("Vector Storage Service", service_result))
    
    # Test convenience function
    convenience_result = await test_convenience_function()
    test_results.append(("Convenience Function", convenience_result))
    
    # Test edge cases
    edge_cases_result = await test_edge_cases()
    test_results.append(("Edge Cases", edge_cases_result))
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 40)
    passed = 0
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Tests passed: {passed}/{len(test_results)}")
    
    if passed == len(test_results):
        print("🎉 All vector storage tests passed successfully!")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")


if __name__ == "__main__":
    asyncio.run(main())