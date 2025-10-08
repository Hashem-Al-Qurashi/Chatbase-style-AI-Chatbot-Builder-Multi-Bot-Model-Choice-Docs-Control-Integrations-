"""
Abstract interfaces for external services.
This prevents vendor lock-in and enables easy testing and provider switching.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, Tuple
from dataclasses import dataclass
from datetime import datetime
import enum


class ServiceStatus(enum.Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass
class EmbeddingResult:
    """Result from embedding generation."""
    embedding: List[float]
    token_count: int
    model: str
    metadata: Dict[str, Any]


@dataclass
class ChatResponse:
    """Response from LLM chat completion."""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    metadata: Dict[str, Any]


@dataclass
class SearchResult:
    """Result from vector search."""
    id: str
    score: float
    metadata: Dict[str, Any]
    content: str


@dataclass
class PaymentIntent:
    """Payment intent from payment processor."""
    id: str
    amount: int
    currency: str
    status: str
    client_secret: str
    metadata: Dict[str, Any]


@dataclass
class WebhookEvent:
    """Webhook event from external service."""
    id: str
    type: str
    data: Dict[str, Any]
    created: datetime
    livemode: bool


class LLMProvider(Protocol):
    """Abstract interface for Language Model providers."""
    
    @abstractmethod
    async def generate_embedding(
        self,
        text: str,
        model: str = "text-embedding-ada-002",
        **kwargs
    ) -> EmbeddingResult:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            model: Model to use for embedding
            **kwargs: Additional provider-specific parameters
            
        Returns:
            EmbeddingResult: Embedding with metadata
            
        Raises:
            LLMProviderError: If embedding generation fails
        """
        ...
    
    @abstractmethod
    async def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> ChatResponse:
        """
        Generate chat completion.
        
        Args:
            messages: Conversation messages
            model: Model to use
            max_tokens: Maximum tokens to generate
            temperature: Randomness in generation
            **kwargs: Additional provider-specific parameters
            
        Returns:
            ChatResponse: Generated response with metadata
            
        Raises:
            LLMProviderError: If chat completion fails
        """
        ...
    
    @abstractmethod
    async def health_check(self) -> ServiceStatus:
        """Check service health."""
        ...


class VectorStore(Protocol):
    """Abstract interface for vector storage providers."""
    
    @abstractmethod
    async def upsert(
        self,
        vectors: List[Tuple[str, List[float], Dict[str, Any]]],
        namespace: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Insert or update vectors.
        
        Args:
            vectors: List of (id, vector, metadata) tuples
            namespace: Optional namespace for isolation
            **kwargs: Additional provider-specific parameters
            
        Raises:
            VectorStoreError: If upsert fails
        """
        ...
    
    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_criteria: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
        include_metadata: bool = True,
        **kwargs
    ) -> List[SearchResult]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query vector
            top_k: Number of results to return
            filter_criteria: Metadata filters
            namespace: Optional namespace
            include_metadata: Include metadata in results
            **kwargs: Additional provider-specific parameters
            
        Returns:
            List[SearchResult]: Search results
            
        Raises:
            VectorStoreError: If search fails
        """
        ...
    
    @abstractmethod
    async def delete(
        self,
        ids: List[str],
        namespace: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Delete vectors by IDs.
        
        Args:
            ids: Vector IDs to delete
            namespace: Optional namespace
            **kwargs: Additional provider-specific parameters
            
        Raises:
            VectorStoreError: If deletion fails
        """
        ...
    
    @abstractmethod
    async def create_index(
        self,
        name: str,
        dimension: int,
        metric: str = "cosine",
        **kwargs
    ) -> None:
        """
        Create a new index.
        
        Args:
            name: Index name
            dimension: Vector dimension
            metric: Distance metric
            **kwargs: Additional provider-specific parameters
            
        Raises:
            VectorStoreError: If index creation fails
        """
        ...
    
    @abstractmethod
    async def health_check(self) -> ServiceStatus:
        """Check service health."""
        ...


class FileStorage(Protocol):
    """Abstract interface for file storage providers."""
    
    @abstractmethod
    async def upload(
        self,
        file_content: bytes,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """
        Upload file to storage.
        
        Args:
            file_content: File content as bytes
            key: Storage key/path
            content_type: MIME type
            metadata: File metadata
            **kwargs: Additional provider-specific parameters
            
        Returns:
            str: Public URL or storage reference
            
        Raises:
            FileStorageError: If upload fails
        """
        ...
    
    @abstractmethod
    async def download(
        self,
        key: str,
        **kwargs
    ) -> bytes:
        """
        Download file from storage.
        
        Args:
            key: Storage key/path
            **kwargs: Additional provider-specific parameters
            
        Returns:
            bytes: File content
            
        Raises:
            FileStorageError: If download fails
        """
        ...
    
    @abstractmethod
    async def delete(
        self,
        key: str,
        **kwargs
    ) -> None:
        """
        Delete file from storage.
        
        Args:
            key: Storage key/path
            **kwargs: Additional provider-specific parameters
            
        Raises:
            FileStorageError: If deletion fails
        """
        ...
    
    @abstractmethod
    async def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
        method: str = "GET",
        **kwargs
    ) -> str:
        """
        Get presigned URL for file access.
        
        Args:
            key: Storage key/path
            expires_in: URL expiration in seconds
            method: HTTP method
            **kwargs: Additional provider-specific parameters
            
        Returns:
            str: Presigned URL
            
        Raises:
            FileStorageError: If URL generation fails
        """
        ...
    
    @abstractmethod
    async def health_check(self) -> ServiceStatus:
        """Check service health."""
        ...


class PaymentProcessor(Protocol):
    """Abstract interface for payment processors."""
    
    @abstractmethod
    async def create_payment_intent(
        self,
        amount: int,
        currency: str = "usd",
        customer_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> PaymentIntent:
        """
        Create payment intent.
        
        Args:
            amount: Amount in smallest currency unit
            currency: Currency code
            customer_id: Customer identifier
            metadata: Payment metadata
            **kwargs: Additional provider-specific parameters
            
        Returns:
            PaymentIntent: Payment intent details
            
        Raises:
            PaymentProcessorError: If payment intent creation fails
        """
        ...
    
    @abstractmethod
    async def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method: str,
        **kwargs
    ) -> PaymentIntent:
        """
        Confirm payment intent.
        
        Args:
            payment_intent_id: Payment intent ID
            payment_method: Payment method
            **kwargs: Additional provider-specific parameters
            
        Returns:
            PaymentIntent: Updated payment intent
            
        Raises:
            PaymentProcessorError: If payment confirmation fails
        """
        ...
    
    @abstractmethod
    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create customer.
        
        Args:
            email: Customer email
            name: Customer name
            metadata: Customer metadata
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Dict[str, Any]: Customer details
            
        Raises:
            PaymentProcessorError: If customer creation fails
        """
        ...
    
    @abstractmethod
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create subscription.
        
        Args:
            customer_id: Customer ID
            price_id: Price/plan ID
            metadata: Subscription metadata
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Dict[str, Any]: Subscription details
            
        Raises:
            PaymentProcessorError: If subscription creation fails
        """
        ...
    
    @abstractmethod
    async def handle_webhook(
        self,
        payload: bytes,
        signature: str,
        **kwargs
    ) -> WebhookEvent:
        """
        Handle webhook event.
        
        Args:
            payload: Webhook payload
            signature: Webhook signature
            **kwargs: Additional provider-specific parameters
            
        Returns:
            WebhookEvent: Parsed webhook event
            
        Raises:
            PaymentProcessorError: If webhook handling fails
        """
        ...
    
    @abstractmethod
    async def health_check(self) -> ServiceStatus:
        """Check service health."""
        ...


class EmailProvider(Protocol):
    """Abstract interface for email providers."""
    
    @abstractmethod
    async def send_email(
        self,
        to: List[str],
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Send email.
        
        Args:
            to: Recipient email addresses
            subject: Email subject
            body_html: HTML body
            body_text: Plain text body
            from_email: Sender email
            reply_to: Reply-to email
            **kwargs: Additional provider-specific parameters
            
        Returns:
            str: Message ID
            
        Raises:
            EmailProviderError: If email sending fails
        """
        ...
    
    @abstractmethod
    async def send_template_email(
        self,
        to: List[str],
        template_id: str,
        template_data: Dict[str, Any],
        from_email: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Send templated email.
        
        Args:
            to: Recipient email addresses
            template_id: Template identifier
            template_data: Template variables
            from_email: Sender email
            **kwargs: Additional provider-specific parameters
            
        Returns:
            str: Message ID
            
        Raises:
            EmailProviderError: If email sending fails
        """
        ...
    
    @abstractmethod
    async def health_check(self) -> ServiceStatus:
        """Check service health."""
        ...


# Custom exceptions for service providers
class ServiceProviderError(Exception):
    """Base exception for service provider errors."""
    
    def __init__(self, message: str, provider: str, original_error: Optional[Exception] = None):
        self.message = message
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"{provider}: {message}")


class LLMProviderError(ServiceProviderError):
    """LLM provider specific error."""
    pass


class VectorStoreError(ServiceProviderError):
    """Vector store specific error."""
    pass


class FileStorageError(ServiceProviderError):
    """File storage specific error."""
    pass


class PaymentProcessorError(ServiceProviderError):
    """Payment processor specific error."""
    pass


class EmailProviderError(ServiceProviderError):
    """Email provider specific error."""
    pass