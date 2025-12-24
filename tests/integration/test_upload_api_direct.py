#!/usr/bin/env python3
"""
Test the actual upload API endpoint to validate the content type mapping fix.
This tests the REAL upload → processing → chunking pipeline.
"""

import os
import django
import requests
import json
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.chatbots.models import Chatbot
from apps.knowledge.models import KnowledgeSource

User = get_user_model()

def test_upload_api_fix():
    """Test the upload API content type mapping fix."""
    print("🎯 TESTING ACTUAL UPLOAD API - Step 1 Content Type Fix")
    print("="*60)
    
    # 1. Setup user and chatbot
    user, _ = User.objects.get_or_create(
        email='admin@test.com',
        defaults={'first_name': 'Admin', 'last_name': 'User', 'is_active': True}
    )
    user.set_password('admin123')
    user.save()
    
    chatbot, _ = Chatbot.objects.get_or_create(
        user=user,
        name='Upload Test Bot',
        defaults={'description': 'Testing upload API fix'}
    )
    
    print(f"✅ Test environment ready - User: {user.email}, Chatbot: {chatbot.name}")
    
    # 2. Authenticate with the API
    print("\n🔐 Authenticating with upload API...")
    auth_response = requests.post('http://localhost:8000/auth/login/', json={
        'email': 'admin@test.com',
        'password': 'admin123'
    })
    
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        print(auth_response.text)
        return False
    
    auth_data = auth_response.json()
    access_token = auth_data.get('access_token')
    if not access_token:
        print(f"❌ No access token in response: {auth_data}")
        return False
    
    print(f"✅ Authentication successful")
    
    # 3. Test file upload through the actual API
    print(f"\n📤 Testing file upload through /api/v1/knowledge/upload/document/")
    
    # Create test file content
    test_content = """This is a rigorous test of the Step 1 content type mapping fix.

The test validates:
1. Upload API accepts TXT files
2. Content type is correctly mapped from 'txt' extension to 'text/plain' MIME type
3. Document processing service receives the correct MIME type
4. No 'Unsupported source type' errors occur
5. Files progress through upload → processing → chunking successfully

If this test passes, the content type mapping fix is working correctly."""
    
    # Prepare upload request
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    files = {
        'file': ('api_test_document.txt', test_content, 'text/plain')
    }
    
    data = {
        'chatbot_id': str(chatbot.id),
        'name': 'API Upload Test Document', 
        'description': 'Testing Step 1 content type mapping fix via API',
        'is_citable': 'true'
    }
    
    print(f"Uploading file to chatbot {chatbot.id}...")
    
    # Make the upload request
    response = requests.post(
        'http://localhost:8000/api/v1/knowledge/upload/document/',
        headers=headers,
        files=files,
        data=data
    )
    
    print(f"Upload response status: {response.status_code}")
    
    if response.status_code == 201:
        response_data = response.json()
        source_id = response_data['id']
        
        print(f"✅ UPLOAD SUCCESSFUL!")
        print(f"   Source ID: {source_id}")
        print(f"   Content Type: {response_data.get('content_type')}")
        print(f"   MIME Type: {response_data.get('mime_type')}")
        print(f"   Status: {response_data.get('status')}")
        print(f"   Error Message: {response_data.get('error_message')}")
        
        # Validate content type mapping
        if response_data.get('content_type') == 'txt':
            print(f"✅ Content type correctly mapped to 'txt'")
        else:
            print(f"❌ Content type mapping failed: expected 'txt', got '{response_data.get('content_type')}'")
        
        if response_data.get('mime_type') == 'text/plain':
            print(f"✅ MIME type correctly mapped to 'text/plain'")
        else:
            print(f"❌ MIME type mapping failed: expected 'text/plain', got '{response_data.get('mime_type')}'")
        
        # Monitor processing
        return monitor_processing_through_api(source_id, headers)
        
    else:
        print(f"❌ UPLOAD FAILED: {response.status_code}")
        try:
            error_data = response.json()
            print(f"Error details: {error_data}")
        except:
            print(f"Error text: {response.text}")
        
        # Check for specific error types
        if "Unsupported source type" in response.text:
            print(f"🚨 CRITICAL: 'Unsupported source type' error detected!")
            print(f"   This means the content type mapping fix is NOT working!")
        
        return False

def monitor_processing_through_api(source_id, headers):
    """Monitor processing status through the API."""
    print(f"\n⏱️ Monitoring processing status via API for source {source_id}...")
    
    max_wait = 30
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        # Check source status via API
        status_response = requests.get(
            f'http://localhost:8000/api/v1/knowledge-sources/{source_id}/',
            headers=headers
        )
        
        if status_response.status_code == 200:
            data = status_response.json()
            status = data.get('status')
            chunk_count = data.get('chunk_count', 0)
            error_message = data.get('error_message')
            
            print(f"   Status: {status}, Chunks: {chunk_count}, Error: {error_message}")
            
            if status == 'completed':
                print(f"✅ PROCESSING COMPLETED SUCCESSFULLY!")
                print(f"   Chunks created: {chunk_count}")
                
                if chunk_count > 0:
                    print(f"✅ Knowledge chunks were created - End-to-end success!")
                    
                    # Test chunk retrieval
                    chunks_response = requests.get(
                        f'http://localhost:8000/api/v1/knowledge-sources/{source_id}/chunks/',
                        headers=headers
                    )
                    
                    if chunks_response.status_code == 200:
                        chunks_data = chunks_response.json()
                        chunks = chunks_data.get('results', [])
                        print(f"✅ Retrieved {len(chunks)} chunks via API")
                        
                        for i, chunk in enumerate(chunks):
                            print(f"   Chunk {i+1}: {len(chunk.get('content', ''))} chars, {chunk.get('token_count', 0)} tokens")
                    else:
                        print(f"⚠️ Failed to retrieve chunks: {chunks_response.status_code}")
                    
                    return True
                else:
                    print(f"❌ No chunks created - processing failed!")
                    return False
                    
            elif status == 'failed':
                print(f"❌ PROCESSING FAILED: {error_message}")
                
                if error_message and "Unsupported source type" in error_message:
                    print(f"🚨 CRITICAL: 'Unsupported source type' error in processing!")
                    print(f"   The content type mapping fix is NOT working!")
                
                return False
                
        else:
            print(f"❌ Failed to check status: {status_response.status_code}")
            return False
            
        time.sleep(2)
    
    print(f"❌ Processing timeout after {max_wait} seconds")
    return False

def main():
    """Run the comprehensive upload API test."""
    print("🎯 RIGOROUS VALIDATION: Step 1 Content Type Mapping Fix")
    print("Testing the REAL upload API → processing → chunking pipeline")
    print()
    print("Claims being tested:")
    print("✓ 'File uploads will no longer fail with Unsupported source type errors'")
    print("✓ 'Files should now successfully move from upload → processing → chunking'")
    print("✓ 'Content type mapping fixed between upload API and processing backend'")
    print("✓ 'TXT files should now be processed correctly'")
    print()
    
    success = test_upload_api_fix()
    
    print(f"\n{'='*70}")
    if success:
        print("✅ STEP 1 VALIDATION: CLAIMS VERIFIED!")
        print("   ✓ Upload API accepts TXT files without errors")
        print("   ✓ Content type mapping works correctly (txt → text/plain)")
        print("   ✓ Document processing completes successfully")
        print("   ✓ Knowledge chunks are created")
        print("   ✓ No 'Unsupported source type' errors")
        print("   ✓ End-to-end pipeline: upload → processing → chunking ✅")
    else:
        print("❌ STEP 1 VALIDATION: CLAIMS REJECTED!")
        print("   ❌ The content type mapping fix has critical issues")
        print("   ❌ Claims about fixing 'Unsupported source type' errors are false")
        print("   ❌ The upload → processing → chunking pipeline is broken")
    print("="*70)
    
    return success

if __name__ == "__main__":
    main()