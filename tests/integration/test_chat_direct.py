#!/usr/bin/env python
"""Test chat endpoint directly."""

import os
import sys
import django
import json
import time
import asyncio

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from apps.chatbots.models import Chatbot
from apps.conversations.models import Conversation, Message
from apps.core.rag.pipeline import RAGPipeline

async def test_chat():
    """Test the chat flow directly."""
    chatbot_id = "57dae851-d7f5-4458-9587-70012aea74ca"
    
    try:
        # Get chatbot
        from asgiref.sync import sync_to_async
        chatbot = await sync_to_async(Chatbot.objects.get)(id=chatbot_id)
        print(f"✓ Found chatbot: {chatbot.name}")
        
        # Create a test conversation
        import uuid
        conversation = await sync_to_async(Conversation.objects.create)(
            chatbot=chatbot,
            session_id=str(uuid.uuid4()),
            user_identifier="test_user"
        )
        print(f"✓ Created conversation: {conversation.id}")
        
        # Create user message
        user_message = await sync_to_async(Message.objects.create)(
            conversation=conversation,
            role="user",
            content="Can you tell me the content of the PDF I gave you?"
        )
        print(f"✓ Created user message")
        
        # Initialize RAG pipeline
        print("\n🔄 Initializing RAG pipeline...")
        rag_pipeline = RAGPipeline()
        
        # Prepare query
        query = "Can you tell me the content of the PDF I gave you?"
        
        print(f"🔍 Processing query: {query}")
        
        # Run RAG pipeline
        start_time = time.time()
        
        try:
            response = await rag_pipeline.run(
                query=query,
                chatbot_id=str(chatbot_id),
                user_id="test_user",
                conversation_id=str(conversation.id),
                stream=False
            )
            
            elapsed = time.time() - start_time
            print(f"\n✓ Got response in {elapsed:.2f} seconds")
            print(f"Response: {response.content[:500]}...")
            print(f"Citations: {len(response.citations)}")
            print(f"Privacy compliant: {response.privacy_compliant}")
            
        except Exception as e:
            print(f"\n❌ RAG pipeline error: {e}")
            import traceback
            traceback.print_exc()
            
            # Try a simpler approach
            print("\n🔄 Trying simpler approach...")
            from apps.core.rag_orchestrator import RAGOrchestrator, RAGQuery
            
            orchestrator = RAGOrchestrator()
            rag_query = RAGQuery(
                text=query,
                user_id="test_user",
                chatbot_id=str(chatbot_id)
            )
            
            response = await orchestrator.process_query(rag_query)
            print(f"✓ Got response: {response.response[:500]}...")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("TESTING CHAT ENDPOINT DIRECTLY")
    print("=" * 60)
    
    # Run async test
    asyncio.run(test_chat())