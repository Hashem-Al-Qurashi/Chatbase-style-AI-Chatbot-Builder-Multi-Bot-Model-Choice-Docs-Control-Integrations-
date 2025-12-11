#!/usr/bin/env python
"""Simple test of RAG components."""

import os
import sys
import django
import asyncio
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from apps.chatbots.models import Chatbot
from apps.knowledge.models import KnowledgeSource, KnowledgeChunk

def test_vector_search():
    """Test vector search directly."""
    chatbot_id = "57dae851-d7f5-4458-9587-70012aea74ca"
    
    print("\n=== Testing Vector Search ===")
    
    # Check what we have
    chatbot = Chatbot.objects.get(id=chatbot_id)
    chunks = KnowledgeChunk.objects.filter(source__chatbot=chatbot)
    
    print(f"Chatbot: {chatbot.name}")
    print(f"Total chunks: {chunks.count()}")
    
    # Check embeddings
    for chunk in chunks:
        has_embedding = bool(chunk.embedding_vector and len(chunk.embedding_vector) > 0)
        print(f"  Chunk {chunk.chunk_index}: {len(chunk.content)} chars, embedding: {has_embedding}")
        if has_embedding and isinstance(chunk.embedding_vector, list):
            print(f"    Embedding dimensions: {len(chunk.embedding_vector)}")
    
    # Try to search
    from apps.core.vector_storage import VectorStorageService
    
    try:
        print("\n🔍 Testing vector storage service...")
        service = VectorStorageService()
        
        # Create a test query embedding (just zeros for testing)
        test_embedding = [0.0] * 1536  # OpenAI ada-002 dimensions
        
        # Search
        from apps.core.vector_storage import VectorSearchQuery
        query = VectorSearchQuery(
            vector=test_embedding,
            top_k=3,
            namespace=f"chatbot_{chatbot_id}"
        )
        
        print("Searching vectors...")
        results = asyncio.run(service.search_vectors(query))
        print(f"Found {len(results)} results")
        
        for i, result in enumerate(results):
            print(f"  Result {i+1}: score={result.score:.3f}, id={result.id}")
            
    except Exception as e:
        print(f"Vector search error: {e}")
        import traceback
        traceback.print_exc()


def test_rag_components():
    """Test individual RAG components."""
    chatbot_id = "57dae851-d7f5-4458-9587-70012aea74ca"
    
    print("\n=== Testing RAG Components ===")
    
    # Test embedding service
    from apps.core.embedding_service import OpenAIEmbeddingService
    
    try:
        print("\n1. Testing embedding service...")
        embedding_service = OpenAIEmbeddingService()
        
        # Generate test embedding
        test_text = "Can you tell me about the confidentiality agreement?"
        result = asyncio.run(embedding_service.generate_embedding(test_text))
        
        if result:
            print(f"✓ Generated embedding: {len(result.embedding)} dimensions")
        else:
            print("❌ Failed to generate embedding")
            
    except Exception as e:
        print(f"❌ Embedding error: {e}")
    
    # Test context builder
    from apps.core.rag.context_builder import ContextBuilder
    
    try:
        print("\n2. Testing context builder...")
        builder = ContextBuilder()
        print("✓ Context builder initialized")
    except Exception as e:
        print(f"❌ Context builder error: {e}")
    
    # Test privacy filter
    from apps.core.rag.privacy_filter import PrivacyFilter
    
    try:
        print("\n3. Testing privacy filter...")
        filter = PrivacyFilter()
        print("✓ Privacy filter initialized")
    except Exception as e:
        print(f"❌ Privacy filter error: {e}")


def main():
    """Run tests."""
    print("=" * 60)
    print("SIMPLE RAG COMPONENT TESTS")
    print("=" * 60)
    
    try:
        test_vector_search()
        test_rag_components()
        
        print("\n" + "=" * 60)
        print("TESTS COMPLETED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()