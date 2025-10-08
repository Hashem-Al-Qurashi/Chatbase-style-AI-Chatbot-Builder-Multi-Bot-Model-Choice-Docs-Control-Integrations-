"""
Test VectorSearchService privacy filtering functionality.

Tests the first layer of privacy protection - database-level filtering  
to ensure only appropriate sources are returned based on user permissions.

CRITICAL: This test validates Layer 1 of the three-layer privacy protection system.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock


class TestVectorSearchServicePrivacyFiltering:
    """Test privacy filtering in VectorSearchService."""
    
    @pytest.mark.asyncio
    async def test_citable_only_filtering(self):
        """Test that filter_citable=True returns only citable sources."""
        
        # Mock search results with mixed privacy levels  
        mock_results = [
            Mock(
                content="This is citable content",
                score=0.95,
                chunk_id="citable_1",
                document_id="doc_1", 
                knowledge_base_id="kb_1",
                can_cite=True,
                citation_text="Public Document",
                metadata={"privacy_level": "citable"}
            ),
            Mock(
                content="This is private content",
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
                citation_text="Reference Manual",
                metadata={"privacy_level": "citable"}
            )
        ]
        
        # Mock dependencies to isolate VectorSearchService
        with patch('apps.core.rag.vector_search_service.create_vector_storage'), \
             patch('apps.core.rag.vector_search_service.OpenAIEmbeddingService'), \
             patch('apps.core.rag.vector_search_service.RAGSearchService') as mock_rag_service:
            
            # Setup mock RAG service
            mock_rag_instance = Mock()
            mock_rag_instance.search_for_rag = AsyncMock(return_value=(mock_results, {}))
            mock_rag_service.return_value = mock_rag_instance
            
            # Import after mocking to avoid import errors
            from apps.core.rag.vector_search_service import VectorSearchService
            
            # Initialize service
            search_service = VectorSearchService("test_chatbot")
            search_service.rag_search_service = mock_rag_instance
            
            # Execute test: Search with citable filtering
            results = await search_service.search(
                query_embedding=[0.1] * 1536,
                query_text="test query",
                user_id="test_user",
                top_k=10,
                filter_citable=True
            )
            
            # Validate results
            assert len(results) == 2, f"Expected 2 citable results, got {len(results)}"
            
            for result in results:
                assert result.is_citable == True, f"Non-citable result found: {result.chunk_id}"
                assert result.citation_text is not None, f"Missing citation: {result.chunk_id}"
            
            print("✅ PASS: filter_citable=True returns only citable sources")
    
    @pytest.mark.asyncio
    async def test_all_sources_when_not_filtering(self):
        """Test that filter_citable=False returns both citable and private sources."""
        
        # Mock search results
        mock_results = [
            Mock(content="Citable", can_cite=True, chunk_id="c1", is_citable=True, citation_text="Source 1", metadata={}),
            Mock(content="Private", can_cite=False, chunk_id="p1", is_citable=False, citation_text=None, metadata={}),
        ]
        
        with patch('apps.core.rag.vector_search_service.create_vector_storage'), \
             patch('apps.core.rag.vector_search_service.OpenAIEmbeddingService'), \
             patch('apps.core.rag.vector_search_service.RAGSearchService') as mock_rag_service:
            
            mock_rag_instance = Mock()
            mock_rag_instance.search_for_rag = AsyncMock(return_value=(mock_results, {}))
            mock_rag_service.return_value = mock_rag_instance
            
            from apps.core.rag.vector_search_service import VectorSearchService
            
            search_service = VectorSearchService("test_chatbot")
            search_service.rag_search_service = mock_rag_instance
            
            # Execute test: Search without filtering
            results = await search_service.search(
                query_embedding=[0.1] * 1536,
                query_text="test query", 
                user_id="test_user",
                filter_citable=False
            )
            
            # Validate both types returned
            assert len(results) == 2, f"Expected 2 total results, got {len(results)}"
            
            citable_count = sum(1 for r in results if r.is_citable)
            private_count = sum(1 for r in results if not r.is_citable)
            
            assert citable_count == 1, f"Expected 1 citable, got {citable_count}"
            assert private_count == 1, f"Expected 1 private, got {private_count}"
            
            print("✅ PASS: filter_citable=False returns both source types")
    
    @pytest.mark.asyncio
    async def test_user_access_controls(self):
        """Test user access controls are enforced."""
        
        with patch('apps.core.rag.vector_search_service.create_vector_storage'), \
             patch('apps.core.rag.vector_search_service.OpenAIEmbeddingService'), \
             patch('apps.core.rag.vector_search_service.RAGSearchService') as mock_rag_service:
            
            mock_rag_instance = Mock()
            mock_rag_instance.search_for_rag = AsyncMock(return_value=([], {}))
            mock_rag_service.return_value = mock_rag_instance
            
            from apps.core.rag.vector_search_service import VectorSearchService
            
            search_service = VectorSearchService("test_chatbot")
            search_service.rag_search_service = mock_rag_instance
            
            # Execute search
            await search_service.search(
                query_embedding=[0.1] * 1536,
                query_text="test query",
                user_id="specific_user_123"
            )
            
            # Verify context was created with correct user ID
            call_args = mock_rag_instance.search_for_rag.call_args[1]
            context = call_args['context']
            
            assert context.user_id == "specific_user_123", f"Wrong user ID: {context.user_id}"
            assert "test_chatbot" in context.knowledge_base_ids, "Chatbot ID missing"
            
            print("✅ PASS: User access controls enforced correctly")
    
    def test_service_caching_functionality(self):
        """Test service instance caching works correctly."""
        
        with patch('apps.core.rag.vector_search_service.get_vector_storage'), \
             patch('apps.core.rag.vector_search_service.EmbeddingService'):
            
            from apps.core.rag.vector_search_service import get_vector_search_service, clear_search_service_cache
            
            # Test caching
            service1 = get_vector_search_service("chatbot_1")
            service2 = get_vector_search_service("chatbot_1") 
            
            assert service1 is service2, "Same chatbot should return cached instance"
            
            # Test different chatbots get different instances
            service3 = get_vector_search_service("chatbot_2")
            assert service1 is not service3, "Different chatbots should get different instances"
            
            # Test cache clearing
            clear_search_service_cache()
            service4 = get_vector_search_service("chatbot_1")
            assert service1 is not service4, "Cache clear should create new instances"
            
            print("✅ PASS: Service caching works correctly")
    
    @pytest.mark.asyncio
    async def test_health_check_functionality(self):
        """Test health check reports correct status."""
        
        with patch('apps.core.rag.vector_search_service.get_vector_storage'), \
             patch('apps.core.rag.vector_search_service.EmbeddingService'):
            
            from apps.core.rag.vector_search_service import VectorSearchService
            
            search_service = VectorSearchService("test_chatbot")
            
            # Mock successful health check
            with patch.object(search_service, 'search', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = []
                
                health = await search_service.health_check()
                
                assert health['status'] == "healthy", f"Expected healthy, got {health['status']}"
                assert 'response_time' in health, "Missing response_time in health check"
                assert health['chatbot_id'] == "test_chatbot", "Wrong chatbot_id in health check"
                
                print("✅ PASS: Health check reports correct healthy status")
    
    @pytest.mark.asyncio
    async def test_health_check_failure_detection(self):
        """Test health check detects failures correctly."""
        
        with patch('apps.core.rag.vector_search_service.get_vector_storage'), \
             patch('apps.core.rag.vector_search_service.EmbeddingService'):
            
            from apps.core.rag.vector_search_service import VectorSearchService
            
            search_service = VectorSearchService("test_chatbot")
            
            # Mock failed health check
            with patch.object(search_service, 'search', new_callable=AsyncMock) as mock_search:
                mock_search.side_effect = Exception("Service unavailable")
                
                health = await search_service.health_check()
                
                assert health['status'] == "unhealthy", f"Expected unhealthy, got {health['status']}"
                assert 'error' in health, "Missing error info in unhealthy status"
                
                print("✅ PASS: Health check detects failures correctly")


# Test execution script
def run_vector_search_tests():
    """Execute all VectorSearchService tests systematically."""
    
    print("🧪 EXECUTING TEST 1: VectorSearchService Privacy Filtering")
    print("=" * 60)
    
    test_instance = TestVectorSearchServicePrivacyFiltering()
    
    try:
        # Execute each test method
        print("\n1.1 Testing citable-only filtering...")
        asyncio.run(test_instance.test_citable_only_filtering())
        
        print("\n1.2 Testing all sources when not filtering...")
        asyncio.run(test_instance.test_all_sources_when_not_filtering()) 
        
        print("\n1.3 Testing user access controls...")
        asyncio.run(test_instance.test_user_access_controls())
        
        print("\n1.4 Testing service caching...")
        test_instance.test_service_caching_functionality()
        
        print("\n1.5 Testing health check functionality...")
        asyncio.run(test_instance.test_health_check_functionality())
        
        print("\n1.6 Testing health check failure detection...")
        asyncio.run(test_instance.test_health_check_failure_detection())
        
        print("\n" + "=" * 60)
        print("🎉 ALL VECTOR SEARCH SERVICE TESTS PASSED!")
        print("✅ COMPLETED: Test 1 - VectorSearchService privacy filtering validated")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        print("❌ FAILED: Test 1 - Issues found in VectorSearchService")
        return False


if __name__ == "__main__":
    import os
    import django
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.test_settings')
    django.setup()
    
    success = run_vector_search_tests()
    exit(0 if success else 1)