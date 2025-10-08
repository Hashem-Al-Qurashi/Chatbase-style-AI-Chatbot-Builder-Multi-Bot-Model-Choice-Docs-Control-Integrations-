"""
Document chunking strategies with privacy enforcement.
Implements semantic chunking, sliding window, and hybrid approaches.
"""

import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib
import logging

import tiktoken
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from apps.core.document_processing import DocumentContent, DocumentChunk, PrivacyLevel
from chatbot_saas.config import get_settings


settings = get_settings()
logger = logging.getLogger(__name__)


class ChunkingStrategy(Enum):
    """Available chunking strategies."""
    FIXED_SIZE = "fixed_size"
    SLIDING_WINDOW = "sliding_window"
    SEMANTIC = "semantic"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    HYBRID = "hybrid"


@dataclass
class ChunkingConfig:
    """Configuration for chunking strategies."""
    strategy: ChunkingStrategy
    chunk_size: int = 1000  # In tokens
    overlap_size: int = 200  # In tokens
    min_chunk_size: int = 100  # Minimum tokens per chunk
    max_chunk_size: int = 2000  # Maximum tokens per chunk
    
    # Semantic chunking parameters
    similarity_threshold: float = 0.5
    min_sentences_per_chunk: int = 2
    max_sentences_per_chunk: int = 20
    
    # Privacy enforcement
    preserve_privacy_boundaries: bool = True
    merge_short_chunks: bool = True


class Chunker(ABC):
    """Abstract base class for document chunkers."""
    
    def __init__(self, config: ChunkingConfig):
        self.config = config
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    @abstractmethod
    def chunk_document(self, content: DocumentContent) -> List[DocumentChunk]:
        """Chunk document content into smaller pieces."""
        pass
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))
    
    def _create_chunk(
        self,
        content: str,
        chunk_index: int,
        start_char: int,
        end_char: int,
        privacy_level: PrivacyLevel,
        metadata: Dict[str, Any]
    ) -> DocumentChunk:
        """Create a document chunk with proper metadata."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        token_count = self._count_tokens(content)
        
        return DocumentChunk(
            content=content,
            chunk_index=chunk_index,
            start_char=start_char,
            end_char=end_char,
            token_count=token_count,
            privacy_level=privacy_level,
            metadata=metadata,
            content_hash=content_hash
        )
    
    def _validate_chunk_size(self, chunk: DocumentChunk) -> bool:
        """Validate chunk size against configuration."""
        return (
            self.config.min_chunk_size <= chunk.token_count <= self.config.max_chunk_size
        )


class FixedSizeChunker(Chunker):
    """Fixed-size chunking with token-based boundaries."""
    
    def chunk_document(self, content: DocumentContent) -> List[DocumentChunk]:
        """Chunk document into fixed-size pieces."""
        text = content.text
        chunks = []
        chunk_index = 0
        
        # Encode full text to work with tokens
        tokens = self.encoding.encode(text)
        
        start_token = 0
        while start_token < len(tokens):
            # Calculate end token with overlap
            end_token = min(start_token + self.config.chunk_size, len(tokens))
            
            # Extract token slice and decode
            chunk_tokens = tokens[start_token:end_token]
            chunk_text = self.encoding.decode(chunk_tokens)
            
            # Find character positions in original text
            # This is approximate due to token-text mapping complexity
            start_char = self._estimate_char_position(text, start_token, tokens)
            end_char = self._estimate_char_position(text, end_token, tokens)
            
            # Create chunk metadata
            chunk_metadata = {
                "chunking_strategy": "fixed_size",
                "chunk_size_tokens": len(chunk_tokens),
                "start_token": start_token,
                "end_token": end_token,
                "source_document_hash": content.content_hash,
                "privacy_level": content.privacy_level.value
            }
            
            chunk = self._create_chunk(
                content=chunk_text,
                chunk_index=chunk_index,
                start_char=start_char,
                end_char=end_char,
                privacy_level=content.privacy_level,
                metadata=chunk_metadata
            )
            
            if self._validate_chunk_size(chunk):
                chunks.append(chunk)
                chunk_index += 1
            
            # Move to next chunk with overlap
            start_token += self.config.chunk_size - self.config.overlap_size
        
        logger.info(f"Fixed-size chunking created {len(chunks)} chunks")
        return chunks
    
    def _estimate_char_position(self, text: str, token_index: int, all_tokens: List[int]) -> int:
        """Estimate character position from token index."""
        if token_index >= len(all_tokens):
            return len(text)
        
        # Decode tokens up to the index to estimate position
        partial_tokens = all_tokens[:token_index]
        partial_text = self.encoding.decode(partial_tokens)
        return len(partial_text)


class SlidingWindowChunker(Chunker):
    """Sliding window chunking with configurable overlap."""
    
    def chunk_document(self, content: DocumentContent) -> List[DocumentChunk]:
        """Chunk document using sliding window approach."""
        text = content.text
        chunks = []
        chunk_index = 0
        
        # Split into sentences for better boundary detection
        sentences = self._split_into_sentences(text)
        current_chunk = []
        current_tokens = 0
        start_char = 0
        
        for i, sentence in enumerate(sentences):
            sentence_tokens = self._count_tokens(sentence)
            
            # Check if adding this sentence would exceed chunk size
            if current_tokens + sentence_tokens > self.config.chunk_size and current_chunk:
                # Create chunk from current sentences
                chunk_text = " ".join(current_chunk)
                end_char = start_char + len(chunk_text)
                
                chunk_metadata = {
                    "chunking_strategy": "sliding_window",
                    "sentence_count": len(current_chunk),
                    "overlap_tokens": self.config.overlap_size,
                    "source_document_hash": content.content_hash,
                    "privacy_level": content.privacy_level.value
                }
                
                chunk = self._create_chunk(
                    content=chunk_text,
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=end_char,
                    privacy_level=content.privacy_level,
                    metadata=chunk_metadata
                )
                
                if self._validate_chunk_size(chunk):
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Calculate overlap for next chunk
                overlap_sentences = self._calculate_overlap_sentences(current_chunk)
                current_chunk = overlap_sentences
                current_tokens = sum(self._count_tokens(s) for s in overlap_sentences)
                
                # Update start position
                if overlap_sentences:
                    overlap_text = " ".join(overlap_sentences)
                    start_char = end_char - len(overlap_text)
                else:
                    start_char = end_char
            
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
        
        # Handle remaining sentences
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            end_char = start_char + len(chunk_text)
            
            chunk_metadata = {
                "chunking_strategy": "sliding_window",
                "sentence_count": len(current_chunk),
                "is_final_chunk": True,
                "source_document_hash": content.content_hash,
                "privacy_level": content.privacy_level.value
            }
            
            chunk = self._create_chunk(
                content=chunk_text,
                chunk_index=chunk_index,
                start_char=start_char,
                end_char=end_char,
                privacy_level=content.privacy_level,
                metadata=chunk_metadata
            )
            
            if self._validate_chunk_size(chunk):
                chunks.append(chunk)
        
        logger.info(f"Sliding window chunking created {len(chunks)} chunks")
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting (can be improved with nltk or spacy)
        sentence_endings = r'[.!?]+\s+'
        sentences = re.split(sentence_endings, text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _calculate_overlap_sentences(self, sentences: List[str]) -> List[str]:
        """Calculate overlap sentences based on token count."""
        overlap_tokens = 0
        overlap_sentences = []
        
        # Take sentences from the end until we reach overlap size
        for sentence in reversed(sentences):
            sentence_tokens = self._count_tokens(sentence)
            if overlap_tokens + sentence_tokens <= self.config.overlap_size:
                overlap_sentences.insert(0, sentence)
                overlap_tokens += sentence_tokens
            else:
                break
        
        return overlap_sentences


class SemanticChunker(Chunker):
    """Semantic chunking based on sentence similarity."""
    
    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        self.sentence_model = None
        self._load_sentence_model()
    
    def _load_sentence_model(self):
        """Load sentence transformer model for semantic similarity."""
        try:
            # Use a lightweight model for embeddings
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"Failed to load sentence transformer: {e}")
            self.sentence_model = None
    
    def chunk_document(self, content: DocumentContent) -> List[DocumentChunk]:
        """Chunk document based on semantic similarity."""
        if not self.sentence_model:
            logger.warning("Semantic model not available, falling back to sliding window")
            fallback_chunker = SlidingWindowChunker(self.config)
            return fallback_chunker.chunk_document(content)
        
        text = content.text
        sentences = self._split_into_sentences(text)
        
        if len(sentences) < self.config.min_sentences_per_chunk:
            # Document too short for semantic chunking
            chunk_metadata = {
                "chunking_strategy": "semantic_single_chunk",
                "sentence_count": len(sentences),
                "source_document_hash": content.content_hash,
                "privacy_level": content.privacy_level.value
            }
            
            chunk = self._create_chunk(
                content=text,
                chunk_index=0,
                start_char=0,
                end_char=len(text),
                privacy_level=content.privacy_level,
                metadata=chunk_metadata
            )
            return [chunk]
        
        # Generate sentence embeddings
        try:
            sentence_embeddings = self.sentence_model.encode(sentences)
        except Exception as e:
            logger.error(f"Failed to generate sentence embeddings: {e}")
            fallback_chunker = SlidingWindowChunker(self.config)
            return fallback_chunker.chunk_document(content)
        
        # Find semantic boundaries
        chunks = self._create_semantic_chunks(
            sentences, sentence_embeddings, content
        )
        
        logger.info(f"Semantic chunking created {len(chunks)} chunks")
        return chunks
    
    def _create_semantic_chunks(
        self,
        sentences: List[str],
        embeddings: np.ndarray,
        content: DocumentContent
    ) -> List[DocumentChunk]:
        """Create chunks based on semantic similarity."""
        chunks = []
        current_chunk_sentences = []
        current_start_idx = 0
        chunk_index = 0
        
        for i in range(len(sentences)):
            current_chunk_sentences.append(sentences[i])
            
            # Check if we should end the current chunk
            should_end_chunk = (
                len(current_chunk_sentences) >= self.config.max_sentences_per_chunk
                or self._should_break_on_similarity(
                    embeddings, current_start_idx, i, len(sentences)
                )
                or self._chunk_exceeds_token_limit(current_chunk_sentences)
            )
            
            if should_end_chunk and len(current_chunk_sentences) >= self.config.min_sentences_per_chunk:
                # Create chunk
                chunk_text = " ".join(current_chunk_sentences)
                start_char = self._calculate_char_position(sentences, current_start_idx)
                end_char = start_char + len(chunk_text)
                
                chunk_metadata = {
                    "chunking_strategy": "semantic",
                    "sentence_count": len(current_chunk_sentences),
                    "start_sentence_idx": current_start_idx,
                    "end_sentence_idx": i,
                    "avg_similarity": self._calculate_avg_similarity(
                        embeddings[current_start_idx:i+1]
                    ),
                    "source_document_hash": content.content_hash,
                    "privacy_level": content.privacy_level.value
                }
                
                chunk = self._create_chunk(
                    content=chunk_text,
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=end_char,
                    privacy_level=content.privacy_level,
                    metadata=chunk_metadata
                )
                
                if self._validate_chunk_size(chunk):
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Start new chunk
                current_chunk_sentences = []
                current_start_idx = i + 1
        
        # Handle remaining sentences
        if current_chunk_sentences and len(current_chunk_sentences) >= self.config.min_sentences_per_chunk:
            chunk_text = " ".join(current_chunk_sentences)
            start_char = self._calculate_char_position(sentences, current_start_idx)
            end_char = start_char + len(chunk_text)
            
            chunk_metadata = {
                "chunking_strategy": "semantic",
                "sentence_count": len(current_chunk_sentences),
                "is_final_chunk": True,
                "source_document_hash": content.content_hash,
                "privacy_level": content.privacy_level.value
            }
            
            chunk = self._create_chunk(
                content=chunk_text,
                chunk_index=chunk_index,
                start_char=start_char,
                end_char=end_char,
                privacy_level=content.privacy_level,
                metadata=chunk_metadata
            )
            
            if self._validate_chunk_size(chunk):
                chunks.append(chunk)
        
        return chunks
    
    def _should_break_on_similarity(
        self,
        embeddings: np.ndarray,
        start_idx: int,
        current_idx: int,
        total_sentences: int
    ) -> bool:
        """Determine if chunk should be broken based on similarity."""
        if current_idx == total_sentences - 1:
            return True
        
        if current_idx - start_idx < self.config.min_sentences_per_chunk:
            return False
        
        # Calculate similarity between current and next sentence
        if current_idx + 1 < len(embeddings):
            current_embedding = embeddings[current_idx].reshape(1, -1)
            next_embedding = embeddings[current_idx + 1].reshape(1, -1)
            similarity = cosine_similarity(current_embedding, next_embedding)[0][0]
            
            return similarity < self.config.similarity_threshold
        
        return False
    
    def _chunk_exceeds_token_limit(self, sentences: List[str]) -> bool:
        """Check if current chunk exceeds token limit."""
        chunk_text = " ".join(sentences)
        return self._count_tokens(chunk_text) > self.config.chunk_size
    
    def _calculate_char_position(self, sentences: List[str], sentence_idx: int) -> int:
        """Calculate character position of sentence start."""
        return sum(len(s) + 1 for s in sentences[:sentence_idx])  # +1 for space
    
    def _calculate_avg_similarity(self, embeddings: np.ndarray) -> float:
        """Calculate average similarity within chunk."""
        if len(embeddings) < 2:
            return 1.0
        
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = cosine_similarity(
                embeddings[i].reshape(1, -1),
                embeddings[i + 1].reshape(1, -1)
            )[0][0]
            similarities.append(sim)
        
        return float(np.mean(similarities))
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences (improved version)."""
        # More sophisticated sentence splitting
        sentence_endings = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\!|\?)\s+'
        sentences = re.split(sentence_endings, text)
        return [s.strip() for s in sentences if s.strip()]


class ParagraphChunker(Chunker):
    """Paragraph-based chunking with token limit enforcement."""
    
    def chunk_document(self, content: DocumentContent) -> List[DocumentChunk]:
        """Chunk document by paragraphs."""
        text = content.text
        paragraphs = self._split_into_paragraphs(text)
        chunks = []
        chunk_index = 0
        
        current_chunk_paragraphs = []
        current_tokens = 0
        start_char = 0
        
        for paragraph in paragraphs:
            paragraph_tokens = self._count_tokens(paragraph)
            
            # Check if adding this paragraph would exceed limit
            if current_tokens + paragraph_tokens > self.config.chunk_size and current_chunk_paragraphs:
                # Create chunk from current paragraphs
                chunk_text = "\n\n".join(current_chunk_paragraphs)
                end_char = start_char + len(chunk_text)
                
                chunk_metadata = {
                    "chunking_strategy": "paragraph",
                    "paragraph_count": len(current_chunk_paragraphs),
                    "source_document_hash": content.content_hash,
                    "privacy_level": content.privacy_level.value
                }
                
                chunk = self._create_chunk(
                    content=chunk_text,
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=end_char,
                    privacy_level=content.privacy_level,
                    metadata=chunk_metadata
                )
                
                if self._validate_chunk_size(chunk):
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Start new chunk
                current_chunk_paragraphs = []
                current_tokens = 0
                start_char = end_char + 2  # +2 for "\n\n"
            
            current_chunk_paragraphs.append(paragraph)
            current_tokens += paragraph_tokens
        
        # Handle remaining paragraphs
        if current_chunk_paragraphs:
            chunk_text = "\n\n".join(current_chunk_paragraphs)
            end_char = start_char + len(chunk_text)
            
            chunk_metadata = {
                "chunking_strategy": "paragraph",
                "paragraph_count": len(current_chunk_paragraphs),
                "is_final_chunk": True,
                "source_document_hash": content.content_hash,
                "privacy_level": content.privacy_level.value
            }
            
            chunk = self._create_chunk(
                content=chunk_text,
                chunk_index=chunk_index,
                start_char=start_char,
                end_char=end_char,
                privacy_level=content.privacy_level,
                metadata=chunk_metadata
            )
            
            if self._validate_chunk_size(chunk):
                chunks.append(chunk)
        
        logger.info(f"Paragraph chunking created {len(chunks)} chunks")
        return chunks
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]


class ChunkingPipeline:
    """Main chunking pipeline with strategy selection."""
    
    def __init__(self):
        self.default_config = ChunkingConfig(
            strategy=ChunkingStrategy.HYBRID,
            chunk_size=1000,
            overlap_size=200,
            min_chunk_size=100,
            max_chunk_size=2000
        )
    
    def chunk_document(
        self,
        content: DocumentContent,
        strategy: Optional[ChunkingStrategy] = None,
        config: Optional[ChunkingConfig] = None
    ) -> List[DocumentChunk]:
        """
        Chunk document using specified strategy.
        
        Args:
            content: Document content to chunk
            strategy: Chunking strategy to use
            config: Chunking configuration
            
        Returns:
            List[DocumentChunk]: Document chunks
        """
        if config is None:
            config = self.default_config
        
        if strategy is not None:
            config.strategy = strategy
        
        # Select appropriate chunker
        chunker = self._get_chunker(config)
        
        # Apply chunking
        chunks = chunker.chunk_document(content)
        
        # Post-process chunks if needed
        if config.merge_short_chunks:
            chunks = self._merge_short_chunks(chunks, config)
        
        # Enforce privacy boundaries
        if config.preserve_privacy_boundaries:
            chunks = self._enforce_privacy_boundaries(chunks)
        
        logger.info(f"Chunking completed: {len(chunks)} chunks created using {config.strategy.value}")
        return chunks
    
    def _get_chunker(self, config: ChunkingConfig) -> Chunker:
        """Get appropriate chunker for strategy."""
        if config.strategy == ChunkingStrategy.FIXED_SIZE:
            return FixedSizeChunker(config)
        elif config.strategy == ChunkingStrategy.SLIDING_WINDOW:
            return SlidingWindowChunker(config)
        elif config.strategy == ChunkingStrategy.SEMANTIC:
            return SemanticChunker(config)
        elif config.strategy == ChunkingStrategy.PARAGRAPH:
            return ParagraphChunker(config)
        elif config.strategy == ChunkingStrategy.HYBRID:
            # Use semantic if available, otherwise sliding window
            try:
                return SemanticChunker(config)
            except Exception:
                logger.info("Semantic chunking not available, using sliding window")
                return SlidingWindowChunker(config)
        else:
            raise ValueError(f"Unknown chunking strategy: {config.strategy}")
    
    def _merge_short_chunks(
        self,
        chunks: List[DocumentChunk],
        config: ChunkingConfig
    ) -> List[DocumentChunk]:
        """Merge chunks that are too short."""
        if not chunks:
            return chunks
        
        merged_chunks = []
        current_chunk = None
        
        for chunk in chunks:
            if chunk.token_count < config.min_chunk_size:
                if current_chunk is None:
                    current_chunk = chunk
                else:
                    # Merge with previous chunk
                    merged_content = current_chunk.content + "\n\n" + chunk.content
                    merged_metadata = current_chunk.metadata.copy()
                    merged_metadata.update({
                        "merged_chunk_count": merged_metadata.get("merged_chunk_count", 1) + 1,
                        "merged_with": chunk.chunk_index
                    })
                    
                    current_chunk = DocumentChunk(
                        content=merged_content,
                        chunk_index=current_chunk.chunk_index,
                        start_char=current_chunk.start_char,
                        end_char=chunk.end_char,
                        token_count=current_chunk.token_count + chunk.token_count,
                        privacy_level=current_chunk.privacy_level,
                        metadata=merged_metadata,
                        content_hash=hashlib.sha256(merged_content.encode()).hexdigest()
                    )
            else:
                if current_chunk is not None:
                    merged_chunks.append(current_chunk)
                current_chunk = chunk
        
        if current_chunk is not None:
            merged_chunks.append(current_chunk)
        
        return merged_chunks
    
    def _enforce_privacy_boundaries(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Enforce privacy boundaries on chunks."""
        # For now, this just ensures privacy level is preserved
        # In a more complex system, this could handle cross-document boundaries
        for chunk in chunks:
            if chunk.privacy_level == PrivacyLevel.PRIVATE:
                # Add additional metadata for private chunks
                chunk.metadata["search_restricted"] = True
                chunk.metadata["citation_allowed"] = False
            elif chunk.privacy_level == PrivacyLevel.CITABLE:
                chunk.metadata["search_restricted"] = False
                chunk.metadata["citation_allowed"] = True
            elif chunk.privacy_level == PrivacyLevel.PUBLIC:
                chunk.metadata["search_restricted"] = False
                chunk.metadata["citation_allowed"] = True
        
        return chunks


# Global chunking pipeline
chunking_pipeline = ChunkingPipeline()