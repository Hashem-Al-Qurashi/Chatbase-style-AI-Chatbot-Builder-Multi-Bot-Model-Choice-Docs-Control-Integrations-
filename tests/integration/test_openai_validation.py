#!/usr/bin/env python3
"""
Comprehensive OpenAI dependency fix validation
Testing all aspects of the claimed fix with deep skepticism
"""

import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
sys.path.append('/home/sakr_quraish/Projects/Ismail')
django.setup()

def test_openai_client_initialization():
    """Test OpenAI client can be initialized with various parameter combinations"""
    print("=== Testing OpenAI Client Initialization ===")
    
    try:
        import openai
        print(f"✅ OpenAI version: {openai.__version__}")
        
        # Test 1: Basic initialization (should work)
        client = openai.OpenAI(api_key="test-key-placeholder")
        print("✅ Basic client initialization successful")
        
        # Test 2: Try the old proxies parameter that was causing issues
        try:
            client_with_proxies = openai.OpenAI(
                api_key="test-key-placeholder",
                proxies={"http": "http://proxy.example.com:8080"}
            )
            print("❌ CRITICAL: Proxies parameter still accepted - this should fail!")
            return False
        except TypeError as e:
            if "unexpected keyword argument 'proxies'" in str(e):
                print("✅ Proxies parameter correctly rejected")
            else:
                print(f"❌ Unexpected error with proxies: {e}")
                return False
        
        # Test 3: Test with http_client parameter (new way to handle proxies)
        try:
            import httpx
            proxy_client = httpx.Client(proxies={"http://": "http://proxy.example.com:8080"})
            client_with_http_client = openai.OpenAI(
                api_key="test-key-placeholder",
                http_client=proxy_client
            )
            print("✅ HTTP client with proxies works correctly")
        except Exception as e:
            print(f"⚠️  HTTP client test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenAI client initialization failed: {e}")
        return False

def test_tiktoken_compatibility():
    """Test tiktoken works with new OpenAI version"""
    print("\n=== Testing Tiktoken Compatibility ===")
    
    try:
        import tiktoken
        print(f"✅ Tiktoken version: {tiktoken.__version__}")
        
        # Test encoding works
        encoding = tiktoken.get_encoding("cl100k_base")
        test_text = "This is a test for tiktoken compatibility with OpenAI 2.2.0"
        tokens = encoding.encode(test_text)
        decoded = encoding.decode(tokens)
        
        assert decoded == test_text, "Encoding/decoding mismatch"
        print(f"✅ Tiktoken encoding/decoding works (test: {len(tokens)} tokens)")
        
        # Test with OpenAI models
        try:
            encoding_gpt4 = tiktoken.encoding_for_model("gpt-4")
            tokens_gpt4 = encoding_gpt4.encode(test_text)
            print(f"✅ GPT-4 encoding works ({len(tokens_gpt4)} tokens)")
        except Exception as e:
            print(f"⚠️  GPT-4 encoding test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Tiktoken test failed: {e}")
        return False

def test_langchain_openai_integration():
    """Test langchain-openai works with new versions"""
    print("\n=== Testing LangChain-OpenAI Integration ===")
    
    try:
        from langchain_openai import OpenAIEmbeddings, ChatOpenAI
        print("✅ LangChain-OpenAI imports successful")
        
        # Test embeddings initialization
        embeddings = OpenAIEmbeddings(
            openai_api_key="test-key-placeholder",
            model="text-embedding-ada-002"
        )
        print("✅ OpenAI embeddings initialization successful")
        
        # Test chat model initialization
        chat_model = ChatOpenAI(
            openai_api_key="test-key-placeholder",
            model="gpt-3.5-turbo"
        )
        print("✅ ChatOpenAI initialization successful")
        
        return True
        
    except Exception as e:
        print(f"❌ LangChain-OpenAI test failed: {e}")
        return False

def test_embedding_service_import():
    """Test the actual embedding service can be imported"""
    print("\n=== Testing Embedding Service Import ===")
    
    try:
        from apps.core.embedding_service import OpenAIEmbeddingService, get_embedding_service
        print("✅ OpenAIEmbeddingService import successful")
        
        # Test initialization (should work with default config)
        service = OpenAIEmbeddingService()
        print("✅ OpenAIEmbeddingService initialization successful")
        
        # Test global service getter
        global_service = get_embedding_service()
        print("✅ Global embedding service getter works")
        
        # Test service stats (should not crash)
        stats = service.get_service_stats()
        print(f"✅ Service stats retrieved: {len(stats)} sections")
        
        return True
        
    except Exception as e:
        print(f"❌ Embedding service test failed: {e}")
        return False

def test_dependency_conflicts():
    """Check for version conflicts that might cause issues"""
    print("\n=== Testing for Dependency Conflicts ===")
    
    try:
        import pkg_resources
        
        # Check for known problematic combinations
        packages_to_check = [
            'openai', 'langchain-openai', 'tiktoken', 'langchain',
            'langchain-core', 'langchain-community'
        ]
        
        versions = {}
        for package in packages_to_check:
            try:
                version = pkg_resources.get_distribution(package).version
                versions[package] = version
                print(f"  {package}: {version}")
            except pkg_resources.DistributionNotFound:
                print(f"  {package}: NOT FOUND")
        
        # Check specific compatibility requirements
        openai_version = versions.get('openai', '0.0.0')
        langchain_openai_version = versions.get('langchain-openai', '0.0.0')
        tiktoken_version = versions.get('tiktoken', '0.0.0')
        
        # Validate version compatibility
        issues = []
        
        if openai_version.startswith('2.'):
            if not langchain_openai_version.startswith('1.'):
                issues.append(f"OpenAI 2.x requires langchain-openai 1.x, got {langchain_openai_version}")
        
        if issues:
            print("❌ Dependency conflicts found:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        else:
            print("✅ No obvious dependency conflicts detected")
            return True
            
    except Exception as e:
        print(f"❌ Dependency conflict check failed: {e}")
        return False

def test_security_validation():
    """Validate that real API keys are not exposed"""
    print("\n=== Testing Security Implementation ===")
    
    # Check settings file
    try:
        from django.conf import settings
        openai_key = getattr(settings, 'OPENAI_API_KEY', 'NOT_SET')
        
        if openai_key == 'your-openai-api-key-here':
            print("✅ API key is placeholder value")
        elif openai_key.startswith('sk-'):
            print("❌ SECURITY RISK: Real OpenAI API key detected in settings!")
            return False
        elif openai_key == 'NOT_SET':
            print("⚠️  OpenAI API key not set in settings")
        else:
            print(f"✅ API key appears to be non-production value: {openai_key[:10]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Security validation failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🔍 COMPREHENSIVE OPENAI DEPENDENCY FIX VALIDATION")
    print("=" * 60)
    
    tests = [
        test_openai_client_initialization,
        test_tiktoken_compatibility,
        test_langchain_openai_integration,
        test_embedding_service_import,
        test_dependency_conflicts,
        test_security_validation
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY:")
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("🎉 OpenAI dependency fix appears to be working correctly!")
        return True
    else:
        print(f"❌ TESTS FAILED ({passed}/{total} passed)")
        print("🚨 OpenAI dependency fix has critical issues that must be resolved!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)