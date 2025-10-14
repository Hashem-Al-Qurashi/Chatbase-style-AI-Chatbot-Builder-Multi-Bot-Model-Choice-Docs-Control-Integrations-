"""
JWT Authentication system with OAuth2 integration.
Implements secure token handling, refresh tokens, and Google OAuth2.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
from enum import Enum

import jwt
import bcrypt
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.cache import cache
from django.core.exceptions import ValidationError

from chatbot_saas.config import get_settings


settings = get_settings()


class TokenType(Enum):
    """Token types for JWT authentication."""
    ACCESS = "access"
    REFRESH = "refresh"
    RESET_PASSWORD = "reset_password"
    VERIFY_EMAIL = "verify_email"


@dataclass
class TokenPayload:
    """JWT token payload structure."""
    user_id: str
    token_type: TokenType
    email: str
    exp: datetime
    iat: datetime
    jti: str  # JWT ID for revocation
    scopes: List[str] = None


@dataclass
class AuthResult:
    """Authentication result with tokens and user data."""
    access_token: str
    refresh_token: str
    user_data: Dict[str, Any]
    expires_in: int


class PasswordSecurity:
    """Secure password handling utilities."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt with proper salt.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        # Use bcrypt with 12 rounds (good balance of security and performance)
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            password: Plain text password
            hashed_password: Stored hash
            
        Returns:
            bool: True if password matches
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if len(password) > 128:
            errors.append("Password must be less than 128 characters")
        
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        # Check for common patterns (only very obvious ones)
        common_patterns = ["password", "admin", "qwerty", "123456"]
        if any(pattern in password.lower() for pattern in common_patterns):
            errors.append("Password contains common patterns")
        
        return len(errors) == 0, errors


class JWTManager:
    """JWT token management with secure practices."""
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_lifetime = timedelta(seconds=settings.JWT_ACCESS_TOKEN_LIFETIME)
        self.refresh_token_lifetime = timedelta(seconds=settings.JWT_REFRESH_TOKEN_LIFETIME)
    
    def generate_tokens(self, user) -> AuthResult:
        """
        Generate access and refresh tokens from user object.
        
        Args:
            user: User instance (Django User model)
            
        Returns:
            AuthResult: Complete authentication result with tokens and user data
        """
        now = timezone.now()
        scopes = ["read", "write"]  # Default scopes
        
        # Extract user data
        user_id = str(user.id)
        email = user.email
        
        # Generate access token
        access_payload = {
            "user_id": user_id,
            "email": email,
            "token_type": TokenType.ACCESS.value,
            "exp": now + self.access_token_lifetime,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "scopes": scopes
        }
        
        access_token = jwt.encode(
            access_payload,
            self.secret_key,
            algorithm=self.algorithm
        )
        
        # Generate refresh token
        refresh_payload = {
            "user_id": user_id,
            "email": email,
            "token_type": TokenType.REFRESH.value,
            "exp": now + self.refresh_token_lifetime,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "scopes": scopes
        }
        
        refresh_token = jwt.encode(
            refresh_payload,
            self.secret_key,
            algorithm=self.algorithm
        )
        
        # Prepare user data (excluding sensitive information)
        user_data = {
            "id": user.id,
            "email": user.email,
            "first_name": getattr(user, 'first_name', ''),
            "last_name": getattr(user, 'last_name', ''),
            "is_active": user.is_active,
            "date_joined": user.created_at.isoformat() if hasattr(user, 'created_at') else None
        }
        
        return AuthResult(
            access_token=access_token,
            refresh_token=refresh_token,
            user_data=user_data,
            expires_in=int(self.access_token_lifetime.total_seconds())
        )
    
    def decode_token(self, token: str, token_type: TokenType) -> Optional[TokenPayload]:
        """
        Decode and validate JWT token (as specified in DEVELOPMENT_STRATEGY.md).
        
        Args:
            token: JWT token to decode
            token_type: Expected token type
            
        Returns:
            Optional[TokenPayload]: Decoded payload or None if invalid
        """
        return self.verify_token(token, token_type)
    
    def verify_token(self, token: str, expected_type: TokenType) -> Optional[TokenPayload]:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token to verify
            expected_type: Expected token type
            
        Returns:
            Optional[TokenPayload]: Decoded payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Verify token type
            if payload.get("token_type") != expected_type.value:
                return None
            
            # Check if token is revoked
            jti = payload.get("jti")
            if self.is_token_revoked(jti):
                return None
            
            return TokenPayload(
                user_id=payload["user_id"],
                token_type=TokenType(payload["token_type"]),
                email=payload["email"],
                exp=datetime.fromtimestamp(payload["exp"]),
                iat=datetime.fromtimestamp(payload["iat"]),
                jti=jti,
                scopes=payload.get("scopes", [])
            )
            
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError, ValueError):
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """
        Generate new access token from refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Optional[str]: New access token or None if refresh token invalid
        """
        payload = self.verify_token(refresh_token, TokenType.REFRESH)
        if not payload:
            return None
        
        # Generate new access token
        now = timezone.now()
        access_payload = {
            "user_id": payload.user_id,
            "email": payload.email,
            "token_type": TokenType.ACCESS.value,
            "exp": now + self.access_token_lifetime,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "scopes": payload.scopes
        }
        
        return jwt.encode(
            access_payload,
            self.secret_key,
            algorithm=self.algorithm
        )
    
    def revoke_token(self, jti: str, expires_at: Optional[datetime] = None) -> bool:
        """
        Revoke token by adding JTI to blacklist.
        
        Args:
            jti: JWT ID to revoke
            expires_at: When to remove from blacklist (token expiry)
            
        Returns:
            bool: True if successfully revoked
        """
        try:
            if not expires_at:
                expires_at = timezone.now() + self.refresh_token_lifetime
            
            # Calculate timeout for cache entry
            timeout = int((expires_at - timezone.now()).total_seconds())
            if timeout > 0:
                cache.set(f"revoked_token:{jti}", True, timeout=timeout)
                return True
            return False
        except Exception:
            return False
    
    def is_token_revoked(self, jti: str) -> bool:
        """
        Check if token is revoked.
        
        Args:
            jti: JWT ID to check
            
        Returns:
            bool: True if token is revoked
        """
        return cache.get(f"revoked_token:{jti}", False)
    
    def generate_special_token(
        self,
        user_id: str,
        email: str,
        token_type: TokenType,
        expires_in: timedelta
    ) -> str:
        """
        Generate special purpose token (password reset, email verification).
        
        Args:
            user_id: User identifier
            email: User email
            token_type: Special token type
            expires_in: Token lifetime
            
        Returns:
            str: Special purpose token
        """
        now = timezone.now()
        payload = {
            "user_id": user_id,
            "email": email,
            "token_type": token_type.value,
            "exp": now + expires_in,
            "iat": now,
            "jti": str(uuid.uuid4())
        }
        
        return jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm
        )


class SessionManager:
    """Manage user sessions with security features."""
    
    def __init__(self):
        self.session_timeout = timedelta(hours=24)
        self.max_sessions_per_user = 5
    
    def create_session(self, user, device_info: Dict[str, str]):
        """
        Create new user session (as specified in DEVELOPMENT_STRATEGY.md).
        
        Args:
            user: User instance (Django User model)
            device_info: Device/browser information
            
        Returns:
            UserSession: Created session instance
        """
        # Import here to avoid circular imports
        from apps.accounts.models import UserSession
        
        session_id = str(uuid.uuid4())
        
        # Create database session record
        session = UserSession.objects.create(
            user=user,
            jti=session_id,
            token_type='session',
            ip_address=device_info.get('ip_address'),
            user_agent=device_info.get('user_agent', ''),
            expires_at=timezone.now() + self.session_timeout,
            metadata=device_info
        )
        
        # Store session in cache for fast lookup
        session_data = {
            "user_id": str(user.id),
            "device_info": device_info,
            "created_at": timezone.now().isoformat(),
            "last_activity": timezone.now().isoformat(),
            "session_db_id": session.id
        }
        
        timeout = int(self.session_timeout.total_seconds())
        cache.set(f"session:{session_id}", session_data, timeout=timeout)
        
        # Track user sessions for limit enforcement
        self._track_user_session(str(user.id), session_id)
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Optional[Dict[str, Any]]: Session data or None if not found
        """
        return cache.get(f"session:{session_id}")
    
    def update_session_activity(self, session_id: str) -> None:
        """
        Update session last activity timestamp.
        
        Args:
            session_id: Session identifier
        """
        session_data = self.get_session(session_id)
        if session_data:
            session_data["last_activity"] = timezone.now().isoformat()
            timeout = int(self.session_timeout.total_seconds())
            cache.set(f"session:{session_id}", session_data, timeout=timeout)
    
    def revoke_session(self, session_id: str) -> None:
        """
        Revoke specific session.
        
        Args:
            session_id: Session identifier
        """
        session_data = self.get_session(session_id)
        if session_data:
            user_id = session_data["user_id"]
            cache.delete(f"session:{session_id}")
            self._remove_user_session(user_id, session_id)
    
    def revoke_all_user_sessions(self, user_id: str) -> None:
        """
        Revoke all sessions for a user.
        
        Args:
            user_id: User identifier
        """
        session_ids = cache.get(f"user_sessions:{user_id}", [])
        for session_id in session_ids:
            cache.delete(f"session:{session_id}")
        cache.delete(f"user_sessions:{user_id}")
    
    def _track_user_session(self, user_id: str, session_id: str) -> None:
        """Track session for user and enforce limits."""
        session_ids = cache.get(f"user_sessions:{user_id}", [])
        session_ids.append(session_id)
        
        # Enforce session limit
        if len(session_ids) > self.max_sessions_per_user:
            # Remove oldest session
            oldest_session = session_ids.pop(0)
            cache.delete(f"session:{oldest_session}")
        
        # Update session list
        timeout = int(self.session_timeout.total_seconds())
        cache.set(f"user_sessions:{user_id}", session_ids, timeout=timeout)
    
    def _remove_user_session(self, user_id: str, session_id: str) -> None:
        """Remove session from user's session list."""
        session_ids = cache.get(f"user_sessions:{user_id}", [])
        if session_id in session_ids:
            session_ids.remove(session_id)
            timeout = int(self.session_timeout.total_seconds())
            cache.set(f"user_sessions:{user_id}", session_ids, timeout=timeout)
    
    def validate_session(self, session_id: str) -> bool:
        """
        Validate session (as specified in DEVELOPMENT_STRATEGY.md).
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if session is valid and active
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        # Check session in database for additional validation
        try:
            from apps.accounts.models import UserSession
            db_session = UserSession.objects.get(
                jti=session_id,
                expires_at__gt=timezone.now(),
                revoked_at__isnull=True
            )
            return True
        except UserSession.DoesNotExist:
            # Clean up cache if database session doesn't exist
            cache.delete(f"session:{session_id}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Cleanup expired sessions (as specified in DEVELOPMENT_STRATEGY.md).
        
        Returns:
            int: Number of expired sessions cleaned up
        """
        try:
            from apps.accounts.models import UserSession
            
            # Find and mark expired sessions as revoked
            expired_sessions = UserSession.objects.filter(
                expires_at__lte=timezone.now(),
                revoked_at__isnull=True
            )
            
            count = expired_sessions.count()
            
            # Mark as revoked instead of deleting for audit trail
            expired_sessions.update(revoked_at=timezone.now())
            
            # Also clean up cache entries for these sessions
            for session in expired_sessions:
                cache.delete(f"session:{session.jti}")
                if session.user_id:
                    self._remove_user_session(str(session.user_id), session.jti)
            
            return count
        except Exception:
            return 0


# Add missing methods to PasswordSecurity class (following DEVELOPMENT_STRATEGY.md)
def _generate_reset_token(user) -> str:
    """Generate password reset token using JWTManager."""
    temp_manager = JWTManager()
    return temp_manager.generate_special_token(
        user_id=str(user.id),
        email=user.email,
        token_type=TokenType.RESET_PASSWORD,
        expires_in=timedelta(hours=1)
    )

def _verify_reset_token(token: str):
    """Verify password reset token using JWTManager."""
    try:
        from django.contrib.auth import get_user_model
        
        temp_manager = JWTManager()
        payload = temp_manager.decode_token(token, TokenType.RESET_PASSWORD)
        
        if not payload:
            return None
        
        User = get_user_model()
        user = User.objects.get(
            id=payload.user_id,
            email=payload.email,
            is_active=True
        )
        
        return user
    except Exception:
        return None

# Add methods to PasswordSecurity class
PasswordSecurity.generate_reset_token = staticmethod(_generate_reset_token)
PasswordSecurity.verify_reset_token = staticmethod(_verify_reset_token)

# Initialize global instances
jwt_manager = JWTManager()
session_manager = SessionManager()
password_security = PasswordSecurity()