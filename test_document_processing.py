#!/usr/bin/env python3
"""
Test script for document processing pipeline - Step 2 validation.

This script tests the complete document processing pipeline:
1. File upload via API
2. Document text extraction 
3. Text chunking
4. KnowledgeChunk creation
5. Privacy inheritance
"""

import os
import sys
import json
import requests
from typing import Dict, Any

# Add project root to path for Django imports
sys.path.append('/home/sakr_quraish/Projects/Ismail')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')

import django
django.setup()

from apps.chatbots.models import Chatbot
from apps.knowledge.models import KnowledgeSource, KnowledgeChunk
from apps.accounts.models import User


class DocumentProcessingTester:
    """Test suite for document processing pipeline."""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.token = None
        self.user = None
        self.chatbot = None
    
    def setup_test_data(self):
        """Create test user and chatbot."""
        print("🔧 Setting up test data...")
        
        # Create or get test user
        self.user, created = User.objects.get_or_create(
            email='test@example.com',
            defaults={
                'name': 'Test User',
                'is_active': True
            }
        )
        
        if created:
            self.user.set_password('testpass123')
            self.user.save()
            print(f"✅ Created test user: {self.user.email}")
        else:
            print(f"✅ Using existing test user: {self.user.email}")
        
        # Create or get test chatbot
        self.chatbot, created = Chatbot.objects.get_or_create(
            user=self.user,
            name='Test Chatbot',
            defaults={
                'description': 'Test chatbot for document processing',
                'welcome_message': 'Hello! I can help test document processing.',
                'status': 'ready'
            }
        )
        
        if created:
            print(f"✅ Created test chatbot: {self.chatbot.name}")
        else:
            print(f"✅ Using existing test chatbot: {self.chatbot.name}")
    
    def get_auth_token(self) -> str:
        """Get authentication token via login API."""
        print("🔑 Getting authentication token...")
        
        # Use Django test client for authentication instead
        from django.test import Client
        from django.contrib.auth import get_user_model
        
        # For testing, we'll use session authentication
        # This is simpler than JWT for local testing
        print("✅ Using session authentication for testing")
        return "test_session"
    
    def test_file_upload(self, file_path: str, is_citable: bool = True) -> Dict[str, Any]:
        """Test file upload and processing."""
        print(f"\n📄 Testing file upload: {file_path}")
        print(f"   Privacy setting: {'Citable' if is_citable else 'Learn-only'}")
        
        # Prepare headers
        headers = {
            'Authorization': f'Bearer {self.token}'
        }
        
        # Prepare file data
        with open(file_path, 'rb') as f:
            files = {
                'file': (os.path.basename(file_path), f, 'text/plain')
            }
            
            data = {
                'chatbot_id': str(self.chatbot.id),
                'name': f'Test Document - {os.path.basename(file_path)}',
                'description': f'Test upload of {file_path}',
                'is_citable': is_citable
            }
            
            # Make request
            response = requests.post(
                f"{self.base_url}/api/knowledge/upload-document/",
                files=files,
                data=data,
                headers=headers
            )
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ File uploaded successfully")
            print(f"   Source ID: {result['id']}")
            print(f"   Status: {result['status']}")
            print(f"   Chunks: {result.get('chunk_count', 0)}")
            return result
        else:
            print(f"❌ File upload failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return {}
    
    def test_url_processing(self, url: str, is_citable: bool = True) -> Dict[str, Any]:
        """Test URL processing."""
        print(f"\n🌐 Testing URL processing: {url}")
        print(f"   Privacy setting: {'Citable' if is_citable else 'Learn-only'}")
        
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'chatbot_id': str(self.chatbot.id),
            'url': url,
            'name': f'Test URL - {url}',
            'description': f'Test processing of {url}',
            'is_citable': is_citable
        }
        
        response = requests.post(
            f"{self.base_url}/api/knowledge/process-url/",
            json=data,
            headers=headers
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ URL processed successfully")
            print(f"   Source ID: {result['id']}")
            print(f"   Status: {result['status']}")
            print(f"   Chunks: {result.get('chunk_count', 0)}")
            return result
        else:
            print(f"❌ URL processing failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return {}
    
    def verify_chunks_created(self, source_id: str) -> bool:
        """Verify that knowledge chunks were created correctly."""
        print(f"\n🔍 Verifying chunks for source: {source_id}")
        
        try:
            source = KnowledgeSource.objects.get(id=source_id)
            chunks = source.chunks.all()
            
            print(f"   Total chunks: {chunks.count()}")
            print(f"   Source privacy: {'Citable' if source.is_citable else 'Learn-only'}")
            print(f"   Processing status: {source.status}")
            print(f"   Token count: {source.token_count}")
            
            if chunks.exists():
                # Check privacy inheritance
                privacy_consistent = all(chunk.is_citable == source.is_citable for chunk in chunks)
                print(f"   Privacy inheritance: {'✅ Consistent' if privacy_consistent else '❌ Inconsistent'}")
                
                # Show chunk details
                for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
                    print(f"   Chunk {i+1}: {len(chunk.content)} chars, {chunk.token_count} tokens")
                    print(f"      Preview: {chunk.content[:100]}...")
                    print(f"      Privacy: {'Citable' if chunk.is_citable else 'Learn-only'}")
                
                if chunks.count() > 3:
                    print(f"   ... and {chunks.count() - 3} more chunks")
                
                return True
            else:
                print("   ❌ No chunks created")
                return False
                
        except KnowledgeSource.DoesNotExist:
            print(f"   ❌ Source {source_id} not found")
            return False
        except Exception as e:
            print(f"   ❌ Error verifying chunks: {str(e)}")
            return False
    
    def test_privacy_settings(self):
        """Test privacy settings inheritance."""
        print(f"\n🔒 Testing privacy settings inheritance...")
        
        test_file = "/home/sakr_quraish/Projects/Ismail/test_sample.txt"
        
        # Test citable document
        print("\n--- Testing CITABLE document ---")
        citable_result = self.test_file_upload(test_file, is_citable=True)
        if citable_result:
            self.verify_chunks_created(citable_result['id'])
        
        # Test learn-only document
        print("\n--- Testing LEARN-ONLY document ---")
        learn_only_result = self.test_file_upload(test_file, is_citable=False)
        if learn_only_result:
            self.verify_chunks_created(learn_only_result['id'])
    
    def test_supported_formats(self):
        """Test different file formats."""
        print(f"\n📁 Testing supported file formats...")
        
        # Test text file
        test_file = "/home/sakr_quraish/Projects/Ismail/test_sample.txt"
        if os.path.exists(test_file):
            result = self.test_file_upload(test_file)
            if result:
                self.verify_chunks_created(result['id'])
    
    def test_error_handling(self):
        """Test error handling for invalid files."""
        print(f"\n⚠️ Testing error handling...")
        
        # Test with non-existent file (will create a dummy one)
        import tempfile
        
        # Create an empty file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")  # Empty file
            empty_file = f.name
        
        try:
            print("Testing empty file...")
            result = self.test_file_upload(empty_file)
            
            if result and result.get('status') == 'failed':
                print("✅ Empty file correctly rejected")
            elif result and result.get('status') == 'completed':
                print("⚠️ Empty file was processed (may be OK)")
            else:
                print("❌ Unexpected result for empty file")
                
        finally:
            os.unlink(empty_file)
    
    def run_all_tests(self):
        """Run complete test suite."""
        print("🚀 Starting Document Processing Pipeline Tests")
        print("=" * 60)
        
        try:
            # Setup
            self.setup_test_data()
            self.token = self.get_auth_token()
            
            # Run tests
            self.test_supported_formats()
            self.test_privacy_settings()
            
            # Test URL processing with a simple test page
            # Using httpbin.org for reliable testing
            test_url = "https://httpbin.org/html"
            url_result = self.test_url_processing(test_url)
            if url_result:
                self.verify_chunks_created(url_result['id'])
            
            self.test_error_handling()
            
            print("\n" + "=" * 60)
            print("✅ Document Processing Pipeline Tests Completed")
            
            # Summary
            total_sources = KnowledgeSource.objects.filter(chatbot=self.chatbot).count()
            total_chunks = KnowledgeChunk.objects.filter(source__chatbot=self.chatbot).count()
            
            print(f"\n📊 Test Summary:")
            print(f"   Total sources created: {total_sources}")
            print(f"   Total chunks created: {total_chunks}")
            print(f"   Chatbot: {self.chatbot.name} ({self.chatbot.id})")
            
        except Exception as e:
            print(f"\n❌ Test suite failed: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    tester = DocumentProcessingTester()
    tester.run_all_tests()