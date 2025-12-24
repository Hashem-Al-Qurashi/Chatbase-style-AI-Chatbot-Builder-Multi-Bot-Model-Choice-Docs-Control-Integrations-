#!/usr/bin/env python3
"""
Debug the TextProcessor to understand why it fails on uploaded files.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from apps.core.document_processors import TextProcessor

def debug_text_processing():
    """Debug the text processing issue."""
    print("🔍 DEBUGGING TEXT PROCESSOR FAILURE")
    print("="*50)
    
    # Test content that should work
    test_content = """This is a test document for validating the content type mapping fix.

The document contains multiple paragraphs to ensure proper chunking and processing.

Key features to test:
1. Content type mapping from txt to text/plain
2. Document processing without "Unsupported source type" errors
3. Successful chunking and knowledge source creation
4. Proper status progression: pending → processing → chunking

If this test succeeds, the content type mapping fix is working correctly."""
    
    print(f"Original content length: {len(test_content)}")
    print(f"Original content preview: {test_content[:100]}...")
    
    # Test the TextProcessor directly
    processor = TextProcessor()
    
    # Test 1: Direct bytes processing
    print(f"\n📝 Test 1: Direct bytes processing")
    file_content = test_content.encode('utf-8')
    print(f"Encoded bytes length: {len(file_content)}")
    
    try:
        result = processor.extract_text(file_content, "test.txt")
        print(f"✅ Text extraction successful!")
        print(f"   Extracted length: {len(result.text_content)}")
        print(f"   Word count: {result.word_count}")
        print(f"   Char count: {result.char_count}")
        print(f"   Quality score: {result.quality_score}")
        print(f"   Extracted preview: {result.text_content[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ Text extraction failed: {e}")
        
        # Debug the cleaning process
        print(f"\n🔧 Debugging text cleaning process...")
        
        # Try to decode manually
        try:
            decoded_content = file_content.decode('utf-8')
            print(f"✅ Manual decode successful: {len(decoded_content)} chars")
            print(f"   Decoded preview: {decoded_content[:100]}...")
            
            # Try cleaning manually
            cleaned_content = processor._clean_text(decoded_content)
            print(f"   Cleaned length: {len(cleaned_content)}")
            print(f"   Cleaned stripped length: {len(cleaned_content.strip())}")
            print(f"   Cleaned preview: {cleaned_content[:100]}...")
            
            if not cleaned_content.strip():
                print(f"❌ ISSUE FOUND: Cleaned text is empty after stripping!")
                print(f"   Raw cleaned repr: {repr(cleaned_content[:200])}")
            
        except Exception as decode_error:
            print(f"❌ Manual decode failed: {decode_error}")
        
        return False

def main():
    """Run the debug test."""
    print("🎯 DEBUGGING: Why TextProcessor fails on uploaded files")
    print("This will help identify if the issue is in text cleaning or file handling")
    print()
    
    success = debug_text_processing()
    
    print(f"\n{'='*60}")
    if success:
        print("✅ TextProcessor works correctly with test content")
        print("   The issue may be in how file content is passed from upload API")
    else:
        print("❌ TextProcessor has internal issues")
        print("   The content type mapping fix is incomplete - text cleaning is broken")
    print("="*60)

if __name__ == "__main__":
    main()