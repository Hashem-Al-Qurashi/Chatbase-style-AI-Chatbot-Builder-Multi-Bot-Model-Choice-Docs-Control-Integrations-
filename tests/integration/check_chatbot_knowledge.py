#!/usr/bin/env python
"""Check if chatbot has knowledge chunks."""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from apps.chatbots.models import Chatbot
from apps.knowledge.models import KnowledgeSource, KnowledgeChunk

chatbot_id = "57dae851-d7f5-4458-9587-70012aea74ca"

try:
    chatbot = Chatbot.objects.get(id=chatbot_id)
    print(f"✓ Found chatbot: {chatbot.name}")
    print(f"  Status: {chatbot.status}")
    print(f"  Model: {chatbot.model_name}")
    
    # Check knowledge sources
    sources = KnowledgeSource.objects.filter(chatbot=chatbot)
    print(f"\n✓ Knowledge Sources: {sources.count()}")
    
    for source in sources:
        print(f"  - {source.name} ({source.status})")
        chunks = KnowledgeChunk.objects.filter(source=source)
        print(f"    Chunks: {chunks.count()}")
        print(f"    Processing status: {source.status}")
        
        # Show first chunk if exists
        if chunks.exists():
            first_chunk = chunks.first()
            print(f"    First chunk preview: {first_chunk.content[:100]}...")
            print(f"    Has embedding: {bool(first_chunk.embedding_vector)}")
            print(f"    Is citable: {first_chunk.is_citable}")
    
    # Check if there are any embeddings
    total_chunks = KnowledgeChunk.objects.filter(source__chatbot=chatbot).count()
    chunks_with_embeddings = KnowledgeChunk.objects.filter(
        source__chatbot=chatbot,
        embedding_vector__isnull=False
    ).exclude(embedding_vector=[]).count()
    
    print(f"\n📊 Summary:")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Chunks with embeddings: {chunks_with_embeddings}")
    
    if total_chunks == 0:
        print("\n❌ NO KNOWLEDGE CHUNKS - This is why chat isn't responding!")
    elif chunks_with_embeddings == 0:
        print("\n❌ NO EMBEDDINGS - Chunks exist but have no embeddings!")
    else:
        print("\n✓ Knowledge base is ready")
        
except Chatbot.DoesNotExist:
    print(f"❌ Chatbot {chatbot_id} not found")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()