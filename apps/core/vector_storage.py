"""
Vector storage service with Pinecone and development fallback support.
Implements repository pattern with multiple storage backends.
"""

import hashlib
import json
import time
import asyncio
from typing import Dict, List, Optional, Tuple, Any, Protocol
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
import structlog

from django.core.cache import cache
from django.conf import settings as django_settings
from django.db import models, connection
from asgiref.sync import sync_to_async
from pydantic import BaseModel, Field

from chatbot_saas.config import get_settings
from .exceptions import VectorStorageError
from .circuit_breaker import CircuitBreaker

settings = get_settings()
logger = structlog.get_logger()


@dataclass
class VectorSearchResult:
    """Result of vector similarity search."""
    id: str
    score: float
    metadata: Dict[str, Any]
    content: Optional[str] = None
    embedding: Optional[List[float]] = None


@dataclass  
class VectorSearchQuery:
    """Vector search query parameters."""
    vector: List[float]
    top_k: int = 10
    namespace: Optional[str] = None
    filter: Optional[Dict[str, Any]] = None
    include_metadata: bool = True
    include_values: bool = False


class VectorStorageConfig(BaseModel):
    """Vector storage configuration."""
    # Storage selection
    backend: str = Field("auto", description="Backend: pinecone, pgvector, or auto")
    
    # Pinecone settings
    pinecone_api_key: str = Field("", env="PINECONE_API_KEY")
    pinecone_environment: str = Field("", env="PINECONE_ENVIRONMENT") 
    pinecone_index_name: str = Field("chatbot-embeddings", env="PINECONE_INDEX_NAME")
    
    # pgvector settings
    vector_dimension: int = Field(1536, description="Vector dimension for embeddings")
    
    # General settings
    batch_size: int = Field(100, description="Batch size for bulk operations")
    timeout_seconds: int = Field(30, description="Operation timeout")
    enable_caching: bool = Field(True, description="Enable result caching")
    cache_ttl_hours: int = Field(1, description="Cache TTL in hours")


class VectorStorageBackend(ABC):
    """Abstract base class for vector storage backends."""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the storage backend."""
        pass
    
    @abstractmethod
    async def upsert_vectors(
        self, 
        vectors: List[Tuple[str, List[float], Dict[str, Any]]], 
        namespace: Optional[str] = None
    ) -> bool:
        """Upsert vectors with metadata."""
        pass
    
    @abstractmethod
    async def search_vectors(self, query: VectorSearchQuery) -> List[VectorSearchResult]:
        """Search for similar vectors."""
        pass
    
    @abstractmethod
    async def delete_vectors(self, ids: List[str], namespace: Optional[str] = None) -> bool:
        """Delete vectors by IDs."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        pass


class PineconeBackend(VectorStorageBackend):
    """Pinecone vector storage backend."""
    
    def __init__(self, config: VectorStorageConfig):
        self.config = config
        self.logger = structlog.get_logger().bind(component="PineconeBackend")
        self.client = None
        self.index = None
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60,
            expected_exception=Exception
        )
    
    async def initialize(self) -> bool:
        """Initialize Pinecone client and index."""
        try:
            import pinecone
            
            # Initialize Pinecone
            pinecone.init(
                api_key=self.config.pinecone_api_key,
                environment=self.config.pinecone_environment
            )
            
            # Connect to index
            if self.config.pinecone_index_name not in pinecone.list_indexes():
                self.logger.error(
                    "Pinecone index not found",
                    index_name=self.config.pinecone_index_name,
                    available_indexes=pinecone.list_indexes()
                )
                return False
            
            self.index = pinecone.Index(self.config.pinecone_index_name)
            
            self.logger.info(
                "Pinecone backend initialized",
                index_name=self.config.pinecone_index_name,
                environment=self.config.pinecone_environment
            )
            return True
            
        except ImportError:
            self.logger.error("Pinecone library not available")
            return False
        except Exception as e:
            self.logger.error(
                "Failed to initialize Pinecone backend",
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def upsert_vectors(
        self, 
        vectors: List[Tuple[str, List[float], Dict[str, Any]]], 
        namespace: Optional[str] = None
    ) -> bool:
        """Upsert vectors to Pinecone."""
        try:
            # Prepare upsert data
            upsert_data = [
                (vector_id, embedding, metadata)
                for vector_id, embedding, metadata in vectors
            ]
            
            # Perform upsert with circuit breaker
            await self.circuit_breaker.call(
                self._perform_upsert,
                upsert_data,
                namespace
            )
            
            self.logger.info(
                "Vectors upserted to Pinecone",
                count=len(vectors),
                namespace=namespace
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to upsert vectors to Pinecone",
                error=str(e),
                error_type=type(e).__name__,
                count=len(vectors)
            )
            return False
    
    def _perform_upsert(self, upsert_data: List, namespace: Optional[str] = None):
        """Perform the actual upsert operation."""
        return self.index.upsert(
            vectors=upsert_data,
            namespace=namespace
        )
    
    async def search_vectors(self, query: VectorSearchQuery) -> List[VectorSearchResult]:
        """Search vectors in Pinecone."""
        try:
            # Perform search with circuit breaker
            response = await self.circuit_breaker.call(
                self._perform_search,
                query
            )
            
            # Convert response to VectorSearchResult objects
            results = []
            for match in response.matches:
                result = VectorSearchResult(
                    id=match.id,
                    score=match.score,
                    metadata=match.metadata or {},
                    content=match.metadata.get('content') if match.metadata else None,
                    embedding=match.values if query.include_values else None
                )
                results.append(result)
            
            self.logger.info(
                "Vector search completed",
                top_k=query.top_k,
                results_count=len(results),
                namespace=query.namespace
            )
            return results
            
        except Exception as e:
            self.logger.error(
                "Failed to search vectors in Pinecone",
                error=str(e),
                error_type=type(e).__name__,
                top_k=query.top_k
            )
            return []
    
    def _perform_search(self, query: VectorSearchQuery):
        """Perform the actual search operation."""
        return self.index.query(
            vector=query.vector,
            top_k=query.top_k,
            namespace=query.namespace,
            filter=query.filter,
            include_metadata=query.include_metadata,
            include_values=query.include_values
        )
    
    async def delete_vectors(self, ids: List[str], namespace: Optional[str] = None) -> bool:
        """Delete vectors from Pinecone."""
        try:
            await self.circuit_breaker.call(
                self._perform_delete,
                ids,
                namespace
            )
            
            self.logger.info(
                "Vectors deleted from Pinecone",
                count=len(ids),
                namespace=namespace
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to delete vectors from Pinecone",
                error=str(e),
                error_type=type(e).__name__,
                count=len(ids)
            )
            return False
    
    def _perform_delete(self, ids: List[str], namespace: Optional[str] = None):
        """Perform the actual delete operation."""
        return self.index.delete(
            ids=ids,
            namespace=namespace
        )
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Pinecone index statistics."""
        try:
            stats = self.index.describe_index_stats()
            return {
                "backend": "pinecone",
                "total_vectors": stats.total_vector_count,
                "index_fullness": stats.index_fullness,
                "dimension": stats.dimension,
                "namespaces": stats.namespaces
            }
        except Exception as e:
            self.logger.error("Failed to get Pinecone stats", error=str(e))
            return {"backend": "pinecone", "error": str(e)}


class PgVectorBackend(VectorStorageBackend):
    """PostgreSQL with pgvector extension backend for development."""
    
    def __init__(self, config: VectorStorageConfig):
        self.config = config
        self.logger = structlog.get_logger().bind(component="PgVectorBackend")
        self.table_name = "vector_embeddings"
        self.is_sqlite = False
    
    async def initialize(self) -> bool:
        """Initialize pgvector tables and extension (with SQLite fallback)."""
        return await sync_to_async(self._initialize_sync)()
    
    def _initialize_sync(self) -> bool:
        """Synchronous database initialization."""
        try:
            with connection.cursor() as cursor:
                # Check if we're using SQLite
                if 'sqlite' in django_settings.DATABASES['default']['ENGINE']:
                    self.is_sqlite = True
                    self.logger.info("Detected SQLite database, using fallback implementation")
                    
                    # Create embeddings table for SQLite
                    cursor.execute(f"""
                        CREATE TABLE IF NOT EXISTS {self.table_name} (
                            id TEXT PRIMARY KEY,
                            embedding TEXT,
                            metadata TEXT,
                            namespace TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Create indexes for SQLite
                    cursor.execute(f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_namespace_idx 
                        ON {self.table_name} (namespace);
                    """)
                    
                else:
                    # PostgreSQL with pgvector
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    
                    # Create embeddings table with vector type
                    cursor.execute(f"""
                        CREATE TABLE IF NOT EXISTS {self.table_name} (
                            id VARCHAR(255) PRIMARY KEY,
                            embedding vector({self.config.vector_dimension}),
                            metadata JSONB,
                            namespace VARCHAR(255),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Create vector indexes for PostgreSQL
                    cursor.execute(f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx 
                        ON {self.table_name} USING ivfflat (embedding vector_cosine_ops);
                    """)
                    
                    cursor.execute(f"""
                        CREATE INDEX IF NOT EXISTS {self.table_name}_namespace_idx 
                        ON {self.table_name} (namespace);
                    """)
            
            backend_type = "SQLite (fallback)" if self.is_sqlite else "PostgreSQL+pgvector"
            self.logger.info(
                "Vector backend initialized",
                backend_type=backend_type,
                table_name=self.table_name,
                dimension=self.config.vector_dimension
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize vector backend",
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def upsert_vectors(
        self, 
        vectors: List[Tuple[str, List[float], Dict[str, Any]]], 
        namespace: Optional[str] = None
    ) -> bool:
        """Upsert vectors to database (SQLite or PostgreSQL)."""
        return await sync_to_async(self._upsert_vectors_sync)(vectors, namespace)
    
    def _upsert_vectors_sync(
        self, 
        vectors: List[Tuple[str, List[float], Dict[str, Any]]], 
        namespace: Optional[str] = None
    ) -> bool:
        """Synchronous vector upsert operation with comprehensive input validation."""
        try:
            # CRITICAL SECURITY: Validate namespace input
            if namespace is not None:
                if not isinstance(namespace, str):
                    raise VectorStorageError(f"Invalid namespace type: must be string or None, got {type(namespace)}")
                if len(namespace.strip()) == 0:
                    namespace = None  # Treat empty string as None for consistency
                else:
                    namespace = namespace.strip()
            
            # CRITICAL SECURITY: Validate all inputs before processing
            validated_vectors = []
            for vector_id, embedding, metadata in vectors:
                # Validate vector ID
                if not vector_id or not isinstance(vector_id, str) or len(vector_id.strip()) == 0:
                    raise VectorStorageError(f"Invalid vector ID: must be non-empty string")
                
                # Validate embedding dimension
                if not isinstance(embedding, list):
                    raise VectorStorageError(f"Invalid embedding: must be a list, got {type(embedding)}")
                    
                if len(embedding) != self.config.vector_dimension:
                    raise VectorStorageError(
                        f"Invalid embedding dimension: expected {self.config.vector_dimension}, got {len(embedding)}"
                    )
                
                # Validate numeric values and check for dangerous values
                validated_embedding = []
                for i, value in enumerate(embedding):
                    if not isinstance(value, (int, float)):
                        raise VectorStorageError(f"Invalid embedding value at index {i}: must be numeric, got {type(value)}")
                    
                    # Check for NaN and Infinity
                    if not isinstance(value, int) and (
                        value != value or  # NaN check
                        value == float('inf') or value == float('-inf')
                    ):
                        raise VectorStorageError(f"Invalid embedding value at index {i}: NaN or Infinity not allowed")
                    
                    validated_embedding.append(float(value))
                
                # Validate metadata
                if metadata is not None:
                    if not isinstance(metadata, dict):
                        raise VectorStorageError(f"Invalid metadata: must be dict, got {type(metadata)}")
                    
                    # Limit metadata size to prevent abuse
                    metadata_str = json.dumps(metadata)
                    if len(metadata_str) > 100000:  # 100KB limit
                        raise VectorStorageError(f"Metadata too large: {len(metadata_str)} bytes (max 100KB)")
                
                validated_vectors.append((vector_id.strip(), validated_embedding, metadata))
            
            # Process validated vectors
            with connection.cursor() as cursor:
                for vector_id, embedding, metadata in validated_vectors:
                    if self.is_sqlite:
                        # SQLite version - use direct sqlite3 to avoid Django debug issues
                        import sqlite3
                        import os
                        from django.conf import settings
                        
                        # Get database path from Django settings
                        db_path = settings.DATABASES['default']['NAME']
                        
                        # Use direct sqlite3 connection to avoid Django's debug formatting
                        sqlite_conn = sqlite3.connect(db_path)
                        sqlite_cursor = sqlite_conn.cursor()
                        
                        try:
                            sqlite_cursor.execute(
                                f"INSERT OR REPLACE INTO {self.table_name} (id, embedding, metadata, namespace, created_at, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                                [
                                    vector_id,
                                    json.dumps(embedding),
                                    json.dumps(metadata),
                                    namespace
                                ]
                            )
                            sqlite_conn.commit()
                        finally:
                            sqlite_cursor.close()
                            sqlite_conn.close()
                    else:
                        # PostgreSQL version with pgvector
                        sql = f"""
                            INSERT INTO {self.table_name} (id, embedding, metadata, namespace)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE SET
                                embedding = EXCLUDED.embedding,
                                metadata = EXCLUDED.metadata,
                                namespace = EXCLUDED.namespace,
                                updated_at = CURRENT_TIMESTAMP;
                        """
                        cursor.execute(sql, [
                            vector_id,
                            embedding,
                            json.dumps(metadata),
                            namespace
                        ])
            
            backend_type = "SQLite" if self.is_sqlite else "PgVector"
            self.logger.info(
                f"Vectors upserted to {backend_type}",
                count=len(vectors),
                namespace=namespace
            )
            return True
            
        except VectorStorageError:
            # Re-raise validation errors to the service layer
            raise
        except Exception as e:
            backend_type = "SQLite" if self.is_sqlite else "PgVector"
            self.logger.error(
                f"Failed to upsert vectors to {backend_type}",
                error=str(e),
                error_type=type(e).__name__,
                count=len(vectors)
            )
            
            # Add more detailed debugging for SQLite
            if self.is_sqlite:
                import traceback
                self.logger.error(
                    "SQLite upsert detailed error",
                    traceback=traceback.format_exc(),
                    table_name=self.table_name
                )
            
            return False
    
    async def search_vectors(self, query: VectorSearchQuery) -> List[VectorSearchResult]:
        """Search vectors using cosine similarity with privacy filtering (PostgreSQL pgvector or SQLite fallback)."""
        try:
            if self.is_sqlite:
                return await sync_to_async(self._search_vectors_sqlite_sync)(query)
            else:
                return await sync_to_async(self._search_vectors_postgresql_sync)(query)
                
        except Exception as e:
            backend_type = "SQLite" if self.is_sqlite else "PgVector"
            self.logger.error(
                f"Failed to search vectors in {backend_type}",
                error=str(e),
                error_type=type(e).__name__,
                top_k=query.top_k
            )
            return []
    
    def _search_vectors_postgresql_sync(self, query: VectorSearchQuery) -> List[VectorSearchResult]:
        """Search vectors in PostgreSQL using pgvector cosine similarity with privacy filtering."""
        with connection.cursor() as cursor:
            # Build WHERE clause for namespace and privacy filters
            where_conditions = []
            params = [query.vector]
            
            if query.namespace:
                where_conditions.append("namespace = %s")
                params.append(query.namespace)
            
            # CRITICAL: Apply privacy filtering - only return citable content unless explicitly requested
            if query.filter and query.filter.get('include_non_citable'):
                # Allow non-citable content (for internal RAG context)
                pass
            else:
                # Default: only citable content
                where_conditions.append("(metadata->>'is_citable' = 'true' OR metadata->>'is_citable' IS NULL)")
            
            # Add any additional metadata filters
            if query.filter:
                for key, value in query.filter.items():
                    if key != 'include_non_citable':  # Skip our special privacy flag
                        where_conditions.append(f"metadata->>%s = %s")
                        params.extend([key, str(value)])
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Add vector parameter for similarity calculation and ordering
            params.append(query.vector)
            params.append(query.top_k)
            
            # Execute similarity search
            sql = f"""
                SELECT id, metadata, 1 - (embedding <=> %s) as similarity
                FROM {self.table_name}
                {where_clause}
                ORDER BY embedding <=> %s
                LIMIT %s;
            """
            cursor.execute(sql, params)
            
            # Convert results
            results = []
            for row in cursor.fetchall():
                vector_id, metadata_json, similarity = row
                metadata = json.loads(metadata_json) if metadata_json else {}
                
                result = VectorSearchResult(
                    id=vector_id,
                    score=similarity,
                    metadata=metadata,
                    content=metadata.get('content'),
                    embedding=None
                )
                results.append(result)
            
            self.logger.info(
                "PgVector search completed with privacy filtering",
                top_k=query.top_k,
                results_count=len(results),
                namespace=query.namespace,
                privacy_filtered=not (query.filter and query.filter.get('include_non_citable', False))
            )
            return results
    
    def _search_vectors_sqlite_sync(self, query: VectorSearchQuery) -> List[VectorSearchResult]:
        """Search vectors in SQLite using Python-based cosine similarity with privacy filtering."""
        import math
        import sqlite3
        from django.conf import settings
        
        # SECURITY: Validate namespace input to prevent injection
        if query.namespace is not None and not isinstance(query.namespace, str):
            raise VectorStorageError(f"Invalid namespace type: must be string or None, got {type(query.namespace)}")
        
        # Use direct sqlite3 to avoid Django debug issues
        db_path = settings.DATABASES['default']['NAME']
        sqlite_conn = sqlite3.connect(db_path)
        sqlite_cursor = sqlite_conn.cursor()
        
        try:
            # Build WHERE clause for namespace filter with proper null handling
            where_conditions = []
            params = []
            
            if query.namespace is not None:
                where_conditions.append("namespace = ?")
                params.append(query.namespace)
            else:
                # SECURITY: Handle null namespace explicitly to prevent unintended data access
                where_conditions.append("(namespace IS NULL OR namespace = '')")
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Get all vectors for similarity calculation
            sql = f"SELECT id, embedding, metadata FROM {self.table_name} {where_clause}"
            sqlite_cursor.execute(sql, params)
            rows = sqlite_cursor.fetchall()
        finally:
            sqlite_cursor.close()
            sqlite_conn.close()
            
        # Calculate cosine similarity in Python with privacy filtering
        results = []
        for row in rows:
            vector_id, embedding_json, metadata_json = row
            
            # CRITICAL FIX: Ensure stored embedding is parsed correctly as float list
            try:
                stored_embedding = json.loads(embedding_json)
                # Validate that it's a list of numbers
                if not isinstance(stored_embedding, list):
                    self.logger.warning(f"Invalid stored embedding format for ID {vector_id}: not a list")
                    continue
                
                # Convert to float list to ensure compatibility
                stored_embedding = [float(x) for x in stored_embedding]
                
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                self.logger.warning(f"Failed to parse embedding for ID {vector_id}: {e}")
                continue
                
            metadata = json.loads(metadata_json) if metadata_json else {}
            
            # CRITICAL: Apply privacy filtering - only return citable content unless explicitly requested
            is_citable = metadata.get('is_citable', True)  # Default to citable if not specified
            include_non_citable = query.filter and query.filter.get('include_non_citable', False)
            
            if not is_citable and not include_non_citable:
                # Skip non-citable content unless explicitly requested
                continue
            
            # Apply additional metadata filters
            if query.filter:
                filter_passed = True
                for key, value in query.filter.items():
                    if key != 'include_non_citable':  # Skip our special privacy flag
                        if metadata.get(key) != value:
                            filter_passed = False
                            break
                if not filter_passed:
                    continue
            
            # Calculate cosine similarity with error handling
            try:
                similarity = self._cosine_similarity(query.vector, stored_embedding)
                
                # Validate similarity score
                if not isinstance(similarity, (int, float)) or similarity != similarity:  # NaN check
                    self.logger.warning(f"Invalid similarity score for ID {vector_id}: {similarity}")
                    similarity = 0.0
                    
            except Exception as e:
                self.logger.warning(f"Failed to calculate similarity for ID {vector_id}: {e}")
                similarity = 0.0
            
            result = VectorSearchResult(
                id=vector_id,
                score=similarity,
                metadata=metadata,
                content=metadata.get('content'),
                embedding=None
            )
            results.append(result)
        
        # Sort by similarity and limit
        results.sort(key=lambda x: x.score, reverse=True)
        results = results[:query.top_k]
        
        self.logger.info(
            "SQLite search completed with privacy filtering",
            top_k=query.top_k,
            results_count=len(results),
            namespace=query.namespace,
            privacy_filtered=not (query.filter and query.filter.get('include_non_citable', False))
        )
        return results
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors with robust error handling.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            float: Cosine similarity score between -1 and 1
        """
        import math
        
        # Input validation
        if not isinstance(vec1, list) or not isinstance(vec2, list):
            raise VectorStorageError(f"Both inputs must be lists, got {type(vec1)} and {type(vec2)}")
        
        if len(vec1) != len(vec2):
            raise VectorStorageError(f"Vector dimensions must match: {len(vec1)} != {len(vec2)}")
        
        if len(vec1) == 0:
            return 0.0
        
        # Convert to float and validate
        try:
            vec1_float = [float(x) for x in vec1]
            vec2_float = [float(x) for x in vec2]
        except (ValueError, TypeError) as e:
            raise VectorStorageError(f"Non-numeric values in vectors: {e}")
        
        # Calculate dot product with overflow protection
        try:
            dot_product = sum(a * b for a, b in zip(vec1_float, vec2_float))
            
            # Check for overflow/underflow
            if not math.isfinite(dot_product):
                self.logger.warning("Dot product overflow detected, returning 0.0")
                return 0.0
                
        except OverflowError:
            self.logger.warning("Dot product calculation overflow, returning 0.0")
            return 0.0
        
        # Calculate magnitudes with overflow protection
        try:
            magnitude1_squared = sum(a * a for a in vec1_float)
            magnitude2_squared = sum(a * a for a in vec2_float)
            
            # Check for zero magnitudes
            if magnitude1_squared == 0.0 or magnitude2_squared == 0.0:
                return 0.0
            
            magnitude1 = math.sqrt(magnitude1_squared)
            magnitude2 = math.sqrt(magnitude2_squared)
            
            # Additional check for very small magnitudes
            if magnitude1 < 1e-12 or magnitude2 < 1e-12:
                return 0.0
            
        except (OverflowError, ValueError):
            self.logger.warning("Magnitude calculation error, returning 0.0")
            return 0.0
        
        # Calculate final similarity
        try:
            similarity = dot_product / (magnitude1 * magnitude2)
            
            # Validate result is within expected range
            if not math.isfinite(similarity):
                return 0.0
            
            # Clamp to valid range due to floating point precision
            similarity = max(-1.0, min(1.0, similarity))
            
            return similarity
            
        except (ZeroDivisionError, OverflowError):
            return 0.0
    
    async def delete_vectors(self, ids: List[str], namespace: Optional[str] = None) -> bool:
        """Delete vectors from database (SQLite or PostgreSQL)."""
        return await sync_to_async(self._delete_vectors_sync)(ids, namespace)
    
    def _delete_vectors_sync(self, ids: List[str], namespace: Optional[str] = None) -> bool:
        """Synchronous vector deletion operation."""
        try:
            with connection.cursor() as cursor:
                if self.is_sqlite:
                    # SQLite version
                    if namespace:
                        placeholders = ','.join('?' * len(ids))
                        sql = "DELETE FROM " + self.table_name + " WHERE id IN (" + placeholders + ") AND namespace = ?"
                        cursor.execute(sql, ids + [namespace])
                    else:
                        placeholders = ','.join('?' * len(ids))
                        sql = "DELETE FROM " + self.table_name + " WHERE id IN (" + placeholders + ")"
                        cursor.execute(sql, ids)
                else:
                    # PostgreSQL version
                    if namespace:
                        sql = f"DELETE FROM {self.table_name} WHERE id = ANY(%s) AND namespace = %s;"
                        cursor.execute(sql, [ids, namespace])
                    else:
                        sql = f"DELETE FROM {self.table_name} WHERE id = ANY(%s);"
                        cursor.execute(sql, [ids])
            
            backend_type = "SQLite" if self.is_sqlite else "PgVector"
            self.logger.info(
                f"Vectors deleted from {backend_type}",
                count=len(ids),
                namespace=namespace
            )
            return True
            
        except Exception as e:
            backend_type = "SQLite" if self.is_sqlite else "PgVector"
            self.logger.error(
                f"Failed to delete vectors from {backend_type}",
                error=str(e),
                error_type=type(e).__name__,
                count=len(ids)
            )
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics (SQLite or PostgreSQL)."""
        return await sync_to_async(self._get_stats_sync)()
    
    def _get_stats_sync(self) -> Dict[str, Any]:
        """Synchronous stats retrieval operation."""
        try:
            with connection.cursor() as cursor:
                if self.is_sqlite:
                    # SQLite version
                    sql = "SELECT COUNT(*) as total_vectors, COUNT(DISTINCT namespace) as namespaces FROM " + self.table_name
                    cursor.execute(sql)
                    
                    row = cursor.fetchone()
                    return {
                        "backend": "sqlite",
                        "total_vectors": row[0],
                        "namespaces": row[1],
                        "table_size": "N/A (SQLite)"
                    }
                else:
                    # PostgreSQL version  
                    sql = f"""
                        SELECT 
                            COUNT(*) as total_vectors,
                            COUNT(DISTINCT namespace) as namespaces,
                            pg_size_pretty(pg_total_relation_size('{self.table_name}')) as table_size
                        FROM {self.table_name};
                    """
                    cursor.execute(sql)
                    
                    row = cursor.fetchone()
                    return {
                        "backend": "pgvector",
                        "total_vectors": row[0],
                        "namespaces": row[1],
                        "table_size": row[2]
                    }
                
        except Exception as e:
            backend_type = "SQLite" if self.is_sqlite else "PgVector"
            self.logger.error(f"Failed to get {backend_type} stats", error=str(e))
            return {"backend": backend_type.lower(), "error": str(e)}


class VectorStorageService:
    """
    Main vector storage service with automatic backend selection and fallback.
    
    Provides a unified interface for vector operations regardless of backend.
    """
    
    def __init__(self, config: VectorStorageConfig = None):
        """Initialize vector storage service."""
        self.config = config or VectorStorageConfig()
        self.logger = structlog.get_logger().bind(component="VectorStorageService")
        self.backend: Optional[VectorStorageBackend] = None
        self.backend_name = None
        
        self.logger.info(
            "Vector storage service initializing",
            backend_preference=self.config.backend,
            caching_enabled=self.config.enable_caching
        )
    
    async def initialize(self) -> bool:
        """Initialize the appropriate backend with fallback logic."""
        if self.config.backend == "pinecone":
            return await self._initialize_pinecone()
        elif self.config.backend == "pgvector":
            return await self._initialize_pgvector()
        else:  # auto selection
            return await self._initialize_auto()
    
    async def _initialize_auto(self) -> bool:
        """Auto-select backend with fallback preference."""
        # Try Pinecone first if API key is available
        if self.config.pinecone_api_key and self.config.pinecone_environment:
            if await self._initialize_pinecone():
                return True
        
        # Fallback to pgvector
        return await self._initialize_pgvector()
    
    async def _initialize_pinecone(self) -> bool:
        """Initialize Pinecone backend."""
        self.backend = PineconeBackend(self.config)
        if await self.backend.initialize():
            self.backend_name = "pinecone"
            self.logger.info("Using Pinecone backend")
            return True
        return False
    
    async def _initialize_pgvector(self) -> bool:
        """Initialize PgVector backend."""
        self.backend = PgVectorBackend(self.config)
        if await self.backend.initialize():
            self.backend_name = "pgvector"
            self.logger.info("Using PgVector backend")
            return True
        return False
    
    async def store_embeddings(
        self,
        embeddings: List[Tuple[str, List[float], Dict[str, Any]]],
        namespace: Optional[str] = None
    ) -> bool:
        """Store embeddings with metadata."""
        if not self.backend:
            raise VectorStorageError("Vector storage not initialized")
        
        try:
            # Process in batches
            success = True
            for i in range(0, len(embeddings), self.config.batch_size):
                batch = embeddings[i:i + self.config.batch_size]
                batch_success = await self.backend.upsert_vectors(batch, namespace)
                if not batch_success:
                    success = False
            
            # If any batch failed, raise an exception for proper error handling
            if not success:
                raise VectorStorageError("One or more embedding batches failed to store")
            
            self.logger.info(
                "Embeddings stored",
                count=len(embeddings),
                namespace=namespace,
                backend=self.backend_name,
                success=success
            )
            return success
            
        except VectorStorageError:
            # Re-raise VectorStorageErrors as-is
            raise
        except Exception as e:
            self.logger.error(
                "Failed to store embeddings",
                error=str(e),
                error_type=type(e).__name__,
                count=len(embeddings)
            )
            raise VectorStorageError(f"Failed to store embeddings: {e}")
    
    async def search_similar(
        self,
        query_vector: List[float],
        top_k: int = 10,
        namespace: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """
        Search for similar vectors with privacy filtering.
        By default, only returns citable content.
        """
        if not self.backend:
            raise VectorStorageError("Vector storage not initialized")
        
        # Check cache first
        cache_key = None
        if self.config.enable_caching:
            cache_key = self._generate_cache_key(query_vector, top_k, namespace, filter_metadata)
            cached_results = cache.get(cache_key)
            if cached_results:
                self.logger.info("Returning cached search results", cache_key=cache_key)
                return cached_results
        
        try:
            query = VectorSearchQuery(
                vector=query_vector,
                top_k=top_k,
                namespace=namespace,
                filter=filter_metadata,
                include_metadata=True
            )
            
            results = await self.backend.search_vectors(query)
            
            # Cache results
            if self.config.enable_caching and cache_key:
                cache.set(
                    cache_key, 
                    results, 
                    timeout=self.config.cache_ttl_hours * 3600
                )
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Failed to search vectors",
                error=str(e),
                error_type=type(e).__name__,
                top_k=top_k
            )
            raise VectorStorageError(f"Failed to search vectors: {e}")
    
    async def search_citable_only(
        self,
        query_vector: List[float],
        top_k: int = 10,
        namespace: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """
        Search for similar vectors, returning only citable content.
        This is the safe method for user-facing responses.
        """
        # Ensure privacy filtering is enabled
        filter_metadata = filter_metadata or {}
        filter_metadata['include_non_citable'] = False
        
        return await self.search_similar(
            query_vector=query_vector,
            top_k=top_k,
            namespace=namespace,
            filter_metadata=filter_metadata
        )
    
    async def search_all_content(
        self,
        query_vector: List[float],
        top_k: int = 10,
        namespace: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """
        Search for similar vectors, including non-citable content.
        WARNING: Only use for internal RAG context, never for user-facing responses.
        """
        # Allow non-citable content for internal use
        filter_metadata = filter_metadata or {}
        filter_metadata['include_non_citable'] = True
        
        self.logger.warning(
            "Searching all content including non-citable - ensure proper usage",
            namespace=namespace,
            top_k=top_k
        )
        
        return await self.search_similar(
            query_vector=query_vector,
            top_k=top_k,
            namespace=namespace,
            filter_metadata=filter_metadata
        )
    
    async def delete_embeddings(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> bool:
        """Delete embeddings by IDs."""
        if not self.backend:
            raise VectorStorageError("Vector storage not initialized")
        
        try:
            success = await self.backend.delete_vectors(ids, namespace)
            
            self.logger.info(
                "Embeddings deleted",
                count=len(ids),
                namespace=namespace,
                backend=self.backend_name,
                success=success
            )
            return success
            
        except Exception as e:
            self.logger.error(
                "Failed to delete embeddings",
                error=str(e),
                error_type=type(e).__name__,
                count=len(ids)
            )
            raise VectorStorageError(f"Failed to delete embeddings: {e}")
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage backend statistics."""
        if not self.backend:
            return {"error": "Vector storage not initialized"}
        
        try:
            stats = await self.backend.get_stats()
            stats["config"] = {
                "backend": self.backend_name,
                "caching_enabled": self.config.enable_caching,
                "batch_size": self.config.batch_size
            }
            return stats
            
        except Exception as e:
            self.logger.error("Failed to get storage stats", error=str(e))
            return {"error": str(e)}
    
    def _generate_cache_key(
        self,
        query_vector: List[float],
        top_k: int,
        namespace: Optional[str],
        filter_metadata: Optional[Dict[str, Any]]
    ) -> str:
        """Generate cache key for search query."""
        key_data = {
            "vector_hash": hashlib.md5(str(query_vector).encode()).hexdigest()[:16],
            "top_k": top_k,
            "namespace": namespace,
            "filter": filter_metadata
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return f"vector_search:{hashlib.md5(key_string.encode()).hexdigest()}"


# Convenience function for quick setup
async def create_vector_storage(backend: str = "auto") -> VectorStorageService:
    """Create and initialize vector storage service."""
    config = VectorStorageConfig(backend=backend)
    service = VectorStorageService(config)
    
    if await service.initialize():
        return service
    else:
        raise VectorStorageError("Failed to initialize vector storage")