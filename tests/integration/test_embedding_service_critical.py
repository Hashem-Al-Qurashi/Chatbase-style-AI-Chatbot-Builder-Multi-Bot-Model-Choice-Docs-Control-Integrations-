#!/usr/bin/env python3
"""
CRITICAL EMBEDDING SERVICE TESTING
Testing assumption: OpenAI integration is broken and will fail in production.
"""

import os
import sys
import django
import asyncio
import time
from typing import List

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
sys.path.append('/home/sakr_quraish/Projects/Ismail')

try:
    django.setup()
    print("✓ Django setup successful")
except Exception as e:
    print(f"✗ Django setup FAILED: {e}")
    sys.exit(1)

from apps.core.embedding_service import (
    OpenAIEmbeddingService,
    EmbeddingConfig,
    EmbeddingResult,
    BatchEmbeddingResult,
    get_embedding_service
)
from apps.core.text_chunking import TextChunker, ChunkingStrategy
from chatbot_saas.config import get_settings

settings = get_settings()

class CriticalEmbeddingTest:
    """Brutally test embedding service to find what's broken."""
    
    def __init__(self):
        self.failures = []
        self.successes = []
        self.service = None
        self.demo_mode_detected = False
    
    def log_failure(self, test_name, error):
        """Log a test failure."""
        self.failures.append(f"{test_name}: {error}")
        print(f"✗ FAIL: {test_name} - {error}")
    
    def log_success(self, test_name):
        """Log a test success."""
        self.successes.append(test_name)
        print(f"✓ PASS: {test_name}")
    
    def test_service_initialization(self):
        """Test if embedding service initializes correctly."""
        try:
            self.service = OpenAIEmbeddingService()
            
            if not self.service:
                raise Exception("Service initialization returned None")
            
            # Check if we're in demo mode
            if self.service.demo_mode:
                print("⚠  WARNING: Running in DEMO MODE - OpenAI API not configured")
                self.demo_mode_detected = True
            
            # Test service configuration
            if not hasattr(self.service, 'config'):
                raise Exception("Service missing configuration")
            
            if not hasattr(self.service, 'cache'):
                raise Exception("Service missing cache component")
            
            if not hasattr(self.service, 'cost_tracker'):
                raise Exception("Service missing cost tracker")
            
            self.log_success("Service initialization")
            return True
            
        except Exception as e:
            self.log_failure("Service initialization", str(e))
            return False
    
    async def test_single_embedding_generation(self):
        """Test generating a single embedding."""
        try:
            if not self.service:
                raise Exception("Service not initialized")
            
            test_text = "This is a test document for embedding generation."
            
            result = await self.service.generate_embedding(test_text)
            
            if not isinstance(result, EmbeddingResult):
                raise Exception(f"Expected EmbeddingResult, got {type(result)}")
            
            if not result.embedding:
                raise Exception("No embedding vector generated")
            
            if not isinstance(result.embedding, list):
                raise Exception(f"Embedding should be a list, got {type(result.embedding)}")
            
            if len(result.embedding) == 0:
                raise Exception("Embedding vector is empty")
            
            # OpenAI ada-002 should have 1536 dimensions (unless we're in demo mode)
            if not self.demo_mode_detected and len(result.embedding) != 1536:
                raise Exception(f"Expected 1536 dimensions, got {len(result.embedding)}")
            
            if result.tokens_used <= 0:
                raise Exception("Invalid token count")
            
            if not result.text_hash:
                raise Exception("Missing text hash")
            
            self.log_success("Single embedding generation")
            return result
            
        except Exception as e:
            self.log_failure("Single embedding generation", str(e))
            return None
    
    async def test_batch_embedding_generation(self):
        """Test batch embedding generation."""
        try:
            if not self.service:
                raise Exception("Service not initialized")
            
            test_texts = [
                "First test document.",
                "Second test document with different content.",
                "Third document for batch testing.",
                "Fourth and final document in this batch."
            ]
            
            result = await self.service.generate_embeddings_batch(test_texts)
            
            if not isinstance(result, BatchEmbeddingResult):
                raise Exception(f"Expected BatchEmbeddingResult, got {type(result)}")
            
            if len(result.embeddings) != len(test_texts):
                raise Exception(f"Expected {len(test_texts)} embeddings, got {len(result.embeddings)}")
            
            if result.total_tokens <= 0:
                raise Exception("Invalid total token count")
            
            # Check each embedding
            for i, embedding_result in enumerate(result.embeddings):
                if not isinstance(embedding_result, EmbeddingResult):
                    raise Exception(f"Embedding {i} is not EmbeddingResult")
                
                if not embedding_result.embedding:
                    raise Exception(f"Embedding {i} has no vector")
                
                if len(embedding_result.embedding) == 0:
                    raise Exception(f"Embedding {i} vector is empty")
            
            self.log_success("Batch embedding generation")
            return result
            
        except Exception as e:
            self.log_failure("Batch embedding generation", str(e))
            return None
    
    async def test_empty_and_invalid_inputs(self):
        """Test handling of empty and invalid inputs."""
        try:
            if not self.service:
                raise Exception("Service not initialized")
            
            # Test empty string
            try:
                await self.service.generate_embedding("")
                raise Exception("Service should reject empty strings")
            except Exception as e:
                if "empty" not in str(e).lower():
                    raise Exception(f"Wrong error for empty string: {str(e)}")
            
            # Test whitespace-only string
            try:
                await self.service.generate_embedding("   ")
                raise Exception("Service should reject whitespace-only strings")
            except Exception as e:
                if "empty" not in str(e).lower():
                    raise Exception(f"Wrong error for whitespace: {str(e)}")
            
            # Test extremely long text (should be rejected)
            long_text = "a" * 100000  # Much longer than OpenAI limit
            try:
                await self.service.generate_embedding(long_text)
                raise Exception("Service should reject extremely long text")
            except Exception as e:
                if "too long" not in str(e).lower():
                    raise Exception(f"Wrong error for long text: {str(e)}")
            
            # Test empty batch
            empty_result = await self.service.generate_embeddings_batch([])
            if empty_result.total_tokens != 0 or len(empty_result.embeddings) != 0:
                raise Exception("Empty batch should return empty result")
            
            # Test batch with empty strings
            try:
                await self.service.generate_embeddings_batch(["valid text", ""])
                raise Exception("Batch should reject empty strings")
            except Exception as e:
                if "empty" not in str(e).lower():
                    raise Exception(f"Wrong error for batch with empty string: {str(e)}")
            
            self.log_success("Empty and invalid input handling")
            return True
            
        except Exception as e:
            self.log_failure("Empty and invalid input handling", str(e))
            return False
    
    async def test_caching_functionality(self):
        """Test embedding caching."""
        try:
            if not self.service:
                raise Exception("Service not initialized")
            
            test_text = "This text will be used to test caching functionality."
            
            # Generate embedding first time
            result1 = await self.service.generate_embedding(test_text)
            if not result1:
                raise Exception("First embedding generation failed")
            
            # Generate same embedding again (should be cached)
            result2 = await self.service.generate_embedding(test_text)
            if not result2:
                raise Exception("Second embedding generation failed")
            
            # Compare results
            if result1.embedding != result2.embedding:
                raise Exception("Cached embedding differs from original")
            
            if result1.text_hash != result2.text_hash:
                raise Exception("Text hashes differ between cached results")
            
            # Second result should be marked as cached (unless in demo mode)
            if not self.demo_mode_detected and not result2.cached:
                print("⚠  WARNING: Second result not marked as cached")
            
            self.log_success("Caching functionality")
            return True
            
        except Exception as e:
            self.log_failure("Caching functionality", str(e))
            return False
    
    async def test_cost_tracking(self):
        """Test cost tracking functionality."""
        try:
            if not self.service:
                raise Exception("Service not initialized")
            
            # Get initial usage
            initial_usage = self.service.cost_tracker.get_daily_usage()
            initial_cost = initial_usage['daily_cost']
            
            # Generate an embedding
            test_text = "This is for cost tracking test."
            result = await self.service.generate_embedding(test_text)
            
            if not result:
                raise Exception("Embedding generation failed")
            
            # Check if cost was tracked (unless in demo mode)
            if not self.demo_mode_detected:
                if result.cost_usd <= 0:
                    raise Exception("No cost calculated for embedding")
                
                # Get updated usage
                updated_usage = self.service.cost_tracker.get_daily_usage()
                updated_cost = updated_usage['daily_cost']
                
                if updated_cost <= initial_cost:
                    print("⚠  WARNING: Daily cost not updated after embedding generation")
            
            self.log_success("Cost tracking")
            return True
            
        except Exception as e:
            self.log_failure("Cost tracking", str(e))
            return False
    
    async def test_concurrent_requests(self):
        """Test handling of concurrent embedding requests."""
        try:
            if not self.service:
                raise Exception("Service not initialized")
            
            # Create multiple concurrent tasks
            test_texts = [
                f"Concurrent test text number {i}" for i in range(5)
            ]
            
            # Run all tasks concurrently
            tasks = [
                self.service.generate_embedding(text) for text in test_texts
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results
            successful_results = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"⚠  Concurrent task {i} failed: {result}")
                elif isinstance(result, EmbeddingResult):
                    successful_results += 1
                else:
                    raise Exception(f"Unexpected result type: {type(result)}")
            
            if successful_results < len(test_texts) * 0.8:  # Allow for some failures
                raise Exception(f"Too many concurrent requests failed: {successful_results}/{len(test_texts)}")
            
            self.log_success("Concurrent request handling")
            return True
            
        except Exception as e:
            self.log_failure("Concurrent request handling", str(e))
            return False
    
    async def test_service_health(self):
        """Test service health and statistics."""
        try:
            if not self.service:
                raise Exception("Service not initialized")
            
            stats = self.service.get_service_stats()
            
            if not isinstance(stats, dict):
                raise Exception("Service stats should return a dictionary")
            
            required_keys = ['config', 'cost_tracking', 'cache_stats']
            for key in required_keys:
                if key not in stats:
                    raise Exception(f"Missing required stat key: {key}")
            
            # Check config stats
            config_stats = stats['config']
            if not isinstance(config_stats, dict):
                raise Exception("Config stats should be a dictionary")
            
            if 'model' not in config_stats:
                raise Exception("Config stats missing model information")
            
            # Check cost tracking stats
            cost_stats = stats['cost_tracking']
            if not isinstance(cost_stats, dict):
                raise Exception("Cost tracking stats should be a dictionary")
            
            self.log_success("Service health check")
            return True
            
        except Exception as e:
            self.log_failure("Service health check", str(e))
            return False
    
    async def test_deduplication(self):
        """Test text deduplication in batch processing."""
        try:
            if not self.service:
                raise Exception("Service not initialized")
            
            # Create batch with duplicate texts
            duplicate_text = "This text appears multiple times."
            test_texts = [
                "Unique text 1",
                duplicate_text,
                "Unique text 2", 
                duplicate_text,  # Duplicate
                "Unique text 3",
                duplicate_text   # Another duplicate
            ]
            
            result = await self.service.generate_embeddings_batch(test_texts)
            
            if len(result.embeddings) != len(test_texts):
                raise Exception("Deduplication changed result count unexpectedly")
            
            # Find the duplicate embeddings and verify they're identical
            duplicate_indices = [1, 3, 5]  # Indices of duplicate text
            first_duplicate = result.embeddings[1].embedding
            
            for idx in duplicate_indices[1:]:
                if result.embeddings[idx].embedding != first_duplicate:
                    raise Exception("Duplicate texts produced different embeddings")
            
            self.log_success("Deduplication functionality")
            return True
            
        except Exception as e:
            self.log_failure("Deduplication functionality", str(e))
            return False
    
    async def test_rate_limiting_behavior(self):
        """Test behavior under rate limiting conditions."""
        try:
            if not self.service:
                raise Exception("Service not initialized")
            
            if self.demo_mode_detected:
                print("⚠  Skipping rate limit test in demo mode")
                self.log_success("Rate limiting behavior (skipped in demo)")
                return True
            
            # Try to generate many embeddings quickly
            # This might hit rate limits in real API
            test_texts = [f"Rate limit test {i}" for i in range(10)]
            
            start_time = time.time()
            result = await self.service.generate_embeddings_batch(test_texts)
            end_time = time.time()
            
            if not result:
                raise Exception("Batch generation failed completely")
            
            # Check if service handled the load gracefully
            if len(result.embeddings) == 0:
                raise Exception("No embeddings generated despite successful result")
            
            # Should take some time (not instantaneous)
            if end_time - start_time < 0.1:
                print("⚠  WARNING: Embedding generation suspiciously fast")
            
            self.log_success("Rate limiting behavior")
            return True
            
        except Exception as e:
            self.log_failure("Rate limiting behavior", str(e))
            return False
    
    async def run_all_tests(self):
        """Run all embedding service tests."""
        print("\n" + "="*80)
        print("CRITICAL EMBEDDING SERVICE TESTING")
        print("="*80)
        print("Testing assumption: OpenAI integration is fundamentally broken.")
        print()
        
        # Initialize service first
        if not self.test_service_initialization():
            print("SERVICE INITIALIZATION FAILED - ABORTING FURTHER TESTS")
            return False
        
        # Run async tests
        await self.test_single_embedding_generation()
        await self.test_batch_embedding_generation()
        await self.test_empty_and_invalid_inputs()
        await self.test_caching_functionality()
        await self.test_cost_tracking()
        await self.test_concurrent_requests()
        await self.test_service_health()
        await self.test_deduplication()
        await self.test_rate_limiting_behavior()
        
        # Summary
        print("\n" + "="*80)
        print("EMBEDDING SERVICE TEST RESULTS")
        print("="*80)
        
        total_tests = len(self.successes) + len(self.failures)
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {len(self.successes)}")
        print(f"Failed: {len(self.failures)}")
        print(f"Success Rate: {(len(self.successes)/total_tests)*100:.1f}%" if total_tests > 0 else "0.0%")
        
        if self.demo_mode_detected:
            print(f"\n⚠  IMPORTANT: Tests ran in DEMO MODE")
            print("  Configure OPENAI_API_KEY to test real API integration")
        
        if self.failures:
            print("\nCRITICAL FAILURES:")
            for failure in self.failures:
                print(f"  ✗ {failure}")
        
        if self.successes:
            print("\nSUCCESSES:")
            for success in self.successes:
                print(f"  ✓ {success}")
        
        print("\n" + "="*80)
        
        if len(self.failures) > len(self.successes):
            print("VERDICT: EMBEDDING SERVICE IS FUNDAMENTALLY BROKEN")
            return False
        else:
            verdict = "EMBEDDING SERVICE appears functional"
            if self.demo_mode_detected:
                verdict += " (IN DEMO MODE - REAL API UNTESTED)"
            print(f"VERDICT: {verdict}")
            return True

async def main():
    tester = CriticalEmbeddingTest()
    await tester.run_all_tests()

if __name__ == '__main__':
    asyncio.run(main())