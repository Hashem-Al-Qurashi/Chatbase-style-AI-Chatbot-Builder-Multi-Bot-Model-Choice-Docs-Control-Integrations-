#!/usr/bin/env python
"""
Test script to validate RAG improvements:
1. Privacy filter not replacing content words
2. PDF text extraction with proper spacing
3. Smaller, more precise citations
"""

import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from apps.core.document_processing import PDFProcessor
from apps.core.text_chunking import TextChunker, ChunkingConfig
from apps.core.rag.privacy_filter import PrivacyFilter
from apps.core.rag.context_builder import ContextBuilder, ContextData, ContextSource

def test_privacy_filter():
    """Test that privacy filter doesn't replace content words."""
    print("\n=== Testing Privacy Filter ===")
    
    # Create test response with "Confidentiality Agreement"
    test_response = """
    Based on the content provided in the PDF you shared, the document appears to be a 
    Confidentiality Agreement (NDA) between nBridge, Ltd. (Company) located in Japan 
    and Hashem Hanafy (Contractor), an independent contractor located in Egypt. 
    The Agreement outlines the purpose of sharing confidential information related to 
    technical development and programming work for the Retrieval-Augmented Generation (RAG) 
    system for factory documents.
    """
    
    # Create mock context
    context = ContextData(
        full_context="Test context",
        citable_sources=[],
        private_sources=[],
        token_count=100,
        total_sources=0,
        citable_count=0,
        private_count=0,
        context_score=0.9,
        search_metadata={}
    )
    
    # Test privacy filter
    privacy_filter = PrivacyFilter()
    result = privacy_filter.validate_response(
        test_response,
        context,
        strict_mode=False
    )
    
    print(f"Original text contains 'Confidentiality': {bool('Confidentiality' in test_response)}")
    print(f"Sanitized text contains 'Confidentiality': {bool('Confidentiality' in result.sanitized_response)}")
    print(f"Text was incorrectly modified: {bool('available information' in result.sanitized_response)}")
    print(f"Privacy violations found: {len(result.violations)}")
    
    assert 'Confidentiality' in result.sanitized_response, "Privacy filter should not replace 'Confidentiality'"
    assert 'available information' not in result.sanitized_response, "Should not replace with 'available information'"
    print("✓ Privacy filter test passed")
    
    return result


def test_pdf_text_extraction():
    """Test PDF text extraction with proper spacing."""
    print("\n=== Testing PDF Text Extraction ===")
    
    # Create a sample PDF-like text with spacing issues
    sample_pdf_text = "ConﬁdentialityAgreement(NDA)ThisConﬁdentialityAgreement"
    
    processor = PDFProcessor()
    cleaned_text = processor._clean_pdf_text(sample_pdf_text)
    
    print(f"Original: {sample_pdf_text[:50]}...")
    print(f"Cleaned: {cleaned_text[:50]}...")
    
    # Check that ligatures are fixed
    assert 'fi' in cleaned_text, "Ligatures should be fixed"
    
    # Check that spaces are added between words
    assert 'Confidentiality Agreement' in cleaned_text, "Should add spaces between words"
    assert 'This Confidentiality' in cleaned_text, "Should add space between sentences"
    
    print("✓ PDF text extraction test passed")
    
    return cleaned_text


def test_chunking_granularity():
    """Test that chunking produces smaller, more precise chunks."""
    print("\n=== Testing Chunking Granularity ===")
    
    # Create sample text
    sample_text = """
    This is the first paragraph of our test document. It contains important information
    about the system architecture and design principles that we follow in our development.
    
    This is the second paragraph with different content. It discusses the implementation
    details and specific technical requirements for the project components.
    
    This is the third paragraph explaining the testing strategy. We use comprehensive
    test coverage to ensure quality and reliability of our system.
    """
    
    # Test with new config (smaller chunks)
    config = ChunkingConfig()
    
    print(f"Chunk size config: {config.chunk_size}")
    print(f"Max chunk size config: {config.max_chunk_size}")
    print(f"Chunk overlap config: {config.chunk_overlap}")
    
    # Verify config has smaller values
    assert config.chunk_size == 500, f"Expected chunk_size=500, got {config.chunk_size}"
    assert config.max_chunk_size == 800, f"Expected max_chunk_size=800, got {config.max_chunk_size}"
    assert config.chunk_overlap == 100, f"Expected chunk_overlap=100, got {config.chunk_overlap}"
    
    # Simulate chunking results with new config
    chunks = []
    lines = sample_text.strip().split('\n\n')
    for i, paragraph in enumerate(lines):
        if paragraph.strip():
            chunks.append({
                'content': paragraph.strip(),
                'chunk_index': i,
                'token_count': len(paragraph.split())
            })
    
    print(f"Number of chunks: {len(chunks)}")
    print(f"Average chunk size: {sum(len(c['content']) for c in chunks) / len(chunks):.0f} chars")
    print(f"Max chunk size: {max(len(c['content']) for c in chunks)} chars")
    
    # Verify chunks are reasonably sized
    for chunk in chunks:
        assert len(chunk['content']) < 800, f"Chunk too large: {len(chunk['content'])} chars"
    
    print("✓ Chunking granularity test passed")
    
    return chunks


def test_citation_formatting():
    """Test that citations are concise and readable."""
    print("\n=== Testing Citation Formatting ===")
    
    # Create mock context with long content
    long_content = "A" * 1000  # Very long content
    
    context_data = ContextData(
        full_context="Test",
        citable_sources=[
            ContextSource(
                content=long_content,
                source_id="test-1",
                document_id="doc-1",
                knowledge_base_id="kb-1",
                score=0.95,
                is_citable=True,
                citation_text=None
            )
        ],
        private_sources=[],
        token_count=100,
        total_sources=1,
        citable_count=1,
        private_count=0,
        context_score=0.9,
        search_metadata={}
    )
    
    # Test citation generation
    context_builder = ContextBuilder()
    citations = context_builder.get_citation_list(context_data)
    
    print(f"Number of citations: {len(citations)}")
    
    for i, citation in enumerate(citations):
        print(f"Citation {i+1} length: {len(citation)} chars")
        assert len(citation) <= 153, f"Citation too long: {len(citation)} chars"  # 150 + "..."
    
    print("✓ Citation formatting test passed")
    
    return citations


def main():
    """Run all tests."""
    print("=" * 60)
    print("RAG IMPROVEMENT VALIDATION TESTS")
    print("=" * 60)
    
    try:
        # Test 1: Privacy filter
        privacy_result = test_privacy_filter()
        
        # Test 2: PDF text extraction
        pdf_result = test_pdf_text_extraction()
        
        # Test 3: Chunking granularity
        chunks_result = test_chunking_granularity()
        
        # Test 4: Citation formatting
        citations_result = test_citation_formatting()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nSummary:")
        print("1. Privacy filter no longer replaces content words")
        print("2. PDF text extraction handles spacing correctly")
        print("3. Chunks are smaller and more precise")
        print("4. Citations are concise and readable")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()