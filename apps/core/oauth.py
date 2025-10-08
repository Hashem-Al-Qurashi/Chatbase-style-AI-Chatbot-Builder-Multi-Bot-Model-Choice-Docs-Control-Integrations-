"""
Google OAuth2 integration with secure session management.
Implements OAuth2 flow with proper state validation and PKCE.
"""

import secrets
import hashlib
import base64
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from urllib.parse import urlencode, parse_qs, urlparse
import json

import requests
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from chatbot_saas.config import get_settings
from apps.core.auth import jwt_manager, session_manager


settings = get_settings()


@dataclass
class OAuthConfig:
    """OAuth configuration for Google."""
    client_id: str
    client_secret: str
    redirect_uri: str
    scope: str = "openid email profile"
    authorization_base_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url: str = "https://oauth2.googleapis.com/token"
    userinfo_url: str = "https://www.googleapis.com/oauth2/v2/userinfo"


@dataclass
class OAuthState:
    """OAuth state for security validation."""
    state: str
    code_verifier: str
    code_challenge: str
    redirect_uri: str
    created_at: str


@dataclass
class UserInfo:
    """User information from OAuth provider."""
    id: str
    email: str
    verified_email: bool
    name: str
    given_name: str
    family_name: str
    picture: str
    locale: str


class GoogleOAuthProvider:
    """Google OAuth2 provider implementation."""
    
    def __init__(self):
        self.config = OAuthConfig(
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            redirect_uri=""  # Will be set lazily when needed
        )
        self.state_ttl = 600  # 10 minutes
    
    def _build_redirect_uri(self) -> str:
        """Build OAuth redirect URI."""
        # In production, this should be the full domain
        base_url = "http://localhost:8000"  # This should come from settings
        return f"{base_url}{reverse('auth:oauth_callback')}"
    
    def _generate_code_verifier(self) -> str:
        """Generate PKCE code verifier."""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    
    def _generate_code_challenge(self, code_verifier: str) -> str:
        """Generate PKCE code challenge."""
        challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')
    
    def generate_authorization_url(self, redirect_uri: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate OAuth authorization URL with PKCE.
        
        Args:
            redirect_uri: Optional custom redirect URI
            
        Returns:
            Tuple[str, str]: (authorization_url, state)
        """
        # Generate PKCE parameters
        code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier)
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Build redirect URI lazily to avoid circular imports
        if not redirect_uri:
            redirect_uri = self._build_redirect_uri()
        
        # Store state and PKCE data for verification
        oauth_state = OAuthState(
            state=state,
            code_verifier=code_verifier,
            code_challenge=code_challenge,
            redirect_uri=redirect_uri,
            created_at=timezone.now().isoformat()
        )
        
        cache.set(
            f"oauth_state:{state}",
            oauth_state.__dict__,
            timeout=self.state_ttl
        )
        
        # Build authorization URL
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": oauth_state.redirect_uri,
            "scope": self.config.scope,
            "response_type": "code",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",  # Request refresh token
            "prompt": "consent"  # Force consent to get refresh token
        }
        
        authorization_url = f"{self.config.authorization_base_url}?{urlencode(params)}"
        return authorization_url, state
    
    def exchange_code_for_tokens(
        self,
        authorization_code: str,
        state: str
    ) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access tokens.
        
        Args:
            authorization_code: OAuth authorization code
            state: State parameter for verification
            
        Returns:
            Optional[Dict[str, Any]]: Token response or None if exchange fails
        """
        # Retrieve and validate state
        oauth_state_data = cache.get(f"oauth_state:{state}")
        if not oauth_state_data:
            raise ValueError("Invalid or expired OAuth state")
        
        oauth_state = OAuthState(**oauth_state_data)
        
        # Clean up state from cache
        cache.delete(f"oauth_state:{state}")
        
        # Prepare token exchange request
        token_data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": authorization_code,
            "grant_type": "authorization_code",
            "redirect_uri": oauth_state.redirect_uri,
            "code_verifier": oauth_state.code_verifier
        }
        
        try:
            response = requests.post(
                self.config.token_url,
                data=token_data,
                headers={"Accept": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            raise ValueError(f"Token exchange failed: {str(e)}")
    
    def get_user_info(self, access_token: str) -> UserInfo:
        """
        Get user information from Google API.
        
        Args:
            access_token: OAuth access token
            
        Returns:
            UserInfo: User information
        """
        try:
            response = requests.get(
                self.config.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30
            )
            response.raise_for_status()
            
            user_data = response.json()
            
            return UserInfo(
                id=user_data["id"],
                email=user_data["email"],
                verified_email=user_data.get("verified_email", False),
                name=user_data.get("name", ""),
                given_name=user_data.get("given_name", ""),
                family_name=user_data.get("family_name", ""),
                picture=user_data.get("picture", ""),
                locale=user_data.get("locale", "en")
            )
            
        except requests.RequestException as e:
            raise ValueError(f"User info retrieval failed: {str(e)}")
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh OAuth access token.
        
        Args:
            refresh_token: OAuth refresh token
            
        Returns:
            Optional[Dict[str, Any]]: New token response or None if refresh fails
        """
        token_data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        try:
            response = requests.post(
                self.config.token_url,
                data=token_data,
                headers={"Accept": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException:
            return None


class OAuthSessionManager:
    """Manage OAuth sessions and user authentication."""
    
    def __init__(self):
        self.oauth_provider = GoogleOAuthProvider()
    
    def authenticate_with_oauth(
        self,
        authorization_code: str,
        state: str,
        device_info: Dict[str, str],
        ip_address: str
    ) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]]]:
        """
        Authenticate user with OAuth code.
        
        Args:
            authorization_code: OAuth authorization code
            state: OAuth state parameter
            device_info: Device/browser information
            ip_address: Client IP address
            
        Returns:
            Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]]]: 
                (access_token, refresh_token, user_data) or (None, None, None) if auth fails
        """
        try:
            # Exchange code for tokens
            token_response = self.oauth_provider.exchange_code_for_tokens(
                authorization_code, state
            )
            
            if not token_response:
                return None, None, None
            
            # Get user information
            oauth_access_token = token_response["access_token"]
            user_info = self.oauth_provider.get_user_info(oauth_access_token)
            
            if not user_info.verified_email:
                raise ValueError("Email not verified with OAuth provider")
            
            # Here you would typically:
            # 1. Check if user exists in your database
            # 2. Create user if they don't exist
            # 3. Update user information if they do exist
            # For now, return user data for the API layer to handle
            
            # Note: The actual JWT token generation and user creation 
            # should be handled in the API layer, not here.
            # This is a separation of concerns - OAuth handles the OAuth flow,
            # the API layer handles user management and JWT tokens.
            
            # Store OAuth tokens for potential refresh
            oauth_data = {
                "access_token": oauth_access_token,
                "refresh_token": token_response.get("refresh_token"),
                "expires_in": token_response.get("expires_in", 3600),
                "token_type": token_response.get("token_type", "Bearer")
            }
            
            # Cache OAuth tokens with user's Google ID
            cache.set(
                f"oauth_tokens:google_{user_info.id}",
                oauth_data,
                timeout=oauth_data["expires_in"]
            )
            
            # Return user data for API layer to handle user creation and JWT generation
            user_data = {
                "user_id": f"google_{user_info.id}",  # Google user ID
                "email": user_info.email,
                "name": user_info.name,
                "given_name": user_info.given_name,
                "family_name": user_info.family_name,
                "picture": user_info.picture,
                "locale": user_info.locale,
                "oauth_provider": "google",
                "verified_email": user_info.verified_email
            }
            
            # Return None for tokens (API layer will generate JWT tokens)
            # and the user data for user creation/lookup
            return None, None, user_data
            
        except ValueError as e:
            # OAuth-specific errors (invalid code, expired state, etc.)
            import structlog
            logger = structlog.get_logger()
            logger.warning(
                "OAuth authentication failed - invalid request",
                error=str(e),
                authorization_code_length=len(authorization_code) if authorization_code else 0,
                state=state
            )
            return None, None, None
            
        except requests.RequestException as e:
            # Network/API errors
            import structlog
            logger = structlog.get_logger()
            logger.error(
                "OAuth authentication failed - external service error", 
                error=str(e),
                error_type=type(e).__name__
            )
            return None, None, None
            
        except Exception as e:
            # Unexpected errors
            import structlog
            logger = structlog.get_logger()
            logger.error(
                "OAuth authentication failed - unexpected error",
                error=str(e),
                error_type=type(e).__name__
            )
            return None, None, None
    
    def revoke_oauth_session(self, user_id: str) -> None:
        """
        Revoke OAuth session and tokens.
        
        Args:
            user_id: User identifier
        """
        # Revoke OAuth tokens from cache
        cache.delete(f"oauth_tokens:{user_id}")
        
        # Revoke all user sessions
        session_manager.revoke_all_user_sessions(user_id)


# Global OAuth instance
oauth_session_manager = OAuthSessionManager()
google_oauth_provider = GoogleOAuthProvider()