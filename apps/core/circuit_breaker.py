"""
Circuit breaker implementation for external service resilience.
Prevents cascading failures and provides fallback mechanisms.
"""

import time
import asyncio
from typing import Callable, Any, Optional, Type
from enum import Enum
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Circuit is open, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    expected_exception: Type[Exception] = Exception
    success_threshold: int = 2  # successes needed to close from half-open


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    
    Implements the circuit breaker pattern to prevent cascading failures
    when external services are down or responding slowly.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open
            expected_exception: Exception type that counts as failure
            success_threshold: Successes needed to close from half-open
        """
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            success_threshold=success_threshold
        )
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        
        self.logger = structlog.get_logger().bind(component="CircuitBreaker")
        
        self.logger.info(
            "Circuit breaker initialized",
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception.__name__
        )
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Original exception if function fails
        """
        # Check if circuit should transition states
        self._check_state_transition()
        
        # Reject calls if circuit is open
        if self.state == CircuitBreakerState.OPEN:
            self.logger.warning(
                "Circuit breaker is open, rejecting call",
                failure_count=self.failure_count,
                last_failure_time=self.last_failure_time
            )
            raise CircuitBreakerError("Circuit breaker is open")
        
        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Record success
            self._record_success()
            
            return result
            
        except self.config.expected_exception as e:
            # Record failure for expected exceptions
            self._record_failure()
            self.logger.warning(
                "Circuit breaker recorded failure",
                error=str(e),
                error_type=type(e).__name__,
                failure_count=self.failure_count,
                state=self.state.value
            )
            raise
        
        except Exception as e:
            # Don't count unexpected exceptions as failures
            self.logger.error(
                "Unexpected exception in circuit breaker",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def _check_state_transition(self) -> None:
        """Check if circuit breaker should transition states."""
        current_time = time.time()
        
        if self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if current_time - self.last_failure_time >= self.config.recovery_timeout:
                self._transition_to_half_open()
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Half-open state is handled by success/failure recording
            pass
    
    def _record_success(self) -> None:
        """Record a successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            
            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            if self.failure_count > 0:
                self.failure_count = 0
                self.logger.info(
                    "Circuit breaker failure count reset",
                    state=self.state.value
                )
    
    def _record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self._transition_to_open()
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Any failure in half-open goes back to open
            self._transition_to_open()
    
    def _transition_to_open(self) -> None:
        """Transition to open state."""
        previous_state = self.state
        self.state = CircuitBreakerState.OPEN
        self.success_count = 0
        
        self.logger.warning(
            "Circuit breaker opened",
            previous_state=previous_state.value,
            failure_count=self.failure_count,
            failure_threshold=self.config.failure_threshold
        )
    
    def _transition_to_half_open(self) -> None:
        """Transition to half-open state."""
        previous_state = self.state
        self.state = CircuitBreakerState.HALF_OPEN
        self.success_count = 0
        
        self.logger.info(
            "Circuit breaker half-opened",
            previous_state=previous_state.value,
            recovery_timeout=self.config.recovery_timeout
        )
    
    def _transition_to_closed(self) -> None:
        """Transition to closed state."""
        previous_state = self.state
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        
        self.logger.info(
            "Circuit breaker closed",
            previous_state=previous_state.value,
            success_threshold=self.config.success_threshold
        )
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "expected_exception": self.config.expected_exception.__name__,
            }
        }
    
    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        
        self.logger.info("Circuit breaker manually reset")
    
    def force_open(self) -> None:
        """Force circuit breaker to open state."""
        self.state = CircuitBreakerState.OPEN
        self.last_failure_time = time.time()
        
        self.logger.warning("Circuit breaker manually opened")


class AsyncCircuitBreaker(CircuitBreaker):
    """
    Async-specific circuit breaker with additional features.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize async circuit breaker."""
        super().__init__(*args, **kwargs)
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute async function with circuit breaker protection.
        
        Uses locks to ensure thread-safety in async environment.
        """
        async with self._lock:
            return await super().call(func, *args, **kwargs)