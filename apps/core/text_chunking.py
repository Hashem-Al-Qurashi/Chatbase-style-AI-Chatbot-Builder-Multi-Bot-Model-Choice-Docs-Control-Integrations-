"""
Intelligent text chunking strategies for RAG systems.
Implements multiple chunking approaches optimized for context retrieval and LLM processing.
"""

import re
import math
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import structlog

# Import tiktoken for token counting
import tiktoken

from .exceptions import ChunkingError

logger = structlog.get_logger()


class ChunkingStrategy(Enum):
    """Available chunking strategies."""
    RECURSIVE_CHARACTER = "recursive_character"
    SEMANTIC = "semantic"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_AWARE = "token_aware"
    MARKDOWN_AWARE = "markdown_aware"


@dataclass
class TextChunk:
    """A chunk of text with metadata."""
    content: str
    chunk_id: str
    start_index: int
    end_index: int
    token_count: int
    metadata: Dict[str, Any]
    overlap_with_previous: bool = False
    overlap_with_next: bool = False
    quality_score: float = 1.0


@dataclass
class ChunkingConfig:
    """Configuration for text chunking."""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE_CHARACTER
    preserve_structure: bool = True
    min_chunk_size: int = 100
    max_chunk_size: int = 2000
    token_model: str = "cl100k_base"  # GPT-3.5/4 tokenizer
    quality_threshold: float = 0.5
    
    def __post_init__(self):
        """Validate configuration."""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be less than chunk size")
        if self.min_chunk_size <= 0:
            raise ValueError("Minimum chunk size must be positive")
        if self.max_chunk_size < self.min_chunk_size:
            raise ValueError("Maximum chunk size must be >= minimum chunk size")


class TextChunker(ABC):
    """Abstract base class for text chunking strategies."""
    
    def __init__(self, config: ChunkingConfig):
        """
        Initialize chunker with configuration.
        
        Args:
            config: Chunking configuration
        """
        self.config = config
        self.logger = structlog.get_logger().bind(chunker=self.__class__.__name__)
        
        # Initialize tokenizer for token counting
        try:
            self.tokenizer = tiktoken.get_encoding(config.token_model)
        except Exception as e:
            self.logger.warning(
                "Failed to load tokenizer, using character-based estimation",
                error=str(e),
                fallback_model="character_estimation"
            )
            self.tokenizer = None
    
    @abstractmethod
    def chunk_text(self, text: str, document_metadata: Dict[str, Any] = None) -> List[TextChunk]:
        """
        Split text into chunks.
        
        Args:
            text: Text to chunk
            document_metadata: Metadata about the source document
            
        Returns:
            List[TextChunk]: List of text chunks
            
        Raises:
            ChunkingError: If chunking fails
        """
        pass
    
    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            int: Number of tokens
        """
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception:
                pass
        
        # Fallback to character-based estimation (rough approximation)
        return max(1, len(text) // 4)
    
    def _calculate_chunk_quality(self, chunk: str) -> float:
        """
        Calculate quality score for a chunk.
        
        Args:
            chunk: Text chunk to evaluate
            
        Returns:
            float: Quality score between 0.0 and 1.0
        """
        if not chunk.strip():
            return 0.0
        
        # Factors that indicate good chunk quality
        word_count = len(chunk.split())
        char_count = len(chunk)
        
        # Check for complete sentences
        sentence_endings = chunk.count('.') + chunk.count('!') + chunk.count('?')
        sentence_completeness = min(1.0, sentence_endings / max(1, word_count / 20))
        
        # Check for paragraph breaks (good structural boundaries)
        paragraph_breaks = chunk.count('\n\n')
        structure_score = min(1.0, paragraph_breaks / max(1, word_count / 100))
        
        # Penalize very short or very long chunks
        length_score = 1.0
        if word_count < 10:
            length_score = word_count / 10
        elif word_count > 300:
            length_score = max(0.5, 300 / word_count)
        
        # Check for code blocks or tables (lower quality for general text)
        has_code = bool(re.search(r'```|{|}|\|\s*\|', chunk))
        code_penalty = 0.8 if has_code else 1.0
        
        # Combine factors
        quality_score = (
            sentence_completeness * 0.4 +
            structure_score * 0.3 +
            length_score * 0.3
        ) * code_penalty
        
        return max(0.0, min(1.0, quality_score))
    
    def _create_chunk_id(self, index: int, text_hash: str) -> str:
        """
        Create unique chunk ID.
        
        Args:
            index: Chunk index
            text_hash: Hash of the source text
            
        Returns:
            str: Unique chunk ID
        """
        import hashlib
        chunk_data = f"{text_hash}_{index}_{self.__class__.__name__}"
        return hashlib.md5(chunk_data.encode()).hexdigest()[:12]


class RecursiveCharacterTextSplitter(TextChunker):
    """
    Recursive character text splitter.
    
    Splits text using a hierarchy of separators, trying to preserve
    natural language structure while maintaining chunk size limits.
    """
    
    def __init__(self, config: ChunkingConfig):
        """Initialize with separators hierarchy."""
        super().__init__(config)
        
        # Hierarchy of separators (in order of preference)
        self.separators = [
            "\n\n",  # Paragraph breaks
            "\n",    # Line breaks
            ". ",    # Sentence endings
            "! ",    # Exclamation sentences
            "? ",    # Question sentences
            "; ",    # Semicolons
            ", ",    # Commas
            " ",     # Spaces
            "",      # Character-by-character
        ]
    
    def chunk_text(self, text: str, document_metadata: Dict[str, Any] = None) -> List[TextChunk]:
        """
        Split text using recursive character splitting.
        
        Args:
            text: Text to chunk
            document_metadata: Metadata about the source document
            
        Returns:
            List[TextChunk]: List of text chunks
        """
        if not text.strip():
            return []
        
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        
        self.logger.info(
            "Starting recursive character chunking",
            text_length=len(text),
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )
        
        try:
            chunks = self._recursive_split(text, self.separators)
            
            # Create TextChunk objects
            text_chunks = []
            current_start = 0
            
            for i, chunk_text in enumerate(chunks):
                if len(chunk_text.strip()) < self.config.min_chunk_size:
                    continue
                
                chunk_start = text.find(chunk_text, current_start)
                chunk_end = chunk_start + len(chunk_text)
                
                chunk = TextChunk(
                    content=chunk_text.strip(),
                    chunk_id=self._create_chunk_id(i, text_hash),
                    start_index=chunk_start,
                    end_index=chunk_end,
                    token_count=self._count_tokens(chunk_text),
                    metadata={
                        "strategy": "recursive_character",
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "document_metadata": document_metadata or {},
                    },
                    quality_score=self._calculate_chunk_quality(chunk_text)
                )
                
                # Check for overlap with previous chunk
                if i > 0 and text_chunks:
                    prev_chunk = text_chunks[-1]
                    overlap_start = max(chunk_start, prev_chunk.start_index)
                    overlap_end = min(chunk_end, prev_chunk.end_index)
                    if overlap_end > overlap_start:
                        chunk.overlap_with_previous = True
                        prev_chunk.overlap_with_next = True
                
                text_chunks.append(chunk)
                current_start = chunk_end
            
            # Filter out low-quality chunks if threshold is set
            if self.config.quality_threshold > 0:
                text_chunks = [
                    chunk for chunk in text_chunks 
                    if chunk.quality_score >= self.config.quality_threshold
                ]
            
            self.logger.info(
                "Recursive character chunking completed",
                total_chunks=len(text_chunks),
                avg_chunk_size=sum(len(c.content) for c in text_chunks) / len(text_chunks) if text_chunks else 0,
                avg_quality_score=sum(c.quality_score for c in text_chunks) / len(text_chunks) if text_chunks else 0
            )
            
            return text_chunks
            
        except Exception as e:
            self.logger.error(
                "Recursive character chunking failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise ChunkingError(f"Recursive character chunking failed: {str(e)}")
    
    def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
        """Recursively split text using separator hierarchy."""
        if not separators:
            return [text]
        
        separator = separators[0]
        remaining_separators = separators[1:]
        
        if separator == "":
            # Character-by-character split as last resort
            return [text[i:i + self.config.chunk_size] for i in range(0, len(text), self.config.chunk_size)]
        
        splits = text.split(separator)
        
        chunks = []
        current_chunk = ""
        
        for split in splits:
            # Add separator back (except for the last split)
            if current_chunk and separator != " ":
                split = separator + split
            
            if len(current_chunk) + len(split) <= self.config.chunk_size:
                current_chunk += split
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                if len(split) > self.config.chunk_size:
                    # Recursively split oversized pieces
                    sub_chunks = self._recursive_split(split, remaining_separators)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = split
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks


class SemanticChunker(TextChunker):
    """
    Semantic chunker that groups related content together.
    
    Uses simple heuristics to identify semantic boundaries:
    - Paragraph breaks
    - Topic changes (keywords)
    - Headers and sections
    """
    
    def chunk_text(self, text: str, document_metadata: Dict[str, Any] = None) -> List[TextChunk]:
        """
        Split text using semantic boundaries.
        
        Args:
            text: Text to chunk
            document_metadata: Metadata about the source document
            
        Returns:
            List[TextChunk]: List of text chunks
        """
        if not text.strip():
            return []
        
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        
        self.logger.info(
            "Starting semantic chunking",
            text_length=len(text),
            chunk_size=self.config.chunk_size
        )
        
        try:
            # Find semantic boundaries
            paragraphs = self._identify_paragraphs(text)
            sections = self._group_paragraphs_semantically(paragraphs)
            
            # Create chunks from sections
            text_chunks = []
            current_start = 0
            
            for i, section in enumerate(sections):
                if len(section.strip()) < self.config.min_chunk_size:
                    continue
                
                chunk_start = text.find(section, current_start)
                chunk_end = chunk_start + len(section)
                
                chunk = TextChunk(
                    content=section.strip(),
                    chunk_id=self._create_chunk_id(i, text_hash),
                    start_index=chunk_start,
                    end_index=chunk_end,
                    token_count=self._count_tokens(section),
                    metadata={
                        "strategy": "semantic",
                        "chunk_index": i,
                        "total_chunks": len(sections),
                        "document_metadata": document_metadata or {},
                    },
                    quality_score=self._calculate_chunk_quality(section)
                )
                
                text_chunks.append(chunk)
                current_start = chunk_end
            
            self.logger.info(
                "Semantic chunking completed",
                total_chunks=len(text_chunks),
                avg_chunk_size=sum(len(c.content) for c in text_chunks) / len(text_chunks) if text_chunks else 0
            )
            
            return text_chunks
            
        except Exception as e:
            self.logger.error(
                "Semantic chunking failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise ChunkingError(f"Semantic chunking failed: {str(e)}")
    
    def _identify_paragraphs(self, text: str) -> List[str]:
        """Identify paragraphs in text."""
        # Split by double newlines (paragraph breaks)
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _group_paragraphs_semantically(self, paragraphs: List[str]) -> List[str]:
        """Group paragraphs into semantic sections."""
        if not paragraphs:
            return []
        
        sections = []
        current_section = ""
        current_size = 0
        
        for paragraph in paragraphs:
            paragraph_size = len(paragraph)
            
            # Check if adding this paragraph would exceed chunk size
            if current_size + paragraph_size > self.config.chunk_size and current_section:
                sections.append(current_section)
                current_section = paragraph
                current_size = paragraph_size
            else:
                if current_section:
                    current_section += "\n\n" + paragraph
                    current_size += paragraph_size + 2  # +2 for the newlines
                else:
                    current_section = paragraph
                    current_size = paragraph_size
        
        if current_section:
            sections.append(current_section)
        
        return sections


class SlidingWindowChunker(TextChunker):
    """
    Sliding window chunker with configurable overlap.
    
    Creates overlapping chunks to ensure context continuity.
    Useful for ensuring important information isn't lost at chunk boundaries.
    """
    
    def chunk_text(self, text: str, document_metadata: Dict[str, Any] = None) -> List[TextChunk]:
        """
        Split text using sliding window with overlap.
        
        Args:
            text: Text to chunk
            document_metadata: Metadata about the source document
            
        Returns:
            List[TextChunk]: List of text chunks with overlap
        """
        if not text.strip():
            return []
        
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        
        self.logger.info(
            "Starting sliding window chunking",
            text_length=len(text),
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap
        )
        
        try:
            text_chunks = []
            start_index = 0
            chunk_index = 0
            
            while start_index < len(text):
                # Calculate end index for this chunk
                end_index = min(start_index + self.config.chunk_size, len(text))
                
                # Extract chunk text
                chunk_text = text[start_index:end_index]
                
                # Skip if chunk is too small
                if len(chunk_text.strip()) < self.config.min_chunk_size:
                    break
                
                # Try to end at a natural boundary (sentence, paragraph)
                if end_index < len(text):
                    chunk_text = self._adjust_chunk_boundary(chunk_text, text, start_index, end_index)
                    end_index = start_index + len(chunk_text)
                
                chunk = TextChunk(
                    content=chunk_text.strip(),
                    chunk_id=self._create_chunk_id(chunk_index, text_hash),
                    start_index=start_index,
                    end_index=end_index,
                    token_count=self._count_tokens(chunk_text),
                    metadata={
                        "strategy": "sliding_window",
                        "chunk_index": chunk_index,
                        "overlap_size": self.config.chunk_overlap,
                        "document_metadata": document_metadata or {},
                    },
                    overlap_with_previous=chunk_index > 0,
                    overlap_with_next=end_index < len(text),
                    quality_score=self._calculate_chunk_quality(chunk_text)
                )
                
                text_chunks.append(chunk)
                
                # Move start index for next chunk (with overlap)
                step_size = self.config.chunk_size - self.config.chunk_overlap
                start_index += max(1, step_size)
                chunk_index += 1
            
            self.logger.info(
                "Sliding window chunking completed",
                total_chunks=len(text_chunks),
                avg_chunk_size=sum(len(c.content) for c in text_chunks) / len(text_chunks) if text_chunks else 0
            )
            
            return text_chunks
            
        except Exception as e:
            self.logger.error(
                "Sliding window chunking failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise ChunkingError(f"Sliding window chunking failed: {str(e)}")
    
    def _adjust_chunk_boundary(self, chunk_text: str, full_text: str, start_idx: int, end_idx: int) -> str:
        """Adjust chunk boundary to end at natural break points."""
        # Look for sentence endings near the end of the chunk
        boundary_search_length = min(100, len(chunk_text) // 4)
        search_start = max(0, len(chunk_text) - boundary_search_length)
        
        # Find the last sentence ending
        sentence_endings = []
        for pattern in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
            pos = chunk_text.rfind(pattern, search_start)
            if pos != -1:
                sentence_endings.append(pos + len(pattern))
        
        if sentence_endings:
            # Use the latest sentence ending
            best_ending = max(sentence_endings)
            return chunk_text[:best_ending]
        
        # If no sentence ending, look for paragraph breaks
        para_break = chunk_text.rfind('\n\n', search_start)
        if para_break != -1:
            return chunk_text[:para_break + 2]
        
        # If no natural boundary, return as-is
        return chunk_text


class TokenAwareChunker(TextChunker):
    """
    Token-aware chunker that respects LLM token limits.
    
    Ensures chunks fit within specified token limits while
    maintaining readability and context.
    """
    
    def __init__(self, config: ChunkingConfig):
        """Initialize with token-based configuration."""
        super().__init__(config)
        self.max_tokens = config.chunk_size  # Interpret chunk_size as token count
        self.overlap_tokens = config.chunk_overlap
    
    def chunk_text(self, text: str, document_metadata: Dict[str, Any] = None) -> List[TextChunk]:
        """
        Split text based on token limits.
        
        Args:
            text: Text to chunk
            document_metadata: Metadata about the source document
            
        Returns:
            List[TextChunk]: List of token-aware text chunks
        """
        if not text.strip():
            return []
        
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        
        self.logger.info(
            "Starting token-aware chunking",
            text_length=len(text),
            max_tokens=self.max_tokens,
            overlap_tokens=self.overlap_tokens
        )
        
        try:
            # Split text into sentences for better boundary detection
            sentences = self._split_into_sentences(text)
            
            text_chunks = []
            current_chunk = ""
            current_tokens = 0
            chunk_index = 0
            sentence_start_idx = 0
            
            for sentence in sentences:
                sentence_tokens = self._count_tokens(sentence)
                
                # If adding this sentence would exceed token limit
                if current_tokens + sentence_tokens > self.max_tokens and current_chunk:
                    # Create chunk from current content
                    chunk_start = sentence_start_idx - len(current_chunk)
                    chunk_end = sentence_start_idx
                    
                    chunk = TextChunk(
                        content=current_chunk.strip(),
                        chunk_id=self._create_chunk_id(chunk_index, text_hash),
                        start_index=chunk_start,
                        end_index=chunk_end,
                        token_count=current_tokens,
                        metadata={
                            "strategy": "token_aware",
                            "chunk_index": chunk_index,
                            "max_tokens": self.max_tokens,
                            "document_metadata": document_metadata or {},
                        },
                        quality_score=self._calculate_chunk_quality(current_chunk)
                    )
                    
                    text_chunks.append(chunk)
                    chunk_index += 1
                    
                    # Start new chunk with overlap
                    if self.overlap_tokens > 0:
                        overlap_text = self._get_overlap_text(current_chunk, self.overlap_tokens)
                        current_chunk = overlap_text + " " + sentence
                        current_tokens = self._count_tokens(current_chunk)
                    else:
                        current_chunk = sentence
                        current_tokens = sentence_tokens
                else:
                    # Add sentence to current chunk
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence
                    current_tokens += sentence_tokens
                
                sentence_start_idx += len(sentence) + 1  # +1 for space
            
            # Add final chunk if there's remaining content
            if current_chunk.strip():
                chunk_start = sentence_start_idx - len(current_chunk)
                chunk_end = sentence_start_idx
                
                chunk = TextChunk(
                    content=current_chunk.strip(),
                    chunk_id=self._create_chunk_id(chunk_index, text_hash),
                    start_index=chunk_start,
                    end_index=chunk_end,
                    token_count=current_tokens,
                    metadata={
                        "strategy": "token_aware",
                        "chunk_index": chunk_index,
                        "max_tokens": self.max_tokens,
                        "document_metadata": document_metadata or {},
                    },
                    quality_score=self._calculate_chunk_quality(current_chunk)
                )
                
                text_chunks.append(chunk)
            
            self.logger.info(
                "Token-aware chunking completed",
                total_chunks=len(text_chunks),
                avg_tokens=sum(c.token_count for c in text_chunks) / len(text_chunks) if text_chunks else 0
            )
            
            return text_chunks
            
        except Exception as e:
            self.logger.error(
                "Token-aware chunking failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise ChunkingError(f"Token-aware chunking failed: {str(e)}")
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting (can be improved with spaCy or NLTK)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_text(self, text: str, max_tokens: int) -> str:
        """Get overlap text from the end of a chunk."""
        if not text or max_tokens <= 0:
            return ""
        
        # Split into words and take from the end
        words = text.split()
        overlap_text = ""
        current_tokens = 0
        
        for word in reversed(words):
            word_tokens = self._count_tokens(word)
            if current_tokens + word_tokens > max_tokens:
                break
            overlap_text = word + " " + overlap_text
            current_tokens += word_tokens
        
        return overlap_text.strip()


class ChunkerFactory:
    """Factory for creating text chunkers based on strategy."""
    
    @staticmethod
    def create_chunker(config: ChunkingConfig) -> TextChunker:
        """
        Create appropriate chunker for the given strategy.
        
        Args:
            config: Chunking configuration
            
        Returns:
            TextChunker: Chunker instance
            
        Raises:
            ValueError: If strategy is not supported
        """
        chunkers = {
            ChunkingStrategy.RECURSIVE_CHARACTER: RecursiveCharacterTextSplitter,
            ChunkingStrategy.SEMANTIC: SemanticChunker,
            ChunkingStrategy.SLIDING_WINDOW: SlidingWindowChunker,
            ChunkingStrategy.TOKEN_AWARE: TokenAwareChunker,
        }
        
        if config.strategy not in chunkers:
            raise ValueError(f"Unsupported chunking strategy: {config.strategy}")
        
        return chunkers[config.strategy](config)
    
    @staticmethod
    def get_available_strategies() -> List[ChunkingStrategy]:
        """Get list of available chunking strategies."""
        return list(ChunkingStrategy)


def chunk_text(
    text: str,
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE_CHARACTER,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    **kwargs
) -> List[TextChunk]:
    """
    Convenience function to chunk text.
    
    Args:
        text: Text to chunk
        strategy: Chunking strategy to use
        chunk_size: Target chunk size
        chunk_overlap: Overlap between chunks
        **kwargs: Additional configuration options
        
    Returns:
        List[TextChunk]: List of text chunks
    """
    config = ChunkingConfig(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        strategy=strategy,
        **kwargs
    )
    
    chunker = ChunkerFactory.create_chunker(config)
    return chunker.chunk_text(text)