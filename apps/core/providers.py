"""
Concrete implementations of external service interfaces.
Each implementation includes circuit breakers, retries, and proper error handling.
"""

import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import boto3
import openai
import pinecone
import stripe
import structlog
from botocore.exceptions import ClientError, BotoCoreError

from chatbot_saas.config import get_settings
from .circuit_breaker import (
    CircuitBreakerConfig, 
    CircuitBreakerError,
    circuit_breaker, 
    retry, 
    RetryConfig
)
from .interfaces import (
    ChatResponse,
    EmbeddingResult,
    EmailProvider,
    FileStorage,
    LLMProvider,
    PaymentIntent,
    PaymentProcessor,
    SearchResult,
    ServiceStatus,
    VectorStore,
    WebhookEvent,
    # Exceptions
    EmailProviderError,
    FileStorageError,
    LLMProviderError,
    PaymentProcessorError,
    VectorStoreError,
)

logger = structlog.get_logger()
settings = get_settings()


class OpenAIProvider(LLMProvider):
    """OpenAI implementation with circuit breaker and retry logic."""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            timeout=settings.OPENAI_TIMEOUT,
            max_retries=0,  # We handle retries ourselves
        )
        
        # Circuit breaker configuration for OpenAI
        self.circuit_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60,
            success_threshold=2,
            timeout=settings.OPENAI_TIMEOUT,
            expected_exception=(openai.OpenAIError, aiohttp.ClientError),
        )
        
        # Retry configuration
        self.retry_config = RetryConfig(
            max_attempts=settings.OPENAI_MAX_RETRIES,
            base_delay=1.0,
            max_delay=30.0,
            retryable_exceptions=(
                openai.RateLimitError,
                openai.InternalServerError,
                openai.UnprocessableEntityError,
                aiohttp.ClientError,
            )
        )
    
    @circuit_breaker("openai_embedding")
    @retry()
    async def generate_embedding(
        self,
        text: str,
        model: str = "text-embedding-ada-002",
        **kwargs
    ) -> EmbeddingResult:
        """Generate embedding using OpenAI API."""
        try:
            logger.debug(
                "Generating embedding",
                text_length=len(text),
                model=model
            )
            
            response = await self.client.embeddings.create(
                input=text,
                model=model,
                **kwargs
            )
            
            embedding_data = response.data[0]
            
            result = EmbeddingResult(
                embedding=embedding_data.embedding,
                token_count=response.usage.total_tokens,
                model=model,
                metadata={
                    "input_length": len(text),
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
            
            logger.debug(
                "Embedding generated successfully",
                token_count=result.token_count,
                model=model
            )
            
            return result
            
        except openai.OpenAIError as e:
            logger.error(
                "OpenAI embedding error",
                error=str(e),
                error_type=type(e).__name__,
                model=model
            )
            raise LLMProviderError(
                f"Failed to generate embedding: {str(e)}",
                "OpenAI",
                e
            )
    
    @circuit_breaker("openai_chat")
    @retry()
    async def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> ChatResponse:
        """Generate chat completion using OpenAI API."""
        try:
            logger.debug(
                "Generating chat completion",
                message_count=len(messages),
                model=model,
                max_tokens=max_tokens
            )
            
            response = await self.client.chat.completions.create(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            choice = response.choices[0]
            
            result = ChatResponse(
                content=choice.message.content,
                model=model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                finish_reason=choice.finish_reason,
                metadata={
                    "created_at": datetime.utcnow().isoformat(),
                    "temperature": temperature,
                }
            )
            
            logger.debug(
                "Chat completion generated",
                total_tokens=result.usage["total_tokens"],
                finish_reason=result.finish_reason
            )
            
            return result
            
        except openai.OpenAIError as e:
            logger.error(
                "OpenAI chat completion error",
                error=str(e),
                error_type=type(e).__name__,
                model=model
            )
            raise LLMProviderError(
                f"Failed to generate chat completion: {str(e)}",
                "OpenAI",
                e
            )
    
    async def health_check(self) -> ServiceStatus:
        """Check OpenAI service health."""
        try:
            # Simple embedding request to test connectivity
            await self.generate_embedding("health check", model="text-embedding-ada-002")
            return ServiceStatus.HEALTHY
        except CircuitBreakerError:
            return ServiceStatus.DOWN
        except Exception:
            return ServiceStatus.DEGRADED


class PineconeVectorStore(VectorStore):
    """Pinecone implementation with circuit breaker and retry logic."""
    
    def __init__(self):
        pinecone.init(
            api_key=settings.PINECONE_API_KEY,
            environment=settings.PINECONE_ENVIRONMENT
        )
        
        self.circuit_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60,
            success_threshold=2,
            timeout=30,
        )
        
        self.retry_config = RetryConfig(
            max_attempts=3,
            base_delay=2.0,
            max_delay=30.0,
        )
    
    @circuit_breaker("pinecone_upsert")
    @retry()
    async def upsert(
        self,
        vectors: List[Tuple[str, List[float], Dict[str, Any]]],
        namespace: Optional[str] = None,
        **kwargs
    ) -> None:
        """Upsert vectors to Pinecone index."""
        try:
            index_name = kwargs.get("index_name", "chatbot-embeddings")
            index = pinecone.Index(index_name)
            
            # Convert to Pinecone format
            pinecone_vectors = [
                {
                    "id": vector_id,
                    "values": vector,
                    "metadata": metadata
                }
                for vector_id, vector, metadata in vectors
            ]
            
            # Upsert in batches to avoid rate limits
            batch_size = 100
            for i in range(0, len(pinecone_vectors), batch_size):
                batch = pinecone_vectors[i:i + batch_size]
                
                # Run in thread pool since pinecone client is sync
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: index.upsert(vectors=batch, namespace=namespace)
                )
            
            logger.debug(
                "Vectors upserted successfully",
                count=len(vectors),
                namespace=namespace,
                index=index_name
            )
            
        except Exception as e:
            logger.error(
                "Pinecone upsert error",
                error=str(e),
                vector_count=len(vectors),
                namespace=namespace
            )
            raise VectorStoreError(
                f"Failed to upsert vectors: {str(e)}",
                "Pinecone",
                e
            )
    
    @circuit_breaker("pinecone_search")
    @retry()
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_criteria: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
        include_metadata: bool = True,
        **kwargs
    ) -> List[SearchResult]:
        """Search for similar vectors in Pinecone."""
        try:
            index_name = kwargs.get("index_name", "chatbot-embeddings")
            index = pinecone.Index(index_name)
            
            # Run in thread pool since pinecone client is sync
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: index.query(
                    vector=query_vector,
                    top_k=top_k,
                    filter=filter_criteria,
                    namespace=namespace,
                    include_metadata=include_metadata,
                    include_values=False
                )
            )
            
            results = []
            for match in response.matches:
                results.append(SearchResult(
                    id=match.id,
                    score=match.score,
                    metadata=match.metadata or {},
                    content=match.metadata.get("content", "") if match.metadata else ""
                ))
            
            logger.debug(
                "Vector search completed",
                result_count=len(results),
                top_k=top_k,
                namespace=namespace
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Pinecone search error",
                error=str(e),
                top_k=top_k,
                namespace=namespace
            )
            raise VectorStoreError(
                f"Failed to search vectors: {str(e)}",
                "Pinecone",
                e
            )
    
    @circuit_breaker("pinecone_delete")
    @retry()
    async def delete(
        self,
        ids: List[str],
        namespace: Optional[str] = None,
        **kwargs
    ) -> None:
        """Delete vectors from Pinecone index."""
        try:
            index_name = kwargs.get("index_name", "chatbot-embeddings")
            index = pinecone.Index(index_name)
            
            # Run in thread pool since pinecone client is sync
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: index.delete(ids=ids, namespace=namespace)
            )
            
            logger.debug(
                "Vectors deleted successfully",
                count=len(ids),
                namespace=namespace
            )
            
        except Exception as e:
            logger.error(
                "Pinecone delete error",
                error=str(e),
                id_count=len(ids),
                namespace=namespace
            )
            raise VectorStoreError(
                f"Failed to delete vectors: {str(e)}",
                "Pinecone",
                e
            )
    
    async def create_index(
        self,
        name: str,
        dimension: int,
        metric: str = "cosine",
        **kwargs
    ) -> None:
        """Create Pinecone index."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: pinecone.create_index(
                    name=name,
                    dimension=dimension,
                    metric=metric
                )
            )
            
            logger.info(
                "Pinecone index created",
                name=name,
                dimension=dimension,
                metric=metric
            )
            
        except Exception as e:
            logger.error(
                "Pinecone index creation error",
                error=str(e),
                name=name,
                dimension=dimension
            )
            raise VectorStoreError(
                f"Failed to create index: {str(e)}",
                "Pinecone",
                e
            )
    
    async def health_check(self) -> ServiceStatus:
        """Check Pinecone service health."""
        try:
            # List indexes to test connectivity
            await asyncio.get_event_loop().run_in_executor(
                None,
                pinecone.list_indexes
            )
            return ServiceStatus.HEALTHY
        except CircuitBreakerError:
            return ServiceStatus.DOWN
        except Exception:
            return ServiceStatus.DEGRADED


class S3FileStorage(FileStorage):
    """AWS S3 implementation with circuit breaker and retry logic."""
    
    def __init__(self):
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        
        self.circuit_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60,
            success_threshold=2,
            timeout=30,
            expected_exception=(ClientError, BotoCoreError),
        )
        
        self.retry_config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            retryable_exceptions=(ClientError, BotoCoreError),
        )
    
    @circuit_breaker("s3_upload")
    @retry()
    async def upload(
        self,
        file_content: bytes,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """Upload file to S3."""
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            if metadata:
                extra_args['Metadata'] = metadata
            
            # Upload in thread pool since boto3 is sync
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=file_content,
                    **extra_args
                )
            )
            
            # Return public URL
            url = f"https://{self.bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{key}"
            
            logger.debug(
                "File uploaded to S3",
                key=key,
                size=len(file_content),
                content_type=content_type
            )
            
            return url
            
        except (ClientError, BotoCoreError) as e:
            logger.error(
                "S3 upload error",
                error=str(e),
                key=key,
                size=len(file_content)
            )
            raise FileStorageError(
                f"Failed to upload file: {str(e)}",
                "S3",
                e
            )
    
    @circuit_breaker("s3_download")
    @retry()
    async def download(self, key: str, **kwargs) -> bytes:
        """Download file from S3."""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.get_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
            )
            
            content = response['Body'].read()
            
            logger.debug(
                "File downloaded from S3",
                key=key,
                size=len(content)
            )
            
            return content
            
        except (ClientError, BotoCoreError) as e:
            logger.error(
                "S3 download error",
                error=str(e),
                key=key
            )
            raise FileStorageError(
                f"Failed to download file: {str(e)}",
                "S3",
                e
            )
    
    @circuit_breaker("s3_delete")
    @retry()
    async def delete(self, key: str, **kwargs) -> None:
        """Delete file from S3."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.delete_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
            )
            
            logger.debug("File deleted from S3", key=key)
            
        except (ClientError, BotoCoreError) as e:
            logger.error(
                "S3 delete error",
                error=str(e),
                key=key
            )
            raise FileStorageError(
                f"Failed to delete file: {str(e)}",
                "S3",
                e
            )
    
    @circuit_breaker("s3_presigned_url")
    @retry()
    async def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
        method: str = "GET",
        **kwargs
    ) -> str:
        """Get presigned URL for S3 object."""
        try:
            operation = "get_object" if method == "GET" else "put_object"
            
            url = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.generate_presigned_url(
                    operation,
                    Params={'Bucket': self.bucket_name, 'Key': key},
                    ExpiresIn=expires_in
                )
            )
            
            logger.debug(
                "Presigned URL generated",
                key=key,
                expires_in=expires_in,
                method=method
            )
            
            return url
            
        except (ClientError, BotoCoreError) as e:
            logger.error(
                "S3 presigned URL error",
                error=str(e),
                key=key,
                method=method
            )
            raise FileStorageError(
                f"Failed to generate presigned URL: {str(e)}",
                "S3",
                e
            )
    
    async def health_check(self) -> ServiceStatus:
        """Check S3 service health."""
        try:
            # List bucket to test connectivity
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.head_bucket(Bucket=self.bucket_name)
            )
            return ServiceStatus.HEALTHY
        except CircuitBreakerError:
            return ServiceStatus.DOWN
        except Exception:
            return ServiceStatus.DEGRADED


class StripePaymentProcessor(PaymentProcessor):
    """Stripe implementation with circuit breaker and retry logic."""
    
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        
        self.circuit_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60,
            success_threshold=2,
            timeout=30,
            expected_exception=stripe.error.StripeError,
        )
        
        self.retry_config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            retryable_exceptions=(
                stripe.error.RateLimitError,
                stripe.error.APIConnectionError,
            ),
        )
    
    @circuit_breaker("stripe_payment_intent")
    @retry()
    async def create_payment_intent(
        self,
        amount: int,
        currency: str = "usd",
        customer_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> PaymentIntent:
        """Create Stripe payment intent."""
        try:
            intent_data = {
                "amount": amount,
                "currency": currency,
                "metadata": metadata or {},
            }
            
            if customer_id:
                intent_data["customer"] = customer_id
            
            intent_data.update(kwargs)
            
            # Run in thread pool since Stripe client is sync
            intent = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: stripe.PaymentIntent.create(**intent_data)
            )
            
            result = PaymentIntent(
                id=intent.id,
                amount=intent.amount,
                currency=intent.currency,
                status=intent.status,
                client_secret=intent.client_secret,
                metadata=intent.metadata or {}
            )
            
            logger.debug(
                "Payment intent created",
                intent_id=result.id,
                amount=result.amount,
                currency=result.currency
            )
            
            return result
            
        except stripe.error.StripeError as e:
            logger.error(
                "Stripe payment intent error",
                error=str(e),
                amount=amount,
                currency=currency
            )
            raise PaymentProcessorError(
                f"Failed to create payment intent: {str(e)}",
                "Stripe",
                e
            )
    
    @circuit_breaker("stripe_confirm_payment")
    @retry()
    async def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method: str,
        **kwargs
    ) -> PaymentIntent:
        """Confirm Stripe payment intent."""
        try:
            intent = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: stripe.PaymentIntent.confirm(
                    payment_intent_id,
                    payment_method=payment_method,
                    **kwargs
                )
            )
            
            result = PaymentIntent(
                id=intent.id,
                amount=intent.amount,
                currency=intent.currency,
                status=intent.status,
                client_secret=intent.client_secret,
                metadata=intent.metadata or {}
            )
            
            logger.debug(
                "Payment confirmed",
                intent_id=result.id,
                status=result.status
            )
            
            return result
            
        except stripe.error.StripeError as e:
            logger.error(
                "Stripe payment confirmation error",
                error=str(e),
                payment_intent_id=payment_intent_id
            )
            raise PaymentProcessorError(
                f"Failed to confirm payment: {str(e)}",
                "Stripe",
                e
            )
    
    @circuit_breaker("stripe_customer")
    @retry()
    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create Stripe customer."""
        try:
            customer_data = {
                "email": email,
                "metadata": metadata or {},
            }
            
            if name:
                customer_data["name"] = name
            
            customer_data.update(kwargs)
            
            customer = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: stripe.Customer.create(**customer_data)
            )
            
            result = {
                "id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "created": customer.created,
                "metadata": customer.metadata or {}
            }
            
            logger.debug(
                "Customer created",
                customer_id=result["id"],
                email=email
            )
            
            return result
            
        except stripe.error.StripeError as e:
            logger.error(
                "Stripe customer creation error",
                error=str(e),
                email=email
            )
            raise PaymentProcessorError(
                f"Failed to create customer: {str(e)}",
                "Stripe",
                e
            )
    
    @circuit_breaker("stripe_subscription")
    @retry()
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        metadata: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create Stripe subscription."""
        try:
            subscription_data = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "metadata": metadata or {},
            }
            
            subscription_data.update(kwargs)
            
            subscription = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: stripe.Subscription.create(**subscription_data)
            )
            
            result = {
                "id": subscription.id,
                "customer": subscription.customer,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "metadata": subscription.metadata or {}
            }
            
            logger.debug(
                "Subscription created",
                subscription_id=result["id"],
                customer_id=customer_id,
                price_id=price_id
            )
            
            return result
            
        except stripe.error.StripeError as e:
            logger.error(
                "Stripe subscription creation error",
                error=str(e),
                customer_id=customer_id,
                price_id=price_id
            )
            raise PaymentProcessorError(
                f"Failed to create subscription: {str(e)}",
                "Stripe",
                e
            )
    
    async def handle_webhook(
        self,
        payload: bytes,
        signature: str,
        **kwargs
    ) -> WebhookEvent:
        """Handle Stripe webhook event."""
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret
            )
            
            result = WebhookEvent(
                id=event["id"],
                type=event["type"],
                data=event["data"],
                created=datetime.fromtimestamp(event["created"]),
                livemode=event["livemode"]
            )
            
            logger.debug(
                "Webhook event received",
                event_id=result.id,
                event_type=result.type,
                livemode=result.livemode
            )
            
            return result
            
        except (stripe.error.SignatureVerificationError, ValueError) as e:
            logger.error(
                "Stripe webhook verification error",
                error=str(e)
            )
            raise PaymentProcessorError(
                f"Failed to verify webhook: {str(e)}",
                "Stripe",
                e
            )
    
    async def health_check(self) -> ServiceStatus:
        """Check Stripe service health."""
        try:
            # Retrieve account to test connectivity
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: stripe.Account.retrieve()
            )
            return ServiceStatus.HEALTHY
        except CircuitBreakerError:
            return ServiceStatus.DOWN
        except Exception:
            return ServiceStatus.DEGRADED