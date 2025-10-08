"""
Pytest configuration and fixtures for the RAG chatbot system tests.
Provides comprehensive test utilities and mocked dependencies.
"""

import pytest
import asyncio
import uuid
import os
import sys
import tempfile
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any, Optional

import django
from django.conf import settings as django_settings
from django.test.utils import setup_test_environment, teardown_test_environment
from django.core.management import execute_from_command_line

# Set up Django before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.test_settings')
django.setup()

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from apps.core.document_processing import DocumentContent, PrivacyLevel, DocumentType
from apps.core.chunking import DocumentChunk
from apps.core.embeddings import EmbeddingBatch
from apps.core.vector_search import SearchResultWithCitation
from apps.core.auth import TokenPayload, TokenType
from chatbot_saas.config import get_settings


User = get_user_model()
config_settings = get_settings()


# Pytest configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    with patch('apps.core.auth.settings') as mock_settings:
        mock_settings.JWT_SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ACCESS_TOKEN_LIFETIME = 900
        mock_settings.JWT_REFRESH_TOKEN_LIFETIME = 604800
        mock_settings.ENABLE_CACHING = True
        mock_settings.CACHE_TTL_SECONDS = 3600
        mock_settings.MAX_FILE_SIZE_MB = 100
        mock_settings.MAX_EMBEDDING_BATCH_SIZE = 100
        yield mock_settings


# User and authentication fixtures
@pytest.fixture
def test_user():
    """Create a test user."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpassword123",
        first_name="Test",
        last_name="User"
    )
    return user


@pytest.fixture
def test_user_data():
    """Test user data dictionary."""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User"
    }


@pytest.fixture
def mock_jwt_payload():
    """Mock JWT token payload."""
    return TokenPayload(
        user_id="test-user-id",
        token_type=TokenType.ACCESS,
        email="test@example.com",
        exp=timezone.now() + timezone.timedelta(minutes=15),
        iat=timezone.now(),
        jti=str(uuid.uuid4()),
        scopes=["read", "write"]
    )


@pytest.fixture
def mock_oauth_user_info():
    """Mock OAuth user information."""
    from apps.core.oauth import UserInfo
    
    return UserInfo(
        id="google-user-id",
        email="test@example.com",
        verified_email=True,
        name="Test User",
        given_name="Test",
        family_name="User",
        picture="https://example.com/avatar.jpg",
        locale="en"
    )


# Document processing fixtures
@pytest.fixture
def sample_pdf_content():
    """Sample PDF file content."""
    # This would be actual PDF bytes in a real test
    return b"%PDF-1.4 sample content"


@pytest.fixture
def sample_text_content():
    """Sample text content."""
    return "This is a sample document with multiple paragraphs.\n\nThis is the second paragraph with some important information that should be processed and chunked appropriately."


@pytest.fixture
def mock_document_content():
    """Mock document content object."""
    return DocumentContent(
        text="This is a sample document content for testing purposes. It contains multiple sentences to test chunking.",
        title="Test Document",
        author="Test Author",
        metadata={
            "filename": "test.pdf",
            "page_count": 1,
            "processing_method": "test"
        },
        privacy_level=PrivacyLevel.CITABLE,
        source_type=DocumentType.PDF,
        content_hash="test-hash-123",
        token_count=50
    )


@pytest.fixture
def mock_document_chunks():
    """Mock document chunks."""
    chunks = []
    for i in range(3):
        chunk = DocumentChunk(
            content=f"This is chunk {i} content with some text to process.",
            chunk_index=i,
            start_char=i * 50,
            end_char=(i + 1) * 50,
            token_count=10,
            privacy_level=PrivacyLevel.CITABLE,
            metadata={
                "chunking_strategy": "test",
                "chunk_size_tokens": 10,
                "source_document_hash": "test-hash-123"
            },
            content_hash=f"chunk-hash-{i}"
        )
        chunks.append(chunk)
    return chunks


# Embedding and vector search fixtures
@pytest.fixture
def mock_embedding_batch():
    """Mock embedding batch."""
    return EmbeddingBatch(
        embeddings=[[0.1, 0.2, 0.3] for _ in range(3)],
        chunks=[],  # Would contain actual chunks in real scenario
        metadata={
            "total_chunks": 3,
            "cached_chunks": 0,
            "generated_chunks": 3,
            "model": "test-model",
            "dimension": 3
        },
        processing_time=0.5,
        provider="test",
        model="test-model"
    )


@pytest.fixture
def mock_search_results():
    """Mock vector search results."""
    results = []
    for i in range(3):
        result = SearchResultWithCitation(
            content=f"Search result {i} content",
            score=0.9 - (i * 0.1),
            chunk_id=f"chunk-{i}",
            document_id=f"doc-{i}",
            knowledge_base_id="kb-1",
            privacy_level=PrivacyLevel.CITABLE,
            can_cite=True,
            citation_text=f"Test Document {i}",
            source_title=f"Test Document {i}",
            source_author="Test Author",
            source_url=None,
            page_number=1,
            chunk_index=i,
            start_char=i * 50,
            end_char=(i + 1) * 50,
            metadata={
                "document_title": f"Test Document {i}",
                "privacy_level": "citable"
            }
        )
        results.append(result)
    return results


# Mock external services
@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    mock_client = AsyncMock()
    
    # Mock embeddings response
    mock_embedding_response = Mock()
    mock_embedding_response.data = [
        Mock(embedding=[0.1, 0.2, 0.3])
    ]
    mock_embedding_response.usage = Mock(total_tokens=10)
    mock_client.embeddings.create.return_value = mock_embedding_response
    
    # Mock chat completion response
    mock_chat_response = Mock()
    mock_chat_response.choices = [
        Mock(message=Mock(content="Test response"))
    ]
    mock_chat_response.usage = Mock(
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15
    )
    mock_client.chat.completions.create.return_value = mock_chat_response
    
    return mock_client


@pytest.fixture
def mock_vector_store():
    """Mock vector store."""
    mock_store = AsyncMock()
    
    # Mock search method
    from apps.core.interfaces import SearchResult
    mock_results = [
        SearchResult(
            id=f"result-{i}",
            score=0.9 - (i * 0.1),
            metadata={
                "document_id": f"doc-{i}",
                "privacy_level": "citable",
                "chunk_index": i
            },
            content=f"Result {i} content"
        )
        for i in range(3)
    ]
    mock_store.search.return_value = mock_results
    
    # Mock upsert method
    mock_store.upsert.return_value = None
    
    # Mock health check
    from apps.core.interfaces import ServiceStatus
    mock_store.health_check.return_value = ServiceStatus.HEALTHY
    
    return mock_store


@pytest.fixture
def mock_file_storage():
    """Mock file storage."""
    mock_storage = AsyncMock()
    
    mock_storage.upload.return_value = "https://example.com/file.pdf"
    mock_storage.download.return_value = b"file content"
    mock_storage.get_presigned_url.return_value = "https://example.com/presigned"
    
    from apps.core.interfaces import ServiceStatus
    mock_storage.health_check.return_value = ServiceStatus.HEALTHY
    
    return mock_storage


@pytest.fixture
def mock_sentence_transformer():
    """Mock sentence transformer model."""
    mock_model = Mock()
    mock_model.encode.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    
    with patch('sentence_transformers.SentenceTransformer') as mock_st:
        mock_st.return_value = mock_model
        yield mock_model


# Repository and service mocks
@pytest.fixture
def mock_user_repository():
    """Mock user repository."""
    mock_repo = Mock()
    
    # Mock user object
    mock_user = Mock()
    mock_user.id = "test-user-id"
    mock_user.email = "test@example.com"
    mock_user.is_active = True
    mock_user.password = "hashed-password"
    
    mock_repo.get_by_email.return_value = mock_user
    mock_repo.get_by_id.return_value = mock_user
    mock_repo.create.return_value = mock_user
    mock_repo.update.return_value = mock_user
    
    return mock_repo


@pytest.fixture
def mock_document_repository():
    """Mock document repository."""
    mock_repo = Mock()
    
    mock_document = Mock()
    mock_document.id = "test-doc-id"
    mock_document.filename = "test.pdf"
    mock_document.status = "uploaded"
    mock_document.privacy_level = "citable"
    
    mock_repo.get_by_id.return_value = mock_document
    mock_repo.create.return_value = mock_document
    mock_repo.update.return_value = mock_document
    
    return mock_repo


@pytest.fixture
def mock_knowledge_base_repository():
    """Mock knowledge base repository."""
    mock_repo = Mock()
    
    mock_kb = Mock()
    mock_kb.id = "test-kb-id"
    mock_kb.name = "Test KB"
    mock_kb.user_id = "test-user-id"
    mock_kb.privacy_level = "citable"
    
    mock_repo.get_by_id.return_value = mock_kb
    mock_repo.create.return_value = mock_kb
    mock_repo.get_by_user.return_value = [mock_kb]
    
    return mock_repo


# Celery task mocking
@pytest.fixture
def mock_celery_task():
    """Mock Celery task."""
    mock_task = Mock()
    mock_task.id = "test-task-id"
    mock_task.state = "SUCCESS"
    mock_task.result = {"status": "completed"}
    
    return mock_task


@pytest.fixture
def mock_celery_app():
    """Mock Celery app."""
    with patch('apps.core.tasks.app') as mock_app:
        mock_app.control.inspect.return_value.active.return_value = {"worker1": []}
        yield mock_app


# Database fixtures
@pytest.fixture
def mock_database_models():
    """Mock database models."""
    models = {}
    
    # Mock KnowledgeBase model
    mock_kb_model = Mock()
    mock_kb_model.objects.create.return_value = Mock(id="kb-1", name="Test KB")
    mock_kb_model.objects.get.return_value = Mock(id="kb-1", user_id="user-1")
    models['KnowledgeBase'] = mock_kb_model
    
    # Mock Document model
    mock_doc_model = Mock()
    mock_doc_model.objects.create.return_value = Mock(id="doc-1", filename="test.pdf")
    mock_doc_model.objects.get.return_value = Mock(id="doc-1", status="uploaded")
    models['Document'] = mock_doc_model
    
    return models


# HTTP request mocking
@pytest.fixture
def mock_http_request():
    """Mock HTTP request."""
    mock_request = Mock()
    mock_request.META = {
        'HTTP_X_FORWARDED_FOR': '192.168.1.1',
        'REMOTE_ADDR': '127.0.0.1',
        'HTTP_USER_AGENT': 'Test Browser',
        'HTTP_ACCEPT_LANGUAGE': 'en-US',
        'HTTP_ACCEPT_ENCODING': 'gzip'
    }
    mock_request.method = 'POST'
    mock_request.path = '/api/test'
    
    return mock_request


# File system fixtures
@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"Test file content")
        tmp.flush()
        yield tmp.name
    
    # Cleanup
    try:
        os.unlink(tmp.name)
    except FileNotFoundError:
        pass


@pytest.fixture
def sample_files():
    """Sample files for testing document processing."""
    files = {
        'pdf': b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        'txt': b"This is a sample text file for testing.\n\nIt has multiple paragraphs.",
        'docx': b"PK\x03\x04" + b"x" * 100  # Simplified DOCX header
    }
    return files


# Async testing utilities
@pytest.fixture
def run_async():
    """Utility to run async functions in tests."""
    def _run_async(coro):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    return _run_async


# Test data generators
@pytest.fixture
def generate_test_data():
    """Generate test data for various scenarios."""
    def _generate_user_data(count=1):
        users = []
        for i in range(count):
            users.append({
                "email": f"user{i}@example.com",
                "password": "TestPassword123!",
                "first_name": f"User{i}",
                "last_name": "Test"
            })
        return users
    
    def _generate_document_data(count=1):
        documents = []
        for i in range(count):
            documents.append({
                "filename": f"document{i}.pdf",
                "content_type": "application/pdf",
                "file_size": 1024 * (i + 1),
                "privacy_level": "citable"
            })
        return documents
    
    return {
        "users": _generate_user_data,
        "documents": _generate_document_data
    }


# Performance testing fixtures
@pytest.fixture
def performance_monitor():
    """Monitor for performance testing."""
    import time
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.metrics = {}
        
        def start(self):
            self.start_time = time.time()
        
        def end(self, operation_name):
            if self.start_time:
                duration = time.time() - self.start_time
                self.metrics[operation_name] = duration
                self.start_time = None
                return duration
            return 0
        
        def assert_performance(self, operation_name, max_duration):
            assert operation_name in self.metrics
            assert self.metrics[operation_name] <= max_duration, \
                f"{operation_name} took {self.metrics[operation_name]}s, expected <= {max_duration}s"
    
    return PerformanceMonitor()


# Error simulation fixtures
@pytest.fixture
def error_simulator():
    """Simulate various error conditions for testing."""
    class ErrorSimulator:
        @staticmethod
        def connection_error():
            return ConnectionError("Simulated connection error")
        
        @staticmethod
        def timeout_error():
            return TimeoutError("Simulated timeout error")
        
        @staticmethod
        def validation_error():
            from apps.core.error_handling import ValidationError
            return ValidationError("Simulated validation error", field="test_field")
        
        @staticmethod
        def rate_limit_error():
            from apps.core.error_handling import RateLimitError
            return RateLimitError("Rate limit exceeded", retry_after=60)
        
        @staticmethod
        def external_service_error():
            from apps.core.error_handling import ExternalServiceError
            return ExternalServiceError("External service error", service="test_service")
    
    return ErrorSimulator()


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Clean up test data after each test."""
    yield
    # Cleanup logic here (clear cache, reset mocks, etc.)
    cache.clear()


# Mark for async tests
pytest_mark_asyncio = pytest.mark.asyncio