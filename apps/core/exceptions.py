"""
Custom exception handling for the API.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import structlog

logger = structlog.get_logger()


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides structured error responses.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Log the exception
        logger.error(
            "API exception occurred",
            exception_type=type(exc).__name__,
            exception_message=str(exc),
            status_code=response.status_code,
            path=context['request'].path if 'request' in context else None,
            method=context['request'].method if 'request' in context else None,
        )

        # Customize the response format
        custom_response_data = {
            'error': {
                'type': type(exc).__name__,
                'message': str(exc),
                'status_code': response.status_code,
            }
        }

        # Add details for validation errors
        if hasattr(response, 'data') and response.data:
            custom_response_data['error']['details'] = response.data

        response.data = custom_response_data

    return response


class ServiceError(Exception):
    """Base service error."""
    
    def __init__(self, message: str, error_code: str = None, status_code: int = 500):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)


class ValidationError(ServiceError):
    """Validation error."""
    
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message, "VALIDATION_ERROR", 400)


class AuthenticationError(ServiceError):
    """Authentication error."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTHENTICATION_ERROR", 401)


class AuthorizationError(ServiceError):
    """Authorization error."""
    
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, "AUTHORIZATION_ERROR", 403)


class NotFoundError(ServiceError):
    """Resource not found error."""
    
    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", "NOT_FOUND_ERROR", 404)


class ConflictError(ServiceError):
    """Conflict error."""
    
    def __init__(self, message: str):
        super().__init__(message, "CONFLICT_ERROR", 409)


class RateLimitError(ServiceError):
    """Rate limit exceeded error."""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, "RATE_LIMIT_ERROR", 429)


class ExternalServiceError(ServiceError):
    """External service error."""
    
    def __init__(self, service: str, message: str):
        super().__init__(f"{service}: {message}", "EXTERNAL_SERVICE_ERROR", 502)


# Document Processing Exceptions

class DocumentValidationError(ValidationError):
    """Raised when document validation fails."""
    
    def __init__(self, message: str):
        super().__init__(message)
        self.error_code = "DOCUMENT_VALIDATION_ERROR"


class UnsupportedFileTypeError(DocumentValidationError):
    """Raised when uploaded file type is not supported."""
    
    def __init__(self, file_type: str):
        super().__init__(f"File type '{file_type}' is not supported")
        self.error_code = "UNSUPPORTED_FILE_TYPE"


class FileSizeExceededError(DocumentValidationError):
    """Raised when uploaded file exceeds size limits."""
    
    def __init__(self, file_size: int, max_size: int):
        super().__init__(f"File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)")
        self.error_code = "FILE_SIZE_EXCEEDED"


class VirusScanFailedError(ServiceError):
    """Raised when virus scanning fails or finds threats."""
    
    def __init__(self, message: str = "File failed virus scanning"):
        super().__init__(message, "VIRUS_SCAN_FAILED", 422)


class MaliciousContentError(ServiceError):
    """Raised when file contains potentially malicious content."""
    
    def __init__(self, message: str = "File contains suspicious or malicious content"):
        super().__init__(message, "MALICIOUS_CONTENT_DETECTED", 422)


class DocumentProcessingError(ServiceError):
    """Raised when document processing fails."""
    
    def __init__(self, message: str):
        super().__init__(message, "DOCUMENT_PROCESSING_ERROR", 500)


class TextExtractionError(DocumentProcessingError):
    """Raised when text extraction from document fails."""
    
    def __init__(self, message: str = "Failed to extract text from document"):
        super().__init__(message)
        self.error_code = "TEXT_EXTRACTION_FAILED"


class ChunkingError(DocumentProcessingError):
    """Raised when text chunking fails."""
    
    def __init__(self, message: str = "Failed to chunk document text"):
        super().__init__(message)
        self.error_code = "TEXT_CHUNKING_FAILED"


class EmbeddingGenerationError(ExternalServiceError):
    """Raised when embedding generation fails."""
    
    def __init__(self, message: str = "Failed to generate embeddings"):
        super().__init__("OpenAI", message)
        self.error_code = "EMBEDDING_GENERATION_FAILED"


class VectorStorageError(ExternalServiceError):
    """Raised when vector storage operations fail."""
    
    def __init__(self, service: str, message: str = "Vector storage operation failed"):
        super().__init__(service, message)
        self.error_code = "VECTOR_STORAGE_ERROR"