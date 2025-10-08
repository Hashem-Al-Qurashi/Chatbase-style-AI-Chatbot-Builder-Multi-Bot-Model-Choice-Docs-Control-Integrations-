#!/usr/bin/env python3
"""
Quick test script for document processing functionality.
Tests the document validator and processor factory.
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

from apps.core.document_processors import DocumentProcessorFactory, process_document


def test_document_processing():
    """Test document processing functionality."""
    print("🧪 Testing Document Processing System")
    print("=" * 50)
    
    # Test factory initialization
    factory = DocumentProcessorFactory()
    supported_types = factory.get_supported_mime_types()
    
    print(f"✅ Factory initialized successfully")
    print(f"📋 Supported MIME types: {supported_types}")
    
    # Test processor creation
    for mime_type in supported_types:
        try:
            processor = factory.create_processor(mime_type)
            print(f"✅ Created processor for {mime_type}: {type(processor).__name__}")
        except Exception as e:
            print(f"❌ Failed to create processor for {mime_type}: {e}")
    
    # Test unsupported type
    try:
        factory.create_processor("application/unknown")
        print("❌ Should have failed for unknown type")
    except Exception as e:
        print(f"✅ Correctly rejected unknown type: {e}")
    
    # Test simple text processing
    print("\n📝 Testing text processing...")
    test_text = "This is a test document with some sample content.\nIt has multiple lines and words."
    text_bytes = test_text.encode('utf-8')
    
    try:
        result = process_document(text_bytes, "test.txt", "text/plain")
        print(f"✅ Text processing successful:")
        print(f"   📊 Word count: {result.word_count}")
        print(f"   📊 Character count: {result.char_count}")
        print(f"   📊 Quality score: {result.quality_score:.2f}")
        print(f"   ⏱️ Processing time: {result.processing_time_ms}ms")
        print(f"   📄 Content preview: {result.text_content[:100]}...")
    except Exception as e:
        print(f"❌ Text processing failed: {e}")
    
    print("\n✅ Document processing system test completed!")


if __name__ == "__main__":
    test_document_processing()