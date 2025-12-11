#!/usr/bin/env python3
"""
Direct test for document processing pipeline - Step 2 validation.

This script tests the document processing service directly without using the API.
"""

import os
import sys

# Add project root to path for Django imports
sys.path.append('/home/sakr_quraish/Projects/Ismail')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')

import django
django.setup()

from apps.chatbots.models import Chatbot
from apps.knowledge.models import KnowledgeSource, KnowledgeChunk
from apps.accounts.models import User
from apps.core.document_processing_service import DocumentProcessingService


def test_document_processing_pipeline():
    """Test the complete document processing pipeline."""
    print("🚀 Testing Document Processing Pipeline - Step 2")
    print("=" * 60)
    
    # Setup test data
    print("🔧 Setting up test data...")
    
    # Create or get test user
    user, created = User.objects.get_or_create(
        email='test@example.com',
        defaults={
            'name': 'Test User',
            'is_active': True
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"✅ Created test user: {user.email}")
    else:
        print(f"✅ Using existing test user: {user.email}")
    
    # Create or get test chatbot
    chatbot, created = Chatbot.objects.get_or_create(
        user=user,
        name='Test Chatbot Direct',
        defaults={
            'description': 'Test chatbot for direct document processing',
            'welcome_message': 'Hello! I can help test document processing.',
            'status': 'ready'
        }
    )
    
    if created:
        print(f"✅ Created test chatbot: {chatbot.name}")
    else:
        print(f"✅ Using existing test chatbot: {chatbot.name}")
    
    # Test 1: File processing with CITABLE setting
    print("\n📄 Test 1: Processing CITABLE document")
    test_file_path = "/home/sakr_quraish/Projects/Ismail/test_sample.txt"
    
    try:
        # Read test file
        with open(test_file_path, 'rb') as f:
            file_content = f.read()
        
        # Create knowledge source
        source_citable = KnowledgeSource.objects.create(
            chatbot=chatbot,
            name='Test Sample Document (Citable)',
            description='Test document for citable processing',
            content_type='document',
            file_path=test_file_path,
            file_size=len(file_content),
            mime_type='text/plain',
            is_citable=True,  # CITABLE
            status='pending',
            metadata={
                'original_filename': 'test_sample.txt',
                'test_type': 'citable'
            }
        )
        
        print(f"✅ Created citable knowledge source: {source_citable.id}")
        
        # Process the document
        doc_service = DocumentProcessingService()
        result = doc_service.process_uploaded_file(
            knowledge_source=source_citable,
            file_content=file_content,
            filename='test_sample.txt',
            mime_type='text/plain'
        )
        
        if result.success:
            print(f"✅ Document processed successfully")
            print(f"   Chunks created: {len(result.chunks)}")
            print(f"   Total tokens: {result.total_tokens}")
            print(f"   Processing time: {result.processing_time_ms}ms")
            print(f"   Quality score: {result.processed_document.quality_score}")
            
            # Verify chunks
            chunks = source_citable.chunks.all()
            print(f"   Database chunks: {chunks.count()}")
            
            # Check privacy inheritance
            privacy_consistent = all(chunk.is_citable == True for chunk in chunks)
            print(f"   Privacy inheritance: {'✅ Consistent' if privacy_consistent else '❌ Inconsistent'}")
            
            # Show first chunk details
            if chunks.exists():
                first_chunk = chunks.first()
                print(f"   First chunk preview: {first_chunk.content[:100]}...")
                print(f"   First chunk privacy: {'Citable' if first_chunk.is_citable else 'Learn-only'}")
                print(f"   First chunk tokens: {first_chunk.token_count}")
        else:
            print(f"❌ Document processing failed: {result.error_message}")
            
    except Exception as e:
        print(f"❌ Test 1 failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test 2: File processing with LEARN-ONLY setting
    print("\n📄 Test 2: Processing LEARN-ONLY document")
    
    try:
        # Create knowledge source with learn-only setting
        source_learn_only = KnowledgeSource.objects.create(
            chatbot=chatbot,
            name='Test Sample Document (Learn-Only)',
            description='Test document for learn-only processing',
            content_type='document',
            file_path=test_file_path,
            file_size=len(file_content),
            mime_type='text/plain',
            is_citable=False,  # LEARN-ONLY
            status='pending',
            metadata={
                'original_filename': 'test_sample.txt',
                'test_type': 'learn_only'
            }
        )
        
        print(f"✅ Created learn-only knowledge source: {source_learn_only.id}")
        
        # Process the document
        result2 = doc_service.process_uploaded_file(
            knowledge_source=source_learn_only,
            file_content=file_content,
            filename='test_sample.txt',
            mime_type='text/plain'
        )
        
        if result2.success:
            print(f"✅ Document processed successfully")
            print(f"   Chunks created: {len(result2.chunks)}")
            print(f"   Total tokens: {result2.total_tokens}")
            print(f"   Processing time: {result2.processing_time_ms}ms")
            
            # Verify chunks
            chunks = source_learn_only.chunks.all()
            print(f"   Database chunks: {chunks.count()}")
            
            # Check privacy inheritance
            privacy_consistent = all(chunk.is_citable == False for chunk in chunks)
            print(f"   Privacy inheritance: {'✅ Consistent' if privacy_consistent else '❌ Inconsistent'}")
            
            # Show first chunk details
            if chunks.exists():
                first_chunk = chunks.first()
                print(f"   First chunk preview: {first_chunk.content[:100]}...")
                print(f"   First chunk privacy: {'Citable' if first_chunk.is_citable else 'Learn-only'}")
                print(f"   First chunk tokens: {first_chunk.token_count}")
        else:
            print(f"❌ Document processing failed: {result2.error_message}")
            
    except Exception as e:
        print(f"❌ Test 2 failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test 3: URL processing
    print("\n🌐 Test 3: Processing URL content")
    
    try:
        # Create URL knowledge source
        test_url = "https://httpbin.org/html"
        url_hash = hash(test_url)
        
        source_url = KnowledgeSource.objects.create(
            chatbot=chatbot,
            name='Test URL Source',
            description='Test URL processing',
            content_type='url',
            source_url=test_url,
            file_hash=str(abs(url_hash)),
            is_citable=True,
            status='pending',
            metadata={
                'original_url': test_url,
                'test_type': 'url'
            }
        )
        
        print(f"✅ Created URL knowledge source: {source_url.id}")
        
        # Process the URL
        result3 = doc_service.process_url_content(
            knowledge_source=source_url,
            url=test_url
        )
        
        if result3.success:
            print(f"✅ URL processed successfully")
            print(f"   Chunks created: {len(result3.chunks)}")
            print(f"   Total tokens: {result3.total_tokens}")
            print(f"   Processing time: {result3.processing_time_ms}ms")
            
            # Verify chunks
            chunks = source_url.chunks.all()
            print(f"   Database chunks: {chunks.count()}")
            
            if chunks.exists():
                first_chunk = chunks.first()
                print(f"   First chunk preview: {first_chunk.content[:100]}...")
                print(f"   First chunk privacy: {'Citable' if first_chunk.is_citable else 'Learn-only'}")
        else:
            print(f"❌ URL processing failed: {result3.error_message}")
            
    except Exception as e:
        print(f"❌ Test 3 failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Final summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    
    total_sources = KnowledgeSource.objects.filter(chatbot=chatbot).count()
    total_chunks = KnowledgeChunk.objects.filter(source__chatbot=chatbot).count()
    
    citable_chunks = KnowledgeChunk.objects.filter(source__chatbot=chatbot, is_citable=True).count()
    learn_only_chunks = KnowledgeChunk.objects.filter(source__chatbot=chatbot, is_citable=False).count()
    
    print(f"   Total knowledge sources: {total_sources}")
    print(f"   Total chunks created: {total_chunks}")
    print(f"   Citable chunks: {citable_chunks}")
    print(f"   Learn-only chunks: {learn_only_chunks}")
    print(f"   Chatbot: {chatbot.name}")
    
    # Show recent sources
    recent_sources = KnowledgeSource.objects.filter(chatbot=chatbot).order_by('-created_at')[:5]
    print(f"\n📋 Recent sources:")
    for source in recent_sources:
        status_emoji = "✅" if source.status == 'completed' else "❌" if source.status == 'failed' else "⏳"
        privacy_emoji = "🔒" if not source.is_citable else "📖"
        print(f"   {status_emoji} {privacy_emoji} {source.name} ({source.chunk_count} chunks)")
    
    print("\n✅ Document Processing Pipeline Testing Complete!")


if __name__ == "__main__":
    test_document_processing_pipeline()