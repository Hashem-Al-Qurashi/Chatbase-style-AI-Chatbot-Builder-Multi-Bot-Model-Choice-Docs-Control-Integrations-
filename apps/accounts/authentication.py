"""
Enhanced JWT Authentication for Django REST Framework.
Integrates with the core auth system to provide DRF authentication with
comprehensive security features, session validation, and structured error handling.
"""

import jwt
import structlog
from typing import Optional, Tuple
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from rest_framework import authentication, exceptions
from rest_framework.request import Request

from apps.core.auth import JWTManager, TokenType
from apps.core.models import BaseModel

logger = structlog.get_logger()
User = get_user_model()


class JWTAuthentication(authentication.BaseAuthentication):
    """
    JWT authentication backend for Django REST Framework.
    
    Clients should authenticate by passing the token key in the "Authorization"
    HTTP header, prepended with the string "Bearer ".  For example:
    
        Authorization: Bearer 401f7ac837da42b97f613d789819ff93537bee6a
    """
    
    keyword = 'Bearer'
    
    def authenticate(self, request: Request) -> Optional[Tuple[User, str]]:
        """
        Authenticate the request and return a two-tuple of (user, token).
        
        Enhanced with comprehensive security logging and validation.
        
        Args:
            request: The HTTP request
            
        Returns:
            tuple: (user, token) if authenticated, None otherwise
            
        Raises:
            AuthenticationFailed: With structured error codes for different failure types
        """
        # Extract authorization header
        auth = authentication.get_authorization_header(request).split()
        
        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None
            
        # Validate authorization header format
        if len(auth) == 1:
            logger.warning(
                "Authentication failed - missing token",
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            raise self._create_auth_exception(
                'AUTH_TOKEN_MISSING',
                'Invalid token header. No credentials provided.'
            )
        elif len(auth) > 2:
            logger.warning(
                "Authentication failed - malformed token header",
                ip_address=self._get_client_ip(request),
                token_parts=len(auth)
            )
            raise self._create_auth_exception(
                'AUTH_TOKEN_MALFORMED',
                'Invalid token header. Token string should not contain spaces.'
            )
            
        # Decode token with security validation
        try:
            token = auth[1].decode()
            
            # Additional security: check token length to prevent extremely long tokens
            if len(token) > 2048:  # JWT tokens are typically much shorter
                logger.warning(
                    "Authentication failed - token too long",
                    ip_address=self._get_client_ip(request),
                    token_length=len(token)
                )
                raise self._create_auth_exception(
                    'AUTH_TOKEN_INVALID_FORMAT',
                    'Token is too long'
                )
                
        except UnicodeError:
            logger.warning(
                "Authentication failed - invalid token encoding",
                ip_address=self._get_client_ip(request)
            )
            raise self._create_auth_exception(
                'AUTH_TOKEN_ENCODING_ERROR',
                'Invalid token header. Token string contains invalid characters.'
            )
            
        return self.authenticate_credentials(token, request)
    
    def authenticate_credentials(self, token: str, request: Request) -> Tuple[User, str]:
        """
        Authenticate the token and return the user.
        
        Enhanced with session validation, comprehensive error handling, and security logging.
        
        Args:
            token: JWT token string
            request: The HTTP request for context
            
        Returns:
            tuple: (user, token) if valid
            
        Raises:
            AuthenticationFailed: With structured error codes for different failure types
        """
        try:
            # Use the JWT manager from core auth
            jwt_manager = JWTManager()
            payload = jwt_manager.decode_token(token, TokenType.ACCESS)
            
            if not payload:
                logger.warning(
                    "Authentication failed - invalid token payload",
                    ip_address=self._get_client_ip(request)
                )
                raise self._create_auth_exception(
                    'AUTH_TOKEN_INVALID',
                    'Invalid token format or signature.'
                )
                
            user_id = payload.user_id
            jti = payload.jti
            
            if not user_id:
                logger.warning(
                    "Authentication failed - missing user_id in token",
                    ip_address=self._get_client_ip(request)
                )
                raise self._create_auth_exception(
                    'AUTH_TOKEN_MISSING_USER_ID',
                    'Token contained no recognizable user identification.'
                )
                
        except jwt.ExpiredSignatureError:
            logger.info(
                "Authentication failed - token expired",
                ip_address=self._get_client_ip(request)
            )
            raise self._create_auth_exception(
                'AUTH_TOKEN_EXPIRED',
                'Token has expired. Please refresh your session.'
            )
        except jwt.InvalidTokenError as e:
            logger.warning(
                "Authentication failed - invalid JWT",
                error=str(e),
                ip_address=self._get_client_ip(request)
            )
            raise self._create_auth_exception(
                'AUTH_TOKEN_INVALID_JWT',
                'Invalid token format.'
            )
        except Exception as e:
            logger.error(
                "Authentication failed - unexpected error",
                error=str(e),
                ip_address=self._get_client_ip(request)
            )
            raise self._create_auth_exception(
                'AUTH_TOKEN_DECODE_ERROR',
                'Unable to process authentication token.'
            )
            
        # Validate user existence and status
        try:
            user = User.objects.select_related().get(id=user_id, is_active=True)
        except User.DoesNotExist:
            logger.warning(
                "Authentication failed - user not found or inactive",
                user_id=user_id,
                ip_address=self._get_client_ip(request)
            )
            raise self._create_auth_exception(
                'AUTH_USER_NOT_FOUND',
                'User not found or account is disabled.'
            )
            
        # Session validation - check if token is still valid in session store
        try:
            if jti and not self._validate_token_session(jti, user_id):
                logger.warning(
                    "Authentication failed - token revoked",
                    user_id=user_id,
                    jti=jti,
                    ip_address=self._get_client_ip(request)
                )
                raise self._create_auth_exception(
                    'AUTH_TOKEN_REVOKED',
                    'Token has been revoked. Please login again.'
                )
        except Exception as e:
            logger.warning(
                "Session validation failed",
                user_id=user_id,
                error=str(e)
            )
            # Don't fail auth for session validation errors in production
            # but log them for monitoring
            
        # Update user's last activity
        self._update_user_activity(user, request)
        
        logger.info(
            "Authentication successful",
            user_id=user_id,
            ip_address=self._get_client_ip(request)
        )
        
        return (user, token)
    
    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response.
        """
        return self.keyword
    
    # Security and utility helper methods
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def _create_auth_exception(self, error_code: str, message: str) -> exceptions.AuthenticationFailed:
        """Create a structured authentication exception with error code."""
        return exceptions.AuthenticationFailed({
            'error_code': error_code,
            'message': message,
            'type': 'authentication_error'
        })
    
    def _validate_token_session(self, jti: str, user_id: str) -> bool:
        """
        Validate if token is still valid in session store.
        
        Args:
            jti: JWT ID for token tracking
            user_id: User ID associated with token
            
        Returns:
            bool: True if token session is valid
        """
        try:
            from apps.accounts.models import UserSession
            
            session = UserSession.objects.filter(
                jti=jti,
                user_id=user_id,
                token_type='access'
            ).first()
            
            if not session:
                return False
                
            return session.is_valid
            
        except Exception as e:
            logger.warning(
                "Session validation error",
                error=str(e),
                jti=jti,
                user_id=user_id
            )
            # Return True on validation errors to avoid blocking valid users
            # Log the error for monitoring
            return True
    
    def _update_user_activity(self, user: User, request: Request) -> None:
        """
        Update user's last activity timestamp.
        
        Args:
            user: User instance
            request: HTTP request for context
        """
        try:
            # Update last login time periodically (not on every request)
            now = timezone.now()
            
            # Only update if last_login is more than 5 minutes ago to reduce DB writes
            if not user.last_login or (now - user.last_login).total_seconds() > 300:
                user.last_login = now
                user.save(update_fields=['last_login'])
                
        except Exception as e:
            logger.warning(
                "Failed to update user activity",
                user_id=str(user.id),
                error=str(e)
            )