#!/usr/bin/env python3
"""
Debug the embedding integration pipeline failure.
"""

import os
import sys
import django
import asyncio
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from apps.core.rag_integration import RAGIntegrationService
from apps.core.embedding_service import EmbeddingConfig
from apps.core.vector_storage import VectorStorageConfig
from apps.knowledge.models import KnowledgeSource, KnowledgeChunk
from apps.chatbots.models import Chatbot
from apps.accounts.models import User
from asgiref.sync import sync_to_async

async def debug_embedding_integration():
    """Debug the embedding integration pipeline."""
    print("🔧 Debugging Embedding Integration Pipeline")
    print("=" * 60)
    
    # Create test user and chatbot
    user = await get_or_create_test_user()
    chatbot = await get_or_create_test_chatbot(user)
    print(f"✅ Test user and chatbot created: {chatbot.name}")
    
    # Clean up any existing test data
    await cleanup_test_data(chatbot)
    print("✅ Cleaned up existing test data")
    
    # Create fresh test knowledge source and chunks
    source = await create_test_knowledge_source(chatbot)
    chunks = await create_test_knowledge_chunks(source)
    print(f"✅ Created {len(chunks)} test knowledge chunks")
    
    # Initialize services
    embedding_config = EmbeddingConfig(
        model="text-embedding-ada-002",
        max_batch_size=10,
        enable_caching=True,
        enable_deduplication=True
    )
    
    vector_config = VectorStorageConfig(
        backend="pgvector",  # Will fallback to SQLite
        vector_dimension=1536,
        batch_size=10,
        enable_caching=True
    )
    
    rag_service = RAGIntegrationService(embedding_config, vector_config)
    await rag_service.initialize()
    print("✅ RAG integration service initialized")
    
    # Process chunks individually to debug
    print("\n🔄 Processing chunks individually for debugging:")
    
    for i, chunk in enumerate(chunks):
        try:
            print(f"\n  Processing chunk {i+1}: {chunk.content[:50]}...")
            
            # Process single chunk
            result = await rag_service.process_knowledge_chunks([chunk])
            
            print(f"    ✅ Processed: {result.processed_chunks} chunks")
            print(f"    📊 Embeddings generated: {result.total_embeddings_generated}")
            print(f"    💾 Embeddings stored: {result.total_embeddings_stored}")
            print(f"    💰 Cost: ${result.total_cost_usd:.6f}")
            
            if result.errors:
                print(f"    ❌ Errors: {result.errors}")
            
        except Exception as e:
            print(f"    ❌ Failed to process chunk {i+1}: {str(e)}")
            print(f"    📋 Chunk details:")
            print(f"      - ID: {chunk.id}")
            print(f"      - Source ID: {chunk.source.id}")
            print(f"      - Index: {chunk.chunk_index}")
            print(f"      - Content length: {len(chunk.content)}")
            
            # Check if chunk already has embedding
            if chunk.embedding_vector:
                print(f"      - Has existing embedding: Yes")
            else:
                print(f"      - Has existing embedding: No")
    
    # Try processing all chunks together
    print("\n🔄 Processing all chunks together:")
    try:
        # Reload chunks to get fresh instances
        fresh_chunks = await get_knowledge_chunks(source)
        result = await rag_service.process_knowledge_chunks(fresh_chunks)
        
        print(f"✅ Batch processing successful:")
        print(f"   Processed: {result.processed_chunks} chunks")
        print(f"   Embeddings generated: {result.total_embeddings_generated}")
        print(f"   Embeddings stored: {result.total_embeddings_stored}")
        print(f"   Cost: ${result.total_cost_usd:.6f}")
        
        if result.errors:
            print(f"❌ Errors during batch processing: {result.errors}")
        
    except Exception as e:
        print(f"❌ Batch processing failed: {str(e)}")
        import traceback
        print("📋 Full traceback:")
        print(traceback.format_exc())
    
    # Test similarity search after processing
    print("\n🔍 Testing similarity search after processing:")
    try:
        search_results = await rag_service.search_similar_content(
            query_text="machine learning algorithms",
            chatbot_id=str(chatbot.id),
            top_k=5,
            citable_only=True
        )
        
        print(f"✅ Search completed: {len(search_results)} results found")
        for result in search_results:
            print(f"   - Score: {result.score:.4f}, Content: {result.metadata.get('content', 'N/A')[:50]}...")
        
    except Exception as e:
        print(f"❌ Search failed: {str(e)}")
    
    return True

async def get_or_create_test_user():
    """Get or create test user."""
    @sync_to_async
    def create_user():
        user, created = User.objects.get_or_create(
            email="debug@embedtest.com",
            defaults={
                "first_name": "Debug",
                "last_name": "Test",
                "is_active": True
            }
        )
        return user
    
    return await create_user()

async def get_or_create_test_chatbot(user):
    """Get or create test chatbot."""
    @sync_to_async
    def create_chatbot():
        # Delete existing test chatbot if it exists
        Chatbot.objects.filter(name="Debug Embedding Test Bot", user=user).delete()
        
        chatbot = Chatbot.objects.create(
            name="Debug Embedding Test Bot",
            user=user,
            description="Debug test chatbot for embedding integration",
            status="completed",
            metadata={}
        )
        return chatbot
    
    return await create_chatbot()

async def cleanup_test_data(chatbot):
    """Clean up any existing test data."""
    @sync_to_async
    def cleanup():
        # Delete existing knowledge sources and chunks
        KnowledgeSource.objects.filter(chatbot=chatbot).delete()
    
    await cleanup()

async def create_test_knowledge_source(chatbot):
    """Create test knowledge source."""
    @sync_to_async
    def create_source():
        source = KnowledgeSource.objects.create(
            name="Debug Test Source",
            chatbot=chatbot,
            description="Debug test source for embedding integration",
            content_type="text",
            is_citable=True,
            status="completed",
            metadata={}
        )
        return source
    
    return await create_source()

async def create_test_knowledge_chunks(source):
    """Create test knowledge chunks."""
    @sync_to_async
    def create_chunks():
        chunks = []
        import time
        timestamp = int(time.time())
        
        test_contents = [
            (f"Machine learning algorithms for data analysis - debug test {timestamp}", True),
            (f"Deep learning neural networks and training - debug test {timestamp}", True),
            (f"Internal proprietary ML algorithms - debug test {timestamp}", False),
        ]
        
        for i, (content, is_citable) in enumerate(test_contents):
            chunk = KnowledgeChunk.objects.create(
                source=source,
                chunk_index=i,
                content=content,
                is_citable=is_citable,
                token_count=len(content.split()),
                metadata={"test": True, "debug": True, "timestamp": timestamp}
            )
            chunks.append(chunk)
        
        return chunks
    
    return await create_chunks()

async def get_knowledge_chunks(source):
    """Get knowledge chunks for a source."""
    @sync_to_async
    def get_chunks():
        return list(KnowledgeChunk.objects.filter(source=source).order_by('chunk_index'))
    
    return await get_chunks()

async def main():
    """Run embedding integration debugging."""
    try:
        await debug_embedding_integration()
        print("\n🎯 Embedding integration debugging completed!")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Debug failed: {str(e)}")
        import traceback
        print("📋 Full traceback:")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())