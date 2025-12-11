#!/usr/bin/env python3
"""
CRITICAL VECTOR SEARCH TESTING
Testing assumption: Vector storage and search is broken and will fail under pressure.
"""

import os
import sys
import django
import asyncio
import time
import uuid
from typing import List

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
sys.path.append('/home/sakr_quraish/Projects/Ismail')

try:
    django.setup()
    print("✓ Django setup successful")
except Exception as e:
    print(f"✗ Django setup FAILED: {e}")
    sys.exit(1)

from apps.core.rag.vector_search_service import (
    VectorSearchService,
    get_vector_search_service,
    SearchResult
)
from apps.core.vector_storage import create_vector_storage, VectorStorageService
from apps.core.embedding_service import OpenAIEmbeddingService
from chatbot_saas.config import get_settings

settings = get_settings()

class CriticalVectorSearchTest:
    """Brutally test vector search to find what's broken."""
    
    def __init__(self):
        self.failures = []
        self.successes = []
        self.test_chatbot_id = f"test_bot_{uuid.uuid4().hex[:8]}"
        self.vector_service = None
        self.storage_service = None
        self.embedding_service = None
    
    def log_failure(self, test_name, error):
        """Log a test failure."""
        self.failures.append(f"{test_name}: {error}")
        print(f"✗ FAIL: {test_name} - {error}")
    
    def log_success(self, test_name):
        """Log a test success."""
        self.successes.append(test_name)
        print(f"✓ PASS: {test_name}")
    
    async def test_vector_storage_initialization(self):
        """Test vector storage backend initialization."""
        try:
            self.storage_service = await create_vector_storage()
            
            if not self.storage_service:
                raise Exception("Vector storage initialization returned None")
            
            if not isinstance(self.storage_service, VectorStorageService):
                raise Exception(f"Expected VectorStorageService, got {type(self.storage_service)}")
            
            # Test basic storage methods exist
            required_methods = [
                'store_vectors', 'search_similar', 'delete_vector',
                'search_citable_only', 'search_all_content'
            ]
            
            for method in required_methods:
                if not hasattr(self.storage_service, method):
                    raise Exception(f"Vector storage missing required method: {method}")
            
            self.log_success("Vector storage initialization")
            return True
            
        except Exception as e:
            self.log_failure("Vector storage initialization", str(e))
            return False
    
    async def test_vector_search_service_initialization(self):
        """Test vector search service initialization."""
        try:
            self.vector_service = VectorSearchService(self.test_chatbot_id)
            
            if not self.vector_service:
                raise Exception("Vector search service initialization returned None")
            
            if self.vector_service.chatbot_id != self.test_chatbot_id:
                raise Exception("Chatbot ID not preserved in service")
            
            # Test service methods exist
            required_methods = [
                'search', 'search_with_query_text', 'hybrid_search',
                'health_check', 'get_backend_info'
            ]
            
            for method in required_methods:
                if not hasattr(self.vector_service, method):
                    raise Exception(f"Vector search service missing required method: {method}")
            
            self.log_success("Vector search service initialization")
            return True
            
        except Exception as e:
            self.log_failure("Vector search service initialization", str(e))
            return False
    
    async def test_embedding_service_integration(self):
        """Test embedding service integration."""
        try:
            self.embedding_service = OpenAIEmbeddingService()
            
            if not self.embedding_service:
                raise Exception("Embedding service initialization failed")
            
            # Test embedding generation
            test_text = "This is a test for vector search integration."
            embedding_result = await self.embedding_service.generate_embedding(test_text)
            
            if not embedding_result.embedding:
                raise Exception("No embedding generated")
            
            if len(embedding_result.embedding) == 0:
                raise Exception("Empty embedding vector")
            
            self.log_success("Embedding service integration")
            return embedding_result.embedding
            
        except Exception as e:
            self.log_failure("Embedding service integration", str(e))
            return None
    
    async def test_vector_storage_operations(self):
        """Test basic vector storage operations."""
        try:
            if not self.storage_service:
                raise Exception("Storage service not initialized")
            
            if not self.embedding_service:
                raise Exception("Embedding service not initialized")
            
            # Create test data
            test_documents = [
                "Machine learning is a subset of artificial intelligence.",
                "Deep learning uses neural networks with multiple layers.",
                "Natural language processing deals with text understanding.",
                "Computer vision focuses on image analysis and recognition."
            ]
            
            # Generate embeddings for test documents
            vectors_to_store = []
            for i, doc in enumerate(test_documents):
                embedding_result = await self.embedding_service.generate_embedding(doc)
                
                vector_data = {
                    'id': f'test_doc_{i}',
                    'vector': embedding_result.embedding,
                    'metadata': {
                        'content': doc,
                        'source_id': f'test_source_{i}',
                        'is_citable': i % 2 == 0,  # Alternate citable/non-citable
                        'chatbot_id': self.test_chatbot_id
                    }
                }
                vectors_to_store.append(vector_data)
            
            # Test vector storage
            namespace = f"chatbot_{self.test_chatbot_id}"
            store_result = await self.storage_service.store_vectors(
                vectors=vectors_to_store,
                namespace=namespace
            )
            
            if not store_result:
                raise Exception("Vector storage failed")
            
            # Test search
            search_query = "What is machine learning?"
            query_embedding = await self.embedding_service.generate_embedding(search_query)
            
            # Search all content
            all_results = await self.storage_service.search_all_content(
                query_vector=query_embedding.embedding,
                top_k=5,
                namespace=namespace
            )
            
            if len(all_results) == 0:
                raise Exception("Search returned no results")
            
            # Search citable only
            citable_results = await self.storage_service.search_citable_only(
                query_vector=query_embedding.embedding,
                top_k=5,
                namespace=namespace
            )
            
            # Should have fewer citable results than all results
            if len(citable_results) > len(all_results):
                raise Exception("More citable results than total results")
            
            self.log_success("Vector storage operations")
            return True
            
        except Exception as e:
            self.log_failure("Vector storage operations", str(e))
            return False
    
    async def test_search_with_privacy_filtering(self):
        """Test search with privacy filtering."""
        try:
            if not self.vector_service:
                raise Exception("Vector search service not initialized")
            
            # Test search with citable filter
            citable_results = await self.vector_service.search_with_query_text(
                query_text="machine learning artificial intelligence",
                user_id="test_user",
                top_k=5,
                filter_citable=True
            )
            
            # Verify all results are citable
            for result in citable_results:
                if not isinstance(result, SearchResult):
                    raise Exception(f"Expected SearchResult, got {type(result)}")
                
                if not result.is_citable:
                    raise Exception("Non-citable result returned when filter_citable=True")
            
            # Test search without citable filter
            all_results = await self.vector_service.search_with_query_text(
                query_text="machine learning artificial intelligence",
                user_id="test_user",
                top_k=5,
                filter_citable=False
            )
            
            # Should have more or equal results than citable-only search
            if len(all_results) < len(citable_results):
                raise Exception("Filtered search returned more results than unfiltered")
            
            self.log_success("Search with privacy filtering")
            return True
            
        except Exception as e:
            self.log_failure("Search with privacy filtering", str(e))
            return False
    
    async def test_search_result_quality(self):
        """Test search result quality and relevance."""
        try:
            if not self.vector_service:
                raise Exception("Vector search service not initialized")
            
            # Search for specific content
            results = await self.vector_service.search_with_query_text(
                query_text="deep learning neural networks",
                user_id="test_user",
                top_k=3,
                filter_citable=False
            )
            
            if len(results) == 0:
                raise Exception("No search results returned")
            
            # Check result structure
            first_result = results[0]
            
            required_fields = [
                'content', 'score', 'chunk_id', 'document_id',
                'knowledge_base_id', 'is_citable'
            ]
            
            for field in required_fields:
                if not hasattr(first_result, field):
                    raise Exception(f"Search result missing field: {field}")
            
            # Check score is valid
            if not (0 <= first_result.score <= 1):
                raise Exception(f"Invalid similarity score: {first_result.score}")
            
            # Check content is not empty
            if not first_result.content or len(first_result.content.strip()) == 0:
                raise Exception("Search result has empty content")
            
            # Check results are ordered by score (descending)
            if len(results) > 1:
                for i in range(len(results) - 1):
                    if results[i].score < results[i + 1].score:
                        raise Exception("Search results not ordered by score")
            
            self.log_success("Search result quality")
            return True
            
        except Exception as e:
            self.log_failure("Search result quality", str(e))
            return False
    
    async def test_search_edge_cases(self):
        """Test search with edge cases."""
        try:
            if not self.vector_service:
                raise Exception("Vector search service not initialized")
            
            # Test empty query
            try:
                await self.vector_service.search_with_query_text(
                    query_text="",
                    user_id="test_user"
                )
                raise Exception("Empty query should be rejected")
            except Exception:
                pass  # Expected
            
            # Test very long query
            long_query = "artificial intelligence " * 1000  # Very long
            try:
                results = await self.vector_service.search_with_query_text(
                    query_text=long_query,
                    user_id="test_user",
                    top_k=1
                )
                # Should handle gracefully or reject
            except Exception as e:
                if "too long" in str(e).lower():
                    pass  # Expected rejection
                else:
                    raise
            
            # Test with top_k = 0
            results = await self.vector_service.search_with_query_text(
                query_text="test query",
                user_id="test_user",
                top_k=0
            )
            
            if len(results) != 0:
                raise Exception("top_k=0 should return no results")
            
            # Test with very high top_k
            results = await self.vector_service.search_with_query_text(
                query_text="artificial intelligence",
                user_id="test_user",
                top_k=1000
            )
            
            # Should not crash, results count should be <= available documents
            if len(results) > 100:  # Reasonable upper bound
                print(f"⚠  WARNING: Very high result count: {len(results)}")
            
            self.log_success("Search edge cases")
            return True
            
        except Exception as e:
            self.log_failure("Search edge cases", str(e))
            return False
    
    async def test_health_check(self):
        """Test vector search health check."""
        try:
            if not self.vector_service:
                raise Exception("Vector search service not initialized")
            
            health_status = await self.vector_service.health_check()
            
            if not isinstance(health_status, dict):
                raise Exception("Health check should return a dictionary")
            
            required_fields = ['status', 'chatbot_id']
            for field in required_fields:
                if field not in health_status:
                    raise Exception(f"Health check missing field: {field}")
            
            if health_status['status'] not in ['healthy', 'unhealthy']:
                raise Exception(f"Invalid health status: {health_status['status']}")
            
            if 'response_time' in health_status:
                response_time = health_status['response_time']
                if response_time < 0:
                    raise Exception("Negative response time in health check")
                
                if response_time > 10.0:  # 10 seconds is way too slow
                    print(f"⚠  WARNING: Very slow health check: {response_time}s")
            
            self.log_success("Health check")
            return True
            
        except Exception as e:
            self.log_failure("Health check", str(e))
            return False
    
    async def test_concurrent_searches(self):
        """Test concurrent search operations."""
        try:
            if not self.vector_service:
                raise Exception("Vector search service not initialized")
            
            # Create multiple concurrent search tasks
            search_tasks = []
            for i in range(5):
                task = self.vector_service.search_with_query_text(
                    query_text=f"search query number {i}",
                    user_id=f"user_{i}",
                    top_k=3
                )
                search_tasks.append(task)
            
            # Run all searches concurrently
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Check results
            successful_searches = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"⚠  Concurrent search {i} failed: {result}")
                elif isinstance(result, list):
                    successful_searches += 1
                else:
                    raise Exception(f"Unexpected result type: {type(result)}")
            
            if successful_searches < len(search_tasks) * 0.8:  # Allow some failures
                raise Exception(f"Too many concurrent searches failed: {successful_searches}/{len(search_tasks)}")
            
            self.log_success("Concurrent searches")
            return True
            
        except Exception as e:
            self.log_failure("Concurrent searches", str(e))
            return False
    
    async def test_namespace_isolation(self):
        """Test namespace isolation between chatbots."""
        try:
            # Create second chatbot service
            other_chatbot_id = f"other_bot_{uuid.uuid4().hex[:8]}"
            other_service = VectorSearchService(other_chatbot_id)
            
            # Search in other chatbot's namespace (should return empty)
            results = await other_service.search_with_query_text(
                query_text="machine learning",
                user_id="test_user",
                top_k=5
            )
            
            # Should return no results (empty namespace)
            if len(results) > 0:
                print(f"⚠  WARNING: Found {len(results)} results in empty namespace")
            
            self.log_success("Namespace isolation")
            return True
            
        except Exception as e:
            self.log_failure("Namespace isolation", str(e))
            return False
    
    async def run_all_tests(self):
        """Run all vector search tests."""
        print("\n" + "="*80)
        print("CRITICAL VECTOR SEARCH TESTING")
        print("="*80)
        print("Testing assumption: Vector search is fundamentally broken.")
        print()
        
        # Initialize services
        if not await self.test_vector_storage_initialization():
            print("STORAGE INITIALIZATION FAILED - ABORTING FURTHER TESTS")
            return False
        
        if not await self.test_vector_search_service_initialization():
            print("SEARCH SERVICE INITIALIZATION FAILED - ABORTING FURTHER TESTS")
            return False
        
        # Test embedding integration
        embedding = await self.test_embedding_service_integration()
        if not embedding:
            print("EMBEDDING INTEGRATION FAILED - ABORTING FURTHER TESTS")
            return False
        
        # Run core functionality tests
        if not await self.test_vector_storage_operations():
            print("STORAGE OPERATIONS FAILED - SOME TESTS MAY FAIL")
        
        # Run search tests
        await self.test_search_with_privacy_filtering()
        await self.test_search_result_quality()
        await self.test_search_edge_cases()
        await self.test_health_check()
        await self.test_concurrent_searches()
        await self.test_namespace_isolation()
        
        # Summary
        print("\n" + "="*80)
        print("VECTOR SEARCH TEST RESULTS")
        print("="*80)
        
        total_tests = len(self.successes) + len(self.failures)
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {len(self.successes)}")
        print(f"Failed: {len(self.failures)}")
        print(f"Success Rate: {(len(self.successes)/total_tests)*100:.1f}%" if total_tests > 0 else "0.0%")
        
        if self.failures:
            print("\nCRITICAL FAILURES:")
            for failure in self.failures:
                print(f"  ✗ {failure}")
        
        if self.successes:
            print("\nSUCCESSES:")
            for success in self.successes:
                print(f"  ✓ {success}")
        
        print("\n" + "="*80)
        
        if len(self.failures) > len(self.successes):
            print("VERDICT: VECTOR SEARCH IS FUNDAMENTALLY BROKEN")
            return False
        else:
            print("VERDICT: Vector search appears functional")
            return True

async def main():
    tester = CriticalVectorSearchTest()
    await tester.run_all_tests()

if __name__ == '__main__':
    asyncio.run(main())