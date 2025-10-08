"""
User and authentication models.
"""

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
from django.core.validators import EmailValidator
import structlog

from apps.core.models import BaseModel, PlanTier, JSONField

logger = structlog.get_logger()


class UserManager(BaseUserManager):
    """Custom user manager."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user."""
        if not email:
            raise ValueError('Email is required')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """
    Custom user model with email as username field.
    Includes subscription and usage tracking.
    """
    
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        help_text="User's email address"
    )
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    
    # Authentication fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    
    # Subscription and billing
    plan_tier = models.CharField(
        max_length=20,
        choices=PlanTier.choices,
        default=PlanTier.FREE
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True
    )
    subscription_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    subscription_status = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )
    subscription_current_period_end = models.DateTimeField(
        null=True,
        blank=True
    )
    
    # Usage tracking
    message_quota = models.PositiveIntegerField(
        default=100,
        help_text="Monthly message quota"
    )
    messages_used = models.PositiveIntegerField(
        default=0,
        help_text="Messages used this period"
    )
    quota_reset_date = models.DateTimeField(
        default=timezone.now,
        help_text="When quota resets"
    )
    
    # OAuth fields
    google_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True
    )
    
    # Profile
    avatar_url = models.URLField(null=True, blank=True)
    timezone = models.CharField(
        max_length=50,
        default='UTC'
    )
    
    # Metadata
    metadata = JSONField(
        help_text="Additional user metadata"
    )
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['plan_tier']),
            models.Index(fields=['stripe_customer_id']),
            models.Index(fields=['is_active', 'is_email_verified']),
        ]
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self) -> str:
        """Return full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def display_name(self) -> str:
        """Return display name."""
        return self.full_name or self.email
    
    @property
    def has_quota_remaining(self) -> bool:
        """Check if user has message quota remaining."""
        return self.messages_used < self.message_quota
    
    @property
    def quota_percentage_used(self) -> float:
        """Get percentage of quota used."""
        if self.message_quota == 0:
            return 100.0
        return (self.messages_used / self.message_quota) * 100
    
    def consume_quota(self, count: int = 1) -> bool:
        """
        Consume message quota.
        
        Args:
            count: Number of messages to consume
            
        Returns:
            bool: True if quota was consumed, False if insufficient
        """
        if self.messages_used + count > self.message_quota:
            logger.warning(
                "Quota exceeded",
                user_id=str(self.id),
                current_usage=self.messages_used,
                quota=self.message_quota,
                requested=count
            )
            return False
        
        self.messages_used += count
        self.save(update_fields=['messages_used'])
        return True
    
    def reset_quota(self) -> None:
        """Reset message quota."""
        self.messages_used = 0
        self.quota_reset_date = timezone.now()
        self.save(update_fields=['messages_used', 'quota_reset_date'])
        
        logger.info(
            "Quota reset",
            user_id=str(self.id),
            quota=self.message_quota
        )
    
    def verify_email(self) -> None:
        """Mark email as verified."""
        self.is_email_verified = True
        self.email_verified_at = timezone.now()
        self.save(update_fields=['is_email_verified', 'email_verified_at'])
        
        logger.info(
            "Email verified",
            user_id=str(self.id),
            email=self.email
        )
    
    def upgrade_plan(self, plan_tier: str, stripe_subscription_id: str = None) -> None:
        """
        Upgrade user plan.
        
        Args:
            plan_tier: New plan tier
            stripe_subscription_id: Stripe subscription ID
        """
        old_plan = self.plan_tier
        self.plan_tier = plan_tier
        
        if stripe_subscription_id:
            self.subscription_id = stripe_subscription_id
        
        # Update quota based on plan
        quota_map = {
            PlanTier.FREE: 100,
            PlanTier.PRO: 1000,
            PlanTier.ENTERPRISE: 10000,
        }
        self.message_quota = quota_map.get(plan_tier, 100)
        
        self.save(update_fields=[
            'plan_tier',
            'subscription_id',
            'message_quota'
        ])
        
        logger.info(
            "Plan upgraded",
            user_id=str(self.id),
            old_plan=old_plan,
            new_plan=plan_tier,
            new_quota=self.message_quota
        )


class UserSession(BaseModel):
    """
    User session tracking for JWT tokens.
    Enables token revocation and session management.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    
    # JWT token info
    jti = models.CharField(
        max_length=255,
        unique=True,
        help_text="JWT ID for token revocation"
    )
    token_type = models.CharField(
        max_length=20,
        choices=[
            ('access', 'Access Token'),
            ('refresh', 'Refresh Token'),
        ]
    )
    
    # Session info
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    # Token lifecycle
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    metadata = JSONField()
    
    class Meta:
        db_table = 'user_sessions'
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
        indexes = [
            models.Index(fields=['jti']),
            models.Index(fields=['user', 'token_type']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['revoked_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.token_type} - {self.jti}"
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return timezone.now() > self.expires_at
    
    @property
    def is_revoked(self) -> bool:
        """Check if session is revoked."""
        return self.revoked_at is not None
    
    @property
    def is_valid(self) -> bool:
        """Check if session is valid (not expired or revoked)."""
        return not self.is_expired and not self.is_revoked
    
    def revoke(self) -> None:
        """Revoke the session."""
        self.revoked_at = timezone.now()
        self.save(update_fields=['revoked_at'])
        
        logger.info(
            "Session revoked",
            user_id=str(self.user.id),
            jti=self.jti,
            token_type=self.token_type
        )


class UserProfile(BaseModel):
    """
    Extended user profile information.
    Separate from User model to avoid bloating core table.
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    # Company/Organization
    company_name = models.CharField(max_length=255, blank=True)
    company_size = models.CharField(
        max_length=50,
        choices=[
            ('1-10', '1-10 employees'),
            ('11-50', '11-50 employees'),
            ('51-200', '51-200 employees'),
            ('201-1000', '201-1000 employees'),
            ('1000+', '1000+ employees'),
        ],
        blank=True
    )
    industry = models.CharField(max_length=255, blank=True)
    
    # Contact
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    
    # Preferences
    email_notifications = models.BooleanField(default=True)
    marketing_emails = models.BooleanField(default=True)
    
    # Onboarding
    onboarding_completed = models.BooleanField(default=False)
    onboarding_step = models.CharField(max_length=50, blank=True)
    
    # Analytics opt-in
    analytics_enabled = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.user.email} Profile"


class Organization(BaseModel):
    """
    Organization/company model for multi-user collaboration.
    """
    
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Settings
    plan_tier = models.CharField(
        max_length=20,
        choices=PlanTier.choices,
        default=PlanTier.FREE
    )
    
    # Subscription and billing
    stripe_customer_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True
    )
    subscription_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    
    # Usage tracking
    member_limit = models.PositiveIntegerField(
        default=5,
        help_text="Maximum number of team members"
    )
    chatbot_limit = models.PositiveIntegerField(
        default=3,
        help_text="Maximum number of chatbots"
    )
    
    # Contact info
    website = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    
    # Metadata
    metadata = JSONField(
        help_text="Additional organization metadata"
    )
    
    class Meta:
        db_table = 'organizations'
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['plan_tier']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def member_count(self) -> int:
        """Get current member count."""
        return self.members.count()
    
    @property
    def chatbot_count(self) -> int:
        """Get current chatbot count."""
        return self.chatbots.count()
    
    @property
    def can_add_member(self) -> bool:
        """Check if organization can add more members."""
        return self.member_count < self.member_limit
    
    @property
    def can_add_chatbot(self) -> bool:
        """Check if organization can add more chatbots."""
        return self.chatbot_count < self.chatbot_limit


class TeamMember(BaseModel):
    """
    Team member model for organization collaboration.
    """
    
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='members'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='team_memberships'
    )
    
    # Role and permissions
    role = models.CharField(
        max_length=20,
        choices=[
            ('owner', 'Owner'),
            ('admin', 'Administrator'),
            ('editor', 'Editor'),
            ('viewer', 'Viewer'),
        ],
        default='viewer'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    invited_at = models.DateTimeField(auto_now_add=True)
    joined_at = models.DateTimeField(null=True, blank=True)
    
    # Invitation details
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_invitations'
    )
    invitation_token = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True
    )
    
    class Meta:
        db_table = 'team_members'
        verbose_name = 'Team Member'
        verbose_name_plural = 'Team Members'
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['user']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'user'],
                name='unique_member_per_organization'
            )
        ]
    
    def __str__(self):
        return f"{self.user.email} ({self.role}) in {self.organization.name}"
    
    @property
    def can_invite_members(self) -> bool:
        """Check if member can invite other members."""
        return self.role in ['owner', 'admin']
    
    @property
    def can_manage_chatbots(self) -> bool:
        """Check if member can create/edit chatbots."""
        return self.role in ['owner', 'admin', 'editor']
    
    @property
    def can_view_analytics(self) -> bool:
        """Check if member can view analytics."""
        return self.role in ['owner', 'admin', 'editor']
