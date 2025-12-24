#!/usr/bin/env python3
"""
Test script for embedding service functionality.
Tests caching, batching, and cost optimization features.
"""

import os
import sys
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')

import django
django.setup()

from apps.core.embedding_service import (
    EmbeddingConfig, OpenAIEmbeddingService, EmbeddingResult, BatchEmbeddingResult
)
from apps.core.circuit_breaker import CircuitBreaker


def create_mock_openai_response(input_texts):
    """Create mock OpenAI embedding response dynamically based on input."""
    # Handle both single string and list inputs
    if isinstance(input_texts, str):
        texts = [input_texts]
    else:
        texts = input_texts
    
    mock_response = Mock()
    mock_response.data = []
    
    for i, text in enumerate(texts):
        mock_embedding = Mock()
        mock_embedding.embedding = [0.1 + i * 0.01] * 1536  # Slightly different embeddings
        mock_response.data.append(mock_embedding)
    
    mock_response.usage = Mock()
    mock_response.usage.total_tokens = sum(len(text.split()) for text in texts) * 2  # Rough estimate
    
    return mock_response


async def test_embedding_service():
    """Test embedding service functionality."""
    print("🧪 Testing Embedding Service")
    print("=" * 50)
    
    # Test configuration
    config = EmbeddingConfig(
        model="text-embedding-ada-002",
        max_batch_size=5,  # Small for testing
        cache_ttl_hours=1,
        enable_caching=True,
        enable_deduplication=True,
        daily_budget_usd=10.0
    )
    
    print(f"✅ Configuration created:")
    print(f"   📊 Model: {config.model}")
    print(f"   📊 Max batch size: {config.max_batch_size}")
    print(f"   📊 Caching enabled: {config.enable_caching}")
    print(f"   📊 Deduplication enabled: {config.enable_deduplication}")
    print(f"   💰 Daily budget: ${config.daily_budget_usd}")
    
    # Initialize service
    service = OpenAIEmbeddingService(config)
    
    # Test service stats
    stats = service.get_service_stats()
    print(f"\n📊 Service Statistics:")
    print(f"   📊 Config: {stats['config']}")
    print(f"   💰 Cost tracking: {stats['cost_tracking']}")
    
    # Test texts
    test_texts = [
        "This is the first test document for embedding generation.",
        "Here is another piece of text to test our embedding service.",
        "This is the first test document for embedding generation.",  # Duplicate for deduplication test
        "A fourth unique text for batch processing testing.",
        "Final test text to complete our batch processing example."
    ]
    
    print(f"\n📝 Test texts prepared:")
    print(f"   📊 Total texts: {len(test_texts)}")
    print(f"   📊 Unique texts: {len(set(test_texts))}")
    
    # Mock OpenAI API for testing without actual API calls  
    with patch.object(service.client.embeddings, 'create') as mock_create:
        # Use side_effect to dynamically create responses based on input
        mock_create.side_effect = lambda input, model=None, **kwargs: create_mock_openai_response(input)
        
        try:
            print(f"\n🔄 Testing batch embedding generation...")
            
            # Test batch embedding generation
            result = await service.generate_embeddings_batch(test_texts)
            
            print(f"✅ Batch embedding generation successful:")
            print(f"   📊 Total embeddings: {len(result.embeddings)}")
            print(f"   📊 Total tokens: {result.total_tokens}")
            print(f"   💰 Total cost: ${result.total_cost_usd:.6f}")
            print(f"   📊 Cache hits: {result.cache_hits}")
            print(f"   📊 API calls: {result.api_calls}")
            print(f"   ⏱️ Processing time: {result.processing_time_ms}ms")
            
            # Verify embeddings
            if result.embeddings:
                first_embedding = result.embeddings[0]
                print(f"   📄 First embedding:")
                print(f"      🆔 Hash: {first_embedding.text_hash}")
                print(f"      📏 Dimensions: {first_embedding.dimensions}")
                print(f"      🎯 Tokens used: {first_embedding.tokens_used}")
                print(f"      💰 Cost: ${first_embedding.cost_usd:.6f}")
                print(f"      📄 Preview: {first_embedding.embedding[:5]}...")
            
            # Test single embedding
            print(f"\n🔄 Testing single embedding generation...")
            single_result = await service.generate_embedding("Test single embedding generation.")
            
            print(f"✅ Single embedding generation successful:")
            print(f"   📏 Dimensions: {single_result.dimensions}")
            print(f"   🎯 Tokens used: {single_result.tokens_used}")
            print(f"   💰 Cost: ${single_result.cost_usd:.6f}")
            print(f"   📄 Cached: {single_result.cached}")
            
            # Test caching (run same batch again)
            print(f"\n🔄 Testing caching (re-running same batch)...")
            cached_result = await service.generate_embeddings_batch(test_texts)
            
            print(f"✅ Cached batch generation successful:")
            print(f"   📊 Cache hits: {cached_result.cache_hits}")
            print(f"   📊 API calls: {cached_result.api_calls}")
            print(f"   💰 Total cost: ${cached_result.total_cost_usd:.6f}")
            print(f"   ⏱️ Processing time: {cached_result.processing_time_ms}ms")
            
            if cached_result.cache_hits > 0:
                print(f"   ✅ Caching is working correctly!")
            
        except Exception as e:
            print(f"❌ Embedding service test failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Test edge cases
    print(f"\n🔄 Testing edge cases...")
    
    # Empty texts
    try:
        empty_result = await service.generate_embeddings_batch([])
        print(f"✅ Empty batch handling: {len(empty_result.embeddings)} embeddings")
    except Exception as e:
        print(f"❌ Empty batch handling failed: {e}")
    
    # Single empty text
    try:
        await service.generate_embedding("")
        print(f"❌ Should have failed for empty text")
    except Exception as e:
        print(f"✅ Correctly rejected empty text: {e}")
    
    print(f"\n📊 Final service statistics:")
    final_stats = service.get_service_stats()
    print(f"   💰 Daily usage: {final_stats['cost_tracking']}")
    
    print(f"\n✅ Embedding service test completed!")


def test_circuit_breaker():
    """Test circuit breaker functionality."""
    print("\n🧪 Testing Circuit Breaker")
    print("=" * 30)
    
    # Create circuit breaker with low thresholds for testing
    circuit_breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=1,  # 1 second for quick testing
        expected_exception=Exception
    )
    
    print(f"✅ Circuit breaker created:")
    print(f"   📊 Failure threshold: {circuit_breaker.config.failure_threshold}")
    print(f"   📊 Recovery timeout: {circuit_breaker.config.recovery_timeout}s")
    print(f"   📊 Initial state: {circuit_breaker.state.value}")
    
    async def test_function(should_fail=False):
        """Test function that can succeed or fail."""
        if should_fail:
            raise Exception("Test failure")
        return "success"
    
    async def run_circuit_breaker_test():
        """Run circuit breaker tests."""
        
        # Test successful calls
        try:
            result = await circuit_breaker.call(test_function, should_fail=False)
            print(f"✅ Successful call: {result}")
        except Exception as e:
            print(f"❌ Unexpected failure: {e}")
        
        # Test failure calls to trigger circuit breaker
        for i in range(3):
            try:
                await circuit_breaker.call(test_function, should_fail=True)
            except Exception as e:
                print(f"🔥 Failure {i+1}: {e}")
        
        print(f"   📊 Circuit state after failures: {circuit_breaker.state.value}")
        print(f"   📊 Failure count: {circuit_breaker.failure_count}")
        
        # Try to call when circuit is open
        try:
            await circuit_breaker.call(test_function, should_fail=False)
            print(f"❌ Should have been rejected")
        except Exception as e:
            print(f"✅ Correctly rejected call: {e}")
        
        # Wait for recovery and test half-open
        print(f"⏱️ Waiting for recovery timeout...")
        await asyncio.sleep(1.5)
        
        try:
            result = await circuit_breaker.call(test_function, should_fail=False)
            print(f"✅ Recovery successful: {result}")
            print(f"   📊 Circuit state: {circuit_breaker.state.value}")
        except Exception as e:
            print(f"❌ Recovery failed: {e}")
        
        # Get final stats
        stats = circuit_breaker.get_stats()
        print(f"📊 Final circuit breaker stats: {stats}")
    
    asyncio.run(run_circuit_breaker_test())


if __name__ == "__main__":
    # Test embedding service
    asyncio.run(test_embedding_service())
    
    # Test circuit breaker
    test_circuit_breaker()