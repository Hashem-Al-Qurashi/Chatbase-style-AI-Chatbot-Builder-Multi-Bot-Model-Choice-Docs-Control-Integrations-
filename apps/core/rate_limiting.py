"""
Rate limiting for authentication endpoints with sliding window and adaptive limits.
Implements security measures against brute force attacks and abuse.
"""

import time
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
import json

from django.core.cache import cache
from django.http import HttpRequest
from django.utils import timezone
from django.conf import settings

from chatbot_saas.config import get_settings


app_settings = get_settings()


class RateLimitType(Enum):
    """Types of rate limits."""
    LOGIN_ATTEMPTS = "login_attempts"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"
    OAUTH_ATTEMPTS = "oauth_attempts"
    API_REQUESTS = "api_requests"
    REGISTRATION = "registration"


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    max_attempts: int
    window_seconds: int
    block_duration_seconds: int
    adaptive_scaling: bool = True
    max_block_duration: int = 3600  # 1 hour max block


@dataclass
class RateLimitStatus:
    """Current rate limit status."""
    attempts: int
    max_attempts: int
    window_start: float
    blocked_until: Optional[float]
    next_reset: float


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter with sliding window and progressive penalties.
    """
    
    # Default rate limit configurations
    DEFAULT_CONFIGS = {
        RateLimitType.LOGIN_ATTEMPTS: RateLimitConfig(
            max_attempts=5,
            window_seconds=300,  # 5 minutes
            block_duration_seconds=900,  # 15 minutes
            adaptive_scaling=True,
            max_block_duration=3600  # 1 hour
        ),
        RateLimitType.PASSWORD_RESET: RateLimitConfig(
            max_attempts=3,
            window_seconds=3600,  # 1 hour
            block_duration_seconds=1800,  # 30 minutes
            adaptive_scaling=True,
            max_block_duration=7200  # 2 hours
        ),
        RateLimitType.EMAIL_VERIFICATION: RateLimitConfig(
            max_attempts=5,
            window_seconds=3600,  # 1 hour
            block_duration_seconds=600,  # 10 minutes
            adaptive_scaling=False
        ),
        RateLimitType.OAUTH_ATTEMPTS: RateLimitConfig(
            max_attempts=10,
            window_seconds=300,  # 5 minutes
            block_duration_seconds=600,  # 10 minutes
            adaptive_scaling=True
        ),
        RateLimitType.API_REQUESTS: RateLimitConfig(
            max_attempts=100,
            window_seconds=60,  # 1 minute
            block_duration_seconds=300,  # 5 minutes
            adaptive_scaling=False
        ),
        RateLimitType.REGISTRATION: RateLimitConfig(
            max_attempts=3,
            window_seconds=3600,  # 1 hour
            block_duration_seconds=1800,  # 30 minutes
            adaptive_scaling=False
        )
    }
    
    def __init__(self):
        self.configs = self.DEFAULT_CONFIGS.copy()
    
    def _get_cache_key(self, limit_type: RateLimitType, identifier: str) -> str:
        """Generate cache key for rate limit tracking."""
        return f"rate_limit:{limit_type.value}:{identifier}"
    
    def _get_block_cache_key(self, limit_type: RateLimitType, identifier: str) -> str:
        """Generate cache key for block tracking."""
        return f"rate_limit_block:{limit_type.value}:{identifier}"
    
    def _get_attempt_history_key(self, limit_type: RateLimitType, identifier: str) -> str:
        """Generate cache key for attempt history."""
        return f"rate_limit_history:{limit_type.value}:{identifier}"
    
    def check_rate_limit(
        self,
        limit_type: RateLimitType,
        identifier: str
    ) -> RateLimitStatus:
        """
        Check current rate limit status.
        
        Args:
            limit_type: Type of rate limit
            identifier: Unique identifier (IP, user ID, etc.)
            
        Returns:
            RateLimitStatus: Current status
        """
        config = self.configs[limit_type]
        cache_key = self._get_cache_key(limit_type, identifier)
        block_key = self._get_block_cache_key(limit_type, identifier)
        
        now = time.time()
        
        # Check if currently blocked
        blocked_until = cache.get(block_key)
        if blocked_until and now < blocked_until:
            return RateLimitStatus(
                attempts=config.max_attempts,
                max_attempts=config.max_attempts,
                window_start=now - config.window_seconds,
                blocked_until=blocked_until,
                next_reset=blocked_until
            )
        
        # Get current attempt count
        attempts_data = cache.get(cache_key, {"count": 0, "window_start": now})
        attempts = attempts_data["count"]
        window_start = attempts_data["window_start"]
        
        # Reset window if expired
        if now - window_start > config.window_seconds:
            attempts = 0
            window_start = now
        
        next_reset = window_start + config.window_seconds
        
        return RateLimitStatus(
            attempts=attempts,
            max_attempts=config.max_attempts,
            window_start=window_start,
            blocked_until=None,
            next_reset=next_reset
        )
    
    def record_attempt(
        self,
        limit_type: RateLimitType,
        identifier: str,
        success: bool = False
    ) -> RateLimitStatus:
        """
        Record an attempt and update rate limit status.
        
        Args:
            limit_type: Type of rate limit
            identifier: Unique identifier
            success: Whether the attempt was successful
            
        Returns:
            RateLimitStatus: Updated status
        """
        config = self.configs[limit_type]
        cache_key = self._get_cache_key(limit_type, identifier)
        block_key = self._get_block_cache_key(limit_type, identifier)
        history_key = self._get_attempt_history_key(limit_type, identifier)
        
        now = time.time()
        
        # Get current status
        status = self.check_rate_limit(limit_type, identifier)
        
        # Don't record if currently blocked
        if status.blocked_until and now < status.blocked_until:
            return status
        
        # Reset attempts on successful authentication
        if success and limit_type in [RateLimitType.LOGIN_ATTEMPTS, RateLimitType.OAUTH_ATTEMPTS]:
            cache.delete(cache_key)
            cache.delete(block_key)
            cache.delete(history_key)
            return self.check_rate_limit(limit_type, identifier)
        
        # Increment attempt count
        new_attempts = status.attempts + 1
        
        # Update attempts in cache
        attempts_data = {
            "count": new_attempts,
            "window_start": status.window_start
        }
        cache.set(cache_key, attempts_data, timeout=config.window_seconds * 2)
        
        # Check if limit exceeded
        if new_attempts >= config.max_attempts:
            block_duration = self._calculate_block_duration(
                limit_type, identifier, config
            )
            blocked_until = now + block_duration
            
            # Set block
            cache.set(block_key, blocked_until, timeout=block_duration)
            
            # Record in attempt history for adaptive scaling
            if config.adaptive_scaling:
                self._record_block_history(history_key, now, block_duration)
            
            return RateLimitStatus(
                attempts=new_attempts,
                max_attempts=config.max_attempts,
                window_start=status.window_start,
                blocked_until=blocked_until,
                next_reset=blocked_until
            )
        
        return RateLimitStatus(
            attempts=new_attempts,
            max_attempts=config.max_attempts,
            window_start=status.window_start,
            blocked_until=None,
            next_reset=status.next_reset
        )
    
    def _calculate_block_duration(
        self,
        limit_type: RateLimitType,
        identifier: str,
        config: RateLimitConfig
    ) -> int:
        """Calculate block duration with adaptive scaling."""
        base_duration = config.block_duration_seconds
        
        if not config.adaptive_scaling:
            return base_duration
        
        # Get block history for adaptive scaling
        history_key = self._get_attempt_history_key(limit_type, identifier)
        history = cache.get(history_key, [])
        
        # Count recent blocks (last 24 hours)
        now = time.time()
        recent_blocks = [
            block for block in history
            if now - block["timestamp"] < 86400  # 24 hours
        ]
        
        # Progressive penalty: each recent block doubles the duration
        multiplier = 2 ** len(recent_blocks)
        duration = min(base_duration * multiplier, config.max_block_duration)
        
        return int(duration)
    
    def _record_block_history(
        self,
        history_key: str,
        timestamp: float,
        duration: int
    ) -> None:
        """Record block in history for adaptive scaling."""
        history = cache.get(history_key, [])
        
        # Add new block
        history.append({
            "timestamp": timestamp,
            "duration": duration
        })
        
        # Keep only last 10 blocks and last 7 days
        cutoff = timestamp - 604800  # 7 days
        history = [
            block for block in history[-10:]
            if block["timestamp"] > cutoff
        ]
        
        # Store updated history
        cache.set(history_key, history, timeout=604800)  # 7 days
    
    def is_blocked(self, limit_type: RateLimitType, identifier: str) -> bool:
        """
        Check if identifier is currently blocked.
        
        Args:
            limit_type: Type of rate limit
            identifier: Unique identifier
            
        Returns:
            bool: True if blocked
        """
        status = self.check_rate_limit(limit_type, identifier)
        return status.blocked_until is not None and time.time() < status.blocked_until
    
    def reset_rate_limit(self, limit_type: RateLimitType, identifier: str) -> None:
        """
        Reset rate limit for identifier (admin function).
        
        Args:
            limit_type: Type of rate limit
            identifier: Unique identifier
        """
        cache_key = self._get_cache_key(limit_type, identifier)
        block_key = self._get_block_cache_key(limit_type, identifier)
        
        cache.delete(cache_key)
        cache.delete(block_key)


class RequestIdentifier:
    """Extract identifiers from HTTP requests for rate limiting."""
    
    @staticmethod
    def get_ip_address(request: HttpRequest) -> str:
        """
        Get client IP address from request.
        
        Args:
            request: HTTP request
            
        Returns:
            str: Client IP address
        """
        # Check for forwarded IPs (proxy/load balancer)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take first IP if multiple
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        
        return ip
    
    @staticmethod
    def get_user_agent(request: HttpRequest) -> str:
        """
        Get user agent from request.
        
        Args:
            request: HTTP request
            
        Returns:
            str: User agent string
        """
        return request.META.get('HTTP_USER_AGENT', '')
    
    @staticmethod
    def get_fingerprint(request: HttpRequest) -> str:
        """
        Generate device fingerprint from request.
        
        Args:
            request: HTTP request
            
        Returns:
            str: Device fingerprint
        """
        import hashlib
        
        components = [
            RequestIdentifier.get_ip_address(request),
            RequestIdentifier.get_user_agent(request),
            request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
            request.META.get('HTTP_ACCEPT_ENCODING', ''),
        ]
        
        fingerprint_data = '|'.join(components)
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]


# Global rate limiter instance
rate_limiter = AdaptiveRateLimiter()


def rate_limit_decorator(limit_type: RateLimitType, identifier_func=None):
    """
    Decorator for rate limiting views.
    
    Args:
        limit_type: Type of rate limit to apply
        identifier_func: Function to extract identifier from request
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            from django.http import JsonResponse
            
            # Get identifier
            if identifier_func:
                identifier = identifier_func(request)
            else:
                identifier = RequestIdentifier.get_ip_address(request)
            
            # Check rate limit
            if rate_limiter.is_blocked(limit_type, identifier):
                status = rate_limiter.check_rate_limit(limit_type, identifier)
                return JsonResponse({
                    "error": "Rate limit exceeded",
                    "blocked_until": status.blocked_until,
                    "retry_after": int(status.blocked_until - time.time()) if status.blocked_until else 0
                }, status=429)
            
            # Record attempt
            response = view_func(request, *args, **kwargs)
            
            # Record success/failure based on response status
            success = 200 <= response.status_code < 300
            rate_limiter.record_attempt(limit_type, identifier, success=success)
            
            return response
        
        return wrapper
    return decorator