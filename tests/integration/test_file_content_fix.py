#!/usr/bin/env python3
"""
Test script to validate the file content corruption fix.
Tests the upload → processing pipeline to ensure files are processed successfully.
"""

import os
import sys
import django
import requests
import json
import time
from io import BytesIO

# Setup Django
sys.path.append('/home/sakr_quraish/Projects/Ismail')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.chatbots.models import Chatbot
from apps.knowledge.models import KnowledgeSource, KnowledgeChunk

User = get_user_model()

def create_test_file():
    """Create a simple test file for upload."""
    content = """
This is a test document for validating file processing.

Key Information:
- File upload should work correctly
- Text extraction should find this content
- Knowledge chunks should be created
- Processing status should be 'completed'

This document contains multiple paragraphs to ensure proper chunking.
The text should be extracted without corruption and processed into searchable chunks.

Test completion criteria:
1. File uploads successfully
2. Text extraction finds readable content  
3. Chunk count > 0
4. Status = 'completed'
"""
    return BytesIO(content.encode('utf-8'))

def test_file_upload_and_processing():
    """Test the complete file upload and processing pipeline."""
    print("🧪 Testing File Content Corruption Fix")
    print("=" * 50)
    
    # Get or create test user and chatbot
    try:
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            print("❌ No superuser found. Please create one first.")
            return False
            
        chatbot = Chatbot.objects.filter(user=user).first()
        if not chatbot:
            print("❌ No chatbot found for user. Please create one first.")
            return False
            
        print(f"✅ Using chatbot: {chatbot.name} (ID: {chatbot.id})")
        
    except Exception as e:
        print(f"❌ Database setup error: {e}")
        return False
    
    # Authenticate first
    print("🔐 Authenticating...")
    auth_response = requests.post("http://localhost:8000/api/v1/auth/login/", json={
        'email': 'admin@test.com',
        'password': 'admin123'
    })
    
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        print(auth_response.text)
        return False
    
    auth_data = auth_response.json()
    print(f"Auth response: {auth_data}")
    
    # Try different token key names
    auth_token = auth_data.get('access') or auth_data.get('token') or auth_data.get('access_token')
    if not auth_token:
        print(f"❌ No auth token found in response: {auth_data}")
        return False
        
    print("✅ Authentication successful")
    
    # Create test file
    test_file = create_test_file()
    
    # Prepare upload request
    url = "http://localhost:8000/api/v1/knowledge/upload/document/"
    headers = {
        'Authorization': f'Bearer {auth_token}'
    }
    files = {
        'file': ('test_document.txt', test_file, 'text/plain')
    }
    data = {
        'chatbot_id': str(chatbot.id),
        'name': 'Test Document for Content Fix',
        'description': 'Testing file content corruption fix'
    }
    
    print(f"📤 Uploading test file to: {url}")
    
    try:
        # Upload file
        response = requests.post(url, files=files, data=data, headers=headers)
        
        if response.status_code != 201:
            print(f"❌ Upload failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        result = response.json()
        source_id = result.get('id')
        print(f"✅ File uploaded successfully. Source ID: {source_id}")
        
        # Wait for processing
        print("⏳ Waiting for document processing...")
        time.sleep(3)
        
        # Check processing results
        source = KnowledgeSource.objects.get(id=source_id)
        chunks = KnowledgeChunk.objects.filter(source=source)
        
        print(f"📊 Processing Results:")
        print(f"   Status: {source.status}")
        print(f"   Chunks created: {chunks.count()}")
        print(f"   File size: {source.file_size} bytes")
        print(f"   Content type: {source.content_type}")
        print(f"   MIME type: {source.mime_type}")
        
        # Validate results
        success = True
        
        if source.status != 'completed':
            print(f"❌ Processing failed. Status: {source.status}")
            if source.error_message:
                print(f"   Error: {source.error_message}")
            success = False
        else:
            print("✅ Processing completed successfully")
            
        if chunks.count() == 0:
            print("❌ No knowledge chunks created")
            success = False
        else:
            print(f"✅ Created {chunks.count()} knowledge chunks")
            
            # Show sample chunk content
            sample_chunk = chunks.first()
            if sample_chunk:
                preview = sample_chunk.content[:100] + "..." if len(sample_chunk.content) > 100 else sample_chunk.content
                print(f"   Sample chunk: {preview}")
        
        return success
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Django server at localhost:8000")
        print("   Make sure the server is running with: python manage.py runserver")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def main():
    """Run the file content corruption fix test."""
    print("Starting File Content Corruption Fix Validation")
    print("This test validates that uploaded files are processed correctly")
    print()
    
    success = test_file_upload_and_processing()
    
    print()
    print("=" * 50)
    if success:
        print("🎉 TEST PASSED: File content corruption fix is working!")
        print("   ✅ Files upload successfully")
        print("   ✅ Text extraction works") 
        print("   ✅ Knowledge chunks are created")
        print("   ✅ Processing completes without errors")
    else:
        print("🚨 TEST FAILED: File content corruption issue still exists")
        print("   Check the error messages above for details")
    
    return success

if __name__ == "__main__":
    main()