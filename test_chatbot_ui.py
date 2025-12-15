#!/usr/bin/env python
"""
Comprehensive chatbot testing script.
"""

import requests
import json
import time

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USER = {
    "email": "validation-test@example.com",
    "password": "TestPass123@"
}
CHATBOT_ID = "b3c35778-396b-4e68-a325-e3a573f318ff"

def login():
    """Get authentication token."""
    response = requests.post(f"{BASE_URL}/auth/login/", json=TEST_USER)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None

def test_chatbot_conversation(token):
    """Test chatbot conversation quality."""
    print("🤖 TESTING CHATBOT CONVERSATION QUALITY")
    print("=" * 45)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test messages to evaluate conversation quality
    test_messages = [
        "Hello! How are you today?",
        "What can you help me with?",
        "Can you remember what I just asked?",
        "Tell me about your capabilities",
        "What's the weather like today?"
    ]
    
    conversation_id = None
    credits_before = None
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n📝 Test Message {i}: '{message}'")
        
        payload = {"message": message}
        if conversation_id:
            payload["conversation_id"] = conversation_id
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/chat/private/{CHATBOT_ID}/",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract response
                bot_response = data.get("response", "No response")
                conversation_id = data.get("conversation_id")
                usage = data.get("usage", {})
                
                print(f"✅ Bot Response: {bot_response[:100]}{'...' if len(bot_response) > 100 else ''}")
                print(f"📊 Credits consumed: {usage.get('credits_consumed', 'N/A')}")
                print(f"💰 Credits remaining: {usage.get('credits_remaining', 'N/A')}")
                print(f"🆔 Conversation ID: {conversation_id}")
                
                # Track credit consumption
                if credits_before is None:
                    credits_before = usage.get('credits_remaining', 0)
                
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"   Error: {response.text[:200]}")
                break
                
        except Exception as e:
            print(f"💥 Exception: {e}")
            break
        
        # Small delay between messages
        time.sleep(1)
    
    return conversation_id, credits_before

def test_memory_persistence(token, conversation_id):
    """Test if chatbot remembers conversation context."""
    print("\n🧠 TESTING MEMORY PERSISTENCE")
    print("=" * 35)
    
    if not conversation_id:
        print("❌ No conversation ID to test memory")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test memory with follow-up question
    memory_test_message = "What was the first thing I asked you?"
    
    payload = {
        "message": memory_test_message,
        "conversation_id": conversation_id
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/private/{CHATBOT_ID}/",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            bot_response = data.get("response", "No response")
            
            print(f"📝 Memory test: '{memory_test_message}'")
            print(f"🤖 Bot response: {bot_response}")
            
            # Check if bot remembers the conversation
            if "hello" in bot_response.lower() or "how are you" in bot_response.lower():
                print("✅ MEMORY WORKING: Bot remembers previous messages")
            else:
                print("❌ MEMORY ISSUE: Bot doesn't remember context")
                
        else:
            print(f"❌ Memory test failed: {response.status_code}")
            
    except Exception as e:
        print(f"💥 Memory test exception: {e}")

def main():
    print("🧪 COMPREHENSIVE CHATBOT ASSESSMENT")
    print("=" * 50)
    
    # Step 1: Login
    token = login()
    if not token:
        return
    
    print("✅ Authentication successful")
    
    # Step 2: Test conversation quality
    conversation_id, credits_before = test_chatbot_conversation(token)
    
    # Step 3: Test memory persistence
    if conversation_id:
        test_memory_persistence(token, conversation_id)
    
    # Step 4: Summary
    print("\n📊 CHATBOT ASSESSMENT SUMMARY")
    print("=" * 35)
    print("✅ Authentication: Working")
    print(f"✅ Conversation: {'Working' if conversation_id else 'Failed'}")
    print(f"✅ Credit system: {'Functional' if credits_before else 'Not tracked'}")
    print("✅ Memory: Test completed")

if __name__ == "__main__":
    main()