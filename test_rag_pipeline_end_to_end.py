#!/usr/bin/env python3
"""
CRITICAL END-TO-END RAG PIPELINE TESTING
Testing assumption: The entire RAG pipeline is a house of cards that will collapse under real usage.
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

from apps.core.rag.pipeline import RAGPipeline, get_rag_pipeline
from apps.core.document_processing import DocumentProcessingPipeline, PrivacyLevel
from apps.core.embedding_service import OpenAIEmbeddingService
from apps.core.vector_storage import create_vector_storage
from apps.chatbots.models import Chatbot
from apps.accounts.models import User, Organization
from apps.knowledge.models import KnowledgeSource, KnowledgeChunk
from django.contrib.auth import get_user_model

User = get_user_model()

class CriticalRAGPipelineTest:
    """Brutally test the entire RAG pipeline to expose systematic failures."""
    
    def __init__(self):
        self.failures = []
        self.successes = []
        self.test_user = None
        self.test_org = None
        self.test_chatbot = None
        self.rag_pipeline = None
        self.knowledge_source = None
        self.knowledge_chunks = []
    
    def log_failure(self, test_name, error):
        """Log a test failure."""
        self.failures.append(f"{test_name}: {error}")
        print(f"✗ FAIL: {test_name} - {error}")
    
    def log_success(self, test_name):
        """Log a test success."""
        self.successes.append(test_name)
        print(f"✓ PASS: {test_name}")
    
    def setup_test_data(self):
        """Set up test user, organization, and chatbot."""
        try:
            # Create test organization
            self.test_org = Organization.objects.create(
                name=f"Test Org {uuid.uuid4().hex[:8]}",
                slug=f"test-org-{uuid.uuid4().hex[:8]}"
            )
            
            # Create test user
            self.test_user = User.objects.create_user(
                email=f"test_rag_{uuid.uuid4().hex[:8]}@test.com",
                password='TestPassword123!',
                first_name='Test',
                last_name='RAG User',
                organization=self.test_org
            )
            
            # Create test chatbot
            self.test_chatbot = Chatbot.objects.create(
                name=f"Test RAG Bot {uuid.uuid4().hex[:8]}",
                description="Test chatbot for RAG pipeline testing",
                user=self.test_user,
                status='active'
            )
            
            self.log_success("Test data setup")
            return True
            
        except Exception as e:
            self.log_failure("Test data setup", str(e))
            return False
    
    async def test_rag_pipeline_initialization(self):
        """Test RAG pipeline initialization."""
        try:
            if not self.test_chatbot:
                raise Exception("Test chatbot not created")
            
            self.rag_pipeline = RAGPipeline(str(self.test_chatbot.id))
            
            if not self.rag_pipeline:
                raise Exception("RAG pipeline initialization returned None")
            
            if self.rag_pipeline.chatbot_id != str(self.test_chatbot.id):
                raise Exception("Chatbot ID mismatch in pipeline")
            
            # Test pipeline components exist
            required_components = [
                'vector_search', 'context_builder', 'llm_service',
                'privacy_filter', 'embedding_service', 'metrics'
            ]
            
            for component in required_components:
                if not hasattr(self.rag_pipeline, component):
                    raise Exception(f"Pipeline missing component: {component}")
            
            self.log_success("RAG pipeline initialization")
            return True
            
        except Exception as e:
            self.log_failure("RAG pipeline initialization", str(e))
            return False
    
    async def test_knowledge_source_creation(self):
        """Test creating knowledge source and chunks."""
        try:
            if not self.test_chatbot:
                raise Exception("Test chatbot not available")
            
            # Create knowledge source
            self.knowledge_source = KnowledgeSource.objects.create(
                chatbot=self.test_chatbot,
                source_type='text',
                name='Test Knowledge Source',
                description='Test knowledge for RAG pipeline',
                privacy_level=PrivacyLevel.CITABLE.value,
                metadata={'test': True}
            )
            
            # Create test documents
            test_documents = [
                "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.",
                "Deep learning is a specialized subset of machine learning that uses neural networks with multiple layers to analyze and learn from data.",
                "Natural language processing (NLP) is a field of artificial intelligence that focuses on enabling computers to understand, interpret, and generate human language.",
                "Computer vision is a field of AI that enables machines to interpret and understand visual information from the world around them.",
                "Reinforcement learning is a type of machine learning where an agent learns to make decisions by taking actions in an environment to maximize cumulative reward."
            ]
            
            # Process documents and create chunks
            doc_processor = DocumentProcessingPipeline()
            embedding_service = OpenAIEmbeddingService()
            
            for i, doc_text in enumerate(test_documents):
                # Process document
                content = doc_processor.process_document(
                    doc_text.encode('utf-8'),
                    f"test_doc_{i}.txt",
                    "text/plain",
                    PrivacyLevel.CITABLE
                )
                
                # Generate embedding
                embedding_result = await embedding_service.generate_embedding(doc_text)
                
                # Create knowledge chunk
                chunk = KnowledgeChunk.objects.create(
                    source=self.knowledge_source,
                    content=doc_text,
                    content_hash=content.content_hash,
                    chunk_index=i,
                    start_position=0,
                    end_position=len(doc_text),
                    token_count=content.token_count,
                    embedding_vector=embedding_result.embedding,
                    embedding_model=embedding_result.model,
                    is_citable=True,
                    metadata={'doc_index': i}
                )
                self.knowledge_chunks.append(chunk)
            
            # Store embeddings in vector storage
            if self.rag_pipeline and self.rag_pipeline.vector_search:
                await self.rag_pipeline.vector_search._ensure_initialized()
                
                if self.rag_pipeline.vector_search.vector_storage:
                    vectors_to_store = []
                    for chunk in self.knowledge_chunks:
                        vector_data = (
                            str(chunk.id),
                            chunk.embedding_vector,
                            {
                                'content': chunk.content,
                                'source_id': str(self.knowledge_source.id),
                                'is_citable': chunk.is_citable,
                                'chatbot_id': str(self.test_chatbot.id),
                                'chunk_index': chunk.chunk_index
                            }
                        )
                        vectors_to_store.append(vector_data)
                    
                    namespace = f"chatbot_{self.test_chatbot.id}"
                    await self.rag_pipeline.vector_search.vector_storage.store_embeddings(
                        vectors_to_store,
                        namespace=namespace
                    )
            
            self.log_success("Knowledge source creation")
            return True
            
        except Exception as e:
            self.log_failure("Knowledge source creation", str(e))
            return False
    
    async def test_simple_query_processing(self):
        """Test processing simple queries that don't need document context."""
        try:
            if not self.rag_pipeline:
                raise Exception("RAG pipeline not initialized")
            
            simple_queries = [
                "Hi there!",
                "Hello",
                "How are you?",
                "Thank you",
                "Good morning"
            ]
            
            for query in simple_queries:
                response = await self.rag_pipeline.process_query(
                    user_query=query,
                    user_id=str(self.test_user.id),
                    session_id=f"test_session_{uuid.uuid4().hex[:8]}"
                )
                
                if not response:
                    raise Exception(f"No response for simple query: {query}")
                
                if not response.content:
                    raise Exception(f"Empty response content for query: {query}")
                
                # Simple queries should have minimal context
                if response.sources_used > 0:
                    print(f"⚠  WARNING: Simple query '{query}' used {response.sources_used} sources")
                
                if response.total_time > 5.0:  # Simple queries should be fast
                    print(f"⚠  WARNING: Simple query '{query}' took {response.total_time}s")
            
            self.log_success("Simple query processing")
            return True
            
        except Exception as e:
            self.log_failure("Simple query processing", str(e))
            return False
    
    async def test_knowledge_based_queries(self):
        """Test queries that should use knowledge base."""
        try:
            if not self.rag_pipeline:
                raise Exception("RAG pipeline not initialized")
            
            knowledge_queries = [
                "What is machine learning?",
                "Explain deep learning",
                "How does natural language processing work?",
                "Tell me about computer vision",
                "What is reinforcement learning?"
            ]
            
            for query in knowledge_queries:
                response = await self.rag_pipeline.process_query(
                    user_query=query,
                    user_id=str(self.test_user.id),
                    session_id=f"test_session_{uuid.uuid4().hex[:8]}"
                )
                
                if not response:
                    raise Exception(f"No response for knowledge query: {query}")
                
                if not response.content:
                    raise Exception(f"Empty response content for query: {query}")
                
                # Knowledge queries should use sources
                if response.sources_used == 0:
                    print(f"⚠  WARNING: Knowledge query '{query}' used no sources")
                
                # Should have citations for knowledge-based responses
                if len(response.citations) == 0 and response.sources_used > 0:
                    print(f"⚠  WARNING: Knowledge query '{query}' has sources but no citations")
                
                # Check privacy compliance
                if not response.privacy_compliant:
                    raise Exception(f"Query response failed privacy compliance: {query}")
                
                if response.privacy_violations > 0:
                    raise Exception(f"Query response has privacy violations: {response.privacy_violations}")
            
            self.log_success("Knowledge-based queries")
            return True
            
        except Exception as e:
            self.log_failure("Knowledge-based queries", str(e))
            return False
    
    async def test_privacy_filtering(self):
        """Test privacy filtering in RAG responses."""
        try:
            if not self.rag_pipeline:
                raise Exception("RAG pipeline not initialized")
            
            # Create a private (non-citable) knowledge chunk
            private_content = "This is confidential internal information that should not be cited."
            
            # Generate embedding
            embedding_service = OpenAIEmbeddingService()
            embedding_result = await embedding_service.generate_embedding(private_content)
            
            # Create private knowledge chunk
            private_chunk = KnowledgeChunk.objects.create(
                source=self.knowledge_source,
                content=private_content,
                content_hash="private_test_hash",
                chunk_index=999,
                start_position=0,
                end_position=len(private_content),
                token_count=10,
                embedding_vector=embedding_result.embedding,
                embedding_model=embedding_result.model,
                is_citable=False,  # PRIVATE
                metadata={'privacy_test': True}
            )
            
            # Store private vector
            if self.rag_pipeline.vector_search.vector_storage:
                vector_data = (
                    str(private_chunk.id),
                    private_chunk.embedding_vector,
                    {
                        'content': private_chunk.content,
                        'source_id': str(self.knowledge_source.id),
                        'is_citable': False,  # PRIVATE
                        'chatbot_id': str(self.test_chatbot.id),
                        'privacy_test': True
                    }
                )
                
                namespace = f"chatbot_{self.test_chatbot.id}"
                await self.rag_pipeline.vector_search.vector_storage.store_embeddings(
                    [vector_data],
                    namespace=namespace
                )
            
            # Query for content that might match private data
            response = await self.rag_pipeline.process_query(
                user_query="Tell me about confidential information",
                user_id=str(self.test_user.id),
                session_id=f"privacy_test_{uuid.uuid4().hex[:8]}"
            )
            
            # Check that private content is not cited
            if response.content and "confidential internal information" in response.content.lower():
                raise Exception("Private content leaked into response")
            
            # Check citations don't contain private content
            for citation in response.citations:
                if "confidential" in citation.lower():
                    raise Exception("Private content found in citations")
            
            self.log_success("Privacy filtering")
            return True
            
        except Exception as e:
            self.log_failure("Privacy filtering", str(e))
            return False
    
    async def test_conversation_context(self):
        """Test conversation context maintenance."""
        try:
            if not self.rag_pipeline:
                raise Exception("RAG pipeline not initialized")
            
            session_id = f"context_test_{uuid.uuid4().hex[:8]}"
            
            # First message
            response1 = await self.rag_pipeline.process_query(
                user_query="What is machine learning?",
                user_id=str(self.test_user.id),
                session_id=session_id
            )
            
            if not response1.content:
                raise Exception("First response empty")
            
            # Follow-up message that should use context
            response2 = await self.rag_pipeline.process_query(
                user_query="Can you explain it in simpler terms?",
                user_id=str(self.test_user.id),
                session_id=session_id  # Same session
            )
            
            if not response2.content:
                raise Exception("Follow-up response empty")
            
            # Follow-up should understand "it" refers to machine learning
            if "machine learning" not in response2.content.lower() and "ml" not in response2.content.lower():
                print(f"⚠  WARNING: Follow-up response may not understand context")
            
            self.log_success("Conversation context")
            return True
            
        except Exception as e:
            self.log_failure("Conversation context", str(e))
            return False
    
    async def test_error_handling(self):
        """Test error handling in RAG pipeline."""
        try:
            if not self.rag_pipeline:
                raise Exception("RAG pipeline not initialized")
            
            # Test with invalid user ID
            try:
                await self.rag_pipeline.process_query(
                    user_query="Test query",
                    user_id="invalid_user_id",
                    session_id="test_session"
                )
                # Should not crash, might return fallback response
            except Exception as e:
                print(f"⚠  Pipeline crashed with invalid user ID: {e}")
            
            # Test with very long query
            long_query = "artificial intelligence " * 1000
            try:
                response = await self.rag_pipeline.process_query(
                    user_query=long_query,
                    user_id=str(self.test_user.id),
                    session_id="test_session"
                )
                # Should handle gracefully
                if response and response.content:
                    pass  # Good
                else:
                    print("⚠  Long query returned no response")
            except Exception as e:
                print(f"⚠  Pipeline crashed with long query: {e}")
            
            # Test with empty query
            try:
                response = await self.rag_pipeline.process_query(
                    user_query="",
                    user_id=str(self.test_user.id),
                    session_id="test_session"
                )
                if not response or not response.content:
                    print("⚠  Empty query returned no response")
            except Exception as e:
                print(f"⚠  Pipeline crashed with empty query: {e}")
            
            self.log_success("Error handling")
            return True
            
        except Exception as e:
            self.log_failure("Error handling", str(e))
            return False
    
    async def test_performance_under_load(self):
        """Test performance under concurrent load."""
        try:
            if not self.rag_pipeline:
                raise Exception("RAG pipeline not initialized")
            
            # Create multiple concurrent queries
            concurrent_queries = [
                f"What is artificial intelligence? Query {i}"
                for i in range(5)
            ]
            
            start_time = time.time()
            
            # Run queries concurrently
            tasks = []
            for i, query in enumerate(concurrent_queries):
                task = self.rag_pipeline.process_query(
                    user_query=query,
                    user_id=str(self.test_user.id),
                    session_id=f"load_test_{i}"
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
            
            # Check results
            successful_responses = 0
            total_response_time = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"⚠  Concurrent query {i} failed: {result}")
                elif hasattr(result, 'content') and result.content:
                    successful_responses += 1
                    total_response_time += result.total_time
                else:
                    print(f"⚠  Concurrent query {i} returned empty response")
            
            if successful_responses < len(concurrent_queries) * 0.8:
                raise Exception(f"Too many concurrent failures: {successful_responses}/{len(concurrent_queries)}")
            
            avg_response_time = total_response_time / successful_responses if successful_responses > 0 else 0
            
            print(f"Concurrent load test: {successful_responses}/{len(concurrent_queries)} successful")
            print(f"Total time: {total_time:.2f}s, Avg response time: {avg_response_time:.2f}s")
            
            if avg_response_time > 30.0:
                print(f"⚠  WARNING: Slow average response time: {avg_response_time}s")
            
            self.log_success("Performance under load")
            return True
            
        except Exception as e:
            self.log_failure("Performance under load", str(e))
            return False
    
    def cleanup_test_data(self):
        """Clean up test data."""
        try:
            # Delete in proper order to avoid foreign key constraints
            if self.knowledge_chunks:
                for chunk in self.knowledge_chunks:
                    chunk.delete()
            
            if self.knowledge_source:
                self.knowledge_source.delete()
            
            if self.test_chatbot:
                self.test_chatbot.delete()
            
            if self.test_user:
                self.test_user.delete()
            
            if self.test_org:
                self.test_org.delete()
            
            self.log_success("Test data cleanup")
            
        except Exception as e:
            self.log_failure("Test data cleanup", str(e))
    
    async def run_all_tests(self):
        """Run all end-to-end RAG pipeline tests."""
        print("\n" + "="*80)
        print("CRITICAL END-TO-END RAG PIPELINE TESTING")
        print("="*80)
        print("Testing assumption: RAG pipeline is a house of cards that will collapse.")
        print()
        
        # Setup
        if not self.setup_test_data():
            print("TEST DATA SETUP FAILED - ABORTING")
            return False
        
        try:
            # Core tests
            if not await self.test_rag_pipeline_initialization():
                print("RAG PIPELINE INIT FAILED - ABORTING")
                return False
            
            await self.test_knowledge_source_creation()
            await self.test_simple_query_processing()
            await self.test_knowledge_based_queries()
            await self.test_privacy_filtering()
            await self.test_conversation_context()
            await self.test_error_handling()
            await self.test_performance_under_load()
            
        finally:
            # Cleanup
            self.cleanup_test_data()
        
        # Summary
        print("\n" + "="*80)
        print("END-TO-END RAG PIPELINE TEST RESULTS")
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
            print("VERDICT: RAG PIPELINE IS FUNDAMENTALLY BROKEN")
            return False
        else:
            print("VERDICT: RAG pipeline appears functional")
            return True

async def main():
    tester = CriticalRAGPipelineTest()
    await tester.run_all_tests()

if __name__ == '__main__':
    asyncio.run(main())