#!/usr/bin/env python3
"""
Rigorous OpenAI Client Testing Script
Tests the supposedly fixed OpenAI client integration
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

import traceback
from openai import OpenAI
from apps.core.embedding_service import OpenAIEmbeddingService, EmbeddingConfig
from chatbot_saas.config import get_settings

def test_openai_version():
    """Test 1: Verify OpenAI version"""
    print("=== Test 1: OpenAI Version Check ===")
    try:
        import openai
        print(f"✓ OpenAI version: {openai.__version__}")
        if openai.__version__ != "2.2.0":
            print(f"❌ FAIL: Expected 2.2.0, got {openai.__version__}")
            return False
        print("✓ PASS: Correct OpenAI version")
        return True
    except Exception as e:
        print(f"❌ FAIL: Version check failed: {e}")
        return False

def test_openai_client_initialization():
    """Test 2: OpenAI Client Basic Initialization"""
    print("\n=== Test 2: OpenAI Client Initialization ===")
    
    # Test 1: Basic initialization
    try:
        client = OpenAI(api_key="test_key_basic")
        print("✓ PASS: Basic OpenAI client initialization")
    except Exception as e:
        print(f"❌ FAIL: Basic initialization failed: {e}")
        return False
    
    # Test 2: The problematic 'proxies' parameter that was causing issues
    try:
        client = OpenAI(api_key="test_key_proxy", http_client=None)
        print("✓ PASS: OpenAI client with http_client parameter")
    except Exception as e:
        print(f"❌ FAIL: http_client parameter failed: {e}")
        return False
    
    # Test 3: Multiple parameters
    try:
        client = OpenAI(
            api_key="test_key_multi",
            base_url="https://api.openai.com/v1",
            timeout=30,
            max_retries=3
        )
        print("✓ PASS: OpenAI client with multiple parameters")
    except Exception as e:
        print(f"❌ FAIL: Multiple parameters failed: {e}")
        return False
    
    # Test 4: Test that the old 'proxies' parameter is no longer accepted
    try:
        client = OpenAI(api_key="test_key_proxy", proxies={"http": "http://proxy:8080"})
        print("❌ FAIL: 'proxies' parameter should not be accepted")
        return False
    except TypeError as e:
        if "proxies" in str(e):
            print("✓ PASS: 'proxies' parameter correctly rejected")
        else:
            print(f"❌ FAIL: Unexpected TypeError: {e}")
            return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected exception testing proxies: {e}")
        return False
    
    return True

def test_embedding_service_initialization():
    """Test 3: OpenAIEmbeddingService Initialization"""
    print("\n=== Test 3: OpenAIEmbeddingService Initialization ===")
    
    try:
        # Test with minimal config
        embedding_service = OpenAIEmbeddingService(
            api_key="test_key_embedding",
            model="text-embedding-3-small"
        )
        print("✓ PASS: OpenAIEmbeddingService basic initialization")
    except Exception as e:
        print(f"❌ FAIL: OpenAIEmbeddingService initialization failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        # Test loading from config
        settings = get_settings()
        config = EmbeddingConfig()
        # This should work even if the API key is not set (but we need to mock it)
        import os
        original_key = os.environ.get('OPENAI_API_KEY')
        os.environ['OPENAI_API_KEY'] = 'test_key_config'
        try:
            embedding_service = OpenAIEmbeddingService(config)
            print("✓ PASS: OpenAIEmbeddingService from config")
        finally:
            if original_key:
                os.environ['OPENAI_API_KEY'] = original_key
            else:
                os.environ.pop('OPENAI_API_KEY', None)
    except Exception as e:
        print(f"❌ FAIL: OpenAIEmbeddingService from config failed: {e}")
        traceback.print_exc()
        return False
    
    return True

def test_embedding_service_methods():
    """Test 4: OpenAIEmbeddingService Methods"""
    print("\n=== Test 4: OpenAIEmbeddingService Methods ===")
    
    try:
        import os
        original_key = os.environ.get('OPENAI_API_KEY')
        os.environ['OPENAI_API_KEY'] = 'test_key_methods'
        try:
            config = EmbeddingConfig(model="text-embedding-3-small")
            embedding_service = OpenAIEmbeddingService(config)
        
            # Test that methods exist and are callable
            assert hasattr(embedding_service, 'generate_embedding'), "Missing generate_embedding method"
            assert callable(embedding_service.generate_embedding), "generate_embedding not callable"
            
            assert hasattr(embedding_service, 'generate_embeddings_batch'), "Missing generate_embeddings_batch method"
            assert callable(embedding_service.generate_embeddings_batch), "generate_embeddings_batch not callable"
            
            print("✓ PASS: OpenAIEmbeddingService methods exist")
            
            # Test service stats method (shouldn't require API call)
            try:
                stats = embedding_service.get_service_stats()
                print(f"✓ PASS: get_service_stats returned stats with model: {stats.get('config', {}).get('model')}")
            except Exception as e:
                print(f"❌ FAIL: get_service_stats failed: {e}")
                return False
        
        finally:
            if original_key:
                os.environ['OPENAI_API_KEY'] = original_key
            else:
                os.environ.pop('OPENAI_API_KEY', None)
        
    except Exception as e:
        print(f"❌ FAIL: OpenAIEmbeddingService method testing failed: {e}")
        traceback.print_exc()
        return False
    
    return True

def test_langchain_compatibility():
    """Test 5: LangChain OpenAI Integration"""
    print("\n=== Test 5: LangChain OpenAI Compatibility ===")
    
    try:
        from langchain_openai import OpenAIEmbeddings
        print("✓ PASS: langchain_openai import successful")
    except Exception as e:
        print(f"❌ FAIL: langchain_openai import failed: {e}")
        return False
    
    try:
        # Test initialization (should work even with dummy key)
        embeddings = OpenAIEmbeddings(
            openai_api_key="test_key_langchain",
            model="text-embedding-3-small"
        )
        print("✓ PASS: LangChain OpenAIEmbeddings initialization")
    except Exception as e:
        print(f"❌ FAIL: LangChain OpenAIEmbeddings initialization failed: {e}")
        traceback.print_exc()
        return False
    
    return True

def test_error_handling():
    """Test 6: Error Handling"""
    print("\n=== Test 6: Error Handling ===")
    
    # Test invalid API key handling
    try:
        client = OpenAI(api_key="")
        print("✓ PASS: Empty API key accepted (error will come at API call)")
    except Exception as e:
        print(f"❌ FAIL: Empty API key rejected during initialization: {e}")
        return False
    
    # Test None API key
    try:
        client = OpenAI(api_key=None)
        print("❌ FAIL: None API key should be rejected")
        return False
    except Exception as e:
        print("✓ PASS: None API key correctly rejected")
    
    return True

def main():
    """Run all tests"""
    print("🔬 RIGOROUS OPENAI CLIENT TESTING")
    print("=" * 50)
    
    tests = [
        test_openai_version,
        test_openai_client_initialization,
        test_embedding_service_initialization,
        test_embedding_service_methods,
        test_langchain_compatibility,
        test_error_handling
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ CRITICAL FAILURE in {test.__name__}: {e}")
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    
    if failed > 0:
        print("❌ OVERALL: SYSTEM NOT READY FOR PRODUCTION")
        print("Critical issues detected that must be fixed before proceeding")
        return False
    else:
        print("✅ OVERALL: Basic OpenAI integration appears functional")
        print("⚠️  WARNING: Dependency conflicts still exist and need resolution")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)