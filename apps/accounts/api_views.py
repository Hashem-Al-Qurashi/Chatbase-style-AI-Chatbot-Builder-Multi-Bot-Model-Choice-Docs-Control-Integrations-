"""
API views for accounts app.
Handles user authentication and organization management.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.cache import cache
from django.db import models
import structlog

from apps.accounts.models import Organization, TeamMember, UserProfile
from apps.accounts.serializers import (
    UserSerializer, UserRegistrationSerializer, LoginSerializer,
    TokenRefreshSerializer, PasswordChangeSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    OrganizationSerializer, TeamMemberSerializer, UserProfileSerializer,
    OAuth2AuthorizeSerializer, OAuth2CallbackSerializer
)
from apps.core.auth import jwt_manager, session_manager, password_security
from apps.core.oauth import oauth_session_manager
# AuthenticationService not yet implemented - using direct OAuth integration

logger = structlog.get_logger()
User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user management.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return users visible to current user."""
        user = self.request.user
        # Users can see themselves and team members
        org_ids = user.team_memberships.filter(is_active=True).values_list('organization_id', flat=True)
        return User.objects.filter(
            models.Q(id=user.id) |
            models.Q(team_memberships__organization_id__in=org_ids)
        ).distinct()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user details."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['patch'])
    def update_profile(self, request):
        """Update current user profile."""
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change current user password."""
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        # Verify old password
        if not password_security.verify_password(
            serializer.validated_data['old_password'],
            user.password
        ):
            raise ValidationError({'old_password': 'Invalid password'})
        
        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        logger.info(
            "Password changed",
            user_id=str(user.id)
        )
        
        return Response({'message': 'Password changed successfully'})


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for organization management.
    """
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return organizations user belongs to."""
        user = self.request.user
        return Organization.objects.filter(
            members__user=user,
            members__is_active=True
        ).distinct()
    
    def perform_create(self, serializer):
        """Create organization with current user as owner."""
        org = serializer.save(owner=self.request.user)
        
        # Add owner as admin member
        TeamMember.objects.create(
            organization=org,
            user=self.request.user,
            role='owner',
            is_active=True,
            joined_at=timezone.now()
        )
        
        logger.info(
            "Organization created",
            org_id=str(org.id),
            user_id=str(self.request.user.id)
        )
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get organization members."""
        org = self.get_object()
        members = org.members.filter(is_active=True)
        serializer = TeamMemberSerializer(members, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def invite_member(self, request, pk=None):
        """Invite new member to organization."""
        org = self.get_object()
        
        # Check permissions
        membership = org.members.filter(user=request.user).first()
        if not membership or membership.role not in ['owner', 'admin']:
            raise ValidationError("You don't have permission to invite members")
        
        # Check member limit
        if org.members.filter(is_active=True).count() >= org.max_team_members:
            raise ValidationError("Organization member limit reached")
        
        serializer = TeamMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        member = serializer.save(organization=org)
        
        # Send invitation email
        from apps.core.tasks import send_invitation_email_task
        send_invitation_email_task.delay(
            member_id=str(member.id),
            inviter_name=request.user.get_full_name()
        )
        
        logger.info(
            "Member invited",
            org_id=str(org.id),
            member_id=str(member.id),
            inviter_id=str(request.user.id)
        )
        
        return Response(
            TeamMemberSerializer(member).data,
            status=status.HTTP_201_CREATED
        )


class TeamMemberViewSet(viewsets.ModelViewSet):
    """
    ViewSet for team member management.
    """
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return team members visible to current user."""
        user = self.request.user
        org_ids = user.team_memberships.filter(
            is_active=True
        ).values_list('organization_id', flat=True)
        
        return TeamMember.objects.filter(
            organization_id__in=org_ids,
            is_active=True
        )
    
    @action(detail=True, methods=['post'])
    def remove(self, request, pk=None):
        """Remove team member."""
        member = self.get_object()
        
        # Check permissions
        requester_membership = member.organization.members.filter(
            user=request.user
        ).first()
        
        if not requester_membership or requester_membership.role not in ['owner', 'admin']:
            raise ValidationError("You don't have permission to remove members")
        
        # Can't remove owner
        if member.role == 'owner':
            raise ValidationError("Cannot remove organization owner")
        
        member.is_active = False
        member.save()
        
        logger.info(
            "Member removed",
            org_id=str(member.organization.id),
            member_id=str(member.id),
            remover_id=str(request.user.id)
        )
        
        return Response({'message': 'Member removed successfully'})


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    User registration endpoint.
    """
    serializer = UserRegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # Create user
    user = serializer.save()
    
    # Create default organization
    org = Organization.objects.create(
        name=f"{user.first_name}'s Organization",
        owner=user
    )
    
    # Add as owner
    TeamMember.objects.create(
        organization=org,
        user=user,
        role='owner',
        is_active=True,
        joined_at=timezone.now()
    )
    
    # Create user profile
    UserProfile.objects.create(user=user)
    
    # Generate tokens
    access_token = jwt_manager.create_access_token(str(user.id))
    refresh_token = jwt_manager.create_refresh_token(str(user.id))
    
    logger.info(
        "User registered",
        user_id=str(user.id),
        email=user.email
    )
    
    return Response({
        'user': UserSerializer(user).data,
        'access_token': access_token,
        'refresh_token': refresh_token
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    User login endpoint.
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    remember_me = serializer.validated_data.get('remember_me', False)
    
    # Authenticate user
    auth_service = AuthenticationService()
    result = auth_service.authenticate(email, password)
    
    if not result.success:
        raise ValidationError({'error': result.error})
    
    # Update last login
    user = User.objects.get(id=result.user_data['user_id'])
    user.last_login = timezone.now()
    user.save()
    
    logger.info(
        "User logged in",
        user_id=str(user.id),
        email=user.email
    )
    
    return Response({
        'user': UserSerializer(user).data,
        'access_token': result.access_token,
        'refresh_token': result.refresh_token,
        'session_id': result.session_id
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    User logout endpoint.
    """
    # Get token from header
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        
        # Invalidate token
        jwt_manager.revoke_token(token)
        
        # Clear session if exists
        session_id = request.data.get('session_id')
        if session_id:
            session_manager.end_session(session_id)
    
    logger.info(
        "User logged out",
        user_id=str(request.user.id)
    )
    
    return Response({'message': 'Logged out successfully'})


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    """
    Request password reset.
    """
    serializer = PasswordResetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    email = serializer.validated_data['email']
    
    # Find user
    user = User.objects.filter(email=email).first()
    
    if user:
        # Generate reset token
        reset_token = jwt_manager.create_password_reset_token(str(user.id))
        
        # Send reset email
        from apps.core.tasks import send_password_reset_email_task
        send_password_reset_email_task.delay(
            user_id=str(user.id),
            reset_token=reset_token
        )
        
        logger.info(
            "Password reset requested",
            user_id=str(user.id),
            email=email
        )
    
    # Always return success to prevent email enumeration
    return Response({
        'message': 'If the email exists, a password reset link has been sent.'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    """
    Confirm password reset.
    """
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    token = serializer.validated_data['token']
    new_password = serializer.validated_data['new_password']
    
    # Verify token
    payload = jwt_manager.verify_token(token, TokenType.PASSWORD_RESET)
    
    if not payload:
        raise ValidationError({'error': 'Invalid or expired reset token'})
    
    # Update password
    user = User.objects.get(id=payload['user_id'])
    user.set_password(new_password)
    user.save()
    
    logger.info(
        "Password reset completed",
        user_id=str(user.id)
    )
    
    return Response({'message': 'Password reset successfully'})


@api_view(['GET'])
@permission_classes([AllowAny])
def oauth2_authorize(request):
    """
    Initiate OAuth2 authorization.
    
    GET /api/auth/oauth2/authorize/?provider=google&redirect_uri=...
    
    Response:
    {
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
        "state": "csrf_protection_state"
    }
    """
    try:
        serializer = OAuth2AuthorizeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        provider = serializer.validated_data['provider']
        redirect_uri = serializer.validated_data.get('redirect_uri')
        
        # Currently only Google is implemented
        if provider != 'google':
            raise ValidationError({
                'provider': 'Only Google OAuth2 is currently supported'
            })
        
        # Generate authorization URL using the core OAuth provider
        try:
            from apps.core.oauth import google_oauth_provider
            authorization_url, state = google_oauth_provider.generate_authorization_url(
                redirect_uri=redirect_uri
            )
            
            if not authorization_url:
                raise ValidationError({
                    'error': 'OAuth2 configuration error',
                    'details': 'Unable to generate authorization URL'
                })
                
        except Exception as e:
            logger.error(
                "OAuth2 authorization URL generation failed",
                error=str(e),
                provider=provider,
                redirect_uri=redirect_uri
            )
            raise ValidationError({
                'error': 'OAuth2 initialization failed',
                'details': 'Unable to start OAuth2 flow'
            })
        
        logger.info(
            "OAuth2 authorization initiated",
            provider=provider,
            state=state,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response({
            'authorization_url': authorization_url,
            'state': state
        })
        
    except Exception as e:
        logger.error(
            "OAuth2 authorization error",
            error=str(e),
            provider=serializer.validated_data.get('provider') if 'serializer' in locals() else 'unknown',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return Response(
            {'error': 'OAuth2 authorization failed', 'details': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def oauth2_callback(request):
    """
    Handle OAuth2 callback.
    
    POST /api/auth/oauth2/callback/
    {
        "code": "authorization_code_from_google",
        "state": "csrf_protection_state"
    }
    
    Response:
    {
        "user": {...},
        "access_token": "jwt_token",
        "refresh_token": "jwt_refresh_token",
        "created": false
    }
    """
    try:
        serializer = OAuth2CallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data['code']
        state = serializer.validated_data.get('state')
        
        # Use the OAuth session manager to authenticate
        from apps.core.oauth import oauth_session_manager
        device_info = {
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'oauth_login': True
        }
        ip_address = request.META.get('REMOTE_ADDR', '')
        
        # Authenticate with OAuth code
        oauth_access_token, oauth_refresh_token, user_data = oauth_session_manager.authenticate_with_oauth(
            authorization_code=code,
            state=state,
            device_info=device_info,
            ip_address=ip_address
        )
        
        if not user_data:
            logger.warning(
                "OAuth2 authentication failed",
                code_length=len(code) if code else 0,
                state=state,
                ip_address=ip_address
            )
            raise ValidationError({
                'error': 'OAuth2 authentication failed',
                'details': 'Invalid authorization code or state'
            })
        
        # Handle account linking with comprehensive error handling
        try:
            with transaction.atomic():
                # Check if a user with this Google ID already exists
                google_id = user_data['user_id'].replace('google_', '')
                existing_google_user = None
                
                if google_id:
                    try:
                        existing_google_user = User.objects.get(google_id=google_id)
                    except User.DoesNotExist:
                        pass
                
                if existing_google_user:
                    # User with this Google ID already exists
                    user = existing_google_user
                    created = False
                    
                    # Update user's email if it's different (Google email might have changed)
                    if user.email != user_data['email']:
                        logger.info(
                            "Google user email changed",
                            user_id=str(user.id),
                            old_email=user.email,
                            new_email=user_data['email']
                        )
                        user.email = user_data['email']
                        user.save(update_fields=['email'])
                        
                else:
                    # Try to find user by email
                    try:
                        user = User.objects.get(email=user_data['email'])
                        created = False
                        
                        # Link Google account to existing user
                        if user.google_id and user.google_id != google_id:
                            # User already has a different Google account linked
                            logger.warning(
                                "Attempted to link different Google account to existing user",
                                user_id=str(user.id),
                                existing_google_id=user.google_id,
                                new_google_id=google_id
                            )
                            raise ValidationError({
                                'error': 'Email conflict',
                                'details': 'This email is already associated with a different Google account'
                            })
                        
                        # Link Google account
                        user.google_id = google_id
                        user.avatar_url = user_data.get('picture', user.avatar_url)
                        user.save(update_fields=['google_id', 'avatar_url'])
                        
                        logger.info(
                            "Google account linked to existing user",
                            user_id=str(user.id),
                            email=user.email,
                            google_id=google_id
                        )
                        
                    except User.DoesNotExist:
                        # Create new user
                        user = User.objects.create(
                            email=user_data['email'],
                            first_name=user_data.get('given_name', ''),
                            last_name=user_data.get('family_name', ''),
                            is_active=True,
                            google_id=google_id,
                            avatar_url=user_data.get('picture', ''),
                            is_email_verified=True  # Google emails are verified
                        )
                        created = True
                        
                        logger.info(
                            "New user created from Google OAuth",
                            user_id=str(user.id),
                            email=user.email,
                            google_id=google_id
                        )
                        
        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                "Account linking error",
                error=str(e),
                email=user_data.get('email'),
                google_id=google_id if 'google_id' in locals() else None
            )
            raise ValidationError({
                'error': 'Account linking failed',
                'details': 'Unable to link or create account'
            })
        
        if created:
            # Create organization and profile for new user
            org = Organization.objects.create(
                name=f"{user.first_name}'s Organization" if user.first_name else f"{user.email}'s Organization"
            )
            
            TeamMember.objects.create(
                organization=org,
                user=user,
                role='owner',
                is_active=True,
                joined_at=timezone.now()
            )
            
            UserProfile.objects.create(user=user)
            
            logger.info(
                "New user created via OAuth2",
                user_id=str(user.id),
                email=user.email,
                provider='google'
            )
        else:
            logger.info(
                "Existing user logged in via OAuth2",
                user_id=str(user.id),
                email=user.email,
                provider='google'
            )
        
        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Generate JWT tokens using our authentication system
        from apps.core.auth import jwt_manager
        auth_result = jwt_manager.generate_tokens(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'access_token': auth_result.access_token,
            'refresh_token': auth_result.refresh_token,
            'expires_in': auth_result.expires_in,
            'created': created
        }, status=status.HTTP_200_OK)
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error(
            "OAuth2 callback error",
            error=str(e),
            code_length=len(serializer.validated_data.get('code', '')) if 'serializer' in locals() else 0,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return Response(
            {'error': 'OAuth2 callback failed', 'details': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )