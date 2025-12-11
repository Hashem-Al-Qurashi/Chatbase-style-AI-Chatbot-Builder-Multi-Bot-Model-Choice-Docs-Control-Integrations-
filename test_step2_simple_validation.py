#!/usr/bin/env python3
"""
Simple Step 2 test - just run the task and check results
"""

import os
import sys
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')

import django
django.setup()

from apps.knowledge.models import KnowledgeSource
from apps.core.tasks import generate_embeddings_for_knowledge_chunks

def test_step2_simple():
    print('🔧 STEP 2 SIMPLE TEST: Vector Storage Transfer')
    print('=' * 50)
    
    # Get our test knowledge source
    sources = KnowledgeSource.objects.filter(name='Step1_Upload_Test.txt').order_by('-created_at')[:1]
    if not sources:
        print('❌ No test source found')
        return False
        
    source = sources[0]
    print(f'Testing source: {source.name} (ID: {source.id})')
    print(f'Chatbot ID: {source.chatbot.id}')
    
    # Force regenerate embeddings to test the vector storage transfer
    print('\n🚀 Running embedding generation with vector storage transfer...')
    try:
        result = generate_embeddings_for_knowledge_chunks(
            knowledge_source_id=str(source.id),
            force_regenerate=True  # This should trigger vector storage transfer
        )
        
        print(f'\n📋 Task result:')
        if result and isinstance(result, dict):
            print(f'  Status: {result.get("status", "unknown")}')
            task_result = result.get('result', {})
            print(f'  Processed chunks: {task_result.get("processed_chunks", 0)}')
            print(f'  Generated embeddings: {task_result.get("generated_embeddings", 0)}')
            print(f'  Model: {task_result.get("model", "unknown")}')
        
        success = result and result.get('status') == 'success'
        print(f'\n🎯 Task success: {success}')
        
        return success
        
    except Exception as e:
        print(f'❌ Task failed: {str(e)}')
        return False

if __name__ == "__main__":
    success = test_step2_simple()
    if success:
        print('\n✅ STEP 2 FIX APPLIED')
        print('   Check logs above for "Vector storage update" messages')
        print('   If you see "embeddings stored > 0", the fix is working!')
    else:
        print('\n❌ STEP 2 FIX FAILED')
    
    sys.exit(0 if success else 1)