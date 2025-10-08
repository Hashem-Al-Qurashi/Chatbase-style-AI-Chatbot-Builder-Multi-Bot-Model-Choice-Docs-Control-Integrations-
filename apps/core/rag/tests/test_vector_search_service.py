"""
Test VectorSearchService privacy filtering functionality.

Tests the first layer of privacy protection - database-level filtering
to ensure only appropriate sources are returned based on user permissions.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from ..vector_search_service import VectorSearchService, SearchResult, get_vector_search_service
from apps.core.vector_search import SearchScope, SearchConfig, SearchContext
from apps.core.document_processing import PrivacyLevel


class TestVectorSearchServicePrivacyFiltering:
    """Test privacy filtering in VectorSearchService."""
    
    @pytest.fixture
    def mock_vector_storage(self):
        """Mock vector storage backend."""
        return Mock()
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service."""
        service = Mock()
        service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        return service
    
    @pytest.fixture
    def sample_search_results(self):
        """Sample search results with mixed privacy levels."""
        return [
            Mock(
                content="This is citable public content",
                score=0.95,
                chunk_id="citable_1",
                document_id="doc_1",
                knowledge_base_id="kb_1",
                can_cite=True,
                citation_text="Public Document, Page 1",
                metadata={"privacy_level": "citable"}
            ),
            Mock(
                content="This is private confidential content",
                score=0.85,
                chunk_id="private_1",
                document_id="doc_2", 
                knowledge_base_id="kb_1",
                can_cite=False,
                citation_text=None,
                metadata={"privacy_level": "private"}
            ),
            Mock(
                content="Another citable source",
                score=0.80,
                chunk_id="citable_2",
                document_id="doc_3",
                knowledge_base_id="kb_1",
                can_cite=True,
                citation_text="Reference Manual, Section 2",
                metadata={"privacy_level": "citable"}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_privacy_filtering_citable_only(self, sample_search_results):
        """Test that filter_citable=True returns only citable sources."""
        
        with patch('apps.core.rag.vector_search_service.get_vector_storage'), \
             patch('apps.core.rag.vector_search_service.EmbeddingService'):
            
            search_service = VectorSearchService("test_chatbot")
            
            # Mock the RAG search service to return our test data
            with patch.object(search_service.rag_search_service, 'search_for_rag', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = (sample_search_results, {})
                
                # Test with citable filtering enabled
                results = await search_service.search(
                    query_embedding=[0.1] * 1536,
                    query_text="test query",
                    user_id="test_user",
                    top_k=10,
                    filter_citable=True
                )
                
                # Should only return citable results
                assert len(results) == 2, f"Expected 2 citable results, got {len(results)}"
                
                for result in results:
                    assert result.is_citable == True, f"Non-citable result found: {result.chunk_id}"
                    assert result.citation_text is not None, f"Missing citation for citable result: {result.chunk_id}"
                
                print("✅ PASS: filter_citable=True returns only citable sources")
    
    @pytest.mark.asyncio
    async def test_privacy_filtering_all_sources(self, sample_search_results):
        """Test that filter_citable=False returns both citable and private sources."""
        
        with patch('apps.core.rag.vector_search_service.get_vector_storage'), \
             patch('apps.core.rag.vector_search_service.EmbeddingService'):
            
            search_service = VectorSearchService("test_chatbot")
            
            with patch.object(search_service.rag_search_service, 'search_for_rag', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = (sample_search_results, {})
                
                # Test with citable filtering disabled
                results = await search_service.search(
                    query_embedding=[0.1] * 1536,
                    query_text="test query",
                    user_id="test_user",
                    top_k=10,
                    filter_citable=False
                )
                
                # Should return all results
                assert len(results) == 3, f"Expected 3 total results, got {len(results)}"
                
                # Check we have both types
                citable_count = sum(1 for r in results if r.is_citable)
                private_count = sum(1 for r in results if not r.is_citable)
                
                assert citable_count == 2, f"Expected 2 citable results, got {citable_count}"
                assert private_count == 1, f"Expected 1 private result, got {private_count}"
                
                print("✅ PASS: filter_citable=False returns both citable and private sources")
    
    @pytest.mark.asyncio
    async def test_search_with_query_text(self):
        """Test search_with_query_text method generates embedding correctly."""
        
        with patch('apps.core.rag.vector_search_service.get_vector_storage'), \
             patch('apps.core.rag.vector_search_service.EmbeddingService') as mock_embedding_service:
            
            # Setup mock embedding service
            mock_embedding_instance = Mock()
            mock_embedding_instance.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
            mock_embedding_service.return_value = mock_embedding_instance
            
            search_service = VectorSearchService("test_chatbot")
            search_service.embedding_service = mock_embedding_instance
            
            # Mock the search method
            with patch.object(search_service, 'search', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = []
                
                # Test search with query text
                await search_service.search_with_query_text(
                    query_text="test query",
                    user_id="test_user"
                )
                
                # Verify embedding was generated
                mock_embedding_instance.generate_embedding.assert_called_once_with("test query")
                
                # Verify search was called with embedding
                mock_search.assert_called_once()
                call_args = mock_search.call_args[1]
                assert call_args['query_embedding'] == [0.1] * 1536
                assert call_args['query_text'] == "test query"
                
                print("✅ PASS: search_with_query_text generates embedding correctly")
    
    @pytest.mark.asyncio
    async def test_user_access_controls(self, sample_search_results):
        """Test that user access controls are enforced properly."""
        
        with patch('apps.core.rag.vector_search_service.get_vector_storage'), \
             patch('apps.core.rag.vector_search_service.EmbeddingService'):
            
            search_service = VectorSearchService("test_chatbot")
            
            with patch.object(search_service.rag_search_service, 'search_for_rag', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = (sample_search_results, {})
                
                # Test search with specific user ID
                await search_service.search(
                    query_embedding=[0.1] * 1536,
                    query_text="test query",
                    user_id="specific_user",
                    filter_citable=True
                )
                
                # Verify the search was called with correct context
                call_args = mock_search.call_args[1]
                context = call_args['context']
                
                assert context.user_id == "specific_user", f"Wrong user ID in context: {context.user_id}"
                assert "test_chatbot" in context.knowledge_base_ids, "Chatbot ID not in knowledge base IDs"
                
                print("✅ PASS: User access controls enforced correctly")
    
    def test_backend_info_retrieval(self):
        """Test backend information retrieval."""
        
        with patch('apps.core.rag.vector_search_service.get_vector_storage') as mock_storage:
            mock_storage.return_value = Mock(__class__.__name__="MockVectorStorage")
            
            search_service = VectorSearchService("test_chatbot")
            
            info = search_service.get_backend_info()
            
            assert info['backend_type'] == "MockVectorStorage"
            assert info['chatbot_id'] == "test_chatbot"
            assert 'settings' in info
            
            print("✅ PASS: Backend info retrieval works correctly")
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check functionality."""
        
        with patch('apps.core.rag.vector_search_service.get_vector_storage'), \
             patch('apps.core.rag.vector_search_service.EmbeddingService'):
            
            search_service = VectorSearchService("test_chatbot")
            
            # Mock successful search for health check
            with patch.object(search_service, 'search', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = []
                
                health_status = await search_service.health_check()
                
                assert health_status['status'] == "healthy"
                assert 'response_time' in health_status
                assert health_status['chatbot_id'] == "test_chatbot"
                
                print("✅ PASS: Health check returns healthy status")
    
    @pytest.mark.asyncio 
    async def test_health_check_failure(self):
        """Test health check failure scenario."""
        
        with patch('apps.core.rag.vector_search_service.get_vector_storage'), \
             patch('apps.core.rag.vector_search_service.EmbeddingService'):
            
            search_service = VectorSearchService("test_chatbot")
            
            # Mock failed search for health check
            with patch.object(search_service, 'search', new_callable=AsyncMock) as mock_search:
                mock_search.side_effect = Exception("Health check failed")
                
                health_status = await search_service.health_check()
                
                assert health_status['status'] == "unhealthy"
                assert 'error' in health_status
                assert health_status['chatbot_id'] == "test_chatbot"
                
                print("✅ PASS: Health check detects and reports failures")
    
    def test_service_cache_management(self):
        """Test vector search service caching."""
        
        with patch('apps.core.rag.vector_search_service.get_vector_storage'), \
             patch('apps.core.rag.vector_search_service.EmbeddingService'):
            
            # Test service creation and caching
            service1 = get_vector_search_service("chatbot_1")
            service2 = get_vector_search_service("chatbot_1")
            service3 = get_vector_search_service("chatbot_2")
            
            # Same chatbot should return same instance
            assert service1 is service2, "Same chatbot should return cached instance"
            
            # Different chatbot should return different instance
            assert service1 is not service3, "Different chatbots should return different instances"
            
            # Test cache clearing
            from ..vector_search_service import clear_search_service_cache
            clear_search_service_cache()
            
            service4 = get_vector_search_service("chatbot_1")
            assert service1 is not service4, "Cache clear should create new instances"
            
            print("✅ PASS: Service cache management works correctly")


class TestVectorSearchPrivacyEdgeCases:
    """Test edge cases and error scenarios in privacy filtering."""
    
    @pytest.mark.asyncio
    async def test_empty_search_results(self):
        """Test handling of empty search results."""
        
        with patch('apps.core.rag.vector_search_service.get_vector_storage'), \
             patch('apps.core.rag.vector_search_service.EmbeddingService'):
            
            search_service = VectorSearchService("test_chatbot")
            
            with patch.object(search_service.rag_search_service, 'search_for_rag', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = ([], {})
                
                results = await search_service.search(
                    query_embedding=[0.1] * 1536,
                    query_text="test query",
                    user_id="test_user",
                    filter_citable=True
                )
                
                assert results == [], "Empty results should return empty list"
                print("✅ PASS: Empty search results handled correctly")
    
    @pytest.mark.asyncio
    async def test_all_private_sources_filtered(self):
        """Test scenario where all sources are private and get filtered out."""
        
        private_results = [
            Mock(
                content="Private content 1",
                score=0.9,
                chunk_id="private_1", 
                can_cite=False,
                metadata={"privacy_level": "private"}
            ),
            Mock(
                content="Private content 2",
                score=0.8,
                chunk_id="private_2",
                can_cite=False, 
                metadata={"privacy_level": "private"}
            )
        ]
        
        with patch('apps.core.rag.vector_search_service.get_vector_storage'), \
             patch('apps.core.rag.vector_search_service.EmbeddingService'):
            
            search_service = VectorSearchService("test_chatbot")
            
            with patch.object(search_service.rag_search_service, 'search_for_rag', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = (private_results, {})
                
                results = await search_service.search(
                    query_embedding=[0.1] * 1536,
                    query_text="test query",
                    user_id="test_user", 
                    filter_citable=True
                )
                
                assert len(results) == 0, "All private sources should be filtered out"
                print("✅ PASS: All private sources correctly filtered when filter_citable=True")


# Test execution function
def run_vector_search_tests():
    """Run all vector search service tests."""
    
    print("🧪 EXECUTING TEST 1: VectorSearchService Privacy Filtering")
    print("=" * 60)
    
    test_class = TestVectorSearchServicePrivacyFiltering()
    edge_test_class = TestVectorSearchPrivacyEdgeCases()
    
    # Mock data for testing
    sample_results = [
        Mock(content="Citable content", can_cite=True, chunk_id="c1", is_citable=True, citation_text="Source 1", metadata={}),
        Mock(content="Private content", can_cite=False, chunk_id="p1", is_citable=False, citation_text=None, metadata={}),
        Mock(content="Another citable", can_cite=True, chunk_id="c2", is_citable=True, citation_text="Source 2", metadata={})
    ]
    
    try:
        # Run each test
        asyncio.run(test_class.test_privacy_filtering_citable_only(sample_results))
        asyncio.run(test_class.test_privacy_filtering_all_sources(sample_results))
        asyncio.run(test_class.test_search_with_query_text())
        asyncio.run(test_class.test_user_access_controls(sample_results))
        test_class.test_backend_info_retrieval()
        asyncio.run(test_class.test_health_check())
        asyncio.run(test_class.test_health_check_failure())
        test_class.test_service_cache_management()
        asyncio.run(edge_test_class.test_empty_search_results())
        asyncio.run(edge_test_class.test_all_private_sources_filtered())
        
        print("\n🎉 ALL VECTOR SEARCH SERVICE TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        return False


if __name__ == "__main__":
    success = run_vector_search_tests()
    if success:
        print("✅ Test 1 COMPLETED: VectorSearchService privacy filtering validated")
    else:
        print("❌ Test 1 FAILED: Issues found in VectorSearchService")