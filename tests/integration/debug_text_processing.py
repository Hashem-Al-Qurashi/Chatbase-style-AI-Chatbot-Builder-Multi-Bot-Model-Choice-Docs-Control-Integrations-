#!/usr/bin/env python3
"""
Debug text processing to understand why files are failing
"""

import os
import sys
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')

import django
django.setup()

from apps.core.document_processors import document_processor_factory
import tempfile

def test_text_processing():
    print("🔍 DEBUGGING TEXT PROCESSING")
    print("=" * 50)
    
    # Create the same test content as our failing test
    test_content = """
This is a test document for validating the file upload functionality.

Key points:
- File upload API should process this content
- The document should be chunked into knowledge pieces
- Embeddings should be generated for vector search
- The content should be searchable via the RAG pipeline

Test information for citation validation:
- Document name: Step1_Upload_Test.txt
- Upload timestamp: 2025-10-24
- Expected behavior: Should be citable and searchable
    """
    
    print(f"Original content ({len(test_content)} chars):")
    print(repr(test_content[:200]))
    print()
    
    # Convert to bytes
    content_bytes = test_content.encode('utf-8')
    print(f"Content as bytes: {len(content_bytes)} bytes")
    
    try:
        # Test with text processor
        processor = document_processor_factory.create_processor('text/plain')
        print(f"Using processor: {type(processor).__name__}")
        
        result = processor.extract_text(content_bytes, 'test.txt')
        
        print(f"Extraction successful!")
        print(f"  Text length: {len(result.text_content)}")
        print(f"  Word count: {result.word_count}")
        print(f"  Char count: {result.char_count}")
        print(f"  Processing time: {result.processing_time_ms}ms")
        print(f"  Quality score: {result.quality_score}")
        
        print(f"Extracted text preview:")
        print(repr(result.text_content[:200]))
        
        if result.text_content.strip():
            print("✅ Text extraction successful - content is readable")
        else:
            print("❌ Text extraction failed - content is empty after cleaning")
            
        return True
        
    except Exception as e:
        print(f"❌ Text extraction failed: {str(e)}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_text_processing()
    sys.exit(0 if success else 1)