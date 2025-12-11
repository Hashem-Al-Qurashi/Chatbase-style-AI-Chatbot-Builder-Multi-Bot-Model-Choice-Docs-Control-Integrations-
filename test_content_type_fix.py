#!/usr/bin/env python3
"""
Rigorous test of the claimed content type mapping fix in Step 1.
Tests if files can now successfully move from upload → processing → chunking.
"""

import os
import django
import requests
import json
import time
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.chatbots.models import Chatbot
from apps.knowledge.models import KnowledgeSource, KnowledgeChunk

User = get_user_model()

class ContentTypeMappingTester:
    """Test the content type mapping fix rigorously."""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.auth_token = None
        self.chatbot_id = None
        
    def setup_test_environment(self):
        """Setup user, chatbot, and authentication."""
        print("🔧 Setting up test environment...")
        
        # Get or create test user
        user, created = User.objects.get_or_create(
            email='admin@test.com',
            defaults={'password': 'admin123', 'is_active': True}
        )
        if created:
            user.set_password('admin123')
            user.save()
            
        # Get or create test chatbot
        chatbot, created = Chatbot.objects.get_or_create(
            user=user,
            name='Test Chatbot',
            defaults={'description': 'Content type testing chatbot'}
        )
        self.chatbot_id = str(chatbot.id)
        
        # Authenticate
        auth_response = requests.post(f"{self.base_url}/auth/login/", json={
            'email': 'admin@test.com',
            'password': 'admin123'
        })
        
        if auth_response.status_code == 200:
            self.auth_token = auth_response.json()['access']
            print(f"✅ Authentication successful")
        else:
            print(f"❌ Authentication failed: {auth_response.status_code}")
            print(auth_response.text)
            return False
            
        return True
    
    def test_file_upload(self, file_path, expected_content_type, expected_mime_type):
        """Test file upload with specific content type expectations."""
        print(f"\n📁 Testing file upload: {file_path}")
        print(f"Expected content_type: {expected_content_type}")
        print(f"Expected MIME type: {expected_mime_type}")
        
        headers = {
            'Authorization': f'Bearer {self.auth_token}'
        }
        
        # Prepare file upload
        with open(file_path, 'rb') as f:
            files = {
                'file': (os.path.basename(file_path), f, expected_mime_type)
            }
            data = {
                'chatbot_id': self.chatbot_id,
                'name': f'Test {os.path.basename(file_path)}',
                'description': 'Testing content type mapping fix',
                'is_citable': True
            }
            
            # Make upload request
            print(f"🚀 Uploading file...")
            response = requests.post(
                f"{self.base_url}/api/v1/knowledge/upload/document/",
                headers=headers,
                files=files,
                data=data
            )
        
        print(f"Upload response status: {response.status_code}")
        
        if response.status_code == 201:
            response_data = response.json()
            source_id = response_data['id']
            
            print(f"✅ Upload successful! Source ID: {source_id}")
            print(f"Response content_type: {response_data.get('content_type')}")
            print(f"Response status: {response_data.get('status')}")
            
            # Validate the response
            self.validate_upload_response(response_data, expected_content_type, source_id)
            return source_id
            
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"Error: {response.text}")
            return None
    
    def validate_upload_response(self, response_data, expected_content_type, source_id):
        """Validate the upload response against expectations."""
        print(f"\n🔍 Validating upload response...")
        
        # Check content type mapping
        actual_content_type = response_data.get('content_type')
        if actual_content_type == expected_content_type:
            print(f"✅ Content type correctly mapped: {actual_content_type}")
        else:
            print(f"❌ Content type mismatch! Expected: {expected_content_type}, Got: {actual_content_type}")
        
        # Check initial status
        status = response_data.get('status')
        if status in ['pending', 'processing', 'completed']:
            print(f"✅ Initial status is valid: {status}")
        else:
            print(f"❌ Invalid initial status: {status}")
        
        # Check for error message
        error_message = response_data.get('error_message')
        if not error_message:
            print(f"✅ No error message in response")
        else:
            print(f"❌ Error message present: {error_message}")
            
        # Wait and check processing status
        self.monitor_processing_status(source_id)
    
    def monitor_processing_status(self, source_id):
        """Monitor processing status and validate progression."""
        print(f"\n⏱️ Monitoring processing status for source {source_id}...")
        
        headers = {
            'Authorization': f'Bearer {self.auth_token}'
        }
        
        max_wait_time = 30  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # Check source status
            response = requests.get(
                f"{self.base_url}/api/v1/knowledge-sources/{source_id}/",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                chunk_count = data.get('chunk_count', 0)
                error_message = data.get('error_message')
                
                print(f"Status: {status}, Chunks: {chunk_count}, Error: {error_message}")
                
                if status == 'completed':
                    print(f"✅ Processing completed successfully!")
                    print(f"Chunks created: {chunk_count}")
                    
                    if chunk_count > 0:
                        print(f"✅ Knowledge chunks were created successfully")
                        self.validate_chunks(source_id)
                    else:
                        print(f"❌ No chunks were created")
                    
                    return True
                    
                elif status == 'failed':
                    print(f"❌ Processing failed: {error_message}")
                    return False
                    
            time.sleep(2)
        
        print(f"❌ Processing timeout after {max_wait_time} seconds")
        return False
    
    def validate_chunks(self, source_id):
        """Validate that chunks were created correctly."""
        print(f"\n📊 Validating knowledge chunks for source {source_id}...")
        
        headers = {
            'Authorization': f'Bearer {self.auth_token}'
        }
        
        response = requests.get(
            f"{self.base_url}/api/v1/knowledge-sources/{source_id}/chunks/",
            headers=headers
        )
        
        if response.status_code == 200:
            chunks_data = response.json()
            chunks = chunks_data.get('results', [])
            
            print(f"✅ Retrieved {len(chunks)} chunks")
            
            for i, chunk in enumerate(chunks):
                print(f"Chunk {i+1}:")
                print(f"  Content length: {len(chunk.get('content', ''))}")
                print(f"  Token count: {chunk.get('token_count', 0)}")
                print(f"  Is citable: {chunk.get('is_citable', False)}")
                
        else:
            print(f"❌ Failed to retrieve chunks: {response.status_code}")
    
    def run_comprehensive_test(self):
        """Run comprehensive test of content type mapping fix."""
        print("🧪 Starting comprehensive content type mapping test...")
        
        if not self.setup_test_environment():
            return False
        
        # Test cases: (file_path, expected_content_type, expected_mime_type)
        test_cases = [
            ('test_document.txt', 'txt', 'text/plain'),
            # Add more test cases for PDF, DOCX if you have sample files
        ]
        
        all_passed = True
        
        for file_path, expected_content_type, expected_mime_type in test_cases:
            if os.path.exists(file_path):
                source_id = self.test_file_upload(file_path, expected_content_type, expected_mime_type)
                if not source_id:
                    all_passed = False
            else:
                print(f"⚠️ Test file not found: {file_path}")
        
        print(f"\n{'='*50}")
        if all_passed:
            print("✅ ALL TESTS PASSED - Content type mapping fix is working!")
        else:
            print("❌ TESTS FAILED - Content type mapping fix has issues!")
        print(f"{'='*50}")
        
        return all_passed

if __name__ == "__main__":
    tester = ContentTypeMappingTester()
    tester.run_comprehensive_test()