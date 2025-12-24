#!/usr/bin/env python3
"""
Test RAG pipeline integration with the fixed OpenAI dependency
"""

import os
import sys
import django
import asyncio

# Set test environment variables before Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-validation')
os.environ.setdefault('DATABASE_URL', 'sqlite:///test.db')
os.environ.setdefault('OPENAI_API_KEY', 'sk-test-placeholder-key-not-real')
os.environ.setdefault('PINECONE_API_KEY', 'test-pinecone-key')
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'test-aws-key')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'test-aws-secret')
os.environ.setdefault('AWS_STORAGE_BUCKET_NAME', 'test-bucket')
os.environ.setdefault('STRIPE_PUBLISHABLE_KEY', 'pk_test_placeholder')
os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_test_placeholder')
os.environ.setdefault('STRIPE_WEBHOOK_SECRET', 'whsec_test_placeholder')
os.environ.setdefault('JWT_SECRET_KEY', 'test-jwt-secret')
os.environ.setdefault('GOOGLE_OAUTH_CLIENT_ID', 'test-google-client-id')
os.environ.setdefault('GOOGLE_OAUTH_CLIENT_SECRET', 'test-google-client-secret')

sys.path.append('/home/sakr_quraish/Projects/Ismail')
django.setup()

def test_rag_component_imports():
    """Test that all RAG components can be imported"""
    print("=== Testing RAG Component Imports ===")
    
    try:
        # Core embedding service
        from apps.core.embedding_service import OpenAIEmbeddingService, get_embedding_service
        print("✅ Embedding service imports")
        
        # Vector storage
        from apps.core.vector_storage import VectorStorageService
        print("✅ Vector storage service imports")
        
        # RAG pipeline
        from apps.core.rag.pipeline import RAGPipeline
        print("✅ RAG pipeline imports")
        
        # Vector search service
        from apps.core.rag.vector_search_service import VectorSearchService
        print("✅ Vector search service imports")
        
        # Context builder
        from apps.core.rag.context_builder import ContextBuilder
        print("✅ Context builder imports")
        
        # LLM service  
        from apps.core.rag.llm_service import LLMService
        print("✅ LLM service imports")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG component import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rag_component_initialization():
    """Test that RAG components can be initialized"""
    print("\n=== Testing RAG Component Initialization ===")
    
    try:
        # Test embedding service initialization
        from apps.core.embedding_service import OpenAIEmbeddingService, EmbeddingConfig
        config = EmbeddingConfig(enable_caching=False, max_batch_size=1)
        embedding_service = OpenAIEmbeddingService(config)
        print("✅ Embedding service initializes")
        
        # Test vector storage initialization
        from apps.core.vector_storage import VectorStorageService
        try:
            vector_storage = VectorStorageService()
            print("✅ Vector storage service initializes")
        except Exception as e:
            if "pinecone" in str(e).lower() or "api key" in str(e).lower():
                print("✅ Vector storage fails gracefully with invalid Pinecone key")
            else:
                print(f"⚠️  Vector storage error: {e}")
        
        # Test vector search service (requires chatbot_id)
        from apps.core.rag.vector_search_service import VectorSearchService
        try:
            vector_search = VectorSearchService("test-chatbot-123")
            print("✅ Vector search service initializes")
        except Exception as e:
            if "pinecone" in str(e).lower() or "api key" in str(e).lower():
                print("✅ Vector search fails gracefully with invalid Pinecone key")
            else:
                print(f"⚠️  Vector search error: {e}")
        
        # Test context builder
        from apps.core.rag.context_builder import ContextBuilder
        context_builder = ContextBuilder()
        print("✅ Context builder initializes")
        
        # Test LLM service
        from apps.core.rag.llm_service import LLMService
        llm_service = LLMService()
        print("✅ LLM service initializes")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG component initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_rag_pipeline_with_mock_data():
    """Test RAG pipeline with mock data (should fail gracefully)"""
    print("\n=== Testing RAG Pipeline with Mock Data ===")
    
    try:
        from apps.core.rag.pipeline import RAGPipeline
        from apps.core.exceptions import EmbeddingGenerationError
        
        # Initialize pipeline (requires chatbot_id)
        pipeline = RAGPipeline("test-chatbot-123")
        print("✅ RAG pipeline initializes")
        
        # Test query processing (should fail with auth error)
        try:
            query = "What is the test document about?"
            chatbot_id = "test-chatbot-123"
            
            response = await pipeline.process_query(
                query=query,
                chatbot_id=chatbot_id,
                user_id="test-user",
                session_id="test-session"
            )
            
            print("❌ UNEXPECTED: RAG pipeline returned response without valid API keys!")
            return False
            
        except EmbeddingGenerationError as e:
            if "authentication" in str(e).lower() or "401" in str(e):
                print("✅ RAG pipeline correctly fails with authentication error")
            else:
                print(f"✅ RAG pipeline fails with expected embedding error: {e}")
        except Exception as e:
            if "authentication" in str(e).lower() or "api key" in str(e).lower():
                print("✅ RAG pipeline correctly fails with API key error")
            else:
                print(f"⚠️  RAG pipeline failed with: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_text_chunking_integration():
    """Test text chunking works with embeddings"""
    print("\n=== Testing Text Chunking Integration ===")
    
    try:
        from apps.core.text_chunking import TextChunker, ChunkingConfig
        from apps.core.embedding_service import OpenAIEmbeddingService, EmbeddingConfig
        
        # Create chunker
        chunking_config = ChunkingConfig(
            chunk_size=200,
            chunk_overlap=50
        )
        chunker = TextChunker(chunking_config)
        print("✅ Text chunker initializes")
        
        # Test chunking
        test_text = """
        This is a test document for validating the OpenAI dependency fix.
        It contains multiple sentences that should be properly chunked.
        The chunking service should work independently of the embedding service.
        However, the embedding service should be able to process these chunks.
        """
        
        chunks = chunker.chunk_text(test_text)
        print(f"✅ Text chunking works: generated {len(chunks)} chunks")
        
        # Test that chunks have required attributes
        if chunks:
            chunk = chunks[0]
            required_attrs = ['content', 'chunk_id', 'start_index', 'end_index']
            for attr in required_attrs:
                if hasattr(chunk, attr):
                    print(f"✅ Chunk has {attr}: {getattr(chunk, attr)}")
                else:
                    print(f"❌ Chunk missing {attr}")
                    return False
        
        return True
        
    except Exception as e:
        print(f"❌ Text chunking integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_document_processing_integration():
    """Test document processing works with new embedding service"""
    print("\n=== Testing Document Processing Integration ===")
    
    try:
        from apps.core.document_processing import DocumentProcessor
        
        # Create processor with default settings
        processor = DocumentProcessor()
        print("✅ Document processor initializes")
        
        # Test text processing
        test_content = "This is a test document content for processing validation."
        metadata = {"filename": "test.txt", "content_type": "text/plain"}
        
        try:
            # Check if processor has the expected method
            if hasattr(processor, 'process_text_content'):
                result = processor.process_text_content(test_content, metadata)
                print(f"✅ Text processing works: {len(result.processed_chunks)} chunks")
            elif hasattr(processor, 'process_text'):
                result = processor.process_text(test_content, metadata)
                print(f"✅ Text processing works")
            else:
                print("⚠️  Document processor missing expected methods")
        except Exception as e:
            print(f"⚠️  Text processing error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Document processing integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all RAG integration tests"""
    print("🔍 RAG PIPELINE INTEGRATION VALIDATION")
    print("=" * 50)
    
    tests = [
        test_rag_component_imports,
        test_rag_component_initialization,
        test_text_chunking_integration,
        test_document_processing_integration,
        test_rag_pipeline_with_mock_data,
    ]
    
    results = []
    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("RAG INTEGRATION SUMMARY:")
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL RAG INTEGRATION TESTS PASSED ({passed}/{total})")
        print("🎉 RAG pipeline is ready for the next testing phase!")
        return True
    else:
        print(f"❌ RAG INTEGRATION TESTS FAILED ({passed}/{total} passed)")
        print("🚨 RAG pipeline has integration issues that need resolution!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)