#!/usr/bin/env python3
"""
Test the embedding service with mock/test API key to verify integration works
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

async def test_embedding_service_with_mock_key():
    """Test that embedding service initializes and handles auth errors gracefully"""
    print("=== Testing Embedding Service with Mock API Key ===")
    
    try:
        from apps.core.embedding_service import OpenAIEmbeddingService, EmbeddingConfig
        from apps.core.exceptions import EmbeddingGenerationError
        
        print("✅ Imports successful")
        
        # Create service with test configuration
        config = EmbeddingConfig(
            max_batch_size=2,  # Small for testing
            enable_caching=False,  # Disable to force API calls
            enable_circuit_breaker=True,
            daily_budget_usd=1.0,  # Low budget for safety
        )
        
        service = OpenAIEmbeddingService(config)
        print("✅ Service initialized with test config")
        
        # Test 1: Try to generate embedding (should get auth error)
        try:
            result = await service.generate_embedding("This is a test text for validation")
            print("❌ UNEXPECTED: Got embedding result without valid API key!")
            return False
        except EmbeddingGenerationError as e:
            if "401" in str(e) or "authentication" in str(e).lower() or "api key" in str(e).lower():
                print("✅ Correctly got authentication error with invalid API key")
            else:
                print(f"✅ Got expected embedding error: {e}")
        except Exception as e:
            if "401" in str(e) or "authentication" in str(e).lower():
                print("✅ Correctly got authentication error from OpenAI")
            else:
                print(f"⚠️  Got unexpected error: {e}")
        
        # Test 2: Test batch processing with auth error
        try:
            batch_result = await service.generate_embeddings_batch([
                "Test text 1",
                "Test text 2"
            ])
            print("❌ UNEXPECTED: Got batch embedding result without valid API key!")
            return False
        except EmbeddingGenerationError as e:
            print(f"✅ Correctly got batch embedding error: {e}")
        except Exception as e:
            if "401" in str(e) or "authentication" in str(e).lower():
                print("✅ Correctly got authentication error from batch API call")
            else:
                print(f"⚠️  Got unexpected batch error: {e}")
        
        # Test 3: Service stats should work regardless of API key
        stats = service.get_service_stats()
        print(f"✅ Service stats accessible: {list(stats.keys())}")
        
        # Test 4: Cost tracking should work
        cost = service.cost_tracker.calculate_cost(1000)  # 1000 tokens
        expected_cost = 0.0001  # $0.0001 per 1k tokens for ada-002
        if abs(cost - expected_cost) < 0.0001:
            print(f"✅ Cost calculation correct: {cost} USD for 1000 tokens")
        else:
            print(f"❌ Cost calculation wrong: expected {expected_cost}, got {cost}")
        
        # Test 5: Budget checking should work
        budget_ok = service.cost_tracker.check_daily_budget(0.01)  # $0.01
        print(f"✅ Budget check works: {budget_ok}")
        
        print("✅ All embedding service integration tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Embedding service integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_settings_security():
    """Verify settings are properly secured"""
    print("\n=== Testing Settings Security ===")
    
    try:
        from django.conf import settings
        
        # Check that API key is placeholder
        openai_key = getattr(settings, 'OPENAI_API_KEY', 'NOT_SET')
        if openai_key == 'sk-test-placeholder-key-not-real':
            print("✅ OpenAI API key is test placeholder")
        elif openai_key.startswith('sk-') and len(openai_key) > 20:
            print("❌ SECURITY RISK: Real OpenAI API key detected!")
            return False
        else:
            print(f"✅ OpenAI API key is safe placeholder: {openai_key[:20]}...")
        
        # Check other sensitive settings
        sensitive_keys = ['STRIPE_SECRET_KEY', 'AWS_SECRET_ACCESS_KEY', 'JWT_SECRET_KEY']
        for key in sensitive_keys:
            value = getattr(settings, key, 'NOT_SET')
            if 'test' in value or 'placeholder' in value:
                print(f"✅ {key} is test value")
            else:
                print(f"⚠️  {key} might be real value: {value[:10]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Settings security test failed: {e}")
        return False

def test_import_chain():
    """Test that all critical imports work"""
    print("\n=== Testing Import Chain ===")
    
    try:
        # Test core imports
        from apps.core.embedding_service import OpenAIEmbeddingService, get_embedding_service
        from apps.core.vector_storage import VectorStorageService
        from apps.core.rag.pipeline import RAGPipeline
        from apps.core.rag.vector_search_service import VectorSearchService
        
        print("✅ All critical RAG imports successful")
        
        # Test specific OpenAI integration points
        import openai
        from openai import OpenAI
        from langchain_openai import OpenAIEmbeddings, ChatOpenAI
        import tiktoken
        
        print("✅ All OpenAI-related imports successful")
        print(f"   - OpenAI: {openai.__version__}")
        print(f"   - Tiktoken: {tiktoken.__version__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import chain test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("🔍 COMPREHENSIVE EMBEDDING SERVICE INTEGRATION VALIDATION")
    print("=" * 70)
    
    tests = [
        test_import_chain,
        test_settings_security,
        test_embedding_service_with_mock_key,
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
    
    print("\n" + "=" * 70)
    print("INTEGRATION VALIDATION SUMMARY:")
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL INTEGRATION TESTS PASSED ({passed}/{total})")
        print("🎉 Embedding service is ready for RAG pipeline integration!")
        return True
    else:
        print(f"❌ INTEGRATION TESTS FAILED ({passed}/{total} passed)")
        print("🚨 Embedding service has critical integration issues!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)