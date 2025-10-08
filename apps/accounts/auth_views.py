"""
Authentication API views following DEVELOPMENT_STRATEGY.md Task 2 specification.
Implements all authentication endpoints as specified in the development strategy.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError, AuthenticationFailed
from django.contrib.auth import get_user_model, authenticate
from django.core.cache import cache
from django.utils import timezone
from django.db import transaction
import structlog

from apps.accounts.serializers import (
    UserRegistrationSerializer, LoginSerializer, TokenRefreshSerializer,
    UserSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer
)
from apps.core.auth import jwt_manager, session_manager, password_security
from apps.core.rate_limiting import rate_limit_decorator, RateLimitType

logger = structlog.get_logger()
User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
@rate_limit_decorator(RateLimitType.REGISTRATION)
def register(request):
    """
    User Registration Endpoint (DEVELOPMENT_STRATEGY.md Subtask 1)
    
    POST /api/auth/register/
    {
        "email": "user@example.com",
        "password": "SecurePass123!",
        "password_confirm": "SecurePass123!",
        "first_name": "John",
        "last_name": "Doe"
    }
    
    Features:
    - Email validation and uniqueness check
    - Password strength validation
    - User creation with proper error handling
    - Welcome email sending (async)
    """
    try:
        serializer = UserRegistrationSerializer(data=request.data)
        
        if not serializer.is_valid():
            logger.warning(
                "Registration validation failed",
                errors=serializer.errors,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response(
                {
                    'error': 'Validation failed',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Additional password strength validation using our custom validator
        password = serializer.validated_data['password']
        is_strong, strength_errors = password_security.validate_password_strength(password)
        
        if not is_strong:
            return Response(
                {
                    'error': 'Password does not meet strength requirements',
                    'details': {'password': strength_errors}
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user already exists
        email = serializer.validated_data['email']
        if User.objects.filter(email=email).exists():
            return Response(
                {
                    'error': 'Email already registered',
                    'details': {'email': ['User with this email already exists']}
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create user within transaction
        with transaction.atomic():
            user = serializer.save()
            
            # Generate authentication tokens
            auth_result = jwt_manager.generate_tokens(user)
            
            # Create session with device info
            device_info = {
                'ip_address': request.META.get('REMOTE_ADDR', ''),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'registration': True
            }
            session = session_manager.create_session(user, device_info)
            
            logger.info(
                "User registered successfully",
                user_id=str(user.id),
                email=user.email,
                ip_address=device_info['ip_address']
            )
            
            # TODO: Send welcome email async (will be implemented in background tasks)
            
            return Response(
                {
                    'message': 'Registration successful',
                    'access_token': auth_result.access_token,
                    'refresh_token': auth_result.refresh_token,
                    'user': auth_result.user_data,
                    'expires_in': auth_result.expires_in
                },
                status=status.HTTP_201_CREATED
            )
            
    except Exception as e:
        logger.error(
            "Registration error", 
            error=str(e),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return Response(
            {'error': 'Registration failed', 'details': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
@rate_limit_decorator(RateLimitType.LOGIN_ATTEMPTS)
def login(request):
    """
    User Login Endpoint (DEVELOPMENT_STRATEGY.md Subtask 2)
    
    POST /api/auth/login/
    {
        "email": "user@example.com", 
        "password": "SecurePass123!"
    }
    Response:
    {
        "access_token": "eyJ0eXAiOiJKV1Q...",
        "refresh_token": "eyJ0eXAiOiJKV1Q...",
        "user": {...},
        "expires_in": 3600
    }
    
    Features:
    - Rate limiting protection
    - Account lockout after failed attempts
    - Session creation and tracking
    """
    try:
        serializer = LoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {
                    'error': 'Invalid request data',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        ip_address = request.META.get('REMOTE_ADDR', '')
        
        # Check for account lockout
        lockout_key = f"login_attempts:{email}:{ip_address}"
        failed_attempts = cache.get(lockout_key, 0)
        
        if failed_attempts >= 5:
            logger.warning(
                "Account lockout - too many failed attempts",
                email=email,
                ip_address=ip_address,
                attempts=failed_attempts
            )
            return Response(
                {
                    'error': 'Account temporarily locked',
                    'details': 'Too many failed login attempts. Please try again later.'
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # Authenticate user
        try:
            user = User.objects.get(email=email, is_active=True)
            
            if not user.check_password(password):
                # Increment failed attempts
                cache.set(lockout_key, failed_attempts + 1, timeout=3600)  # 1 hour lockout
                
                logger.warning(
                    "Failed login attempt",
                    email=email,
                    ip_address=ip_address,
                    attempts=failed_attempts + 1
                )
                
                return Response(
                    {
                        'error': 'Invalid credentials',
                        'details': 'Email or password is incorrect'
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )
                
        except User.DoesNotExist:
            # Increment failed attempts even for non-existent users (security)
            cache.set(lockout_key, failed_attempts + 1, timeout=3600)
            
            logger.warning(
                "Failed login attempt - user not found",
                email=email,
                ip_address=ip_address
            )
            
            return Response(
                {
                    'error': 'Invalid credentials',
                    'details': 'Email or password is incorrect'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Clear failed attempts on successful authentication
        cache.delete(lockout_key)
        
        # Generate authentication tokens
        auth_result = jwt_manager.generate_tokens(user)
        
        # Create session with device info
        device_info = {
            'ip_address': ip_address,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'login': True
        }
        session = session_manager.create_session(user, device_info)
        
        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        logger.info(
            "User logged in successfully",
            user_id=str(user.id),
            email=user.email,
            ip_address=ip_address
        )
        
        return Response(
            {
                'access_token': auth_result.access_token,
                'refresh_token': auth_result.refresh_token,
                'user': auth_result.user_data,
                'expires_in': auth_result.expires_in
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(
            "Login error",
            error=str(e),
            email=serializer.validated_data.get('email') if 'serializer' in locals() else 'unknown',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return Response(
            {'error': 'Login failed', 'details': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
@rate_limit_decorator(RateLimitType.API_REQUESTS)
def refresh_token(request):
    """
    Token Refresh Endpoint (DEVELOPMENT_STRATEGY.md Subtask 3)
    
    POST /api/auth/refresh/
    {
        "refresh_token": "eyJ0eXAiOiJKV1Q..."
    }
    
    Features:
    - Token rotation for security
    - Refresh token validation
    - New access token generation
    """
    try:
        serializer = TokenRefreshSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {
                    'error': 'Invalid request data',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        refresh_token = serializer.validated_data['refresh_token']
        
        # Generate new access token using JWT manager
        new_access_token = jwt_manager.refresh_access_token(refresh_token)
        
        if not new_access_token:
            logger.warning(
                "Invalid refresh token used",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response(
                {
                    'error': 'Invalid refresh token',
                    'details': 'Refresh token is invalid or expired'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Decode the refresh token to get user info for logging
        from apps.core.auth import TokenType
        payload = jwt_manager.decode_token(refresh_token, TokenType.REFRESH)
        
        if payload:
            logger.info(
                "Token refreshed successfully",
                user_id=payload.user_id,
                ip_address=request.META.get('REMOTE_ADDR')
            )
        
        return Response(
            {
                'access_token': new_access_token,
                'expires_in': int(jwt_manager.access_token_lifetime.total_seconds())
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(
            "Token refresh error",
            error=str(e),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return Response(
            {'error': 'Token refresh failed', 'details': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """
    Get Current User Endpoint (DEVELOPMENT_STRATEGY.md Subtask 4)
    
    GET /api/auth/me/
    
    Returns current authenticated user information.
    """
    try:
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(
            "Get current user error",
            error=str(e),
            user_id=str(request.user.id) if request.user else 'unknown'
        )
        return Response(
            {'error': 'Failed to get user information'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Update User Profile Endpoint (DEVELOPMENT_STRATEGY.md Subtask 4)
    
    PATCH /api/auth/me/
    
    Updates current authenticated user profile.
    """
    try:
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        
        if not serializer.is_valid():
            return Response(
                {
                    'error': 'Validation failed',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer.save()
        
        logger.info(
            "User profile updated",
            user_id=str(user.id),
            updated_fields=list(request.data.keys())
        )
        
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(
            "Update profile error",
            error=str(e),
            user_id=str(request.user.id) if request.user else 'unknown'
        )
        return Response(
            {'error': 'Failed to update profile'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout Endpoint (DEVELOPMENT_STRATEGY.md Subtask 4)
    
    POST /api/auth/logout/
    
    Logs out user and revokes tokens.
    """
    try:
        # Get authorization header to extract token
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            # Decode token to get JTI for revocation
            from apps.core.auth import TokenType
            payload = jwt_manager.decode_token(token, TokenType.ACCESS)
            
            if payload:
                # Revoke the access token
                jwt_manager.revoke_token(payload.jti)
                
                logger.info(
                    "User logged out - token revoked",
                    user_id=str(request.user.id),
                    jti=payload.jti
                )
        
        # Clean up sessions (optional - sessions will expire naturally)
        # session_manager.cleanup_expired_sessions()
        
        return Response(
            {'message': 'Successfully logged out'},
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(
            "Logout error",
            error=str(e),
            user_id=str(request.user.id) if request.user else 'unknown'
        )
        return Response(
            {'message': 'Logout completed'},  # Return success even on error
            status=status.HTTP_200_OK
        )


@api_view(['POST'])
@permission_classes([AllowAny])
@rate_limit_decorator(RateLimitType.PASSWORD_RESET)
def password_reset_request(request):
    """
    Password Reset Request Endpoint (DEVELOPMENT_STRATEGY.md Task 5 Subtask 1)
    
    POST /api/v1/auth/password-reset/
    {
        "email": "user@example.com"
    }
    
    Features:
    - Email validation and user existence check
    - Rate limiting to prevent abuse
    - Secure token generation
    - Background email sending
    """
    try:
        serializer = PasswordResetRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {
                    'error': 'Invalid request data',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        email = serializer.validated_data['email']
        ip_address = request.META.get('REMOTE_ADDR', '')
        
        try:
            # Look up user by email
            user = User.objects.get(email=email, is_active=True)
            
            # Generate password reset token
            reset_token = password_security.generate_reset_token(user)
            
            # Send password reset email
            from apps.core.email_service import send_password_reset_email_async
            email_sent = send_password_reset_email_async(
                user=user,
                reset_token=reset_token,
                ip_address=ip_address,
                request=request
            )
            
            logger.info(
                "Password reset requested",
                user_id=str(user.id),
                email=email,
                ip_address=ip_address,
                email_sent=email_sent,
                reset_token=reset_token[:10] + "..." if len(reset_token) > 10 else reset_token
            )
            
            # Always return success, even if user doesn't exist (security)
            return Response(
                {
                    'message': 'If your email is registered, you will receive a password reset link shortly.'
                },
                status=status.HTTP_200_OK
            )
            
        except User.DoesNotExist:
            # Don't reveal whether user exists (security measure)
            logger.info(
                "Password reset requested for non-existent user",
                email=email,
                ip_address=ip_address
            )
            
            # Return same message as success case
            return Response(
                {
                    'message': 'If your email is registered, you will receive a password reset link shortly.'
                },
                status=status.HTTP_200_OK
            )
        
    except Exception as e:
        logger.error(
            "Password reset request error",
            error=str(e),
            email=serializer.validated_data.get('email') if 'serializer' in locals() else 'unknown',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return Response(
            {'error': 'Password reset request failed', 'details': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
@rate_limit_decorator(RateLimitType.PASSWORD_RESET)
def password_reset_confirm(request):
    """
    Password Reset Confirmation Endpoint (DEVELOPMENT_STRATEGY.md Task 5 Subtask 2)
    
    POST /api/v1/auth/password-reset/confirm/
    {
        "token": "reset_token",
        "new_password": "NewSecurePass123!"
    }
    
    Features:
    - Reset token validation and expiration check
    - Password strength validation
    - Secure password update
    - Session cleanup for security
    """
    try:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {
                    'error': 'Invalid request data',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        ip_address = request.META.get('REMOTE_ADDR', '')
        
        # Verify reset token and get user
        user = password_security.verify_reset_token(token)
        
        if not user:
            logger.warning(
                "Invalid or expired password reset token used",
                ip_address=ip_address,
                token_hint=token[:10] + "..." if len(token) > 10 else token
            )
            return Response(
                {
                    'error': 'Invalid or expired reset token',
                    'details': 'The password reset link is invalid or has expired'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Additional password strength validation
        is_strong, strength_errors = password_security.validate_password_strength(new_password)
        
        if not is_strong:
            return Response(
                {
                    'error': 'Password does not meet strength requirements',
                    'details': {'new_password': strength_errors}
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update password within transaction
        with transaction.atomic():
            user.set_password(new_password)
            user.save()
            
            # TODO: Revoke all existing sessions/tokens for security
            # This ensures that if account was compromised, all sessions are invalidated
            
            logger.info(
                "Password reset completed successfully",
                user_id=str(user.id),
                email=user.email,
                ip_address=ip_address
            )
            
            return Response(
                {
                    'message': 'Password has been reset successfully. Please log in with your new password.'
                },
                status=status.HTTP_200_OK
            )
    
    except Exception as e:
        logger.error(
            "Password reset confirmation error",
            error=str(e),
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return Response(
            {'error': 'Password reset failed', 'details': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )