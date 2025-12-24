#!/usr/bin/env python3
"""
BATCH PROCESSING DIAGNOSTIC TEST

This test focuses specifically on the batch processing failure to understand why
batching is not working and costs are not being reduced.
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

from django.core.cache import cache
from apps.core.embedding_service import OpenAIEmbeddingService, EmbeddingConfig


async def diagnostic_test():
    """Run detailed batch processing diagnostic."""
    print("🔍 BATCH PROCESSING DIAGNOSTIC TEST")
    print("=" * 50)
    
    # Clear cache for clean test
    cache.clear()
    
    # Configure service for testing
    config = EmbeddingConfig(
        model="text-embedding-ada-002",
        max_batch_size=10,
        enable_caching=True,
        enable_deduplication=True,
        daily_budget_usd=10.0
    )
    
    service = OpenAIEmbeddingService(config)
    
    # Test data
    test_texts = [
        "Short text one",
        "Short text two", 
        "Short text three"
    ]
    
    print(f"Testing with {len(test_texts)} short texts...")
    print("Texts:", test_texts)
    
    try:
        # Test batch processing
        print("\n🧪 TESTING BATCH PROCESSING")
        print("-" * 30)
        
        start_time = time.time()
        result = await service.generate_embeddings_batch(test_texts)
        end_time = time.time()
        
        print(f"Batch processing completed in {(end_time - start_time)*1000:.0f}ms")
        print(f"Embeddings generated: {len(result.embeddings)}")
        print(f"Total tokens: {result.total_tokens}")
        print(f"Total cost: ${result.total_cost_usd:.8f}")
        print(f"API calls made: {result.api_calls}")
        print(f"Cache hits: {result.cache_hits}")
        print(f"Failed items: {len(result.failed_items)}")
        
        if result.failed_items:
            print("Failed items:")
            for idx, error in result.failed_items:
                print(f"  [{idx}]: {error}")
        
        # Validate each embedding
        for i, embedding_result in enumerate(result.embeddings):
            print(f"Embedding {i+1}:")
            print(f"  Dimensions: {embedding_result.dimensions}")
            print(f"  Tokens: {embedding_result.tokens_used}")
            print(f"  Cost: ${embedding_result.cost_usd:.8f}")
            print(f"  Cached: {embedding_result.cached}")
            print(f"  Model: {embedding_result.model}")
        
        # Test individual calls for comparison
        print("\n🧪 TESTING INDIVIDUAL CALLS")
        print("-" * 30)
        
        cache.clear()  # Clear cache to ensure fair comparison
        
        individual_start = time.time()
        individual_costs = []
        individual_tokens = []
        
        for i, text in enumerate(test_texts):
            print(f"Processing text {i+1}: '{text[:20]}...'")
            individual_result = await service.generate_embedding(text)
            individual_costs.append(individual_result.cost_usd)
            individual_tokens.append(individual_result.tokens_used)
            print(f"  Result: {individual_result.dimensions}d, {individual_result.tokens_used} tokens, ${individual_result.cost_usd:.8f}")
        
        individual_end = time.time()
        
        individual_total_cost = sum(individual_costs)
        individual_total_tokens = sum(individual_tokens)
        individual_time = individual_end - individual_start
        
        print(f"\nIndividual totals:")
        print(f"  Total cost: ${individual_total_cost:.8f}")
        print(f"  Total tokens: {individual_total_tokens}")
        print(f"  Total time: {individual_time*1000:.0f}ms")
        
        # Compare results
        print("\n📊 COMPARISON ANALYSIS")
        print("-" * 30)
        
        if result.total_cost_usd > 0 and individual_total_cost > 0:
            cost_diff = ((individual_total_cost - result.total_cost_usd) / individual_total_cost) * 100
            print(f"Cost difference: {cost_diff:.1f}% ({'SAVING' if cost_diff > 0 else 'INCREASE'})")
        else:
            print("❌ Cost comparison failed - one or both costs are zero")
        
        time_diff = ((individual_time*1000 - (end_time - start_time)*1000) / (individual_time*1000)) * 100
        print(f"Time difference: {time_diff:.1f}% ({'FASTER' if time_diff > 0 else 'SLOWER'})")
        
        # Detailed analysis
        print("\n🔍 DETAILED ANALYSIS")
        print("-" * 30)
        
        if len(result.embeddings) != len(test_texts):
            print(f"❌ BATCH FAILED: Expected {len(test_texts)} embeddings, got {len(result.embeddings)}")
        else:
            print(f"✅ BATCH SUCCESS: Generated all {len(result.embeddings)} embeddings")
        
        if result.api_calls == 0:
            print("❌ NO API CALLS: Batch processing made no API calls")
        elif result.api_calls == 1:
            print("✅ OPTIMAL API CALLS: Batch processing used 1 API call")
        else:
            print(f"⚠️  SUBOPTIMAL API CALLS: Batch processing used {result.api_calls} API calls")
        
        if result.total_cost_usd == 0:
            print("❌ NO COST TRACKING: Batch cost is zero")
        else:
            print(f"✅ COST TRACKING: Batch cost ${result.total_cost_usd:.8f}")
            
    except Exception as e:
        print(f"❌ DIAGNOSTIC FAILED: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(diagnostic_test())