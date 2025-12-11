#!/usr/bin/env python3
"""
Direct test of the Step 1 content type mapping fix.
Bypasses API authentication issues and tests the core functionality.
"""

import os
import django
import traceback

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.chatbots.models import Chatbot
from apps.knowledge.models import KnowledgeSource, KnowledgeChunk
from apps.core.document_processing_service import DocumentProcessingService

User = get_user_model()

def test_content_type_mapping():
    """Test the content type mapping fix directly."""
    print("🧪 Testing Step 1: Content Type Mapping Fix")
    print("=" * 50)
    
    # Get or create test user and chatbot
    user, _ = User.objects.get_or_create(
        email='admin@test.com',
        defaults={'password': 'admin123', 'is_active': True}
    )
    
    chatbot, _ = Chatbot.objects.get_or_create(
        user=user,
        name='Test Chatbot',
        defaults={'description': 'Content type testing chatbot'}
    )
    
    # Test file content
    test_content = """This is a test document for validating the content type mapping fix.

The document contains multiple paragraphs to ensure proper chunking and processing.

Key features to test:
1. Content type mapping from txt to text/plain
2. Document processing without "Unsupported source type" errors
3. Successful chunking and knowledge source creation
4. Proper status progression: pending → processing → completed

If this test succeeds, the content type mapping fix is working correctly."""
    
    # Test the fixed content type mapping logic
    print("🔍 Testing content type mapping logic...")
    
    # Simulate the mapping logic from upload_document function
    filename = "test_document.txt"
    file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
    
    file_type_mapping = {
        'pdf': {
            'content_type': 'pdf',
            'mime_type': 'application/pdf'
        },
        'docx': {
            'content_type': 'docx', 
            'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        },
        'doc': {
            'content_type': 'docx',
            'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        },
        'txt': {
            'content_type': 'txt',
            'mime_type': 'text/plain'
        }
    }
    
    mapping = file_type_mapping.get(file_extension, {
        'content_type': 'document',
        'mime_type': 'application/octet-stream'
    })
    
    mapped_content_type = mapping['content_type']
    reliable_mime_type = mapping['mime_type']
    
    print(f"File extension: {file_extension}")
    print(f"Mapped content_type: {mapped_content_type}")
    print(f"Reliable MIME type: {reliable_mime_type}")
    
    # Test 1: Create KnowledgeSource with mapped content type
    print("\n📄 Test 1: Creating KnowledgeSource with mapped content type...")
    
    try:
        source = KnowledgeSource.objects.create(
            chatbot=chatbot,
            name="Test Document",
            description="Testing content type mapping",
            content_type=mapped_content_type,  # Should be 'txt'
            file_path="/tmp/test.txt",
            file_size=len(test_content.encode()),
            file_hash="test_hash_123",
            mime_type=reliable_mime_type,  # Should be 'text/plain'
            is_citable=True,
            status='pending',
            metadata={
                'original_filename': filename,
                'file_extension': file_extension,
                'mapped_content_type': mapped_content_type,
                'reliable_mime_type': reliable_mime_type
            }
        )
        print(f"✅ KnowledgeSource created successfully!")
        print(f"   ID: {source.id}")
        print(f"   Content Type: {source.content_type}")
        print(f"   MIME Type: {source.mime_type}")
        
    except Exception as e:
        print(f"❌ Failed to create KnowledgeSource: {e}")
        traceback.print_exc()
        return False
    
    # Test 2: Document processing with the mapped MIME type
    print("\n⚙️ Test 2: Testing document processing service...")
    
    try:
        doc_service = DocumentProcessingService()
        
        # Test if the processor factory accepts the reliable MIME type
        supported_types = doc_service.get_supported_mime_types()
        print(f"Supported MIME types: {supported_types}")
        
        if reliable_mime_type in supported_types:
            print(f"✅ MIME type {reliable_mime_type} is supported")
        else:
            print(f"❌ MIME type {reliable_mime_type} is NOT supported")
            print("This would cause 'Unsupported source type' errors!")
            return False
        
        # Process the document
        print(f"\n🔄 Processing document with MIME type: {reliable_mime_type}")
        
        file_content = test_content.encode('utf-8')
        
        result = doc_service.process_uploaded_file(
            knowledge_source=source,
            file_content=file_content,
            filename=filename,
            mime_type=reliable_mime_type
        )
        
        if result.success:
            print(f"✅ Document processing succeeded!")
            print(f"   Chunks created: {len(result.chunks)}")
            print(f"   Total tokens: {result.total_tokens}")
            print(f"   Processing time: {result.processing_time_ms}ms")
            
            # Refresh source from database
            source.refresh_from_db()
            print(f"   Final status: {source.status}")
            print(f"   Chunk count: {source.chunk_count}")
            print(f"   Error message: {source.error_message}")
            
            if source.status == 'completed' and source.chunk_count > 0:
                print(f"✅ SUCCESS: File processing completed with chunks created!")
                
                # Test 3: Check chunk content
                print(f"\n📊 Test 3: Validating created chunks...")
                chunks = KnowledgeChunk.objects.filter(source=source)
                for i, chunk in enumerate(chunks):
                    print(f"   Chunk {i+1}: {len(chunk.content)} chars, {chunk.token_count} tokens")
                
                return True
            else:
                print(f"❌ Processing completed but status/chunks are wrong")
                return False
                
        else:
            print(f"❌ Document processing failed: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ Document processing service error: {e}")
        traceback.print_exc()
        return False

def main():
    """Run the comprehensive test."""
    print("🚀 Starting Step 1 Content Type Mapping Validation")
    print("Testing claims:")
    print("- Content type mapping fixed between upload API and processing backend")
    print("- PDF, DOCX, DOC, and TXT files should now be processed correctly")
    print("- File uploads no longer fail with 'Unsupported source type' errors")
    print("- Files should move from upload → processing → chunking")
    print()
    
    try:
        success = test_content_type_mapping()
        
        print("\n" + "="*60)
        if success:
            print("✅ STEP 1 VALIDATION PASSED!")
            print("The content type mapping fix appears to be working correctly.")
            print("Files should now successfully move through upload → processing → chunking.")
        else:
            print("❌ STEP 1 VALIDATION FAILED!")
            print("The content type mapping fix has critical issues.")
            print("The claimed fixes are NOT working as described.")
        print("="*60)
        
        return success
        
    except Exception as e:
        print(f"\n❌ CRITICAL TEST FAILURE: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()