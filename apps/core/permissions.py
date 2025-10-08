"""
Custom Permission Classes for API Security Framework.
Implements resource ownership, organization membership, and API key permissions.
"""

import structlog
from typing import Any
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.core.cache import cache

from apps.accounts.models import Organization, TeamMember

logger = structlog.get_logger()
User = get_user_model()


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Assumes the model instance has an `owner` or `user` field.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        """
        Instance-level permission that doesn't require a specific object.
        Always allows authenticated access for list views.
        """
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        """
        Object-level permission to only allow owners to modify objects.
        Read permissions are allowed to authenticated users.
        Write permissions are only allowed to the owner of the object.
        """
        # Read permissions for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for the owner
        owner = self._get_object_owner(obj)
        if not owner:
            logger.warning(
                "Permission denied - object has no identifiable owner",
                user_id=str(request.user.id),
                object_type=type(obj).__name__,
                object_id=getattr(obj, 'id', 'unknown')
            )
            return False

        is_owner = owner == request.user
        
        if not is_owner:
            logger.info(
                "Permission denied - user is not object owner",
                user_id=str(request.user.id),
                owner_id=str(owner.id),
                object_type=type(obj).__name__,
                object_id=getattr(obj, 'id', 'unknown')
            )
        
        return is_owner

    def _get_object_owner(self, obj: Any) -> User:
        """
        Extract the owner from an object.
        Handles common ownership patterns: owner, user, created_by fields.
        """
        # Try common owner field names
        for field_name in ['owner', 'user', 'created_by']:
            if hasattr(obj, field_name):
                owner = getattr(obj, field_name)
                if isinstance(owner, User):
                    return owner
        
        # For organization-owned resources
        if hasattr(obj, 'organization'):
            org = obj.organization
            # Find the organization owner
            owner_membership = TeamMember.objects.filter(
                organization=org,
                role='owner',
                is_active=True
            ).select_related('user').first()
            
            if owner_membership:
                return owner_membership.user
        
        return None


class IsOrganizationMember(permissions.BasePermission):
    """
    Permission to check if user is a member of the organization
    that owns the resource.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if user is authenticated."""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        """
        Check if user is a member of the organization that owns the object.
        """
        organization = self._get_object_organization(obj)
        if not organization:
            # If no organization is associated, fall back to owner check
            return IsOwnerOrReadOnly().has_object_permission(request, view, obj)

        # Check if user is a member of the organization
        is_member = self._is_organization_member(request.user, organization)
        
        if not is_member:
            logger.info(
                "Permission denied - user not in organization",
                user_id=str(request.user.id),
                organization_id=str(organization.id),
                object_type=type(obj).__name__
            )
        
        return is_member

    def _get_object_organization(self, obj: Any) -> Organization:
        """Extract organization from object."""
        # Direct organization field
        if hasattr(obj, 'organization'):
            return obj.organization
        
        # Through user relationship
        if hasattr(obj, 'user'):
            user = obj.user
            # Get user's primary organization (where they are owner/admin)
            membership = TeamMember.objects.filter(
                user=user,
                role__in=['owner', 'admin'],
                is_active=True
            ).select_related('organization').first()
            
            if membership:
                return membership.organization
        
        return None

    def _is_organization_member(self, user: User, organization: Organization) -> bool:
        """
        Check if user is a member of the organization.
        Uses caching for performance.
        """
        cache_key = f"org_member:{user.id}:{organization.id}"
        
        # Check cache first
        is_member = cache.get(cache_key)
        if is_member is not None:
            return is_member
        
        # Query database
        membership = TeamMember.objects.filter(
            user=user,
            organization=organization,
            is_active=True
        ).exists()
        
        # Cache result for 5 minutes
        cache.set(cache_key, membership, 300)
        
        return membership


class IsOrganizationAdminOrOwner(IsOrganizationMember):
    """
    Permission that requires user to be an admin or owner of the organization.
    """

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        """Check if user is admin or owner of the organization."""
        organization = self._get_object_organization(obj)
        if not organization:
            return IsOwnerOrReadOnly().has_object_permission(request, view, obj)

        # Check if user is admin or owner
        is_admin_or_owner = self._is_organization_admin_or_owner(request.user, organization)
        
        if not is_admin_or_owner:
            logger.info(
                "Permission denied - user not admin/owner of organization",
                user_id=str(request.user.id),
                organization_id=str(organization.id),
                object_type=type(obj).__name__
            )
        
        return is_admin_or_owner

    def _is_organization_admin_or_owner(self, user: User, organization: Organization) -> bool:
        """Check if user is admin or owner of organization."""
        cache_key = f"org_admin:{user.id}:{organization.id}"
        
        # Check cache first
        is_admin = cache.get(cache_key)
        if is_admin is not None:
            return is_admin
        
        # Query database
        is_admin = TeamMember.objects.filter(
            user=user,
            organization=organization,
            role__in=['owner', 'admin'],
            is_active=True
        ).exists()
        
        # Cache result for 5 minutes
        cache.set(cache_key, is_admin, 300)
        
        return is_admin


class HasAPIKeyAccess(permissions.BasePermission):
    """
    Permission for API key-based access.
    Allows external systems to access specific endpoints with API keys.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        """
        Check if request has valid API key authentication.
        """
        # Check for API key in headers
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            # Also check Authorization header with 'ApiKey' scheme
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('ApiKey '):
                api_key = auth_header.split(' ', 1)[1]

        if not api_key:
            logger.warning(
                "API access denied - no API key provided",
                ip_address=self._get_client_ip(request),
                endpoint=request.path
            )
            return False

        # Validate API key
        is_valid = self._validate_api_key(api_key, request)
        
        if not is_valid:
            logger.warning(
                "API access denied - invalid API key",
                ip_address=self._get_client_ip(request),
                endpoint=request.path,
                api_key_hint=f"{api_key[:8]}..." if len(api_key) > 8 else "short_key"
            )
        
        return is_valid

    def _validate_api_key(self, api_key: str, request: Request) -> bool:
        """
        Validate API key against stored keys.
        
        Args:
            api_key: The API key to validate
            request: The HTTP request
            
        Returns:
            bool: True if API key is valid
        """
        try:
            # TODO: Implement API key model and validation
            # For now, this is a placeholder that would:
            # 1. Look up API key in database
            # 2. Check if key is active and not expired
            # 3. Check if key has access to requested endpoint
            # 4. Update last used timestamp
            # 5. Log API usage for monitoring
            
            # Placeholder implementation - replace with actual API key model
            from django.conf import settings
            
            # In development, accept a hardcoded API key for testing
            if hasattr(settings, 'DEBUG') and settings.DEBUG:
                test_api_key = getattr(settings, 'TEST_API_KEY', 'test_api_key_12345')
                if api_key == test_api_key:
                    logger.info(
                        "API access granted - test key in development",
                        ip_address=self._get_client_ip(request),
                        endpoint=request.path
                    )
                    return True
            
            # In production, implement proper API key validation
            logger.warning(
                "API key validation not fully implemented",
                ip_address=self._get_client_ip(request)
            )
            return False
            
        except Exception as e:
            logger.error(
                "API key validation error",
                error=str(e),
                ip_address=self._get_client_ip(request)
            )
            return False

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip


class HasPlanAccess(permissions.BasePermission):
    """
    Permission to check if user's plan allows access to specific features.
    """

    def __init__(self, required_plan: str = 'free'):
        """
        Initialize with required plan level.
        
        Args:
            required_plan: Minimum plan required ('free', 'pro', 'enterprise')
        """
        self.required_plan = required_plan
        self.plan_hierarchy = {
            'free': 0,
            'pro': 1, 
            'enterprise': 2
        }

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if user's plan allows access."""
        if not request.user or not request.user.is_authenticated:
            return False

        user_plan = getattr(request.user, 'plan_tier', 'free')
        user_plan_level = self.plan_hierarchy.get(user_plan, 0)
        required_plan_level = self.plan_hierarchy.get(self.required_plan, 0)
        
        has_access = user_plan_level >= required_plan_level
        
        if not has_access:
            logger.info(
                "Permission denied - insufficient plan",
                user_id=str(request.user.id),
                user_plan=user_plan,
                required_plan=self.required_plan,
                endpoint=request.path
            )
        
        return has_access