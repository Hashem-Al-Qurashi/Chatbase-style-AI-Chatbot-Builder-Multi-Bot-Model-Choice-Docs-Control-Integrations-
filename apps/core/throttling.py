"""
Advanced Rate Limiting and Throttling for Django REST Framework.
Implements endpoint-specific limits, plan-based throttling, and progressive penalties.
"""

import structlog
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from rest_framework.throttling import BaseThrottle
from rest_framework.request import Request
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.core.rate_limiting import RateLimitType, AdaptiveRateLimiter

logger = structlog.get_logger()
User = get_user_model()


class EndpointSpecificThrottle(BaseThrottle):
    """
    Custom throttle class that implements endpoint-specific rate limiting
    with plan-based limits and progressive penalties.
    """
    
    # Default rate limits per endpoint (requests per hour)
    ENDPOINT_LIMITS = {
        # Authentication endpoints
        '/api/v1/auth/login/': {
            'free': 20,
            'pro': 50, 
            'enterprise': 100,
            'anonymous': 10
        },
        '/api/v1/auth/register/': {
            'free': 5,
            'pro': 10,
            'enterprise': 20,
            'anonymous': 3
        },
        '/api/v1/auth/oauth2/authorize/': {
            'free': 10,
            'pro': 25,
            'enterprise': 50,
            'anonymous': 5
        },
        
        # API endpoints
        '/api/v1/chatbots/': {
            'free': 50,
            'pro': 200,
            'enterprise': 1000,
            'anonymous': 0  # No anonymous access
        },
        '/api/v1/conversations/': {
            'free': 100,
            'pro': 500,
            'enterprise': 2000,
            'anonymous': 0
        },
        
        # Chat endpoints (public)
        '/api/v1/chat/': {
            'free': 200,
            'pro': 1000,
            'enterprise': 5000,
            'anonymous': 50  # Limited anonymous chat
        },
        
        # Default limits for unspecified endpoints
        'default': {
            'free': 100,
            'pro': 500,
            'enterprise': 2000,
            'anonymous': 20
        }
    }
    
    def __init__(self):
        super().__init__()
        self.rate_limiter = AdaptiveRateLimiter()
    
    def allow_request(self, request: Request, view: "APIView") -> bool:
        """
        Determine if the request should be allowed based on rate limits.
        
        Args:
            request: The HTTP request
            view: The API view being accessed
            
        Returns:
            bool: True if request is allowed, False if rate limited
        """
        # Get request identifiers
        user_id = self._get_user_id(request)
        ip_address = self._get_client_ip(request)
        endpoint = self._get_endpoint_key(request)
        user_plan = self._get_user_plan(request)
        
        # Create composite identifier
        identifier = f"{user_id or 'anon'}:{ip_address}"
        
        # Check endpoint-specific rate limit
        if not self._check_endpoint_rate_limit(request, endpoint, user_plan, identifier):
            logger.warning(
                "Request rate limited - endpoint limit exceeded",
                user_id=user_id,
                ip_address=ip_address,
                endpoint=endpoint,
                user_plan=user_plan
            )
            return False
        
        # Check progressive penalty system
        if not self._check_progressive_penalties(request, identifier):
            logger.warning(
                "Request rate limited - progressive penalty applied",
                user_id=user_id,
                ip_address=ip_address
            )
            return False
        
        # Record successful request
        self._record_request(request, endpoint, user_plan, identifier)
        
        return True
    
    def wait(self) -> Optional[float]:
        """
        Return the recommended next request time in seconds.
        """
        # Return the time until the rate limit resets
        return getattr(self, '_wait_time', 60.0)
    
    def _get_user_id(self, request: Request) -> Optional[str]:
        """Get user ID from authenticated user."""
        if request.user and request.user.is_authenticated:
            return str(request.user.id)
        return None
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def _get_endpoint_key(self, request: Request) -> str:
        """
        Generate endpoint key for rate limiting.
        Groups similar endpoints together.
        """
        path = request.path
        
        # Normalize paths with IDs to generic patterns
        import re
        
        # Replace UUIDs with placeholder
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/', '/{id}/', path)
        
        # Replace numeric IDs with placeholder  
        path = re.sub(r'/\d+/', '/{id}/', path)
        
        return path
    
    def _get_user_plan(self, request: Request) -> str:
        """Get user's subscription plan."""
        if request.user and request.user.is_authenticated:
            return getattr(request.user, 'plan_tier', 'free')
        return 'anonymous'
    
    def _check_endpoint_rate_limit(
        self, 
        request: Request, 
        endpoint: str, 
        user_plan: str, 
        identifier: str
    ) -> bool:
        """
        Check endpoint-specific rate limit.
        
        Args:
            request: HTTP request
            endpoint: Normalized endpoint path
            user_plan: User's subscription plan
            identifier: Unique request identifier
            
        Returns:
            bool: True if within limits, False if rate limited
        """
        # Get rate limit for this endpoint and plan
        endpoint_limits = self.ENDPOINT_LIMITS.get(endpoint, self.ENDPOINT_LIMITS['default'])
        max_requests = endpoint_limits.get(user_plan, endpoint_limits.get('free', 100))
        
        # Anonymous users with 0 limit are blocked
        if max_requests == 0:
            return False
        
        # Cache key for this endpoint and user
        cache_key = f"endpoint_throttle:{endpoint}:{identifier}"
        
        # Get current request count and window
        now = datetime.now()
        window_start = now - timedelta(hours=1)  # 1-hour sliding window
        
        request_data = cache.get(cache_key, {
            'requests': [],
            'count': 0
        })
        
        # Clean old requests outside the window
        recent_requests = [
            req_time for req_time in request_data.get('requests', [])
            if datetime.fromisoformat(req_time) > window_start
        ]
        
        # Check if limit exceeded
        if len(recent_requests) >= max_requests:
            # Set wait time for throttle response
            oldest_request = min(recent_requests)
            self._wait_time = (datetime.fromisoformat(oldest_request) + timedelta(hours=1) - now).total_seconds()
            return False
        
        return True
    
    def _check_progressive_penalties(self, request: Request, identifier: str) -> bool:
        """
        Check progressive penalty system for repeat offenders.
        
        Args:
            request: HTTP request
            identifier: Unique request identifier
            
        Returns:
            bool: True if no penalties apply, False if blocked
        """
        penalty_key = f"progressive_penalty:{identifier}"
        penalty_data = cache.get(penalty_key, {
            'violations': 0,
            'last_violation': None,
            'penalty_until': None
        })
        
        # Check if currently under penalty
        if penalty_data.get('penalty_until'):
            penalty_until = datetime.fromisoformat(penalty_data['penalty_until'])
            if datetime.now() < penalty_until:
                return False
        
        return True
    
    def _record_request(
        self, 
        request: Request, 
        endpoint: str, 
        user_plan: str, 
        identifier: str
    ) -> None:
        """
        Record successful request for rate limiting.
        
        Args:
            request: HTTP request
            endpoint: Normalized endpoint path
            user_plan: User's subscription plan
            identifier: Unique request identifier
        """
        cache_key = f"endpoint_throttle:{endpoint}:{identifier}"
        now = datetime.now()
        
        # Get current data
        request_data = cache.get(cache_key, {
            'requests': [],
            'count': 0
        })
        
        # Add current request
        request_data['requests'].append(now.isoformat())
        request_data['count'] = len(request_data['requests'])
        
        # Clean old requests (keep only last hour)
        window_start = now - timedelta(hours=1)
        request_data['requests'] = [
            req_time for req_time in request_data['requests']
            if datetime.fromisoformat(req_time) > window_start
        ]
        
        # Cache for 2 hours (longer than window for safety)
        cache.set(cache_key, request_data, timeout=7200)
    
    def _apply_progressive_penalty(self, identifier: str, violation_type: str) -> None:
        """
        Apply progressive penalty for rate limit violations.
        
        Args:
            identifier: Unique request identifier
            violation_type: Type of violation that occurred
        """
        penalty_key = f"progressive_penalty:{identifier}"
        penalty_data = cache.get(penalty_key, {
            'violations': 0,
            'last_violation': None,
            'penalty_until': None
        })
        
        # Increment violation count
        penalty_data['violations'] += 1
        penalty_data['last_violation'] = datetime.now().isoformat()
        
        # Calculate penalty duration (exponential backoff)
        base_penalty = 300  # 5 minutes
        penalty_duration = min(
            base_penalty * (2 ** (penalty_data['violations'] - 1)),
            3600 * 24  # Max 24 hours
        )
        
        penalty_until = datetime.now() + timedelta(seconds=penalty_duration)
        penalty_data['penalty_until'] = penalty_until.isoformat()
        
        # Cache penalty for the duration + buffer
        cache.set(penalty_key, penalty_data, timeout=penalty_duration + 3600)
        
        logger.warning(
            "Progressive penalty applied",
            identifier=identifier,
            violation_type=violation_type,
            violations=penalty_data['violations'],
            penalty_duration=penalty_duration,
            penalty_until=penalty_until.isoformat()
        )


class PlanBasedUserThrottle(BaseThrottle):
    """
    User-specific throttle that adjusts limits based on subscription plan.
    """
    
    # Base limits per plan (requests per hour)
    PLAN_LIMITS = {
        'free': 1000,
        'pro': 5000,
        'enterprise': 20000
    }
    
    def allow_request(self, request: Request, view: "APIView") -> bool:
        """Allow request based on user's plan limits."""
        if not request.user or not request.user.is_authenticated:
            return True  # Let EndpointSpecificThrottle handle anonymous
        
        user_plan = getattr(request.user, 'plan_tier', 'free')
        max_requests = self.PLAN_LIMITS.get(user_plan, self.PLAN_LIMITS['free'])
        
        cache_key = f"user_throttle:{request.user.id}"
        
        # Use sliding window approach
        now = datetime.now()
        window_start = now - timedelta(hours=1)
        
        request_data = cache.get(cache_key, {'requests': []})
        
        # Clean old requests
        recent_requests = [
            req_time for req_time in request_data['requests']
            if datetime.fromisoformat(req_time) > window_start
        ]
        
        # Check limit
        if len(recent_requests) >= max_requests:
            logger.info(
                "User rate limited by plan",
                user_id=str(request.user.id),
                plan=user_plan,
                limit=max_requests
            )
            return False
        
        # Record request
        recent_requests.append(now.isoformat())
        cache.set(cache_key, {'requests': recent_requests}, timeout=7200)
        
        return True
    
    def wait(self) -> Optional[float]:
        """Return wait time in seconds."""
        return 3600.0  # 1 hour


class AbuseDetectionThrottle(BaseThrottle):
    """
    Throttle that detects and blocks abusive behavior patterns.
    """
    
    def allow_request(self, request: Request, view: "APIView") -> bool:
        """Detect and block abusive patterns."""
        ip_address = self._get_client_ip(request)
        
        # Check for rapid-fire requests (more than 10 per minute)
        rapid_fire_key = f"rapid_fire:{ip_address}"
        now = datetime.now()
        
        request_times = cache.get(rapid_fire_key, [])
        
        # Clean requests older than 1 minute
        minute_ago = now - timedelta(minutes=1)
        recent_requests = [
            req_time for req_time in request_times
            if datetime.fromisoformat(req_time) > minute_ago
        ]
        
        if len(recent_requests) > 10:
            logger.warning(
                "Abuse detected - rapid fire requests",
                ip_address=ip_address,
                requests_per_minute=len(recent_requests)
            )
            return False
        
        # Record this request
        recent_requests.append(now.isoformat())
        cache.set(rapid_fire_key, recent_requests, timeout=60)
        
        return True
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def wait(self) -> Optional[float]:
        """Return wait time."""
        return 60.0  # 1 minute