#!/usr/bin/env python3
"""
Test script for text chunking functionality.
Tests different chunking strategies and configurations.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')

import django
django.setup()

from apps.core.text_chunking import (
    ChunkingStrategy, ChunkingConfig, ChunkerFactory, chunk_text
)


def test_chunking_strategies():
    """Test different chunking strategies."""
    print("🧪 Testing Text Chunking System")
    print("=" * 50)
    
    # Sample text for testing
    sample_text = """
    This is the first paragraph of our test document. It contains multiple sentences that we will use to test our chunking strategies. The sentences should be kept together when possible to maintain context and readability.

    This is the second paragraph. It discusses a different topic to test how well our chunking strategies handle topic boundaries. Semantic chunking should ideally keep related content together while respecting size limits.

    The third paragraph is here to provide more content for testing. We want to ensure that our chunking algorithms can handle various document structures including headers, paragraphs, and different content types.

    Finally, this is the last paragraph of our test document. It serves as a conclusion and helps us verify that all content is properly processed and chunked according to our specifications.
    """.strip()
    
    print(f"📄 Sample text length: {len(sample_text)} characters")
    print(f"📄 Sample text words: {len(sample_text.split())} words")
    
    # Test different strategies
    strategies = [
        ChunkingStrategy.RECURSIVE_CHARACTER,
        ChunkingStrategy.SEMANTIC,
        ChunkingStrategy.SLIDING_WINDOW,
        ChunkingStrategy.TOKEN_AWARE,
    ]
    
    for strategy in strategies:
        print(f"\n🔄 Testing {strategy.value} strategy...")
        
        try:
            config = ChunkingConfig(
                chunk_size=200,  # Small chunks for testing
                chunk_overlap=50,
                strategy=strategy,
                min_chunk_size=50
            )
            
            chunker = ChunkerFactory.create_chunker(config)
            chunks = chunker.chunk_text(sample_text)
            
            print(f"✅ {strategy.value} chunking successful:")
            print(f"   📊 Number of chunks: {len(chunks)}")
            
            if chunks:
                avg_size = sum(len(c.content) for c in chunks) / len(chunks)
                avg_tokens = sum(c.token_count for c in chunks) / len(chunks)
                avg_quality = sum(c.quality_score for c in chunks) / len(chunks)
                
                print(f"   📊 Average chunk size: {avg_size:.1f} characters")
                print(f"   📊 Average token count: {avg_tokens:.1f} tokens")
                print(f"   📊 Average quality score: {avg_quality:.2f}")
                
                # Show first chunk as example
                first_chunk = chunks[0]
                print(f"   📄 First chunk preview: {first_chunk.content[:100]}...")
                print(f"   🔗 Chunk ID: {first_chunk.chunk_id}")
                print(f"   📍 Position: {first_chunk.start_index}-{first_chunk.end_index}")
                
                # Check for overlaps
                overlapping_chunks = [c for c in chunks if c.overlap_with_previous or c.overlap_with_next]
                if overlapping_chunks:
                    print(f"   🔗 Chunks with overlap: {len(overlapping_chunks)}")
            
        except Exception as e:
            print(f"❌ {strategy.value} chunking failed: {e}")
    
    # Test convenience function
    print(f"\n🔄 Testing convenience function...")
    try:
        quick_chunks = chunk_text(
            sample_text,
            strategy=ChunkingStrategy.RECURSIVE_CHARACTER,
            chunk_size=150,
            chunk_overlap=30
        )
        print(f"✅ Convenience function successful: {len(quick_chunks)} chunks")
    except Exception as e:
        print(f"❌ Convenience function failed: {e}")
    
    # Test edge cases
    print(f"\n🔄 Testing edge cases...")
    
    # Empty text
    try:
        empty_chunks = chunk_text("", chunk_size=100)
        print(f"✅ Empty text handling: {len(empty_chunks)} chunks")
    except Exception as e:
        print(f"❌ Empty text handling failed: {e}")
    
    # Very short text
    try:
        short_chunks = chunk_text("Short text.", chunk_size=100, min_chunk_size=5)
        print(f"✅ Short text handling: {len(short_chunks)} chunks")
        if short_chunks:
            print(f"   📄 Content: '{short_chunks[0].content}'")
    except Exception as e:
        print(f"❌ Short text handling failed: {e}")
    
    print("\n✅ Text chunking system test completed!")


if __name__ == "__main__":
    test_chunking_strategies()