#!/usr/bin/env python3
"""
Test actual embedding generation with the supposedly fixed OpenAI client
"""

import os
import sys
import django
import asyncio
from pathlib import Path

# Setup Django
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from apps.core.embedding_service import OpenAIEmbeddingService, EmbeddingConfig

async def test_embedding_generation():
    """Test actual embedding generation"""
    print("=== Testing Embedding Generation ===")
    
    # Set dummy API key
    original_key = os.environ.get('OPENAI_API_KEY')
    os.environ['OPENAI_API_KEY'] = 'sk-test_dummy_key_for_initialization'
    
    try:
        config = EmbeddingConfig(model="text-embedding-3-small")
        service = OpenAIEmbeddingService(config)
        
        print("✓ Service initialized successfully")
        
        # Test with a simple text (this will fail with invalid API key, but should show us how the client behaves)
        try:
            result = await service.generate_embedding("This is a test text for embedding generation.")
            print(f"✓ UNEXPECTED: Embedding generation succeeded: {len(result.embedding)} dimensions")
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            print(f"✓ EXPECTED: Embedding generation failed with {error_type}: {error_msg}")
            
            # Check if error is related to API key (expected) or client issues (problematic)
            if "api" in error_msg.lower() or "auth" in error_msg.lower() or "key" in error_msg.lower():
                print("✓ PASS: Failure is due to invalid API key (expected)")
            else:
                print(f"❌ FAIL: Failure seems to be due to client issues: {error_msg}")
                return False
        
        # Test batch generation
        try:
            result = await service.generate_embeddings_batch(["Text 1", "Text 2", "Text 3"])
            print(f"✓ UNEXPECTED: Batch embedding generation succeeded: {len(result.embeddings)} embeddings")
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            print(f"✓ EXPECTED: Batch embedding generation failed with {error_type}: {error_msg}")
            
            if "api" in error_msg.lower() or "auth" in error_msg.lower() or "key" in error_msg.lower():
                print("✓ PASS: Batch failure is due to invalid API key (expected)")
            else:
                print(f"❌ FAIL: Batch failure seems to be due to client issues: {error_msg}")
                return False
        
        return True
        
    finally:
        if original_key:
            os.environ['OPENAI_API_KEY'] = original_key
        else:
            os.environ.pop('OPENAI_API_KEY', None)

def test_langchain_direct():
    """Test LangChain OpenAI directly"""
    print("\n=== Testing LangChain OpenAI Direct ===")
    
    try:
        from langchain_openai import OpenAIEmbeddings
        print("✓ langchain_openai import succeeded")
        
        try:
            embeddings = OpenAIEmbeddings(
                openai_api_key="sk-test_dummy_key",
                model="text-embedding-3-small"
            )
            print("✓ LangChain OpenAIEmbeddings initialization succeeded")
            return True
        except Exception as e:
            print(f"❌ FAIL: LangChain OpenAIEmbeddings initialization failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: langchain_openai import failed: {e}")
        return False

async def main():
    """Run all embedding tests"""
    print("🧪 OPENAI EMBEDDING GENERATION TESTING")
    print("=" * 50)
    
    tests = [
        test_embedding_generation(),
        test_langchain_direct()
    ]
    
    results = []
    for test in tests:
        if asyncio.iscoroutine(test):
            result = await test
        else:
            result = test
        results.append(result)
    
    passed = sum(results)
    failed = len(results) - passed
    
    print("\n" + "=" * 50)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    
    if failed > 0:
        print("❌ EMBEDDING SYSTEM NOT READY")
        print("Critical dependency conflicts prevent proper operation")
        return False
    else:
        print("✅ EMBEDDING SYSTEM BASIC STRUCTURE FUNCTIONAL")
        print("⚠️  WARNING: Still has dependency conflicts that need resolution")
        return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)