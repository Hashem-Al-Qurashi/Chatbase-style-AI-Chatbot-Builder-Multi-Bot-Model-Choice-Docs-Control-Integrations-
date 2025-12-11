#!/usr/bin/env python3
"""
Step 1 Content Type Fix Validation Script

Tests that the file upload API correctly maps file extensions to the proper
content types and MIME types, resolving the critical processing mismatch.
"""

import os
import sys
import django
import json
import tempfile
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
sys.path.append('/home/sakr_quraish/Projects/Ismail')
django.setup()

from django.contrib.auth import get_user_model
from apps.chatbots.models import Chatbot
from apps.knowledge.api_views import upload_document
from apps.knowledge.models import KnowledgeSource
from apps.core.document_processing_service import DocumentProcessingService
from django.test import RequestFactory
from rest_framework.test import force_authenticate

User = get_user_model()

def test_content_type_mapping():
    """Test that file uploads get correct content_type and mime_type mapping."""
    
    print("🧪 STEP 1 VALIDATION: Content Type Mapping Fix")
    print("=" * 60)
    
    # Create test user and chatbot
    user = User.objects.filter(email='admin@test.com').first()
    if not user:
        print("❌ Test user admin@test.com not found")
        return False
        
    chatbot = Chatbot.objects.filter(user=user).first()
    if not chatbot:
        print("❌ No chatbot found for test user")
        return False
    
    print(f"✅ Using chatbot: {chatbot.name} (ID: {chatbot.id})")
    
    # Clean up any existing test sources to avoid hash conflicts
    test_sources = KnowledgeSource.objects.filter(
        chatbot=chatbot,
        name__startswith='Test '
    )
    if test_sources.exists():
        print(f"🧹 Cleaning up {test_sources.count()} existing test sources...")
        for source in test_sources:
            try:
                if source.file_path and os.path.exists(source.file_path):
                    os.remove(source.file_path)
            except Exception:
                pass
        test_sources.delete()
    
    # Test cases: file extension -> expected content_type and mime_type
    # Using unique content for each file to avoid hash conflicts
    test_cases = [
        {
            'filename': 'test_document.pdf',
            'content': b'%PDF-1.4 fake pdf content for testing unique hash 12345',
            'expected_content_type': 'pdf',
            'expected_mime_type': 'application/pdf'
        },
        {
            'filename': 'test_document.docx', 
            'content': b'fake docx content for testing unique hash 67890 ABCDEF',
            'expected_content_type': 'docx',
            'expected_mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        },
        {
            'filename': 'test_document.txt',
            'content': b'This is a simple text file for testing unique hash GHIJKL 111222.',
            'expected_content_type': 'txt',
            'expected_mime_type': 'text/plain'
        },
        {
            'filename': 'test_document.doc',  # Should be mapped to docx
            'content': b'fake old word doc content for testing unique hash MNOPQR 333444',
            'expected_content_type': 'docx',
            'expected_mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
    ]
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}/{total_count}: {test_case['filename']}")
        
        try:
            # Create uploaded file
            uploaded_file = SimpleUploadedFile(
                name=test_case['filename'],
                content=test_case['content'],
                content_type='application/octet-stream'  # Generic type from browser
            )
            
            # Create request
            factory = RequestFactory()
            request = factory.post('/api/knowledge/upload/document/', {
                'file': uploaded_file,
                'chatbot_id': str(chatbot.id),
                'name': f"Test {test_case['filename']}",
                'is_citable': True
            })
            force_authenticate(request, user=user)
            
            # Call the upload API
            response = upload_document(request)
            
            if response.status_code == 201:
                response_data = response.data
                source_id = response_data['id']
                
                # Check the created KnowledgeSource
                source = KnowledgeSource.objects.get(id=source_id)
                
                # Validate content_type mapping
                actual_content_type = source.content_type
                expected_content_type = test_case['expected_content_type']
                
                if actual_content_type == expected_content_type:
                    print(f"  ✅ content_type: {actual_content_type} (correct)")
                else:
                    print(f"  ❌ content_type: {actual_content_type} (expected {expected_content_type})")
                    continue
                
                # Validate mime_type mapping
                actual_mime_type = source.mime_type
                expected_mime_type = test_case['expected_mime_type']
                
                if actual_mime_type == expected_mime_type:
                    print(f"  ✅ mime_type: {actual_mime_type} (correct)")
                else:
                    print(f"  ❌ mime_type: {actual_mime_type} (expected {expected_mime_type})")
                    continue
                
                # Validate metadata contains mapping info
                metadata = source.metadata
                if 'file_extension' in metadata and 'mapped_content_type' in metadata:
                    print(f"  ✅ metadata contains mapping info")
                    print(f"    - file_extension: {metadata['file_extension']}")
                    print(f"    - mapped_content_type: {metadata['mapped_content_type']}")
                else:
                    print(f"  ❌ metadata missing mapping info")
                    continue
                
                # Check if processing would work with DocumentProcessingService
                try:
                    doc_service = DocumentProcessingService()
                    supported_types = doc_service.get_supported_mime_types()
                    
                    if actual_mime_type in supported_types:
                        print(f"  ✅ MIME type supported by document processor")
                    else:
                        print(f"  ❌ MIME type NOT supported by document processor")
                        print(f"      Supported types: {supported_types}")
                        continue
                        
                except Exception as e:
                    print(f"  ⚠️  Could not check processor support: {e}")
                
                success_count += 1
                print(f"  🎉 Test PASSED for {test_case['filename']}")
                
                # Clean up
                try:
                    source.delete()
                    if source.file_path and os.path.exists(source.file_path):
                        os.remove(source.file_path)
                except Exception as e:
                    print(f"  ⚠️  Cleanup warning: {e}")
                
            else:
                print(f"  ❌ Upload failed with status {response.status_code}")
                if hasattr(response, 'data'):
                    print(f"      Error: {response.data}")
                
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n📊 STEP 1 VALIDATION RESULTS")
    print("=" * 40)
    print(f"Tests passed: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 STEP 1 FIX SUCCESSFUL!")
        print("   Content type mapping is now working correctly.")
        print("   File uploads should no longer fail with 'Unsupported source type' errors.")
        return True
    else:
        print("❌ STEP 1 FIX INCOMPLETE!")
        print("   Some content type mappings are still incorrect.")
        return False

if __name__ == '__main__':
    success = test_content_type_mapping()
    sys.exit(0 if success else 1)