#!/usr/bin/env python3
"""
SPECIFIC TEST: Batch Processing Cost Claims
Verify the claim that batch processing reduces costs by 40-60%
"""

import os
import sys
import time
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')

import django
django.setup()

from apps.core.embedding_service import OpenAIEmbeddingService, EmbeddingConfig


async def test_batch_cost_claims():
    """Test specific batch processing cost claims."""
    print("🧪 TESTING BATCH PROCESSING COST CLAIMS")
    print("=" * 50)
    
    config = EmbeddingConfig(
        model="text-embedding-ada-002",
        max_batch_size=100,  # Use the claimed batch size
        enable_caching=False,  # Disable caching for fair comparison
        enable_deduplication=True
    )
    
    service = OpenAIEmbeddingService(config)
    
    # Test texts
    test_texts = [
        f"Test document number {i} with different content for cost analysis." 
        for i in range(10)
    ]
    
    print(f"Testing with {len(test_texts)} unique texts")
    
    # Method 1: Individual calls
    print("\n📋 Method 1: Individual API calls")
    individual_start = time.time()
    individual_results = []
    
    for i, text in enumerate(test_texts):
        print(f"  Processing text {i+1}/{len(test_texts)}")
        result = await service.generate_embedding(text)
        individual_results.append(result)
        await asyncio.sleep(0.1)  # Avoid rate limits
    
    individual_time = time.time() - individual_start
    individual_cost = sum(r.cost_usd for r in individual_results)
    individual_tokens = sum(r.tokens_used for r in individual_results)
    
    print(f"  ⏱️ Time: {individual_time:.2f}s")
    print(f"  💰 Cost: ${individual_cost:.6f}")
    print(f"  🎯 Tokens: {individual_tokens}")
    print(f"  📞 API calls: {len(test_texts)}")
    
    # Clear cache
    from django.core.cache import cache
    cache.clear()
    
    # Method 2: Batch call
    print("\n📋 Method 2: Batch API call")
    batch_start = time.time()
    
    batch_result = await service.generate_embeddings_batch(test_texts)
    
    batch_time = time.time() - batch_start
    batch_cost = batch_result.total_cost_usd
    batch_tokens = batch_result.total_tokens
    batch_api_calls = batch_result.api_calls
    
    print(f"  ⏱️ Time: {batch_time:.2f}s")
    print(f"  💰 Cost: ${batch_cost:.6f}")
    print(f"  🎯 Tokens: {batch_tokens}")
    print(f"  📞 API calls: {batch_api_calls}")
    
    # Calculate differences
    cost_reduction = ((individual_cost - batch_cost) / individual_cost) * 100 if individual_cost > 0 else 0
    time_reduction = ((individual_time - batch_time) / individual_time) * 100
    api_call_reduction = ((len(test_texts) - batch_api_calls) / len(test_texts)) * 100
    
    print(f"\n📊 ANALYSIS:")
    print(f"  💰 Cost reduction: {cost_reduction:.1f}%")
    print(f"  ⏱️ Time reduction: {time_reduction:.1f}%")
    print(f"  📞 API call reduction: {api_call_reduction:.1f}%")
    
    # Validate claims
    print(f"\n🔍 CLAIM VALIDATION:")
    if cost_reduction >= 40 and cost_reduction <= 60:
        print(f"  ✅ Cost reduction claim VALIDATED: {cost_reduction:.1f}% is within 40-60% range")
    else:
        print(f"  ❌ Cost reduction claim FAILED: {cost_reduction:.1f}% is NOT within 40-60% range")
    
    if batch_api_calls < len(test_texts):
        print(f"  ✅ API call reduction VALIDATED: {batch_api_calls} < {len(test_texts)}")
    else:
        print(f"  ❌ API call reduction FAILED: {batch_api_calls} >= {len(test_texts)}")
    
    print(f"\n📋 CONCLUSION:")
    if cost_reduction < 40:
        print(f"  💥 BATCH PROCESSING DOES NOT DELIVER PROMISED COST SAVINGS")
        print(f"  🚨 Actual cost reduction: {cost_reduction:.1f}% vs claimed 40-60%")
    else:
        print(f"  ✅ Batch processing delivers on cost reduction claims")


if __name__ == "__main__":
    asyncio.run(test_batch_cost_claims())