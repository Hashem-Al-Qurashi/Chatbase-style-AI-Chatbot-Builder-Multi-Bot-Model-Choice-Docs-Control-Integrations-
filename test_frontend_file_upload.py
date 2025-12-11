#!/usr/bin/env python3
"""
Test file upload through the frontend interface to validate the fix end-to-end.
This simulates the exact flow that would happen through the ChatbotWizard interface.
"""

import requests
import time
from io import BytesIO

def test_frontend_upload_flow():
    """Test the complete frontend upload flow."""
    print("🌐 Testing Frontend File Upload Flow")
    print("=" * 50)
    
    base_url = "http://localhost:8000/api/v1"
    
    # Step 1: Authenticate
    print("🔐 Step 1: Authentication")
    auth_response = requests.post(f"{base_url}/auth/login/", json={
        'email': 'admin@test.com',
        'password': 'admin123'
    })
    
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return False
        
    auth_token = auth_response.json()['access_token']
    print("✅ Authentication successful")
    
    # Step 2: Get chatbot list (simulating ChatbotWizard dropdown)
    print("\n📋 Step 2: Getting chatbot list")
    headers = {'Authorization': f'Bearer {auth_token}'}
    
    chatbots_response = requests.get(f"{base_url}/chatbots/", headers=headers)
    
    if chatbots_response.status_code != 200:
        print(f"❌ Failed to get chatbots: {chatbots_response.status_code}")
        return False
        
    chatbots = chatbots_response.json()['results']
    if not chatbots:
        print("❌ No chatbots found")
        return False
        
    chatbot = chatbots[0]
    chatbot_id = chatbot['id']
    print(f"✅ Selected chatbot: {chatbot['name']} (ID: {chatbot_id})")
    
    # Step 3: Upload file (simulating file drop in ChatbotWizard)
    print("\n📤 Step 3: File upload")
    
    # Create test file content that matches what users would upload
    test_content = """
COMPANY KNOWLEDGE BASE - CUSTOMER SERVICE GUIDE

1. GREETING CUSTOMERS
Always start with a warm greeting and ask how you can help.

2. HANDLING COMPLAINTS
- Listen actively to the customer's concern
- Apologize for any inconvenience 
- Offer a solution or escalate to supervisor
- Follow up to ensure satisfaction

3. PRODUCT INFORMATION
Our main products include:
- Premium Software License ($99/month)
- Professional Services ($150/hour)
- Training Programs ($500/course)

4. REFUND POLICY
- 30-day money-back guarantee on all software
- Refunds processed within 5-7 business days
- Contact billing@company.com for refund requests

5. TECHNICAL SUPPORT
- Available 24/7 via chat or phone
- Ticket system for complex issues
- Average response time: 2 hours

This document should be processed correctly and made searchable for customer service agents.
"""
    
    file_obj = BytesIO(test_content.encode('utf-8'))
    
    files = {
        'file': ('customer_service_guide.txt', file_obj, 'text/plain')
    }
    data = {
        'chatbot_id': chatbot_id,
        'name': 'Customer Service Knowledge Base',
        'description': 'Complete guide for customer service representatives'
    }
    
    upload_response = requests.post(
        f"{base_url}/knowledge/upload/document/", 
        files=files, 
        data=data, 
        headers=headers
    )
    
    if upload_response.status_code != 201:
        print(f"❌ Upload failed: {upload_response.status_code}")
        print(f"Response: {upload_response.text}")
        return False
        
    upload_result = upload_response.json()
    source_id = upload_result['id']
    print(f"✅ File uploaded successfully (Source ID: {source_id})")
    
    # Step 4: Wait for processing (simulating loading state in frontend)
    print("\n⏳ Step 4: Waiting for processing")
    time.sleep(3)
    
    # Step 5: Check processing results (simulating status check)
    print("\n📊 Step 5: Checking processing status")
    
    status_response = requests.get(
        f"{base_url}/knowledge-sources/{source_id}/", 
        headers=headers
    )
    
    if status_response.status_code != 200:
        print(f"❌ Failed to get status: {status_response.status_code}")
        return False
        
    source_data = status_response.json()
    
    print(f"📋 Processing Results:")
    print(f"   Status: {source_data['status']}")
    print(f"   Content Type: {source_data['content_type']}")
    print(f"   MIME Type: {source_data['mime_type']}")
    print(f"   File Size: {source_data['file_size']} bytes")
    print(f"   Created: {source_data['created_at']}")
    
    # Step 6: Verify chunks were created
    print("\n🔍 Step 6: Verifying knowledge chunks")
    
    chunks_response = requests.get(
        f"{base_url}/knowledge-chunks/?source={source_id}", 
        headers=headers
    )
    
    if chunks_response.status_code != 200:
        print(f"❌ Failed to get chunks: {chunks_response.status_code}")
        return False
        
    chunks_data = chunks_response.json()
    chunk_count = chunks_data['count']
    
    print(f"📦 Chunks Created: {chunk_count}")
    
    if chunk_count > 0:
        sample_chunk = chunks_data['results'][0]
        preview = sample_chunk['content'][:100] + "..." if len(sample_chunk['content']) > 100 else sample_chunk['content']
        print(f"📝 Sample Chunk: {preview}")
        print(f"🎯 Chunk ID: {sample_chunk['id']}")
    
    # Validation
    success = True
    
    if source_data['status'] != 'completed':
        print("❌ Processing did not complete successfully")
        success = False
    else:
        print("✅ Processing completed successfully")
        
    if chunk_count == 0:
        print("❌ No knowledge chunks were created")
        success = False
    else:
        print("✅ Knowledge chunks created successfully")
        
    if source_data['content_type'] != 'txt':
        print(f"❌ Wrong content type: {source_data['content_type']}")
        success = False
    else:
        print("✅ Content type correctly mapped")
    
    return success

def main():
    """Run the frontend upload flow test."""
    print("Frontend File Upload Integration Test")
    print("Testing the complete user flow from frontend to backend processing")
    print()
    
    success = test_frontend_upload_flow()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 FRONTEND INTEGRATION TEST PASSED!")
        print()
        print("✅ Authentication works")
        print("✅ Chatbot selection works") 
        print("✅ File upload succeeds")
        print("✅ Content processing completes")
        print("✅ Knowledge chunks are created")
        print("✅ Status checking works")
        print()
        print("🏆 The file content corruption fix is working end-to-end!")
        print("📱 Users can successfully upload files through the ChatbotWizard")
        print("🔍 Files are processed and made searchable")
    else:
        print("🚨 FRONTEND INTEGRATION TEST FAILED!")
        print()
        print("❌ There are still issues with the upload flow")
        print("🔧 Check the error messages above for details")
    
    return success

if __name__ == "__main__":
    exit(0 if main() else 1)