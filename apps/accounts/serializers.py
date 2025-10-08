"""
Serializers for accounts app.
Handles user authentication, registration, and profile management.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from apps.accounts.models import Organization, TeamMember, UserProfile

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """User registration serializer with password validation."""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ('email', 'password', 'password_confirm', 'first_name', 'last_name')
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True}
        }
    
    def validate(self, attrs):
        """Validate passwords match."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password': 'Password fields must match.'
            })
        return attrs
    
    def create(self, validated_data):
        """Create new user."""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    """User serializer for authenticated users."""
    
    full_name = serializers.SerializerMethodField()
    organization = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'is_active', 'date_joined', 'last_login', 'organization'
        )
        read_only_fields = ('id', 'email', 'date_joined', 'last_login')
    
    def get_full_name(self, obj):
        """Get user's full name."""
        return f"{obj.first_name} {obj.last_name}".strip()
    
    def get_organization(self, obj):
        """Get user's primary organization."""
        membership = obj.team_memberships.filter(
            is_active=True,
            role__in=['owner', 'admin']
        ).first()
        
        if membership:
            return {
                'id': str(membership.organization.id),
                'name': membership.organization.name,
                'role': membership.role
            }
        return None


class LoginSerializer(serializers.Serializer):
    """Login serializer for authentication."""
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    remember_me = serializers.BooleanField(default=False)


class TokenRefreshSerializer(serializers.Serializer):
    """Token refresh serializer."""
    
    refresh_token = serializers.CharField(required=True)


class PasswordChangeSerializer(serializers.Serializer):
    """Password change serializer for authenticated users."""
    
    old_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate new passwords match."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password': 'New password fields must match.'
            })
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Password reset request serializer."""
    
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Password reset confirmation serializer."""
    
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate new passwords match."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password': 'New password fields must match.'
            })
        return attrs


class OrganizationSerializer(serializers.ModelSerializer):
    """Organization serializer."""
    
    owner = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Organization
        fields = (
            'id', 'name', 'slug', 'description', 'owner',
            'subscription_status', 'subscription_tier',
            'max_team_members', 'max_chatbots',
            'member_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'slug', 'owner', 'created_at', 'updated_at')
    
    def get_member_count(self, obj):
        """Get active member count."""
        return obj.members.filter(is_active=True).count()


class TeamMemberSerializer(serializers.ModelSerializer):
    """Team member serializer."""
    
    user = UserSerializer(read_only=True)
    user_email = serializers.EmailField(write_only=True, required=False)
    
    class Meta:
        model = TeamMember
        fields = (
            'id', 'user', 'user_email', 'organization', 'role',
            'is_active', 'invited_at', 'joined_at'
        )
        read_only_fields = ('id', 'user', 'invited_at', 'joined_at')
    
    def create(self, validated_data):
        """Create team member invitation."""
        email = validated_data.pop('user_email', None)
        if email:
            # Find or invite user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'is_active': False}  # Inactive until they accept
            )
            validated_data['user'] = user
        
        return super().create(validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    """User profile serializer."""
    
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = (
            'id', 'user', 'avatar_url', 'bio', 'timezone',
            'language', 'notification_preferences', 'metadata',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')


class OAuth2AuthorizeSerializer(serializers.Serializer):
    """OAuth2 authorization serializer."""
    
    provider = serializers.ChoiceField(choices=['google', 'github', 'microsoft'])
    redirect_uri = serializers.URLField(required=False)
    state = serializers.CharField(required=False)


class OAuth2CallbackSerializer(serializers.Serializer):
    """OAuth2 callback serializer."""
    
    code = serializers.CharField(required=True)
    state = serializers.CharField(required=False)