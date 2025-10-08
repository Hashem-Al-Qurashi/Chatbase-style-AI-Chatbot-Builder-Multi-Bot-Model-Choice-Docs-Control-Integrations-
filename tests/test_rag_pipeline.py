"""
Comprehensive tests for the RAG pipeline components.
Tests document processing, chunking, embeddings, and vector search.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import numpy as np

from apps.core.document_processing import (
    DocumentProcessingPipeline,
    PDFProcessor,
    DOCXProcessor,
    TextProcessor,
    URLProcessor,
    DocumentContent,
    PrivacyLevel,
    DocumentType
)
from apps.core.chunking import (
    ChunkingPipeline,
    FixedSizeChunker,
    SlidingWindowChunker,
    SemanticChunker,
    ParagraphChunker,
    ChunkingStrategy,
    ChunkingConfig
)
from apps.core.embeddings import (
    EmbeddingGenerator,
    PrivacyAwareEmbeddingService,
    EmbeddingConfig,
    EmbeddingProvider
)
from apps.core.vector_search import (
    VectorSearchEngine,
    PrivacyFilter,
    SearchScope,
    SearchConfig,
    SearchContext
)


class TestDocumentProcessing:
    """Test document processing components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pipeline = DocumentProcessingPipeline()
    
    def test_pdf_processor_can_process(self):
        """Test PDF processor file type detection."""
        processor = PDFProcessor()
        
        assert processor.can_process("application/pdf", ".pdf") is True
        assert processor.can_process("text/plain", ".txt") is False
        assert processor.can_process("application/pdf", ".txt") is True  # MIME type takes precedence
    
    @patch('apps.core.document_processing.PdfReader')
    def test_pdf_processor_extract_content(self, mock_pdf_reader):
        """Test PDF content extraction."""
        processor = PDFProcessor()
        
        # Mock PDF reader
        mock_page = Mock()
        mock_page.extract_text.return_value = "Sample PDF content"
        
        mock_reader_instance = Mock()
        mock_reader_instance.pages = [mock_page]
        mock_reader_instance.metadata = {
            "/Title": "Test Document",
            "/Author": "Test Author"
        }
        
        mock_pdf_reader.return_value = mock_reader_instance
        
        # Test extraction
        content = processor.extract_content(
            file_content=b"fake pdf content",
            filename="test.pdf",
            privacy_level=PrivacyLevel.CITABLE
        )
        
        assert content.text == "Sample PDF content"
        assert content.title == "Test Document"
        assert content.author == "Test Author"
        assert content.privacy_level == PrivacyLevel.CITABLE
        assert content.source_type == DocumentType.PDF
        assert content.token_count > 0
    
    def test_text_processor_can_process(self):
        """Test text processor file type detection."""
        processor = TextProcessor()
        
        assert processor.can_process("text/plain", ".txt") is True
        assert processor.can_process("text/markdown", ".md") is True
        assert processor.can_process("application/pdf", ".pdf") is False
    
    def test_text_processor_extract_content(self):
        """Test text content extraction."""
        processor = TextProcessor()
        
        text_content = "This is a sample text file.\n\nWith multiple paragraphs."
        
        content = processor.extract_content(
            file_content=text_content.encode('utf-8'),
            filename="test.txt",
            privacy_level=PrivacyLevel.PUBLIC
        )
        
        assert content.text == text_content
        assert content.title == "test.txt"
        assert content.privacy_level == PrivacyLevel.PUBLIC
        assert content.source_type == DocumentType.TXT
        assert content.token_count > 0
        assert "character_count" in content.metadata
        assert "line_count" in content.metadata
    
    def test_text_processor_markdown(self):
        """Test markdown file processing."""
        processor = TextProcessor()
        
        markdown_content = "# Test Document\n\nThis is a markdown file with a heading."
        
        content = processor.extract_content(
            file_content=markdown_content.encode('utf-8'),
            filename="test.md",
            privacy_level=PrivacyLevel.CITABLE
        )
        
        assert content.text == markdown_content
        assert content.title == "Test Document"  # Extracted from heading
        assert content.source_type == DocumentType.MARKDOWN
        assert content.metadata["format"] == "markdown"
    
    @patch('apps.core.document_processing.requests.get')
    @patch('apps.core.document_processing.BeautifulSoup')
    def test_url_processor_extract_content(self, mock_soup, mock_requests):
        """Test URL content extraction."""
        processor = URLProcessor()
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = b"<html><head><title>Test Page</title></head><body><p>Sample content</p></body></html>"
        mock_response.headers = {"content-type": "text/html"}
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response
        
        # Mock BeautifulSoup
        mock_soup_instance = Mock()
        mock_title = Mock()
        mock_title.get_text.return_value = "Test Page"
        mock_soup_instance.find.return_value = mock_title
        mock_soup_instance.get_text.return_value = "Test Page\nSample content"
        mock_soup.return_value = mock_soup_instance
        
        # Test extraction
        content = processor.extract_content(
            file_content=b"",  # Not used for URLs
            filename="https://example.com/test",
            privacy_level=PrivacyLevel.PUBLIC
        )
        
        assert content.title == "Test Page"
        assert "Sample content" in content.text
        assert content.source_type == DocumentType.URL
        assert content.metadata["url"] == "https://example.com/test"
    
    def test_pipeline_process_document_pdf(self, sample_files):
        """Test pipeline document processing for PDF."""
        with patch.object(self.pipeline, 'processors') as mock_processors:
            mock_processor = Mock()
            mock_processor.can_process.return_value = True
            mock_processor.extract_content.return_value = DocumentContent(
                text="Sample content",
                title="Test Doc",
                author=None,
                metadata={},
                privacy_level=PrivacyLevel.CITABLE,
                source_type=DocumentType.PDF,
                content_hash="test-hash",
                token_count=10
            )
            mock_processors.__iter__.return_value = [mock_processor]
            
            content = self.pipeline.process_document(
                file_content=sample_files['pdf'],
                filename="test.pdf",
                content_type="application/pdf",
                privacy_level=PrivacyLevel.CITABLE
            )
            
            assert content.text == "Sample content"
            assert content.title == "Test Doc"
            assert content.source_type == DocumentType.PDF


class TestChunking:
    """Test document chunking strategies."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pipeline = ChunkingPipeline()
        self.sample_content = DocumentContent(
            text="This is the first sentence. This is the second sentence. " * 20,
            title="Test Document",
            author=None,
            metadata={},
            privacy_level=PrivacyLevel.CITABLE,
            source_type=DocumentType.TXT,
            content_hash="test-hash",
            token_count=100
        )
    
    def test_fixed_size_chunker(self):
        """Test fixed-size chunking."""
        config = ChunkingConfig(
            strategy=ChunkingStrategy.FIXED_SIZE,
            chunk_size=50,
            overlap_size=10
        )
        chunker = FixedSizeChunker(config)
        
        chunks = chunker.chunk_document(self.sample_content)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.privacy_level == PrivacyLevel.CITABLE
            assert chunk.token_count <= config.chunk_size + 10  # Allow some variance
            assert "chunking_strategy" in chunk.metadata
            assert chunk.metadata["chunking_strategy"] == "fixed_size"
    
    def test_sliding_window_chunker(self):
        """Test sliding window chunking."""
        config = ChunkingConfig(
            strategy=ChunkingStrategy.SLIDING_WINDOW,
            chunk_size=30,
            overlap_size=10
        )
        chunker = SlidingWindowChunker(config)
        
        chunks = chunker.chunk_document(self.sample_content)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.privacy_level == PrivacyLevel.CITABLE
            assert "sentence_count" in chunk.metadata
            assert chunk.metadata["chunking_strategy"] == "sliding_window"
    
    def test_paragraph_chunker(self):
        """Test paragraph-based chunking."""
        # Create content with clear paragraphs
        paragraph_content = DocumentContent(
            text="First paragraph with some content.\n\nSecond paragraph with more content.\n\nThird paragraph with additional content.",
            title="Test Document",
            author=None,
            metadata={},
            privacy_level=PrivacyLevel.CITABLE,
            source_type=DocumentType.TXT,
            content_hash="test-hash",
            token_count=50
        )
        
        config = ChunkingConfig(
            strategy=ChunkingStrategy.PARAGRAPH,
            chunk_size=100
        )
        chunker = ParagraphChunker(config)
        
        chunks = chunker.chunk_document(paragraph_content)
        
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.privacy_level == PrivacyLevel.CITABLE
            assert "paragraph_count" in chunk.metadata
            assert chunk.metadata["chunking_strategy"] == "paragraph"
    
    @patch('apps.core.chunking.SentenceTransformer')
    def test_semantic_chunker_with_model(self, mock_sentence_transformer):
        """Test semantic chunking with mocked model."""
        # Mock sentence transformer
        mock_model = Mock()
        mock_embeddings = np.array([
            [0.1, 0.2, 0.3],  # Similar to next
            [0.15, 0.25, 0.35],  # Similar to previous
            [0.8, 0.9, 0.7],  # Different from others
            [0.85, 0.95, 0.75]  # Similar to previous
        ])
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model
        
        config = ChunkingConfig(
            strategy=ChunkingStrategy.SEMANTIC,
            similarity_threshold=0.5,
            min_sentences_per_chunk=1,
            max_sentences_per_chunk=5
        )
        chunker = SemanticChunker(config)
        
        chunks = chunker.chunk_document(self.sample_content)
        
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.privacy_level == PrivacyLevel.CITABLE
            assert "avg_similarity" in chunk.metadata
            assert chunk.metadata["chunking_strategy"] == "semantic"
    
    def test_semantic_chunker_fallback(self):
        """Test semantic chunker fallback when model unavailable."""
        config = ChunkingConfig(strategy=ChunkingStrategy.SEMANTIC)
        
        with patch.object(SemanticChunker, '_load_sentence_model') as mock_load:
            mock_load.side_effect = Exception("Model not available")
            chunker = SemanticChunker(config)
            
            # Should fallback to sliding window
            chunks = chunker.chunk_document(self.sample_content)
            
            assert len(chunks) >= 1
            # Should have used fallback strategy
    
    def test_chunking_pipeline_integration(self):
        """Test complete chunking pipeline."""
        chunks = self.pipeline.chunk_document(
            content=self.sample_content,
            strategy=ChunkingStrategy.FIXED_SIZE
        )
        
        assert len(chunks) > 0
        
        # Verify privacy preservation
        for chunk in chunks:
            assert chunk.privacy_level == self.sample_content.privacy_level
            assert "source_document_hash" in chunk.metadata
            assert chunk.metadata["source_document_hash"] == self.sample_content.content_hash
    
    def test_chunk_merging(self):
        """Test merging of small chunks."""
        config = ChunkingConfig(
            strategy=ChunkingStrategy.FIXED_SIZE,
            chunk_size=5,  # Very small chunks
            min_chunk_size=10,
            merge_short_chunks=True
        )
        
        chunks = self.pipeline.chunk_document(
            content=self.sample_content,
            config=config
        )
        
        # All chunks should meet minimum size requirement
        for chunk in chunks:
            assert chunk.token_count >= config.min_chunk_size or chunk.chunk_index == len(chunks) - 1


class TestEmbeddings:
    """Test embedding generation components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.embedding_service = PrivacyAwareEmbeddingService()
    
    @patch('apps.core.embeddings.OpenAIEmbeddingProvider')
    @pytest.mark.asyncio
    async def test_openai_embedding_provider(self, mock_provider_class):
        """Test OpenAI embedding provider."""
        from apps.core.embeddings import EmbeddingGenerator
        
        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.generate_embeddings.return_value = [
            Mock(embedding=[0.1, 0.2, 0.3], token_count=10, model="ada-002", metadata={})
        ]
        mock_provider_class.return_value = mock_provider
        
        generator = EmbeddingGenerator()
        generator.providers[EmbeddingProvider.OPENAI] = mock_provider
        
        # Create test chunks
        chunks = [
            Mock(
                content="Test content",
                privacy_level=PrivacyLevel.CITABLE,
                chunk_index=0
            )
        ]
        
        config = EmbeddingConfig(
            provider=EmbeddingProvider.OPENAI,
            model="text-embedding-ada-002",
            dimension=1536
        )
        
        batch = await generator.generate_chunk_embeddings(chunks, config)
        
        assert batch.embeddings[0] == [0.1, 0.2, 0.3]
        assert batch.provider == "openai"
        assert batch.metadata["total_chunks"] == 1
    
    @patch('apps.core.embeddings.SentenceTransformerProvider')
    @pytest.mark.asyncio
    async def test_sentence_transformer_provider(self, mock_provider_class):
        """Test Sentence Transformer embedding provider."""
        from apps.core.embeddings import EmbeddingGenerator
        
        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.generate_embeddings.return_value = [
            Mock(embedding=[0.4, 0.5, 0.6], token_count=8, model="miniLM", metadata={})
        ]
        mock_provider_class.return_value = mock_provider
        
        generator = EmbeddingGenerator()
        generator.providers[EmbeddingProvider.SENTENCE_TRANSFORMERS] = mock_provider
        
        chunks = [
            Mock(
                content="Test content",
                privacy_level=PrivacyLevel.PRIVATE,
                chunk_index=0
            )
        ]
        
        config = EmbeddingConfig(
            provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
            model="all-MiniLM-L6-v2",
            dimension=384
        )
        
        batch = await generator.generate_chunk_embeddings(chunks, config)
        
        assert batch.embeddings[0] == [0.4, 0.5, 0.6]
        assert batch.provider == "sentence_transformers"
    
    @pytest.mark.asyncio
    async def test_privacy_aware_embedding_service(self, mock_document_chunks):
        """Test privacy-aware embedding service."""
        # Mock the embedding generator
        with patch.object(self.embedding_service, 'generator') as mock_generator:
            mock_batch = Mock()
            mock_batch.embeddings = [[0.1, 0.2, 0.3] for _ in range(len(mock_document_chunks))]
            mock_batch.metadata = {"total_chunks": len(mock_document_chunks)}
            mock_generator.generate_chunk_embeddings.return_value = mock_batch
            
            results = await self.embedding_service.process_document_chunks(mock_document_chunks)
            
            assert PrivacyLevel.CITABLE in results
            batch = results[PrivacyLevel.CITABLE]
            assert len(batch.embeddings) == len(mock_document_chunks)
    
    def test_privacy_compliance_validation(self, mock_document_chunks):
        """Test privacy compliance validation."""
        # All chunks are CITABLE, should pass for CITABLE target
        is_compliant = self.embedding_service.validate_privacy_compliance(
            mock_document_chunks, PrivacyLevel.CITABLE
        )
        assert is_compliant is True
        
        # CITABLE chunks should fail for PRIVATE target
        is_compliant = self.embedding_service.validate_privacy_compliance(
            mock_document_chunks, PrivacyLevel.PRIVATE
        )
        assert is_compliant is False
    
    @patch('apps.core.embeddings.cache')
    def test_embedding_caching(self, mock_cache):
        """Test embedding caching functionality."""
        from apps.core.embeddings import EmbeddingCache
        
        cache_instance = EmbeddingCache()
        
        # Test cache miss
        mock_cache.get.return_value = None
        result = cache_instance.get_embedding("test content", "ada-002", PrivacyLevel.PUBLIC)
        assert result is None
        
        # Test cache hit
        cached_data = {
            "embedding": [0.1, 0.2, 0.3],
            "model": "ada-002",
            "privacy_level": "public"
        }
        mock_cache.get.return_value = cached_data
        result = cache_instance.get_embedding("test content", "ada-002", PrivacyLevel.PUBLIC)
        assert result == [0.1, 0.2, 0.3]
        
        # Test cache set
        cache_instance.set_embedding(
            "test content", "ada-002", PrivacyLevel.PUBLIC, [0.4, 0.5, 0.6]
        )
        mock_cache.set.assert_called()


class TestVectorSearch:
    """Test vector search components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_vector_store = AsyncMock()
        from apps.core.vector_search import VectorSearchEngine
        self.search_engine = VectorSearchEngine(self.mock_vector_store)
    
    def test_privacy_filter_creation(self):
        """Test privacy filter creation."""
        filters = PrivacyFilter.create_privacy_filters(
            search_scope=SearchScope.CITABLE_AND_PRIVATE,
            user_id="test-user",
            knowledge_base_ids=["kb1", "kb2"]
        )
        
        assert len(filters) > 0
        # Should have privacy level and knowledge base filters
        privacy_filter = next((f for f in filters if f.field == "privacy_level"), None)
        kb_filter = next((f for f in filters if f.field == "knowledge_base_id"), None)
        
        assert privacy_filter is not None
        assert kb_filter is not None
        assert kb_filter.value == ["kb1", "kb2"]
    
    def test_citation_permission_check(self):
        """Test citation permission checking."""
        from apps.core.interfaces import SearchResult
        
        # Public content - should be citable by anyone
        public_result = SearchResult(
            id="result1",
            score=0.9,
            metadata={"privacy_level": "public", "user_id": "other-user"},
            content="Public content"
        )
        assert PrivacyFilter.can_cite_result(public_result, "test-user") is True
        
        # Private content - only citable by owner
        private_result = SearchResult(
            id="result2",
            score=0.8,
            metadata={"privacy_level": "private", "user_id": "test-user"},
            content="Private content"
        )
        assert PrivacyFilter.can_cite_result(private_result, "test-user") is True
        assert PrivacyFilter.can_cite_result(private_result, "other-user") is False
    
    def test_result_sanitization(self):
        """Test search result sanitization for privacy."""
        from apps.core.interfaces import SearchResult
        
        result = SearchResult(
            id="result1",
            score=0.9,
            metadata={
                "privacy_level": "citable",
                "user_id": "test-user",
                "document_title": "Test Document",
                "document_author": "Test Author",
                "chunk_index": 0
            },
            content="Test content"
        )
        
        sanitized = PrivacyFilter.sanitize_result_for_privacy(
            result, "test-user", require_citations=True
        )
        
        assert sanitized is not None
        assert sanitized.can_cite is True
        assert sanitized.citation_text is not None
        assert "Test Document" in sanitized.citation_text
        assert sanitized.privacy_level == PrivacyLevel.CITABLE
    
    @pytest.mark.asyncio
    async def test_vector_search_with_privacy(self, mock_search_results):
        """Test vector search with privacy filtering."""
        from apps.core.vector_search import SearchContext, SearchConfig
        from apps.core.interfaces import SearchResult
        
        # Mock vector store search results
        raw_results = [
            SearchResult(
                id=f"result-{i}",
                score=0.9 - (i * 0.1),
                metadata={
                    "privacy_level": "citable",
                    "user_id": "test-user",
                    "document_id": f"doc-{i}",
                    "knowledge_base_id": "kb-1"
                },
                content=f"Result {i} content"
            )
            for i in range(3)
        ]
        self.mock_vector_store.search.return_value = raw_results
        
        context = SearchContext(
            user_id="test-user",
            knowledge_base_ids=["kb-1"],
            privacy_level=PrivacyLevel.CITABLE,
            search_intent="answer"
        )
        
        config = SearchConfig(
            top_k=5,
            search_scope=SearchScope.CITABLE_AND_PRIVATE
        )
        
        results = await self.search_engine.search(
            query_vector=[0.1, 0.2, 0.3],
            query_text="test query",
            context=context,
            config=config
        )
        
        assert len(results) == 3
        for result in results:
            assert result.can_cite is True
            assert result.privacy_level == PrivacyLevel.CITABLE
    
    @patch('apps.core.vector_search.SemanticReranker')
    @pytest.mark.asyncio
    async def test_semantic_reranking(self, mock_reranker_class):
        """Test semantic reranking of search results."""
        from apps.core.vector_search import SearchContext, SearchConfig
        from apps.core.interfaces import SearchResult
        
        # Mock reranker
        mock_reranker = AsyncMock()
        mock_reranker.rerank_results.return_value = mock_search_results[:2]  # Return top 2
        mock_reranker_class.return_value = mock_reranker
        
        # Create search engine with mocked reranker
        self.search_engine.reranker = mock_reranker
        
        # Mock vector store results
        raw_results = [
            SearchResult(
                id=f"result-{i}",
                score=0.5,  # Low initial scores
                metadata={
                    "privacy_level": "public",
                    "document_id": f"doc-{i}"
                },
                content=f"Result {i} content"
            )
            for i in range(3)
        ]
        self.mock_vector_store.search.return_value = raw_results
        
        context = SearchContext(
            user_id="test-user",
            knowledge_base_ids=["kb-1"],
            privacy_level=PrivacyLevel.PUBLIC,
            search_intent="research"
        )
        
        config = SearchConfig(
            top_k=2,
            enable_reranking=True,
            rerank_top_k=5
        )
        
        results = await self.search_engine.search(
            query_vector=[0.1, 0.2, 0.3],
            query_text="test query",
            context=context,
            config=config
        )
        
        # Should have called reranking
        mock_reranker.rerank_results.assert_called_once()
        assert len(results) <= 2  # Should be limited by top_k


class TestIntegration:
    """Integration tests for RAG pipeline components."""
    
    @pytest.mark.asyncio
    async def test_full_rag_pipeline(self):
        """Test complete RAG pipeline from document to search."""
        # Step 1: Document processing
        sample_text = "This is a comprehensive test document. " * 10
        
        with patch('apps.core.document_processing.tiktoken.get_encoding') as mock_encoding:
            mock_encoder = Mock()
            mock_encoder.encode.return_value = list(range(50))  # Mock 50 tokens
            mock_encoding.return_value = mock_encoder
            
            document_content = DocumentContent(
                text=sample_text,
                title="Test Document",
                author="Test Author",
                metadata={"test": True},
                privacy_level=PrivacyLevel.CITABLE,
                source_type=DocumentType.TXT,
                content_hash="test-hash",
                token_count=50
            )
        
        # Step 2: Chunking
        chunking_pipeline = ChunkingPipeline()
        chunks = chunking_pipeline.chunk_document(
            content=document_content,
            strategy=ChunkingStrategy.FIXED_SIZE
        )
        
        assert len(chunks) > 0
        assert all(chunk.privacy_level == PrivacyLevel.CITABLE for chunk in chunks)
        
        # Step 3: Embedding generation (mocked)
        embedding_service = PrivacyAwareEmbeddingService()
        
        with patch.object(embedding_service, 'generator') as mock_generator:
            mock_batch = Mock()
            mock_batch.embeddings = [[0.1, 0.2, 0.3] for _ in range(len(chunks))]
            mock_batch.metadata = {"total_chunks": len(chunks)}
            mock_generator.generate_chunk_embeddings.return_value = mock_batch
            
            embedding_results = await embedding_service.process_document_chunks(chunks)
            
            assert PrivacyLevel.CITABLE in embedding_results
            batch = embedding_results[PrivacyLevel.CITABLE]
            assert len(batch.embeddings) == len(chunks)
        
        # Step 4: Vector search (mocked)
        mock_vector_store = AsyncMock()
        search_engine = VectorSearchEngine(mock_vector_store)
        
        from apps.core.interfaces import SearchResult
        from apps.core.vector_search import SearchContext, SearchConfig
        
        mock_results = [
            SearchResult(
                id=f"chunk-{i}",
                score=0.9 - (i * 0.1),
                metadata={
                    "privacy_level": "citable",
                    "document_id": "test-doc",
                    "chunk_index": i
                },
                content=f"Chunk {i} content"
            )
            for i in range(len(chunks))
        ]
        mock_vector_store.search.return_value = mock_results
        
        context = SearchContext(
            user_id="test-user",
            knowledge_base_ids=["test-kb"],
            privacy_level=PrivacyLevel.CITABLE,
            search_intent="answer"
        )
        
        config = SearchConfig(top_k=3)
        
        search_results = await search_engine.search(
            query_vector=[0.1, 0.2, 0.3],
            query_text="test query",
            context=context,
            config=config
        )
        
        assert len(search_results) == 3
        assert all(result.can_cite for result in search_results)
    
    def test_privacy_enforcement_throughout_pipeline(self):
        """Test privacy enforcement at each stage of the pipeline."""
        # Test different privacy levels
        privacy_levels = [PrivacyLevel.PRIVATE, PrivacyLevel.CITABLE, PrivacyLevel.PUBLIC]
        
        for privacy_level in privacy_levels:
            # Document processing preserves privacy
            document_content = DocumentContent(
                text="Test content",
                title="Test",
                author=None,
                metadata={},
                privacy_level=privacy_level,
                source_type=DocumentType.TXT,
                content_hash="hash",
                token_count=10
            )
            
            # Chunking preserves privacy
            chunking_pipeline = ChunkingPipeline()
            chunks = chunking_pipeline.chunk_document(
                content=document_content,
                strategy=ChunkingStrategy.FIXED_SIZE
            )
            
            for chunk in chunks:
                assert chunk.privacy_level == privacy_level
                assert chunk.metadata["privacy_level"] == privacy_level.value
            
            # Privacy filter respects privacy levels
            from apps.core.vector_search import PrivacyFilter, SearchScope
            
            # Private content should only be accessible to owner
            if privacy_level == PrivacyLevel.PRIVATE:
                filters = PrivacyFilter.create_privacy_filters(
                    SearchScope.PRIVATE_ONLY, user_id="owner"
                )
                assert any(f.field == "privacy_level" and f.value == "private" for f in filters)
            
            # Public content should be accessible in public scope
            elif privacy_level == PrivacyLevel.PUBLIC:
                filters = PrivacyFilter.create_privacy_filters(SearchScope.PUBLIC_ONLY)
                assert any(f.field == "privacy_level" and f.value == "public" for f in filters)