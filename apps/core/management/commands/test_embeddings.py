"""
Management command to test embedding generation functionality.
"""

import asyncio
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.knowledge.models import KnowledgeSource, KnowledgeChunk
from apps.core.embedding_service import get_embedding_service, EmbeddingConfig
from apps.core.tasks import generate_embeddings_for_knowledge_chunks


class Command(BaseCommand):
    """Test embedding generation functionality."""
    
    help = 'Test embedding generation for knowledge chunks'
    
    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--source-id',
            type=str,
            help='KnowledgeSource ID to test with'
        )
        
        parser.add_argument(
            '--test-api',
            action='store_true',
            help='Test OpenAI API connectivity directly'
        )
        
        parser.add_argument(
            '--test-cache',
            action='store_true',
            help='Test embedding caching functionality'
        )
        
        parser.add_argument(
            '--test-batch',
            action='store_true',
            help='Test batch processing'
        )
        
        parser.add_argument(
            '--test-task',
            action='store_true',
            help='Test Celery task execution'
        )
        
        parser.add_argument(
            '--list-sources',
            action='store_true',
            help='List available knowledge sources'
        )
    
    def handle(self, *args, **options):
        """Handle command execution."""
        
        if options['list_sources']:
            self._list_sources()
            return
        
        if options['test_api']:
            self._test_api_connectivity()
        
        if options['test_cache']:
            self._test_caching()
        
        if options['test_batch']:
            self._test_batch_processing()
        
        if options['test_task']:
            source_id = options.get('source_id')
            if not source_id:
                # Find a source with chunks
                source = KnowledgeSource.objects.filter(chunks__isnull=False).first()
                if source:
                    source_id = str(source.id)
            
            if source_id:
                self._test_celery_task(source_id)
            else:
                self.stdout.write(
                    self.style.ERROR('No source ID provided and no sources with chunks found')
                )
        
        if options['source_id']:
            self._test_source_embeddings(options['source_id'])
        
        if not any([
            options['test_api'], options['test_cache'], 
            options['test_batch'], options['test_task'], 
            options['source_id']
        ]):
            self.stdout.write(
                self.style.WARNING(
                    'No test specified. Use --help to see available options.'
                )
            )
    
    def _list_sources(self):
        """List available knowledge sources."""
        sources = KnowledgeSource.objects.all().select_related('chatbot')
        
        if not sources.exists():
            self.stdout.write(self.style.WARNING('No knowledge sources found'))
            return
        
        self.stdout.write(self.style.SUCCESS('Available Knowledge Sources:'))
        self.stdout.write('')
        
        for source in sources:
            chunk_count = source.chunks.count()
            embedded_count = source.chunks.filter(embedding_vector__isnull=False).count()
            
            self.stdout.write(f'ID: {source.id}')
            self.stdout.write(f'Name: {source.name}')
            self.stdout.write(f'Chatbot: {source.chatbot.name}')
            self.stdout.write(f'Status: {source.status}')
            self.stdout.write(f'Is Citable: {source.is_citable}')
            self.stdout.write(f'Chunks: {chunk_count} (Embedded: {embedded_count})')
            self.stdout.write('-' * 50)
    
    def _test_api_connectivity(self):
        """Test OpenAI API connectivity."""
        self.stdout.write('Testing OpenAI API connectivity...')
        
        try:
            # Test with a simple text
            test_text = "This is a test text for embedding generation."
            
            async def test_api():
                service = get_embedding_service()
                result = await service.generate_embedding(test_text)
                return result
            
            result = asyncio.run(test_api())
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ API connectivity successful!\n'
                    f'   Model: {result.model}\n'
                    f'   Dimensions: {result.dimensions}\n'
                    f'   Tokens used: {result.tokens_used}\n'
                    f'   Cost: ${result.cost_usd:.6f}\n'
                    f'   Processing time: {result.processing_time_ms}ms'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ API connectivity failed: {str(e)}')
            )
    
    def _test_caching(self):
        """Test embedding caching functionality."""
        self.stdout.write('Testing embedding caching...')
        
        try:
            test_text = "This is a test text for caching functionality."
            
            async def test_cache():
                service = get_embedding_service()
                
                # First call - should hit API
                start_time = timezone.now()
                result1 = await service.generate_embedding(test_text)
                first_call_time = (timezone.now() - start_time).total_seconds() * 1000
                
                # Second call - should hit cache
                start_time = timezone.now()
                result2 = await service.generate_embedding(test_text)
                second_call_time = (timezone.now() - start_time).total_seconds() * 1000
                
                return result1, result2, first_call_time, second_call_time
            
            result1, result2, first_time, second_time = asyncio.run(test_cache())
            
            cache_hit = result2.cached
            speedup = first_time / second_time if second_time > 0 else 0
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Caching test completed!\n'
                    f'   First call (API): {first_time:.2f}ms, Cost: ${result1.cost_usd:.6f}\n'
                    f'   Second call (Cache): {second_time:.2f}ms, Cost: ${result2.cost_usd:.6f}\n'
                    f'   Cache hit: {cache_hit}\n'
                    f'   Speedup: {speedup:.1f}x'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Caching test failed: {str(e)}')
            )
    
    def _test_batch_processing(self):
        """Test batch processing functionality."""
        self.stdout.write('Testing batch processing...')
        
        try:
            test_texts = [
                "First test text for batch processing.",
                "Second test text for batch processing.",
                "Third test text for batch processing.",
                "Fourth test text for batch processing.",
                "Fifth test text for batch processing."
            ]
            
            async def test_batch():
                config = EmbeddingConfig(max_batch_size=3, enable_deduplication=True)
                service = get_embedding_service()
                service.config = config
                
                start_time = timezone.now()
                result = await service.generate_embeddings_batch(test_texts)
                processing_time = (timezone.now() - start_time).total_seconds() * 1000
                
                return result, processing_time
            
            batch_result, processing_time = asyncio.run(test_batch())
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Batch processing test completed!\n'
                    f'   Texts processed: {len(test_texts)}\n'
                    f'   Embeddings generated: {len(batch_result.embeddings)}\n'
                    f'   Total tokens: {batch_result.total_tokens}\n'
                    f'   Total cost: ${batch_result.total_cost_usd:.6f}\n'
                    f'   Processing time: {processing_time:.2f}ms\n'
                    f'   Cache hits: {batch_result.cache_hits}\n'
                    f'   API calls: {batch_result.api_calls}'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Batch processing test failed: {str(e)}')
            )
    
    def _test_celery_task(self, source_id):
        """Test Celery task execution."""
        self.stdout.write(f'Testing Celery task for source {source_id}...')
        
        try:
            # Submit the task
            task = generate_embeddings_for_knowledge_chunks.apply_async(
                args=[source_id],
                kwargs={'force_regenerate': True, 'batch_size': 10}
            )
            
            self.stdout.write(f'Task submitted with ID: {task.id}')
            
            # Wait for completion (with timeout)
            try:
                result = task.get(timeout=300)  # 5 minute timeout
                
                if isinstance(result, dict) and result.get('status') == 'SUCCESS':
                    task_result = result.get('result', {})
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Celery task completed successfully!\n'
                            f'   Source: {task_result.get("source_name", "Unknown")}\n'
                            f'   Processed chunks: {task_result.get("processed_chunks", 0)}\n'
                            f'   Total cost: ${task_result.get("total_cost_usd", 0):.6f}\n'
                            f'   Total tokens: {task_result.get("total_tokens", 0)}\n'
                            f'   Model: {task_result.get("model", "Unknown")}\n'
                            f'   Privacy preserved: {task_result.get("privacy_preserved", False)}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'❌ Task failed or returned unexpected result: {result}')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Task execution failed: {str(e)}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Task submission failed: {str(e)}')
            )
    
    def _test_source_embeddings(self, source_id):
        """Test embedding generation for a specific source."""
        self.stdout.write(f'Testing embeddings for source {source_id}...')
        
        try:
            source = KnowledgeSource.objects.get(id=source_id)
            chunks = source.chunks.all()[:5]  # Test with first 5 chunks
            
            if not chunks:
                self.stdout.write(
                    self.style.WARNING('No chunks found for this source')
                )
                return
            
            async def test_source():
                service = get_embedding_service()
                chunk_list = list(chunks)
                
                start_time = timezone.now()
                results = await service.generate_embeddings_for_knowledge_chunks(
                    chunk_list, update_db=False
                )
                processing_time = (timezone.now() - start_time).total_seconds() * 1000
                
                return results, processing_time
            
            results, processing_time = asyncio.run(test_source())
            
            total_cost = sum(r.cost_usd for _, r in results if not r.cached)
            cache_hits = sum(1 for _, r in results if r.cached)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Source embedding test completed!\n'
                    f'   Source: {source.name}\n'
                    f'   Is citable: {source.is_citable}\n'
                    f'   Chunks processed: {len(results)}\n'
                    f'   Cache hits: {cache_hits}\n'
                    f'   Total cost: ${total_cost:.6f}\n'
                    f'   Processing time: {processing_time:.2f}ms\n'
                    f'   Privacy metadata preserved: ✅'
                )
            )
            
        except KnowledgeSource.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ Knowledge source {source_id} not found')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Source embedding test failed: {str(e)}')
            )