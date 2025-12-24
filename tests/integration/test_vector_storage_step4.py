#!/usr/bin/env python3
"""
Comprehensive test suite for Step 4: Vector Storage Integration with Privacy Filtering

Tests all the critical functionality:
1. Vector storage with real embeddings
2. Privacy filtering (citable vs non-citable)
3. Namespace isolation per chatbot
4. Integration with embedding generation
5. End-to-end RAG pipeline functionality

This test validates that the system is ready for Step 5 (RAG Orchestration).
"""

import os
import sys
import django
import asyncio
import json
from typing import List, Dict, Any

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from apps.core.vector_storage import VectorStorageService, VectorStorageConfig
from apps.core.embedding_service import OpenAIEmbeddingService, EmbeddingConfig
from apps.core.rag_integration import RAGIntegrationService
from apps.knowledge.models import KnowledgeSource, KnowledgeChunk
from apps.chatbots.models import Chatbot
from apps.accounts.models import User


class VectorStorageStep4Tests:
    """Comprehensive test suite for vector storage with privacy filtering."""
    
    def __init__(self):
        """Initialize test suite."""
        self.results = {
            "vector_storage_init": False,
            "privacy_filtering": False,
            "namespace_isolation": False,
            "embedding_integration": False,
            "end_to_end_rag": False,
            "detailed_results": {}
        }
        
        # Test configuration
        self.embedding_config = EmbeddingConfig(
            model="text-embedding-ada-002",
            max_batch_size=10,
            enable_caching=True,
            enable_deduplication=True
        )
        
        self.vector_config = VectorStorageConfig(
            backend="pgvector",  # Will fallback to SQLite
            vector_dimension=1536,
            batch_size=10,
            enable_caching=True
        )
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all test scenarios."""
        print("🚀 Starting Step 4: Vector Storage Integration Tests")
        print("=" * 60)
        
        try:
            # Test 1: Vector Storage Initialization
            print("\n📊 Test 1: Vector Storage Initialization")
            await self.test_vector_storage_init()
            
            # Test 2: Privacy Filtering
            print("\n🔒 Test 2: Privacy Filtering")
            await self.test_privacy_filtering()
            
            # Test 3: Namespace Isolation
            print("\n🏢 Test 3: Namespace Isolation")
            await self.test_namespace_isolation()
            
            # Test 4: Embedding Integration
            print("\n🔗 Test 4: Embedding Integration")
            await self.test_embedding_integration()
            
            # Test 5: End-to-End RAG Pipeline
            print("\n🎯 Test 5: End-to-End RAG Pipeline")
            await self.test_end_to_end_rag()
            
        except Exception as e:
            print(f"❌ Critical test failure: {str(e)}")
            self.results["detailed_results"]["critical_error"] = str(e)
        
        # Print final results
        self.print_final_results()
        return self.results
    
    async def test_vector_storage_init(self) -> None:
        """Test vector storage initialization and basic operations."""
        try:
            # Initialize vector storage service
            vector_service = VectorStorageService(self.vector_config)
            init_success = await vector_service.initialize()
            
            if not init_success:
                print("❌ Vector storage initialization failed")
                return
            
            print(f"✅ Vector storage initialized with {vector_service.backend_name} backend")
            
            # Test basic storage and retrieval
            test_embeddings = [
                ("test_1", [0.1] * 1536, {"content": "Test content 1", "is_citable": True}),
                ("test_2", [0.2] * 1536, {"content": "Test content 2", "is_citable": False}),
            ]
            
            # Store test embeddings
            store_success = await vector_service.store_embeddings(
                test_embeddings,
                namespace="test_namespace"
            )
            
            if store_success:
                print("✅ Successfully stored test embeddings")
                
                # Test similarity search
                query_vector = [0.15] * 1536
                results = await vector_service.search_similar(
                    query_vector=query_vector,
                    top_k=5,
                    namespace="test_namespace"
                )
                
                if results:
                    print(f"✅ Retrieved {len(results)} similar results")
                    self.results["vector_storage_init"] = True
                    self.results["detailed_results"]["vector_init"] = {
                        "backend": vector_service.backend_name,
                        "embeddings_stored": len(test_embeddings),
                        "search_results": len(results)
                    }
                else:
                    print("❌ No search results returned")
            else:
                print("❌ Failed to store test embeddings")
        
        except Exception as e:
            print(f"❌ Vector storage test failed: {str(e)}")
            self.results["detailed_results"]["vector_init_error"] = str(e)
    
    async def test_privacy_filtering(self) -> None:
        """Test privacy filtering functionality."""
        try:
            vector_service = VectorStorageService(self.vector_config)
            await vector_service.initialize()
            
            # Create test embeddings with different privacy levels
            privacy_embeddings = [
                ("citable_1", [0.3] * 1536, {"content": "Public content 1", "is_citable": True}),
                ("citable_2", [0.4] * 1536, {"content": "Public content 2", "is_citable": True}),
                ("private_1", [0.5] * 1536, {"content": "Private content 1", "is_citable": False}),
                ("private_2", [0.6] * 1536, {"content": "Private content 2", "is_citable": False}),
            ]
            
            # Store embeddings
            await vector_service.store_embeddings(
                privacy_embeddings,
                namespace="privacy_test"
            )
            
            query_vector = [0.45] * 1536
            
            # Test 1: Search citable only (default behavior)
            citable_results = await vector_service.search_citable_only(
                query_vector=query_vector,
                top_k=10,
                namespace="privacy_test"
            )
            
            # Test 2: Search all content (including non-citable)
            all_results = await vector_service.search_all_content(
                query_vector=query_vector,
                top_k=10,
                namespace="privacy_test"
            )
            
            # Validate privacy filtering
            citable_count = len(citable_results)
            all_count = len(all_results)
            
            print(f"📊 Citable-only results: {citable_count}")
            print(f"📊 All results (including private): {all_count}")
            
            # Verify that citable search returns only citable content
            citable_privacy_check = all(
                result.metadata.get('is_citable', True) for result in citable_results
            )
            
            if citable_privacy_check and all_count >= citable_count:
                print("✅ Privacy filtering working correctly")
                self.results["privacy_filtering"] = True
                self.results["detailed_results"]["privacy_filtering"] = {
                    "citable_results": citable_count,
                    "all_results": all_count,
                    "privacy_respected": citable_privacy_check
                }
            else:
                print("❌ Privacy filtering failed")
                print(f"   Citable check: {citable_privacy_check}")
                print(f"   Result counts - Citable: {citable_count}, All: {all_count}")
        
        except Exception as e:
            print(f"❌ Privacy filtering test failed: {str(e)}")
            self.results["detailed_results"]["privacy_filtering_error"] = str(e)
    
    async def test_namespace_isolation(self) -> None:
        """Test namespace isolation between different chatbots."""
        try:
            vector_service = VectorStorageService(self.vector_config)
            await vector_service.initialize()
            
            # Create embeddings for different chatbots
            chatbot_a_embeddings = [
                ("chatbot_a_1", [0.7] * 1536, {"content": "Chatbot A content 1", "chatbot": "A"}),
                ("chatbot_a_2", [0.8] * 1536, {"content": "Chatbot A content 2", "chatbot": "A"}),
            ]
            
            chatbot_b_embeddings = [
                ("chatbot_b_1", [0.7] * 1536, {"content": "Chatbot B content 1", "chatbot": "B"}),
                ("chatbot_b_2", [0.8] * 1536, {"content": "Chatbot B content 2", "chatbot": "B"}),
            ]
            
            # Store in different namespaces
            await vector_service.store_embeddings(
                chatbot_a_embeddings,
                namespace="chatbot_A"
            )
            
            await vector_service.store_embeddings(
                chatbot_b_embeddings,
                namespace="chatbot_B"
            )
            
            query_vector = [0.75] * 1536
            
            # Search in chatbot A namespace
            results_a = await vector_service.search_similar(
                query_vector=query_vector,
                top_k=10,
                namespace="chatbot_A"
            )
            
            # Search in chatbot B namespace
            results_b = await vector_service.search_similar(
                query_vector=query_vector,
                top_k=10,
                namespace="chatbot_B"
            )
            
            # Verify namespace isolation
            a_contains_only_a = all(
                result.metadata.get('chatbot') == 'A' for result in results_a
            )
            
            b_contains_only_b = all(
                result.metadata.get('chatbot') == 'B' for result in results_b
            )
            
            if a_contains_only_a and b_contains_only_b and len(results_a) > 0 and len(results_b) > 0:
                print("✅ Namespace isolation working correctly")
                self.results["namespace_isolation"] = True
                self.results["detailed_results"]["namespace_isolation"] = {
                    "chatbot_a_results": len(results_a),
                    "chatbot_b_results": len(results_b),
                    "isolation_respected": True
                }
            else:
                print("❌ Namespace isolation failed")
                print(f"   Chatbot A isolation: {a_contains_only_a}")
                print(f"   Chatbot B isolation: {b_contains_only_b}")
                print(f"   Results A: {len(results_a)}, Results B: {len(results_b)}")
        
        except Exception as e:
            print(f"❌ Namespace isolation test failed: {str(e)}")
            self.results["detailed_results"]["namespace_isolation_error"] = str(e)
    
    async def test_embedding_integration(self) -> None:
        """Test integration between embedding generation and vector storage."""
        try:
            # Create test user and chatbot
            user = await self.get_or_create_test_user()
            chatbot = await self.get_or_create_test_chatbot(user)
            
            # Create test knowledge source and chunks
            source = await self.create_test_knowledge_source(chatbot)
            chunks = await self.create_test_knowledge_chunks(source)
            
            print(f"📝 Created {len(chunks)} test knowledge chunks")
            
            # Initialize RAG integration service
            rag_service = RAGIntegrationService(self.embedding_config, self.vector_config)
            await rag_service.initialize()
            
            # Process chunks through the full pipeline
            result = await rag_service.process_knowledge_chunks(chunks)
            
            if result.processed_chunks > 0 and result.total_embeddings_stored > 0:
                print(f"✅ Successfully processed {result.processed_chunks} chunks")
                print(f"   Embeddings generated: {result.total_embeddings_generated}")
                print(f"   Embeddings stored: {result.total_embeddings_stored}")
                print(f"   Cost: ${result.total_cost_usd:.4f}")
                
                # Test similarity search using the integration service
                search_results = await rag_service.search_similar_content(
                    query_text="test content",
                    chatbot_id=str(chatbot.id),
                    top_k=5,
                    citable_only=True
                )
                
                if search_results:
                    print(f"✅ Found {len(search_results)} similar content items")
                    self.results["embedding_integration"] = True
                    self.results["detailed_results"]["embedding_integration"] = {
                        "chunks_processed": result.processed_chunks,
                        "embeddings_generated": result.total_embeddings_generated,
                        "embeddings_stored": result.total_embeddings_stored,
                        "search_results": len(search_results),
                        "cost_usd": result.total_cost_usd
                    }
                else:
                    print("❌ No search results from integrated service")
            else:
                print("❌ Failed to process chunks through integration service")
                print(f"   Processed: {result.processed_chunks}, Stored: {result.total_embeddings_stored}")
                print(f"   Errors: {result.errors}")
        
        except Exception as e:
            print(f"❌ Embedding integration test failed: {str(e)}")
            self.results["detailed_results"]["embedding_integration_error"] = str(e)
    
    async def test_end_to_end_rag(self) -> None:
        """Test complete end-to-end RAG functionality."""
        try:
            # Get test entities
            user = await self.get_or_create_test_user()
            chatbot = await self.get_or_create_test_chatbot(user)
            
            # Initialize RAG service
            rag_service = RAGIntegrationService(self.embedding_config, self.vector_config)
            await rag_service.initialize()
            
            # Test the complete RAG pipeline with different privacy scenarios
            test_scenarios = [
                {
                    "name": "Citable Content Search",
                    "query": "machine learning algorithms",
                    "citable_only": True,
                    "expected_privacy": True
                },
                {
                    "name": "Internal Context Search",
                    "query": "internal training data",
                    "citable_only": False,
                    "expected_privacy": False
                }
            ]
            
            successful_scenarios = 0
            
            for scenario in test_scenarios:
                try:
                    results = await rag_service.search_similar_content(
                        query_text=scenario["query"],
                        chatbot_id=str(chatbot.id),
                        top_k=5,
                        citable_only=scenario["citable_only"]
                    )
                    
                    print(f"   📋 {scenario['name']}: {len(results)} results")
                    
                    # Validate privacy compliance
                    if scenario["citable_only"]:
                        privacy_compliant = all(
                            result.metadata.get('is_citable', True) for result in results
                        )
                        if privacy_compliant:
                            successful_scenarios += 1
                            print(f"   ✅ Privacy compliance verified for {scenario['name']}")
                        else:
                            print(f"   ❌ Privacy violation in {scenario['name']}")
                    else:
                        successful_scenarios += 1
                        print(f"   ✅ Internal search completed for {scenario['name']}")
                
                except Exception as e:
                    print(f"   ❌ {scenario['name']} failed: {str(e)}")
            
            # Get service statistics
            stats = await rag_service.get_service_stats()
            
            if successful_scenarios == len(test_scenarios):
                print("✅ End-to-end RAG pipeline working correctly")
                self.results["end_to_end_rag"] = True
                self.results["detailed_results"]["end_to_end_rag"] = {
                    "successful_scenarios": successful_scenarios,
                    "total_scenarios": len(test_scenarios),
                    "service_stats": stats
                }
            else:
                print(f"❌ RAG pipeline failed: {successful_scenarios}/{len(test_scenarios)} scenarios passed")
        
        except Exception as e:
            print(f"❌ End-to-end RAG test failed: {str(e)}")
            self.results["detailed_results"]["end_to_end_rag_error"] = str(e)
    
    async def get_or_create_test_user(self):
        """Get or create test user."""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def create_user():
            # Clean up any existing test data first
            self._cleanup_test_data_sync()
            
            user, created = User.objects.get_or_create(
                email="test@vectorstorage.com",
                defaults={
                    "first_name": "Vector",
                    "last_name": "Test",
                    "is_active": True
                }
            )
            return user
        
        return await create_user()
    
    def _cleanup_test_data_sync(self):
        """Clean up all existing test data synchronously."""
        from django.db import transaction
        
        with transaction.atomic():
            # Delete test chunks first (due to foreign key constraints)
            KnowledgeChunk.objects.filter(
                source__name__startswith="Vector Storage Test"
            ).delete()
            
            # Delete test sources
            KnowledgeSource.objects.filter(
                name__startswith="Vector Storage Test"
            ).delete()
            
            # Delete test chatbots
            from apps.chatbots.models import Chatbot
            Chatbot.objects.filter(
                name__startswith="Vector Storage Test"
            ).delete()
            
            # Clean up test users
            User.objects.filter(
                email="test@vectorstorage.com"
            ).delete()
    
    async def get_or_create_test_chatbot(self, user):
        """Get or create test chatbot."""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def create_chatbot():
            chatbot, created = Chatbot.objects.get_or_create(
                name="Vector Storage Test Bot",
                user=user,
                defaults={
                    "description": "Test chatbot for vector storage",
                    "status": "completed",
                    "metadata": {}
                }
            )
            return chatbot
        
        return await create_chatbot()
    
    async def create_test_knowledge_source(self, chatbot):
        """Create test knowledge source."""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def create_source():
            source, created = KnowledgeSource.objects.get_or_create(
                name="Vector Storage Test Source",
                chatbot=chatbot,
                defaults={
                    "description": "Test source for vector storage",
                    "content_type": "text",
                    "is_citable": True,
                    "status": "completed",
                    "metadata": {}
                }
            )
            return source
        
        return await create_source()
    
    async def create_test_knowledge_chunks(self, source):
        """Create test knowledge chunks."""
        from asgiref.sync import sync_to_async
        
        @sync_to_async
        def create_chunks():
            # Clear existing chunks and sources for clean test
            from django.db import transaction
            with transaction.atomic():
                # Delete chunks associated with this source first
                KnowledgeChunk.objects.filter(source=source).delete()
                
                # Also clear any existing test chunks that might conflict
                existing_chunks = KnowledgeChunk.objects.filter(
                    source__chatbot=source.chatbot,
                    source__name__startswith="Vector Storage Test"
                )
                existing_chunks.delete()
            
            chunks = []
            import time
            timestamp = int(time.time())
            
            test_contents = [
                (f"Machine learning algorithms are powerful tools for data analysis ({timestamp})", True),
                (f"Deep learning models require large datasets for training ({timestamp})", True),
                (f"Internal training notes: proprietary algorithm details ({timestamp})", False),
                (f"Public documentation about neural network architectures ({timestamp})", True),
                (f"Confidential performance metrics and benchmarks ({timestamp})", False),
            ]
            
            # Create chunks in transaction to ensure consistency
            with transaction.atomic():
                for i, (content, is_citable) in enumerate(test_contents):
                    chunk = KnowledgeChunk.objects.create(
                        source=source,
                        chunk_index=i,
                        content=content,
                        is_citable=is_citable,
                        token_count=len(content.split()),
                        metadata={"test": True, "chunk_type": "synthetic", "timestamp": timestamp}
                    )
                    chunks.append(chunk)
            
            return chunks
        
        return await create_chunks()
    
    def print_final_results(self) -> None:
        """Print comprehensive test results."""
        print("\n" + "=" * 60)
        print("🏁 STEP 4 VECTOR STORAGE INTEGRATION - FINAL RESULTS")
        print("=" * 60)
        
        total_tests = len([k for k in self.results.keys() if k != "detailed_results"])
        passed_tests = sum(1 for k, v in self.results.items() if k != "detailed_results" and v)
        
        print(f"\n📊 OVERALL SCORE: {passed_tests}/{total_tests} tests passed")
        
        # Individual test results
        test_descriptions = {
            "vector_storage_init": "Vector Storage Initialization",
            "privacy_filtering": "Privacy Filtering",
            "namespace_isolation": "Namespace Isolation",
            "embedding_integration": "Embedding Integration",
            "end_to_end_rag": "End-to-End RAG Pipeline"
        }
        
        print(f"\n📋 DETAILED RESULTS:")
        for test_key, description in test_descriptions.items():
            status = "✅ PASS" if self.results[test_key] else "❌ FAIL"
            print(f"   {description}: {status}")
        
        # Step 4 completion status
        if passed_tests == total_tests:
            print(f"\n🎉 STEP 4 COMPLETE!")
            print(f"✅ Vector storage integration is fully functional")
            print(f"✅ Privacy filtering is working correctly")
            print(f"✅ Namespace isolation is maintained")
            print(f"✅ Embedding generation is integrated")
            print(f"✅ End-to-end RAG pipeline is operational")
            print(f"\n🚀 READY FOR STEP 5: RAG Orchestration")
        else:
            print(f"\n⚠️  STEP 4 PARTIALLY COMPLETE")
            print(f"   {passed_tests}/{total_tests} components are working")
            print(f"   Review failed tests before proceeding to Step 5")
        
        # Detailed statistics
        if "detailed_results" in self.results and self.results["detailed_results"]:
            print(f"\n📈 TECHNICAL DETAILS:")
            for key, details in self.results["detailed_results"].items():
                if isinstance(details, dict) and not key.endswith("_error"):
                    print(f"   {key}:")
                    for detail_key, detail_value in details.items():
                        print(f"     {detail_key}: {detail_value}")


async def main():
    """Run vector storage integration tests."""
    test_suite = VectorStorageStep4Tests()
    results = await test_suite.run_all_tests()
    
    # Return exit code based on results
    total_tests = len([k for k in results.keys() if k != "detailed_results"])
    passed_tests = sum(1 for k, v in results.items() if k != "detailed_results" and v)
    
    if passed_tests == total_tests:
        print(f"\n🎯 ALL TESTS PASSED - Vector storage integration ready!")
        sys.exit(0)
    else:
        print(f"\n💥 {total_tests - passed_tests} TEST(S) FAILED - Review and fix issues")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())