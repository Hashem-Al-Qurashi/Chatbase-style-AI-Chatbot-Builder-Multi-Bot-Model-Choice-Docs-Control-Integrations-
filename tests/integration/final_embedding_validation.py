#!/usr/bin/env python3
"""
FINAL COMPREHENSIVE EMBEDDING SERVICE VALIDATION

This test validates all fixed issues and confirms Step 3 is production-ready.

FIXED ISSUES:
1. ✅ Django async context - using sync_to_async properly
2. ✅ Large text handling - added proper validation and limits  
3. ✅ Batch processing - confirmed working (costs are per-token, not per-API-call)
4. ✅ Caching system - working with 100% hit rates on repeat calls
5. ✅ Database integration - using proper async wrappers

VALIDATION CRITERIA:
- OpenAI API integration generates valid 1536-dim embeddings
- Batch processing reduces API calls (1 call for multiple texts vs N calls)
- Caching prevents duplicate API calls (100% hit rate on repeats)
- Database operations work without async context errors
- Error handling works for edge cases
- Cost tracking is accurate
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
from django.db import transaction
from asgiref.sync import sync_to_async

from apps.core.embedding_service import OpenAIEmbeddingService, EmbeddingConfig
from apps.knowledge.models import KnowledgeSource, KnowledgeChunk
from apps.chatbots.models import Chatbot
from apps.accounts.models import User


class FinalEmbeddingValidation:
    """Final comprehensive validation of embedding service."""
    
    def __init__(self):
        self.config = EmbeddingConfig(
            model="text-embedding-ada-002",
            max_batch_size=5,
            enable_caching=True,
            enable_deduplication=True,
            daily_budget_usd=10.0
        )
        self.service = OpenAIEmbeddingService(self.config)
        self.results = {}
        
    async def test_api_integration(self):
        """Test 1: OpenAI API Integration"""
        print("🧪 TEST 1: OpenAI API Integration")
        print("-" * 40)
        
        test_text = "This is a test document for embedding validation."
        
        try:
            result = await self.service.generate_embedding(test_text)
            
            assert len(result.embedding) == 1536, f"Wrong embedding dimension: {len(result.embedding)}"
            assert result.model == "text-embedding-ada-002", f"Wrong model: {result.model}"
            assert result.tokens_used > 0, f"No tokens used: {result.tokens_used}"
            assert result.cost_usd > 0, f"No cost calculated: {result.cost_usd}"
            assert not result.cached, "First call should not be cached"
            
            print(f"✅ Generated 1536-dim embedding, {result.tokens_used} tokens, ${result.cost_usd:.8f}")
            self.results["api_integration"] = "PASSED"
            
        except Exception as e:
            print(f"❌ API integration failed: {e}")
            self.results["api_integration"] = f"FAILED: {e}"
    
    async def test_batch_processing(self):
        """Test 2: Batch Processing Efficiency"""
        print("\n🧪 TEST 2: Batch Processing vs Individual Calls")
        print("-" * 40)
        
        cache.clear()  # Clean slate
        
        test_texts = [
            "First test document for batch processing validation.",
            "Second test document for batch processing validation.", 
            "Third test document for batch processing validation."
        ]
        
        try:
            # Method 1: Individual calls
            individual_start = time.time()
            for text in test_texts:
                await self.service.generate_embedding(text)
            individual_time = time.time() - individual_start
            individual_api_calls = 3  # One per text
            
            cache.clear()  # Reset for fair comparison
            
            # Method 2: Batch call
            batch_start = time.time()
            batch_result = await self.service.generate_embeddings_batch(test_texts)
            batch_time = time.time() - batch_start
            batch_api_calls = batch_result.api_calls
            
            # Validate batch processing efficiency
            assert len(batch_result.embeddings) == 3, f"Wrong embedding count: {len(batch_result.embeddings)}"
            assert batch_api_calls == 1, f"Expected 1 API call, got {batch_api_calls}"
            
            api_call_reduction = ((individual_api_calls - batch_api_calls) / individual_api_calls) * 100
            time_improvement = batch_time < individual_time
            
            print(f"Individual: 3 API calls, {individual_time:.2f}s")
            print(f"Batch: {batch_api_calls} API call, {batch_time:.2f}s")
            print(f"API call reduction: {api_call_reduction:.0f}%")
            print(f"Time improvement: {time_improvement}")
            
            assert api_call_reduction >= 60, f"Insufficient API call reduction: {api_call_reduction:.1f}%"
            
            print(f"✅ Batch processing reduces API calls by {api_call_reduction:.0f}%")
            self.results["batch_processing"] = "PASSED"
            
        except Exception as e:
            print(f"❌ Batch processing failed: {e}")
            self.results["batch_processing"] = f"FAILED: {e}"
    
    async def test_caching_system(self):
        """Test 3: Caching System"""
        print("\n🧪 TEST 3: Caching System")
        print("-" * 40)
        
        cache.clear()
        
        test_texts = [
            "Caching test document one.",
            "Caching test document two."
        ]
        
        try:
            # First call - should miss cache
            first_result = await self.service.generate_embeddings_batch(test_texts)
            assert first_result.cache_hits == 0, f"Unexpected cache hits: {first_result.cache_hits}"
            assert first_result.api_calls == 1, f"Expected 1 API call: {first_result.api_calls}"
            
            # Second call - should hit cache
            second_result = await self.service.generate_embeddings_batch(test_texts)
            assert second_result.cache_hits == 2, f"Expected 2 cache hits: {second_result.cache_hits}"
            assert second_result.api_calls == 0, f"Expected 0 API calls: {second_result.api_calls}"
            
            cache_hit_rate = (second_result.cache_hits / len(test_texts)) * 100
            
            print(f"First call: {first_result.cache_hits} cache hits, {first_result.api_calls} API calls")
            print(f"Second call: {second_result.cache_hits} cache hits, {second_result.api_calls} API calls")
            print(f"Cache hit rate: {cache_hit_rate:.0f}%")
            
            assert cache_hit_rate == 100, f"Expected 100% cache hit rate: {cache_hit_rate}"
            
            print("✅ Caching system working with 100% hit rate")
            self.results["caching_system"] = "PASSED"
            
        except Exception as e:
            print(f"❌ Caching system failed: {e}")
            self.results["caching_system"] = f"FAILED: {e}"
    
    @sync_to_async
    def create_test_data(self):
        """Create test database objects."""
        # Clean up any existing test data
        User.objects.filter(email__startswith="test_embed_final").delete()
        
        user = User.objects.create_user(
            email=f"test_embed_final_{int(time.time())}@test.com",
            password="test_password",
            first_name="Test",
            last_name="User"
        )
        
        chatbot = Chatbot.objects.create(
            name=f"Test Chatbot {int(time.time())}",
            description="Test chatbot for final embedding validation",
            user=user
        )
        
        source = KnowledgeSource.objects.create(
            chatbot=chatbot,
            name="Test Final Source",
            description="Test source for final validation",
            content_type="text",
            is_citable=True,
            status="completed"
        )
        
        chunks = []
        test_contents = [
            "Final validation test chunk one content.",
            "Final validation test chunk two content.",
            "Final validation test chunk three content."
        ]
        
        for i, content in enumerate(test_contents):
            chunk = KnowledgeChunk.objects.create(
                source=source,
                content=content,
                chunk_index=i,
                is_citable=True,
                token_count=len(content.split()) * 2
            )
            chunks.append(chunk)
        
        return user, chunks
    
    @sync_to_async
    def cleanup_test_data(self, user):
        """Clean up test database objects."""
        user.delete()  # Cascades to all related objects
    
    async def test_database_integration(self):
        """Test 4: Database Integration"""
        print("\n🧪 TEST 4: Database Integration")
        print("-" * 40)
        
        try:
            # Create test data
            user, chunks = await self.create_test_data()
            
            print(f"Created {len(chunks)} test chunks")
            
            # Generate embeddings for chunks
            chunk_embeddings = await self.service.generate_embeddings_for_knowledge_chunks(
                chunks, update_db=True
            )
            
            assert len(chunk_embeddings) == len(chunks), f"Wrong embedding count: {len(chunk_embeddings)}"
            
            # Verify database storage
            @sync_to_async
            def verify_chunk_embeddings():
                for chunk, embedding_result in chunk_embeddings:
                    chunk.refresh_from_db()
                    assert chunk.embedding_vector is not None, f"Chunk {chunk.id} has no embedding"
                    assert len(chunk.embedding_vector) == 1536, f"Wrong dimension: {len(chunk.embedding_vector)}"
                    assert chunk.embedding_model == "text-embedding-ada-002", f"Wrong model: {chunk.embedding_model}"
                    assert chunk.is_citable == True, f"Privacy flag not preserved: {chunk.is_citable}"
            
            await verify_chunk_embeddings()
            
            print(f"✅ Successfully stored {len(chunks)} embeddings with privacy flags")
            self.results["database_integration"] = "PASSED"
            
            # Cleanup
            await self.cleanup_test_data(user)
            
        except Exception as e:
            print(f"❌ Database integration failed: {e}")
            self.results["database_integration"] = f"FAILED: {e}"
    
    async def test_error_handling(self):
        """Test 5: Error Handling"""
        print("\n🧪 TEST 5: Error Handling")
        print("-" * 40)
        
        try:
            # Test empty text
            try:
                await self.service.generate_embedding("")
                assert False, "Empty text should be rejected"
            except Exception as e:
                assert "empty" in str(e).lower(), f"Wrong error for empty text: {e}"
            
            # Test large text
            large_text = "word " * 10000  # ~50k characters
            try:
                await self.service.generate_embedding(large_text)
                assert False, "Large text should be rejected"
            except Exception as e:
                assert "too long" in str(e).lower(), f"Wrong error for large text: {e}"
            
            # Test invalid configuration
            try:
                invalid_config = EmbeddingConfig(max_batch_size=0)
                assert False, "Invalid config should be rejected"
            except ValueError:
                pass  # Expected
            
            print("✅ Error handling works for empty text, large text, and invalid config")
            self.results["error_handling"] = "PASSED"
            
        except Exception as e:
            print(f"❌ Error handling failed: {e}")
            self.results["error_handling"] = f"FAILED: {e}"
    
    async def test_cost_tracking(self):
        """Test 6: Cost Tracking"""
        print("\n🧪 TEST 6: Cost Tracking")
        print("-" * 40)
        
        try:
            # Get initial usage
            initial_usage = self.service.cost_tracker.get_daily_usage()
            initial_cost = initial_usage["daily_cost"]
            
            # Generate embedding and track cost
            test_text = "Cost tracking validation text."
            result = await self.service.generate_embedding(test_text)
            
            # Get updated usage
            updated_usage = self.service.cost_tracker.get_daily_usage()
            final_cost = updated_usage["daily_cost"]
            
            cost_increase = final_cost - initial_cost
            
            assert cost_increase > 0, f"No cost increase recorded: {cost_increase}"
            assert abs(cost_increase - result.cost_usd) < 0.000001, f"Cost mismatch: {cost_increase} vs {result.cost_usd}"
            
            print(f"Cost increase: ${cost_increase:.8f}")
            print(f"Embedding cost: ${result.cost_usd:.8f}")
            print(f"Daily usage: ${final_cost:.8f} / ${updated_usage['daily_budget']:.2f}")
            
            print("✅ Cost tracking accurate and functional")
            self.results["cost_tracking"] = "PASSED"
            
        except Exception as e:
            print(f"❌ Cost tracking failed: {e}")
            self.results["cost_tracking"] = f"FAILED: {e}"
    
    def print_final_report(self):
        """Print final validation report."""
        print("\n" + "=" * 60)
        print("🎯 FINAL EMBEDDING SERVICE VALIDATION REPORT")
        print("=" * 60)
        
        passed_count = sum(1 for result in self.results.values() if result == "PASSED")
        total_count = len(self.results)
        
        print(f"\n📊 SUMMARY:")
        print(f"   Tests Passed: {passed_count}/{total_count}")
        print(f"   Success Rate: {(passed_count/total_count)*100:.1f}%")
        
        print(f"\n📋 DETAILED RESULTS:")
        for test_name, result in self.results.items():
            status = "✅ PASSED" if result == "PASSED" else f"❌ {result}"
            print(f"   {test_name.replace('_', ' ').title()}: {status}")
        
        if passed_count == total_count:
            print(f"\n🎉 CONCLUSION: STEP 3 EMBEDDING SERVICE IS PRODUCTION READY")
            print("   All critical functionality has been validated and is working correctly.")
            print("   The service can be confidently used for embedding generation.")
        else:
            print(f"\n💥 CONCLUSION: STEP 3 STILL HAS ISSUES")
            print(f"   {total_count - passed_count} tests failed and must be resolved.")
        
        print("=" * 60)
        
        return passed_count == total_count


async def main():
    """Run final comprehensive validation."""
    print("🚀 FINAL COMPREHENSIVE EMBEDDING SERVICE VALIDATION")
    print("This test validates all fixes and confirms production readiness.")
    print()
    
    validator = FinalEmbeddingValidation()
    
    # Run all validation tests
    await validator.test_api_integration()
    await validator.test_batch_processing()
    await validator.test_caching_system()
    await validator.test_database_integration()
    await validator.test_error_handling()
    await validator.test_cost_tracking()
    
    # Print final report
    success = validator.print_final_report()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)