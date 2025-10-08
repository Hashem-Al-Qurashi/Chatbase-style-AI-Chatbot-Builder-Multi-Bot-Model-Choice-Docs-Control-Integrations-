"""
Comprehensive error handling and resilience patterns.
Implements retry mechanisms, graceful degradation, and error recovery.
"""

import asyncio
import functools
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
from dataclasses import dataclass
from enum import Enum
import logging
import random

from django.core.cache import cache
from django.utils import timezone

from apps.core.circuit_breaker import CircuitBreaker
from apps.core.monitoring import metrics_collector, alert_manager, AlertLevel
from chatbot_saas.config import get_settings


settings = get_settings()
logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    NETWORK = "network"
    PROCESSING = "processing"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for errors."""
    error_id: str
    timestamp: str
    user_id: Optional[str]
    request_id: Optional[str]
    service: str
    operation: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Dict[str, Any]
    traceback: Optional[str]
    metadata: Dict[str, Any]


class SystemError(Exception):
    """Base system error with context."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.metadata = metadata or {}
        self.original_error = original_error
        self.timestamp = timezone.now()


class ValidationError(SystemError):
    """Validation error."""
    
    def __init__(self, message: str, field: str = None, **kwargs):
        super().__init__(message, category=ErrorCategory.VALIDATION, **kwargs)
        if field:
            self.details["field"] = field


class AuthenticationError(SystemError):
    """Authentication error."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.AUTHENTICATION, **kwargs)


class AuthorizationError(SystemError):
    """Authorization error."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.AUTHORIZATION, **kwargs)


class RateLimitError(SystemError):
    """Rate limit exceeded error."""
    
    def __init__(self, message: str, retry_after: int = None, **kwargs):
        super().__init__(message, category=ErrorCategory.RATE_LIMIT, **kwargs)
        if retry_after:
            self.details["retry_after"] = retry_after


class ExternalServiceError(SystemError):
    """External service error."""
    
    def __init__(self, message: str, service: str, **kwargs):
        super().__init__(message, category=ErrorCategory.EXTERNAL_SERVICE, **kwargs)
        self.details["service"] = service


class ProcessingError(SystemError):
    """Processing error."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.PROCESSING, **kwargs)


class RetryConfig:
    """Configuration for retry mechanisms."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        backoff_strategy: str = "exponential"  # linear, exponential, fixed
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.backoff_strategy = backoff_strategy


class RetryManager:
    """Manages retry logic with different strategies."""
    
    @staticmethod
    def calculate_delay(attempt: int, config: RetryConfig) -> float:
        """Calculate retry delay based on strategy."""
        if config.backoff_strategy == "fixed":
            delay = config.base_delay
        elif config.backoff_strategy == "linear":
            delay = config.base_delay * attempt
        elif config.backoff_strategy == "exponential":
            delay = config.base_delay * (config.exponential_base ** attempt)
        else:
            delay = config.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, config.max_delay)
        
        # Add jitter to prevent thundering herd
        if config.jitter:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    @staticmethod
    def should_retry(exception: Exception, attempt: int, config: RetryConfig) -> bool:
        """Determine if operation should be retried."""
        if attempt >= config.max_retries:
            return False
        
        # Don't retry validation errors
        if isinstance(exception, ValidationError):
            return False
        
        # Don't retry authentication/authorization errors
        if isinstance(exception, (AuthenticationError, AuthorizationError)):
            return False
        
        # Retry network and external service errors
        if isinstance(exception, (ExternalServiceError, ConnectionError, TimeoutError)):
            return True
        
        # Retry processing errors with lower probability
        if isinstance(exception, ProcessingError):
            return attempt < 2  # Only retry once for processing errors
        
        # Default: retry for most errors
        return True


def retry_on_failure(
    config: Optional[RetryConfig] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """Decorator for adding retry logic to functions."""
    if config is None:
        config = RetryConfig()
    
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if not RetryManager.should_retry(e, attempt, config):
                        break
                    
                    if attempt < config.max_retries:
                        delay = RetryManager.calculate_delay(attempt, config)
                        
                        logger.warning(
                            f"Function {func.__name__} failed (attempt {attempt + 1}), "
                            f"retrying in {delay:.2f}s: {str(e)}"
                        )
                        
                        if on_retry:
                            await on_retry(e, attempt, delay)
                        
                        await asyncio.sleep(delay)
                
                except Exception as e:
                    # Non-retryable exception
                    logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                    raise
            
            # All retries exhausted
            logger.error(f"All retries exhausted for {func.__name__}: {str(last_exception)}")
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if not RetryManager.should_retry(e, attempt, config):
                        break
                    
                    if attempt < config.max_retries:
                        delay = RetryManager.calculate_delay(attempt, config)
                        
                        logger.warning(
                            f"Function {func.__name__} failed (attempt {attempt + 1}), "
                            f"retrying in {delay:.2f}s: {str(e)}"
                        )
                        
                        if on_retry:
                            on_retry(e, attempt, delay)
                        
                        time.sleep(delay)
                
                except Exception as e:
                    logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                    raise
            
            logger.error(f"All retries exhausted for {func.__name__}: {str(last_exception)}")
            raise last_exception
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class FallbackManager:
    """Manages fallback strategies for graceful degradation."""
    
    @staticmethod
    def with_fallback(
        primary_func: Callable,
        fallback_func: Callable,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
        log_fallback: bool = True
    ):
        """Execute primary function with fallback on failure."""
        async def async_executor(*args, **kwargs):
            try:
                if asyncio.iscoroutinefunction(primary_func):
                    return await primary_func(*args, **kwargs)
                else:
                    return primary_func(*args, **kwargs)
                    
            except exceptions as e:
                if log_fallback:
                    logger.warning(
                        f"Primary function {primary_func.__name__} failed, "
                        f"using fallback: {str(e)}"
                    )
                
                if asyncio.iscoroutinefunction(fallback_func):
                    return await fallback_func(*args, **kwargs)
                else:
                    return fallback_func(*args, **kwargs)
        
        def sync_executor(*args, **kwargs):
            try:
                return primary_func(*args, **kwargs)
                
            except exceptions as e:
                if log_fallback:
                    logger.warning(
                        f"Primary function {primary_func.__name__} failed, "
                        f"using fallback: {str(e)}"
                    )
                
                return fallback_func(*args, **kwargs)
        
        # Return appropriate executor based on primary function type
        if asyncio.iscoroutinefunction(primary_func):
            return async_executor
        else:
            return sync_executor


class ErrorTracker:
    """Tracks and analyzes error patterns."""
    
    def __init__(self):
        self.error_window = 3600  # 1 hour
        self.error_threshold = 10  # errors per window
    
    def track_error(self, error_context: ErrorContext):
        """Track an error occurrence."""
        # Store error in cache with TTL
        cache_key = f"error:{error_context.error_id}"
        cache.set(cache_key, error_context, timeout=self.error_window)
        
        # Update error counters
        self._update_error_metrics(error_context)
        
        # Check for error patterns
        self._analyze_error_patterns(error_context)
        
        # Log error
        self._log_error(error_context)
    
    def _update_error_metrics(self, error_context: ErrorContext):
        """Update Prometheus error metrics."""
        metrics_collector.request_count.labels(
            method="error",
            endpoint=error_context.operation,
            status_code="500"
        ).inc()
    
    def _analyze_error_patterns(self, error_context: ErrorContext):
        """Analyze error patterns and trigger alerts if needed."""
        # Count recent errors of same type
        pattern_key = f"error_pattern:{error_context.category.value}:{error_context.service}"
        recent_errors = cache.get(pattern_key, 0) + 1
        cache.set(pattern_key, recent_errors, timeout=self.error_window)
        
        # Trigger alert if threshold exceeded
        if recent_errors >= self.error_threshold:
            self._trigger_error_pattern_alert(error_context, recent_errors)
    
    def _trigger_error_pattern_alert(self, error_context: ErrorContext, count: int):
        """Trigger alert for error pattern."""
        from apps.core.monitoring import Alert
        
        alert = Alert(
            id=f"error_pattern_{error_context.category.value}_{int(time.time())}",
            title=f"High error rate: {error_context.category.value}",
            description=f"Detected {count} {error_context.category.value} errors in {error_context.service}",
            severity=AlertSeverity.HIGH,
            service=error_context.service,
            status="firing",
            labels={
                "category": error_context.category.value,
                "service": error_context.service
            },
            annotations={
                "error_count": str(count),
                "time_window": str(self.error_window)
            },
            timestamp=timezone.now()
        )
        
        alert_manager._fire_alert(alert)
    
    def _log_error(self, error_context: ErrorContext):
        """Log error with appropriate level."""
        log_data = {
            "error_id": error_context.error_id,
            "category": error_context.category.value,
            "severity": error_context.severity.value,
            "service": error_context.service,
            "operation": error_context.operation,
            "user_id": error_context.user_id,
            "request_id": error_context.request_id,
            "details": error_context.details,
            "metadata": error_context.metadata
        }
        
        if error_context.severity == ErrorSeverity.CRITICAL:
            logger.critical(error_context.message, extra=log_data)
        elif error_context.severity == ErrorSeverity.HIGH:
            logger.error(error_context.message, extra=log_data)
        elif error_context.severity == ErrorSeverity.MEDIUM:
            logger.warning(error_context.message, extra=log_data)
        else:
            logger.info(error_context.message, extra=log_data)


class ErrorHandler:
    """Central error handling coordinator."""
    
    def __init__(self):
        self.error_tracker = ErrorTracker()
        self.circuit_breakers = {}
    
    def handle_error(
        self,
        error: Exception,
        service: str,
        operation: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """Handle an error with full context."""
        import uuid
        
        # Classify error
        category, severity = self._classify_error(error)
        
        # Create error context
        error_context = ErrorContext(
            error_id=str(uuid.uuid4()),
            timestamp=timezone.now().isoformat(),
            user_id=user_id,
            request_id=request_id,
            service=service,
            operation=operation,
            category=category,
            severity=severity,
            message=str(error),
            details=getattr(error, 'details', {}),
            traceback=traceback.format_exc(),
            metadata=additional_context or {}
        )
        
        # Track error
        self.error_tracker.track_error(error_context)
        
        # Update circuit breaker if applicable
        self._update_circuit_breaker(service, error)
        
        return error_context
    
    def _classify_error(self, error: Exception) -> Tuple[ErrorCategory, ErrorSeverity]:
        """Classify error by category and severity."""
        if isinstance(error, SystemError):
            return error.category, error.severity
        
        # Built-in exceptions
        if isinstance(error, (ValueError, TypeError)):
            return ErrorCategory.VALIDATION, ErrorSeverity.LOW
        
        if isinstance(error, PermissionError):
            return ErrorCategory.AUTHORIZATION, ErrorSeverity.MEDIUM
        
        if isinstance(error, ConnectionError):
            return ErrorCategory.NETWORK, ErrorSeverity.HIGH
        
        if isinstance(error, TimeoutError):
            return ErrorCategory.EXTERNAL_SERVICE, ErrorSeverity.MEDIUM
        
        if isinstance(error, MemoryError):
            return ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL
        
        # Default classification
        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM
    
    def _update_circuit_breaker(self, service: str, error: Exception):
        """Update circuit breaker state based on error."""
        if service not in self.circuit_breakers:
            self.circuit_breakers[service] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60,
                expected_exception=Exception
            )
        
        # Record failure
        circuit_breaker = self.circuit_breakers[service]
        try:
            with circuit_breaker:
                raise error
        except:
            pass  # Expected to fail
        
        # Update monitoring
        state_map = {"closed": 0, "open": 1, "half_open": 2}
        state_value = state_map.get(circuit_breaker.state, 0)
        metrics_collector.update_circuit_breaker_state(service, state_value)
    
    def get_circuit_breaker(self, service: str) -> CircuitBreaker:
        """Get circuit breaker for service."""
        if service not in self.circuit_breakers:
            self.circuit_breakers[service] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60,
                expected_exception=Exception
            )
        
        return self.circuit_breakers[service]


# Global error handler instance
error_handler = ErrorHandler()


def handle_exceptions(
    service: str,
    operation: str = None,
    reraise: bool = True,
    fallback_result: Any = None
):
    """Decorator for comprehensive error handling."""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_context = error_handler.handle_error(
                    error=e,
                    service=service,
                    operation=operation or func.__name__,
                    additional_context={"function": func.__name__, "args_count": len(args)}
                )
                
                if reraise:
                    raise
                else:
                    return fallback_result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_context = error_handler.handle_error(
                    error=e,
                    service=service,
                    operation=operation or func.__name__,
                    additional_context={"function": func.__name__, "args_count": len(args)}
                )
                
                if reraise:
                    raise
                else:
                    return fallback_result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Utility functions for graceful degradation
async def execute_with_timeout(
    coro_or_func: Union[Callable, Callable],
    timeout: float,
    fallback_result: Any = None,
    *args,
    **kwargs
) -> Any:
    """Execute function/coroutine with timeout and fallback."""
    try:
        if asyncio.iscoroutinefunction(coro_or_func):
            return await asyncio.wait_for(coro_or_func(*args, **kwargs), timeout=timeout)
        else:
            return await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, coro_or_func, *args, **kwargs),
                timeout=timeout
            )
    except asyncio.TimeoutError:
        logger.warning(f"Operation timed out after {timeout}s, using fallback")
        return fallback_result


def safe_execute(func: Callable, default_result: Any = None, log_errors: bool = True) -> Any:
    """Safely execute a function with error handling."""
    try:
        return func()
    except Exception as e:
        if log_errors:
            logger.warning(f"Safe execution failed: {str(e)}")
        return default_result