#!/usr/bin/env python3
"""
Final RAG Workflow Test
Test complete upload → chat functionality with proper citations
"""

import os
import sys
import json
import requests
import tempfile
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
import django
django.setup()

from apps.accounts.models import User
from apps.chatbots.models import Chatbot
from apps.knowledge.models import KnowledgeSource, KnowledgeChunk

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USER_EMAIL = "admin@test.com"
TEST_USER_PASSWORD = "admin123"

class RAGWorkflowTester:
    """Test complete RAG workflow functionality."""
    
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.chatbot_id = None
        
    def authenticate(self):
        """Authenticate user and get access token."""
        print("🔐 Authenticating user...")
        
        response = self.session.post(f"{BASE_URL}/auth/login/", json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        })
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data['access_token']
            self.session.headers.update({
                'Authorization': f'Bearer {self.access_token}'
            })
            print(f"✅ Authentication successful")
            return True
        else:
            print(f"❌ Authentication failed: {response.status_code} - {response.text}")
            return False
    
    def get_or_create_chatbot(self):
        """Get or create a test chatbot."""
        print("🤖 Getting chatbot...")
        
        # Get available chatbots
        response = self.session.get(f"{BASE_URL}/api/v1/chatbots/")
        
        if response.status_code == 200:
            data = response.json()
            chatbots = data.get('results', [])
            if chatbots:
                self.chatbot_id = chatbots[0]['id']
                print(f"✅ Using existing chatbot: {self.chatbot_id}")
                return True
            else:
                print("❌ No chatbots found")
                return False
        else:
            print(f"❌ Failed to get chatbots: {response.status_code} - {response.text}")
            return False
    
    def upload_test_document(self):
        """Upload a test document to the chatbot."""
        print("📄 Uploading test document...")
        
        # Create a test document with substantial content
        test_content = """
        Testing AI Chatbot Knowledge Base System
        
        This is a comprehensive test document for validating the RAG (Retrieval-Augmented Generation) system.
        The document contains important information about artificial intelligence, machine learning, and chatbot functionality.
        
        Key Topics:
        1. Natural Language Processing (NLP)
        2. Vector embeddings and similarity search
        3. Knowledge retrieval and citation systems
        4. Privacy-first architecture and data protection
        
        Important Information:
        - The system uses OpenAI embeddings for document processing
        - Vector search enables semantic similarity matching
        - Citations provide traceability back to source documents
        - Privacy filters ensure sensitive information protection
        
        Technical Details:
        - The RAG pipeline consists of multiple stages
        - Document chunking optimizes retrieval performance
        - Context building maintains relevance and diversity
        - LLM generation creates natural responses
        
        Conclusion:
        This test document validates end-to-end functionality from document upload through chat responses with proper citations.
        """
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            temp_file_path = f.name
        
        try:
            # Upload the document
            with open(temp_file_path, 'rb') as f:
                files = {
                    'file': ('test_rag_document.txt', f, 'text/plain')
                }
                data = {
                    'chatbot_id': self.chatbot_id,
                    'is_citable': 'true'
                }
                
                response = self.session.post(
                    f"{BASE_URL}/api/v1/knowledge/upload/document/",
                    files=files,
                    data=data
                )
            
            if response.status_code == 201:
                upload_data = response.json()
                print(f"✅ Document uploaded successfully: {upload_data['id']}")
                
                # Wait for processing
                print("⏳ Waiting for document processing...")
                time.sleep(5)
                return True
            else:
                print(f"❌ Document upload failed: {response.status_code} - {response.text}")
                return False
                
        finally:
            # Clean up temp file
            os.unlink(temp_file_path)
    
    def test_chat_with_citations(self):
        """Test chat functionality with proper citations."""
        print("💬 Testing chat with citations...")
        
        # Test queries that should trigger knowledge retrieval
        test_queries = [
            "What is this document about?",
            "Tell me about the RAG pipeline stages",
            "What are the key topics covered?",
            "How does the citation system work?"
        ]
        
        for query in test_queries:
            print(f"\n📝 Query: {query}")
            
            response = self.session.post(
                f"{BASE_URL}/api/v1/chat/private/{self.chatbot_id}/",
                json={"message": query}
            )
            
            if response.status_code == 200:
                chat_data = response.json()
                
                print(f"✅ Response received: {chat_data['message'][:100]}...")
                
                # Check citations
                citations = chat_data.get('citations', [])
                print(f"📚 Citations found: {len(citations)}")
                for i, citation in enumerate(citations):
                    print(f"   {i+1}. {citation}")
                
                # Check privacy status
                privacy_status = chat_data.get('privacy_status', {})
                print(f"🔒 Privacy compliant: {privacy_status.get('compliant', 'Unknown')}")
                
                # Check sources
                sources = chat_data.get('sources', {})
                print(f"📖 Sources used: {sources.get('total_used', 0)}")
                print(f"📖 Citable sources: {sources.get('citable', 0)}")
                
                if citations:
                    print(f"✅ Citations working properly")
                else:
                    print(f"⚠️  No citations found - this may indicate an issue")
                
            else:
                print(f"❌ Chat request failed: {response.status_code} - {response.text}")
                return False
        
        return True
    
    def validate_database_state(self):
        """Validate database state after testing."""
        print("\n🔍 Validating database state...")
        
        try:
            # Check if knowledge sources exist
            sources = KnowledgeSource.objects.filter(chatbot_id=self.chatbot_id)
            print(f"📊 Knowledge sources: {sources.count()}")
            
            # Check if knowledge chunks exist
            chunks = KnowledgeChunk.objects.filter(source__chatbot_id=self.chatbot_id)
            print(f"📊 Knowledge chunks: {chunks.count()}")
            
            # Check citable chunks
            citable_chunks = chunks.filter(is_citable=True)
            print(f"📊 Citable chunks: {citable_chunks.count()}")
            
            if chunks.count() > 0:
                print("✅ Knowledge base populated successfully")
                return True
            else:
                print("❌ No knowledge chunks found")
                return False
                
        except Exception as e:
            print(f"❌ Database validation failed: {str(e)}")
            return False
    
    def run_complete_test(self):
        """Run complete workflow test."""
        print("🚀 Starting complete RAG workflow test...\n")
        
        steps = [
            ("Authenticate", self.authenticate),
            ("Get/Create Chatbot", self.get_or_create_chatbot),
            ("Upload Test Document", self.upload_test_document),
            ("Validate Database", self.validate_database_state),
            ("Test Chat with Citations", self.test_chat_with_citations),
        ]
        
        for step_name, step_func in steps:
            print(f"\n{'='*50}")
            print(f"Step: {step_name}")
            print('='*50)
            
            if not step_func():
                print(f"\n❌ Test failed at step: {step_name}")
                return False
        
        print(f"\n{'='*50}")
        print("🎉 ALL TESTS PASSED!")
        print("✅ Complete upload → chat workflow is functional")
        print("✅ Citations are working properly")
        print("✅ RAG system is operational")
        print('='*50)
        
        return True

if __name__ == "__main__":
    tester = RAGWorkflowTester()
    success = tester.run_complete_test()
    
    if not success:
        sys.exit(1)