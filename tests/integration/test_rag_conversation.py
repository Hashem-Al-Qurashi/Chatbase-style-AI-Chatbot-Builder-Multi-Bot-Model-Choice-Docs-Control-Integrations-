#!/usr/bin/env python3
"""
Test RAG conversation functionality end-to-end
"""

import os
import sys
import asyncio
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from apps.chatbots.models import Chatbot
from apps.conversations.models import Conversation, Message
from apps.knowledge.models import KnowledgeSource, KnowledgeChunk

User = get_user_model()

async def test_conversation_functionality():
    """Test end-to-end RAG conversation functionality"""
    print("🤖 Testing RAG Conversation Pipeline")
    print("=" * 50)
    
    # Get admin user
    try:
        user = await sync_to_async(User.objects.get)(email='admin@test.com')
        print(f"✅ User found: {user.email}")
    except User.DoesNotExist:
        print("❌ Admin user not found")
        return False
    
    # Get test chatbot
    try:
        chatbot = await sync_to_async(lambda: user.chatbots.first())()
        if not chatbot:
            # Create test chatbot if none exists
            chatbot = await sync_to_async(Chatbot.objects.create)(
                user=user,
                name="RAG Functionality Test",
                description="Testing RAG conversation pipeline",
                welcome_message="Hello! I'm ready to test RAG functionality."
            )
            print(f"✅ Created test chatbot: {chatbot.name}")
        else:
            print(f"✅ Using existing chatbot: {chatbot.name}")
            
    except Exception as e:
        print(f"❌ Chatbot setup failed: {e}")
        return False
    
    # Check if we have knowledge sources
    knowledge_sources_count = await sync_to_async(lambda: chatbot.knowledge_sources.filter(status='completed').count())()
    print(f"📚 Knowledge sources available: {knowledge_sources_count}")
    
    # Check for knowledge chunks
    total_chunks = await sync_to_async(KnowledgeChunk.objects.filter(source__chatbot=chatbot).count)()
    citable_chunks = await sync_to_async(KnowledgeChunk.objects.filter(source__chatbot=chatbot, is_citable=True).count)()
    print(f"📄 Knowledge chunks: {total_chunks} total, {citable_chunks} citable")
    
    # Test conversation creation
    try:
        conversation = await sync_to_async(Conversation.objects.create)(
            chatbot=chatbot,
            user_identifier=str(user.id)
        )
        print(f"✅ Conversation created: {conversation.id}")
    except Exception as e:
        print(f"❌ Conversation creation failed: {e}")
        return False
    
    # Test user message creation  
    try:
        user_message = await sync_to_async(Message.objects.create)(
            conversation=conversation,
            role='user',
            content='Hello, can you tell me about the company policies?'
        )
        print(f"✅ User message created: {user_message.id}")
    except Exception as e:
        print(f"❌ User message creation failed: {e}")
        return False
    
    # Test RAG pipeline integration
    print("\n🔍 Testing RAG Pipeline Integration...")
    
    try:
        # Try to import RAG components
        from apps.core.rag.pipeline import get_rag_pipeline
        print("✅ RAG pipeline import successful")
        
        # Try to get RAG pipeline for chatbot
        rag_pipeline = get_rag_pipeline(str(chatbot.id))
        print("✅ RAG pipeline initialized")
        
        # Test basic query processing
        from apps.core.rag.llm_service import ChatbotConfig
        
        chatbot_config = ChatbotConfig(
            name=chatbot.name,
            description=chatbot.description or "AI Assistant",
            temperature=0.7,
            max_response_tokens=100,
            strict_citation_mode=True,
            allow_private_reasoning=True
        )
        print("✅ Chatbot config created")
        
        # Process test query
        test_query = "Hello, can you help me?"
        rag_response = await rag_pipeline.process_query(
            user_query=test_query,
            user_id=str(user.id),
            conversation_id=str(conversation.id),
            chatbot_config=chatbot_config
        )
        
        print(f"✅ RAG response generated:")
        print(f"   Content: {rag_response.content[:100]}...")
        print(f"   Sources cited: {len(rag_response.citations)}")
        print(f"   Input tokens: {rag_response.input_tokens}")  
        print(f"   Output tokens: {rag_response.output_tokens}")
        print(f"   Cost: ${rag_response.estimated_cost:.6f}")
        
        # Test assistant message creation
        assistant_message = await sync_to_async(Message.objects.create)(
            conversation=conversation,
            role='assistant', 
            content=rag_response.content,
            metadata={
                'sources_cited': rag_response.citations,
                'input_tokens': rag_response.input_tokens,
                'output_tokens': rag_response.output_tokens,
                'cost_usd': rag_response.estimated_cost
            }
        )
        print(f"✅ Assistant message created: {assistant_message.id}")
        
        print("\n🎉 RAG CONVERSATION PIPELINE FULLY FUNCTIONAL!")
        return True
        
    except ImportError as e:
        print(f"❌ RAG pipeline import failed: {e}")
        print("   RAG components not available")
        return False
        
    except Exception as e:
        print(f"❌ RAG pipeline processing failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False

async def main():
    """Main test function."""
    success = await test_conversation_functionality()
    if success:
        print("\n✅ RAG conversation system is FUNCTIONAL!")
        sys.exit(0)
    else:
        print("\n❌ RAG conversation system has CRITICAL ISSUES!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())