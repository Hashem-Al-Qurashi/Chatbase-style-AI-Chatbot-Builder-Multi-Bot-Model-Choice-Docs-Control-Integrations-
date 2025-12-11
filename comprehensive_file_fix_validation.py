#!/usr/bin/env python3
"""
Comprehensive validation of the file content corruption fix.
Tests multiple file types to ensure the fix works across all supported formats.
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

class FileContentFixTester:
    def __init__(self):
        self.base_url = "http://localhost:8000/api/v1"
        self.auth_token = None
        self.chatbot_id = None
        
    def authenticate(self):
        """Authenticate and get access token."""
        print("🔐 Authenticating...")
        response = requests.post(f"{self.base_url}/auth/login/", json={
            'email': 'admin@test.com',
            'password': 'admin123'
        })
        
        if response.status_code != 200:
            print(f"❌ Authentication failed: {response.status_code}")
            return False
            
        self.auth_token = response.json()['access_token']
        print("✅ Authentication successful")
        return True
        
    def setup_test_environment(self):
        """Setup test user and chatbot."""
        try:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                print("❌ No superuser found")
                return False
                
            chatbot = Chatbot.objects.filter(user=user).first()
            if not chatbot:
                print("❌ No chatbot found")
                return False
                
            self.chatbot_id = str(chatbot.id)
            print(f"✅ Using chatbot: {chatbot.name} (ID: {chatbot.id})")
            return True
            
        except Exception as e:
            print(f"❌ Setup error: {e}")
            return False
    
    def create_test_file(self, content, filename):
        """Create a test file with given content."""
        return BytesIO(content.encode('utf-8')), filename
    
    def upload_and_test_file(self, content, filename, expected_content_type):
        """Upload a file and test if it processes correctly."""
        print(f"\n📁 Testing: {filename}")
        print(f"   Expected content type: {expected_content_type}")
        
        # Create test file
        file_obj, name = self.create_test_file(content, filename)
        
        # Upload file
        url = f"{self.base_url}/knowledge/upload/document/"
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        files = {'file': (name, file_obj, 'text/plain')}
        data = {
            'chatbot_id': self.chatbot_id,
            'name': f'Test {name}',
            'description': f'Testing file content fix for {name}'
        }
        
        response = requests.post(url, files=files, data=data, headers=headers)
        
        if response.status_code != 201:
            print(f"   ❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
        result = response.json()
        source_id = result['id']
        print(f"   ✅ Upload successful (ID: {source_id})")
        
        # Wait for processing
        time.sleep(2)
        
        # Check results
        try:
            source = KnowledgeSource.objects.get(id=source_id)
            chunks = KnowledgeChunk.objects.filter(source=source)
            
            print(f"   📊 Results:")
            print(f"      Status: {source.status}")
            print(f"      Content type: {source.content_type}")
            print(f"      MIME type: {source.mime_type}")
            print(f"      Chunks: {chunks.count()}")
            print(f"      File size: {source.file_size} bytes")
            
            success = True
            
            # Validate processing status
            if source.status != 'completed':
                print(f"      ❌ Processing failed: {source.status}")
                if source.error_message:
                    print(f"         Error: {source.error_message}")
                success = False
            else:
                print(f"      ✅ Processing completed")
                
            # Validate content type
            if source.content_type != expected_content_type:
                print(f"      ❌ Wrong content type. Expected: {expected_content_type}, Got: {source.content_type}")
                success = False
            else:
                print(f"      ✅ Correct content type")
                
            # Validate chunks created
            if chunks.count() == 0:
                print(f"      ❌ No chunks created")
                success = False
            else:
                print(f"      ✅ Chunks created successfully")
                
                # Show sample content to verify text extraction worked
                sample_chunk = chunks.first()
                if sample_chunk and sample_chunk.content:
                    preview = sample_chunk.content[:50] + "..." if len(sample_chunk.content) > 50 else sample_chunk.content
                    print(f"      📝 Sample content: {preview}")
                    
                    # Check if original content is preserved
                    if "file content corruption fix" in sample_chunk.content.lower():
                        print(f"      ✅ Original content preserved")
                    else:
                        print(f"      ⚠️  Original content may be truncated")
                
            return success
            
        except Exception as e:
            print(f"   ❌ Database error: {e}")
            return False
    
    def run_comprehensive_test(self):
        """Run comprehensive test with multiple file types."""
        print("🧪 COMPREHENSIVE FILE CONTENT CORRUPTION FIX VALIDATION")
        print("=" * 60)
        
        if not self.authenticate():
            return False
            
        if not self.setup_test_environment():
            return False
            
        # Test cases: (content, filename, expected_content_type)
        test_cases = [
            (
                """This is a comprehensive test for file content corruption fix.
                
The issue was that uploaded_file.read() was called AFTER the file buffer 
was consumed by uploaded_file.chunks(), resulting in empty content for 
text extraction and processing.

Key validation points:
1. File uploads successfully
2. Text extraction finds readable content  
3. Knowledge chunks are created (chunk_count > 0)
4. Processing status becomes 'completed' not 'failed'
5. Content type mapping works correctly

This test validates the fix works properly.""",
                "comprehensive_test.txt",
                "txt"
            ),
            (
                """Technical documentation for file processing pipeline.

PROBLEM ANALYSIS:
The file content corruption occurred in apps/knowledge/api_views.py
at lines 304-309 where:

1. uploaded_file.chunks() consumed the file buffer
2. uploaded_file.read() returned empty bytes  
3. Text extraction failed with "No readable text found"
4. Processing failed, no chunks created

SOLUTION IMPLEMENTED:
Moved file_content = uploaded_file.read() BEFORE the file writing loop
to capture content while buffer is still available.

VALIDATION CRITERIA:
✓ Upload succeeds
✓ Text extraction works  
✓ Chunks created > 0
✓ Status = 'completed'""",
                "technical_doc.txt", 
                "txt"
            ),
            (
                """Short test file for edge case validation.

Minimal content to test chunking boundaries and ensure even small files process correctly after the fix.""",
                "small_test.txt",
                "txt"
            )
        ]
        
        results = []
        
        for content, filename, expected_type in test_cases:
            success = self.upload_and_test_file(content, filename, expected_type)
            results.append((filename, success))
            
        # Summary
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        
        passed = 0
        total = len(results)
        
        for filename, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} - {filename}")
            if success:
                passed += 1
                
        print(f"\nResults: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ File content corruption fix is working perfectly")
            print("✅ Upload → Processing → Chunking pipeline working correctly")
            print("✅ Text extraction finding readable content")
            print("✅ Knowledge chunks being created successfully")
            return True
        else:
            print(f"\n🚨 {total - passed} TESTS FAILED!")
            print("❌ File content corruption fix needs attention")
            return False

def main():
    """Run the comprehensive validation."""
    tester = FileContentFixTester()
    success = tester.run_comprehensive_test()
    
    print("\n" + "=" * 60)
    if success:
        print("🏆 VALIDATION COMPLETE: File content corruption fix is WORKING!")
        print("\nThe grumpy-tester critical finding has been RESOLVED:")
        print("   ✅ File content no longer corrupted during upload processing")
        print("   ✅ uploaded_file.read() now captures content before buffer consumption")
        print("   ✅ Text extraction works and finds readable content")
        print("   ✅ Knowledge chunks are created successfully")
        print("   ✅ Processing status becomes 'completed'")
    else:
        print("🚨 VALIDATION FAILED: File content corruption issue persists")
        print("\nPlease review the test output above for specific failures")
    
    return success

if __name__ == "__main__":
    exit(0 if main() else 1)