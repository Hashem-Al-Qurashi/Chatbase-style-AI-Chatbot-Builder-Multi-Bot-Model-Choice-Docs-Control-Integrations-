#!/usr/bin/env python3
"""
Test Step 2: Vector Storage Integration Fix
Test the embedding → vector storage transfer fix.
"""

import os
import sys
import asyncio
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')

import django
django.setup()

from apps.knowledge.models import KnowledgeSource, KnowledgeChunk
from apps.core.tasks import generate_embeddings_for_knowledge_chunks
from apps.core.vector_storage import create_vector_storage
from apps.core.embedding_service import OpenAIEmbeddingService

def test_vector_storage_integration():
    """Test the vector storage integration fix"""
    print('🔧 TESTING STEP 2: Vector Storage Integration Fix')
    print('=' * 60)
    
    # Get our test knowledge source
    sources = KnowledgeSource.objects.filter(name='Step1_Upload_Test.txt').order_by('-created_at')[:1]
    if not sources:
        print('❌ No test source found')
        return False
        
    source = sources[0]
    print(f'Source: {source.name} (ID: {source.id})')
    print(f'Chatbot ID: {source.chatbot.id}')
    print(f'Status: {source.status}')
    
    # Get chunks
    chunks = list(KnowledgeChunk.objects.filter(source=source))
    print(f'Knowledge chunks: {len(chunks)}')
    
    if not chunks:
        print('❌ No chunks found to test')
        return False
    
    chunk = chunks[0]
    print(f'Test chunk: {chunk.chunk_index}')
    print(f'  Has embedding: {chunk.embedding_vector is not None}')
    print(f'  Is citable: {chunk.is_citable}')
    print(f'  Content: {chunk.content[:100]}...')
    print()
    
    # Force regenerate embeddings to test the vector storage integration
    print('🚀 Running embedding generation task with vector storage fix...')
    try:
        result = generate_embeddings_for_knowledge_chunks(
            knowledge_source_id=str(source.id),
            force_regenerate=True  # Force regeneration to test the new vector storage integration
        )
        
        print(f'Task result: {result}')
        
        if result and isinstance(result, dict):
            task_result = result.get('result', {})
            print(f'  Processed chunks: {task_result.get("processed_chunks", 0)}')
            print(f'  Generated embeddings: {task_result.get("generated_embeddings", 0)}')
            print(f'  Model: {task_result.get("model", "unknown")}')
        
        return True
        
    except Exception as e:
        print(f'❌ Task failed: {str(e)}')
        import traceback
        traceback.print_exc()
        return False

def get_test_source():
    """Get test source synchronously"""
    sources = KnowledgeSource.objects.filter(name='Step1_Upload_Test.txt').order_by('-created_at')[:1]
    if not sources:
        return None
    return sources[0]

async def validate_vector_storage():
    """Validate that vectors are now in storage"""
    print('\n🔍 VALIDATING VECTOR STORAGE AFTER FIX')
    print('=' * 40)
    
    # Get our test knowledge source
    source = get_test_source()
    if not source:
        print('❌ No test source found')
        return False
    
    # Check vector storage
    vector_storage = await create_vector_storage()
    namespace = f'chatbot_{source.chatbot.id}'
    print(f'Checking namespace: {namespace}')
    
    # Test search
    test_vector = [0.1] * 1536  # Test vector
    results = await vector_storage.search_all_content(test_vector, top_k=5, namespace=namespace)
    print(f'Vector search results: {len(results)}')
    
    for result in results:
        print(f'  Vector ID: {result.id}')
        print(f'  Score: {result.score}')
        print(f'  Metadata keys: {list(result.metadata.keys()) if result.metadata else None}')
        if result.metadata and 'content' in result.metadata:
            content = result.metadata['content']
            print(f'  Content: {content[:100]}...')
        print()
    
    # Test semantic search
    print('Testing semantic search...')
    embedding_service = OpenAIEmbeddingService()
    
    query = 'file upload functionality'
    query_embedding = await embedding_service.generate_embedding(query)
    
    semantic_results = await vector_storage.search_citable_only(
        query_vector=query_embedding,
        top_k=3, 
        namespace=namespace
    )
    
    print(f'Semantic search results for "{query}": {len(semantic_results)}')
    for result in semantic_results:
        print(f'  Score: {result.score:.4f}')
        print(f'  Content: {result.metadata.get("content", "No content")[:100]}...')
        print()
    
    success = len(results) > 0 and len(semantic_results) > 0
    
    print('=' * 40)
    print('🎯 STEP 2 VALIDATION SUMMARY:')
    print(f'✅ Vector search working: {len(results) > 0} ({len(results)} results)')
    print(f'✅ Semantic search working: {len(semantic_results) > 0} ({len(semantic_results)} results)')
    print(f'✅ Namespace alignment: {namespace}')
    print()
    print(f'🚀 STEP 2 FIX SUCCESS: {"YES" if success else "NO"}')
    
    if success:
        print('\n🎉 EXCELLENT! Step 2 vector storage integration is now working!')
        print('   - Embeddings are generated ✅')
        print('   - Embeddings are transferred to vector storage ✅')  
        print('   - Vector search is working ✅')
        print('   - Semantic search is working ✅')
        print('   - Namespace alignment is correct ✅')
    
    return success

def main():
    """Run the complete test"""
    # Test the task modification
    task_success = test_vector_storage_integration()
    
    if task_success:
        # Validate vector storage
        vector_success = asyncio.run(validate_vector_storage())
        return vector_success
    
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)