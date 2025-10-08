"""
Comprehensive tests for the authentication system.
Tests JWT management, OAuth2 flow, password security, and session management.
"""

import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from django.utils import timezone
from django.core.cache import cache

from apps.core.auth import (
    JWTManager,
    PasswordSecurity,
    SessionManager,
    TokenType,
    jwt_manager,
    session_manager,
    password_security
)
from apps.core.oauth import (
    GoogleOAuthProvider,
    OAuthSessionManager,
    oauth_session_manager
)
from apps.core.rate_limiting import (
    AdaptiveRateLimiter,
    RateLimitType,
    rate_limiter
)


class TestPasswordSecurity:
    """Test password security utilities."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = PasswordSecurity.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
        assert hashed.startswith('$2b$')  # bcrypt prefix
    
    def test_verify_password_success(self):
        """Test successful password verification."""
        password = "TestPassword123!"
        hashed = PasswordSecurity.hash_password(password)
        
        assert PasswordSecurity.verify_password(password, hashed) is True
    
    def test_verify_password_failure(self):
        """Test failed password verification."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = PasswordSecurity.hash_password(password)
        
        assert PasswordSecurity.verify_password(wrong_password, hashed) is False
    
    def test_verify_password_invalid_hash(self):
        """Test password verification with invalid hash."""
        password = "TestPassword123!"
        invalid_hash = "invalid-hash"
        
        assert PasswordSecurity.verify_password(password, invalid_hash) is False
    
    def test_validate_password_strength_valid(self):
        """Test password strength validation for valid password."""
        password = "StrongPassword123!"
        is_valid, errors = PasswordSecurity.validate_password_strength(password)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_password_strength_too_short(self):
        """Test password strength validation for short password."""
        password = "Short1!"
        is_valid, errors = PasswordSecurity.validate_password_strength(password)
        
        assert is_valid is False
        assert "at least 8 characters" in " ".join(errors)
    
    def test_validate_password_strength_no_uppercase(self):
        """Test password strength validation without uppercase."""
        password = "weakpassword123!"
        is_valid, errors = PasswordSecurity.validate_password_strength(password)
        
        assert is_valid is False
        assert "uppercase letter" in " ".join(errors)
    
    def test_validate_password_strength_no_special_char(self):
        """Test password strength validation without special character."""
        password = "WeakPassword123"
        is_valid, errors = PasswordSecurity.validate_password_strength(password)
        
        assert is_valid is False
        assert "special character" in " ".join(errors)
    
    def test_validate_password_strength_common_pattern(self):
        """Test password strength validation with common pattern."""
        password = "Password123!"
        is_valid, errors = PasswordSecurity.validate_password_strength(password)
        
        assert is_valid is False
        assert "common patterns" in " ".join(errors)


class TestJWTManager:
    """Test JWT token management."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.jwt_manager = JWTManager()
        self.user_id = "test-user-id"
        self.email = "test@example.com"
        self.scopes = ["read", "write"]
    
    def test_generate_tokens(self):
        """Test token generation."""
        access_token, refresh_token = self.jwt_manager.generate_tokens(
            self.user_id, self.email, self.scopes
        )
        
        assert access_token is not None
        assert refresh_token is not None
        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)
        assert access_token != refresh_token
    
    def test_verify_access_token(self):
        """Test access token verification."""
        access_token, _ = self.jwt_manager.generate_tokens(
            self.user_id, self.email, self.scopes
        )
        
        payload = self.jwt_manager.verify_token(access_token, TokenType.ACCESS)
        
        assert payload is not None
        assert payload.user_id == self.user_id
        assert payload.email == self.email
        assert payload.token_type == TokenType.ACCESS
        assert payload.scopes == self.scopes
    
    def test_verify_refresh_token(self):
        """Test refresh token verification."""
        _, refresh_token = self.jwt_manager.generate_tokens(
            self.user_id, self.email, self.scopes
        )
        
        payload = self.jwt_manager.verify_token(refresh_token, TokenType.REFRESH)
        
        assert payload is not None
        assert payload.user_id == self.user_id
        assert payload.token_type == TokenType.REFRESH
    
    def test_verify_token_wrong_type(self):
        """Test token verification with wrong type."""
        access_token, _ = self.jwt_manager.generate_tokens(
            self.user_id, self.email, self.scopes
        )
        
        # Try to verify access token as refresh token
        payload = self.jwt_manager.verify_token(access_token, TokenType.REFRESH)
        
        assert payload is None
    
    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"
        
        payload = self.jwt_manager.verify_token(invalid_token, TokenType.ACCESS)
        
        assert payload is None
    
    def test_refresh_access_token(self):
        """Test access token refresh."""
        _, refresh_token = self.jwt_manager.generate_tokens(
            self.user_id, self.email, self.scopes
        )
        
        new_access_token = self.jwt_manager.refresh_access_token(refresh_token)
        
        assert new_access_token is not None
        
        # Verify new access token
        payload = self.jwt_manager.verify_token(new_access_token, TokenType.ACCESS)
        assert payload is not None
        assert payload.user_id == self.user_id
    
    def test_refresh_with_invalid_token(self):
        """Test refresh with invalid token."""
        invalid_token = "invalid.token.here"
        
        new_access_token = self.jwt_manager.refresh_access_token(invalid_token)
        
        assert new_access_token is None
    
    def test_token_revocation(self):
        """Test token revocation."""
        access_token, _ = self.jwt_manager.generate_tokens(
            self.user_id, self.email, self.scopes
        )
        
        # Verify token works initially
        payload = self.jwt_manager.verify_token(access_token, TokenType.ACCESS)
        assert payload is not None
        
        # Revoke token
        self.jwt_manager.revoke_token(payload.jti)
        
        # Verify token is now invalid
        payload = self.jwt_manager.verify_token(access_token, TokenType.ACCESS)
        assert payload is None
    
    def test_generate_special_token(self):
        """Test special token generation."""
        expires_in = timedelta(hours=1)
        
        token = self.jwt_manager.generate_special_token(
            self.user_id,
            self.email,
            TokenType.RESET_PASSWORD,
            expires_in
        )
        
        assert token is not None
        
        # Verify token
        payload = self.jwt_manager.verify_token(token, TokenType.RESET_PASSWORD)
        assert payload is not None
        assert payload.user_id == self.user_id
        assert payload.token_type == TokenType.RESET_PASSWORD


class TestSessionManager:
    """Test session management."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.session_manager = SessionManager()
        self.user_id = "test-user-id"
        self.device_info = {"browser": "Chrome", "os": "Linux"}
        self.ip_address = "192.168.1.1"
    
    def test_create_session(self):
        """Test session creation."""
        session_id = self.session_manager.create_session(
            self.user_id, self.device_info, self.ip_address
        )
        
        assert session_id is not None
        assert isinstance(session_id, str)
        
        # Verify session can be retrieved
        session_data = self.session_manager.get_session(session_id)
        assert session_data is not None
        assert session_data["user_id"] == self.user_id
        assert session_data["device_info"] == self.device_info
        assert session_data["ip_address"] == self.ip_address
    
    def test_get_nonexistent_session(self):
        """Test getting non-existent session."""
        fake_session_id = "fake-session-id"
        
        session_data = self.session_manager.get_session(fake_session_id)
        
        assert session_data is None
    
    def test_update_session_activity(self):
        """Test session activity update."""
        session_id = self.session_manager.create_session(
            self.user_id, self.device_info, self.ip_address
        )
        
        # Get initial session data
        initial_data = self.session_manager.get_session(session_id)
        initial_activity = initial_data["last_activity"]
        
        # Wait a bit and update activity
        time.sleep(0.1)
        self.session_manager.update_session_activity(session_id)
        
        # Verify activity was updated
        updated_data = self.session_manager.get_session(session_id)
        updated_activity = updated_data["last_activity"]
        
        assert updated_activity > initial_activity
    
    def test_revoke_session(self):
        """Test session revocation."""
        session_id = self.session_manager.create_session(
            self.user_id, self.device_info, self.ip_address
        )
        
        # Verify session exists
        assert self.session_manager.get_session(session_id) is not None
        
        # Revoke session
        self.session_manager.revoke_session(session_id)
        
        # Verify session is gone
        assert self.session_manager.get_session(session_id) is None
    
    def test_revoke_all_user_sessions(self):
        """Test revoking all user sessions."""
        # Create multiple sessions for the user
        session_ids = []
        for i in range(3):
            session_id = self.session_manager.create_session(
                self.user_id, self.device_info, f"192.168.1.{i}"
            )
            session_ids.append(session_id)
        
        # Verify all sessions exist
        for session_id in session_ids:
            assert self.session_manager.get_session(session_id) is not None
        
        # Revoke all user sessions
        self.session_manager.revoke_all_user_sessions(self.user_id)
        
        # Verify all sessions are gone
        for session_id in session_ids:
            assert self.session_manager.get_session(session_id) is None


class TestGoogleOAuthProvider:
    """Test Google OAuth provider."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('apps.core.oauth.settings') as mock_settings:
            mock_settings.GOOGLE_OAUTH_CLIENT_ID = "test-client-id"
            mock_settings.GOOGLE_OAUTH_CLIENT_SECRET = "test-client-secret"
            self.oauth_provider = GoogleOAuthProvider()
    
    def test_generate_authorization_url(self):
        """Test authorization URL generation."""
        auth_url, state = self.oauth_provider.generate_authorization_url()
        
        assert auth_url is not None
        assert state is not None
        assert "accounts.google.com" in auth_url
        assert "client_id=test-client-id" in auth_url
        assert f"state={state}" in auth_url
        assert "code_challenge" in auth_url
        
        # Verify state is cached
        oauth_state_data = cache.get(f"oauth_state:{state}")
        assert oauth_state_data is not None
    
    @patch('apps.core.oauth.requests.post')
    def test_exchange_code_for_tokens(self, mock_post):
        """Test code exchange for tokens."""
        # Setup
        auth_url, state = self.oauth_provider.generate_authorization_url()
        authorization_code = "test-auth-code"
        
        # Mock successful token response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Test
        tokens = self.oauth_provider.exchange_code_for_tokens(
            authorization_code, state
        )
        
        assert tokens is not None
        assert tokens["access_token"] == "test-access-token"
        assert tokens["refresh_token"] == "test-refresh-token"
    
    def test_exchange_code_invalid_state(self):
        """Test code exchange with invalid state."""
        authorization_code = "test-auth-code"
        invalid_state = "invalid-state"
        
        with pytest.raises(ValueError, match="Invalid or expired OAuth state"):
            self.oauth_provider.exchange_code_for_tokens(
                authorization_code, invalid_state
            )
    
    @patch('apps.core.oauth.requests.get')
    def test_get_user_info(self, mock_get):
        """Test getting user info from Google."""
        access_token = "test-access-token"
        
        # Mock user info response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "google-user-id",
            "email": "test@example.com",
            "verified_email": True,
            "name": "Test User",
            "given_name": "Test",
            "family_name": "User",
            "picture": "https://example.com/avatar.jpg",
            "locale": "en"
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        user_info = self.oauth_provider.get_user_info(access_token)
        
        assert user_info.id == "google-user-id"
        assert user_info.email == "test@example.com"
        assert user_info.verified_email is True
        assert user_info.name == "Test User"


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rate_limiter = AdaptiveRateLimiter()
        self.identifier = "test-user"
        cache.clear()  # Clear cache before each test
    
    def test_check_rate_limit_within_limit(self):
        """Test rate limit check within limits."""
        status = self.rate_limiter.check_rate_limit(
            RateLimitType.LOGIN_ATTEMPTS, self.identifier
        )
        
        assert status.attempts == 0
        assert status.blocked_until is None
        assert not self.rate_limiter.is_blocked(
            RateLimitType.LOGIN_ATTEMPTS, self.identifier
        )
    
    def test_record_attempt_increment(self):
        """Test recording attempts increments counter."""
        # Record first attempt
        status = self.rate_limiter.record_attempt(
            RateLimitType.LOGIN_ATTEMPTS, self.identifier
        )
        
        assert status.attempts == 1
        assert status.blocked_until is None
    
    def test_rate_limit_blocking(self):
        """Test rate limit blocking after max attempts."""
        config = self.rate_limiter.configs[RateLimitType.LOGIN_ATTEMPTS]
        
        # Exceed the limit
        for i in range(config.max_attempts):
            status = self.rate_limiter.record_attempt(
                RateLimitType.LOGIN_ATTEMPTS, self.identifier
            )
        
        # Should be blocked now
        assert status.blocked_until is not None
        assert self.rate_limiter.is_blocked(
            RateLimitType.LOGIN_ATTEMPTS, self.identifier
        )
    
    def test_successful_attempt_resets_counter(self):
        """Test successful attempt resets counter."""
        # Record some failed attempts
        for i in range(3):
            self.rate_limiter.record_attempt(
                RateLimitType.LOGIN_ATTEMPTS, self.identifier
            )
        
        # Record successful attempt
        status = self.rate_limiter.record_attempt(
            RateLimitType.LOGIN_ATTEMPTS, self.identifier, success=True
        )
        
        # Counter should be reset
        new_status = self.rate_limiter.check_rate_limit(
            RateLimitType.LOGIN_ATTEMPTS, self.identifier
        )
        assert new_status.attempts == 0
    
    def test_different_identifiers_independent(self):
        """Test different identifiers have independent limits."""
        identifier1 = "user1"
        identifier2 = "user2"
        
        # Max out attempts for user1
        config = self.rate_limiter.configs[RateLimitType.LOGIN_ATTEMPTS]
        for i in range(config.max_attempts):
            self.rate_limiter.record_attempt(
                RateLimitType.LOGIN_ATTEMPTS, identifier1
            )
        
        # User1 should be blocked
        assert self.rate_limiter.is_blocked(
            RateLimitType.LOGIN_ATTEMPTS, identifier1
        )
        
        # User2 should not be blocked
        assert not self.rate_limiter.is_blocked(
            RateLimitType.LOGIN_ATTEMPTS, identifier2
        )
    
    def test_reset_rate_limit(self):
        """Test manual rate limit reset."""
        # Block the user
        config = self.rate_limiter.configs[RateLimitType.LOGIN_ATTEMPTS]
        for i in range(config.max_attempts):
            self.rate_limiter.record_attempt(
                RateLimitType.LOGIN_ATTEMPTS, self.identifier
            )
        
        assert self.rate_limiter.is_blocked(
            RateLimitType.LOGIN_ATTEMPTS, self.identifier
        )
        
        # Reset the limit
        self.rate_limiter.reset_rate_limit(
            RateLimitType.LOGIN_ATTEMPTS, self.identifier
        )
        
        # Should no longer be blocked
        assert not self.rate_limiter.is_blocked(
            RateLimitType.LOGIN_ATTEMPTS, self.identifier
        )


@pytest.mark.asyncio
class TestOAuthSessionManager:
    """Test OAuth session management."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('apps.core.oauth.settings') as mock_settings:
            mock_settings.GOOGLE_OAUTH_CLIENT_ID = "test-client-id"
            mock_settings.GOOGLE_OAUTH_CLIENT_SECRET = "test-client-secret"
            self.oauth_session_manager = OAuthSessionManager()
    
    @patch('apps.core.oauth.GoogleOAuthProvider.exchange_code_for_tokens')
    @patch('apps.core.oauth.GoogleOAuthProvider.get_user_info')
    async def test_authenticate_with_oauth_success(self, mock_get_user_info, mock_exchange_tokens):
        """Test successful OAuth authentication."""
        # Setup mocks
        mock_exchange_tokens.return_value = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        
        from apps.core.oauth import UserInfo
        mock_get_user_info.return_value = UserInfo(
            id="google-user-id",
            email="test@example.com",
            verified_email=True,
            name="Test User",
            given_name="Test",
            family_name="User",
            picture="https://example.com/avatar.jpg",
            locale="en"
        )
        
        # Generate state for testing
        auth_url, state = self.oauth_session_manager.oauth_provider.generate_authorization_url()
        
        # Test authentication
        access_token, refresh_token, user_data = self.oauth_session_manager.authenticate_with_oauth(
            authorization_code="test-auth-code",
            state=state,
            device_info={"browser": "Chrome"},
            ip_address="192.168.1.1"
        )
        
        assert access_token is not None
        assert refresh_token is not None
        assert user_data is not None
        assert user_data["email"] == "test@example.com"
        assert user_data["oauth_provider"] == "google"
    
    async def test_authenticate_with_oauth_unverified_email(self):
        """Test OAuth authentication with unverified email."""
        with patch('apps.core.oauth.GoogleOAuthProvider.exchange_code_for_tokens') as mock_exchange, \
             patch('apps.core.oauth.GoogleOAuthProvider.get_user_info') as mock_user_info:
            
            mock_exchange.return_value = {"access_token": "test-token"}
            
            from apps.core.oauth import UserInfo
            mock_user_info.return_value = UserInfo(
                id="google-user-id",
                email="test@example.com",
                verified_email=False,  # Unverified email
                name="Test User",
                given_name="Test",
                family_name="User",
                picture="https://example.com/avatar.jpg",
                locale="en"
            )
            
            # Generate state for testing
            auth_url, state = self.oauth_session_manager.oauth_provider.generate_authorization_url()
            
            # Test should fail with unverified email
            access_token, refresh_token, user_data = self.oauth_session_manager.authenticate_with_oauth(
                authorization_code="test-auth-code",
                state=state,
                device_info={"browser": "Chrome"},
                ip_address="192.168.1.1"
            )
            
            assert access_token is None
            assert refresh_token is None
            assert user_data is None


class TestIntegration:
    """Integration tests for authentication components."""
    
    def test_full_authentication_flow(self):
        """Test complete authentication flow."""
        # Test user creation
        email = "integration@example.com"
        password = "IntegrationTest123!"
        
        # Hash password
        hashed_password = password_security.hash_password(password)
        
        # Generate tokens
        user_id = "integration-user-id"
        access_token, refresh_token = jwt_manager.generate_tokens(
            user_id, email, ["read", "write"]
        )
        
        # Verify tokens
        access_payload = jwt_manager.verify_token(access_token, TokenType.ACCESS)
        refresh_payload = jwt_manager.verify_token(refresh_token, TokenType.REFRESH)
        
        assert access_payload is not None
        assert refresh_payload is not None
        assert access_payload.user_id == user_id
        assert access_payload.email == email
        
        # Create session
        session_id = session_manager.create_session(
            user_id,
            {"browser": "Chrome", "os": "Linux"},
            "192.168.1.1"
        )
        
        # Verify session
        session_data = session_manager.get_session(session_id)
        assert session_data is not None
        assert session_data["user_id"] == user_id
        
        # Test password verification
        assert password_security.verify_password(password, hashed_password)
        
        # Test token refresh
        new_access_token = jwt_manager.refresh_access_token(refresh_token)
        assert new_access_token is not None
        
        new_access_payload = jwt_manager.verify_token(new_access_token, TokenType.ACCESS)
        assert new_access_payload is not None
        assert new_access_payload.user_id == user_id
    
    def test_security_measures(self):
        """Test security measures work together."""
        identifier = "security-test-user"
        
        # Test rate limiting prevents brute force
        config = rate_limiter.configs[RateLimitType.LOGIN_ATTEMPTS]
        
        # Simulate failed login attempts
        for i in range(config.max_attempts):
            rate_limiter.record_attempt(RateLimitType.LOGIN_ATTEMPTS, identifier)
        
        # Should be blocked
        assert rate_limiter.is_blocked(RateLimitType.LOGIN_ATTEMPTS, identifier)
        
        # Test token revocation
        user_id = "security-user-id"
        email = "security@example.com"
        access_token, _ = jwt_manager.generate_tokens(user_id, email)
        
        # Verify token works
        payload = jwt_manager.verify_token(access_token, TokenType.ACCESS)
        assert payload is not None
        
        # Revoke token
        jwt_manager.revoke_token(payload.jti)
        
        # Token should no longer work
        payload = jwt_manager.verify_token(access_token, TokenType.ACCESS)
        assert payload is None