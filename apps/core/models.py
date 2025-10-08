"""
Base models and mixins for the application.
Includes soft delete functionality and common fields.
"""

from django.db import models
from django.utils import timezone
from typing import Any, Dict, List, Optional
import uuid


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet for soft delete functionality."""
    
    def active(self):
        """Return only non-deleted objects."""
        return self.filter(deleted_at__isnull=True)
    
    def deleted(self):
        """Return only deleted objects."""
        return self.filter(deleted_at__isnull=False)
    
    def delete(self):
        """Soft delete all objects in queryset."""
        return self.update(deleted_at=timezone.now())
    
    def hard_delete(self):
        """Permanently delete all objects in queryset."""
        return super().delete()


class SoftDeleteManager(models.Manager):
    """Manager for soft delete functionality."""
    
    def get_queryset(self):
        """Return queryset filtered to active objects only."""
        return SoftDeleteQuerySet(self.model, using=self._db).active()
    
    def all_with_deleted(self):
        """Return all objects including deleted ones."""
        return SoftDeleteQuerySet(self.model, using=self._db)
    
    def deleted_only(self):
        """Return only deleted objects."""
        return SoftDeleteQuerySet(self.model, using=self._db).deleted()


class TimestampedModel(models.Model):
    """Abstract model with created and updated timestamps."""
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    
    class Meta:
        abstract = True


class SoftDeleteModel(TimestampedModel):
    """Abstract model with soft delete functionality."""
    
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Access to all objects including deleted
    
    class Meta:
        abstract = True
    
    def delete(self, using=None, keep_parents=False):
        """Soft delete the object."""
        self.deleted_at = timezone.now()
        self.save(using=using, update_fields=['deleted_at'])
    
    def hard_delete(self, using=None, keep_parents=False):
        """Permanently delete the object."""
        super().delete(using=using, keep_parents=keep_parents)
    
    def restore(self):
        """Restore a soft-deleted object."""
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])
    
    @property
    def is_deleted(self) -> bool:
        """Check if object is soft-deleted."""
        return self.deleted_at is not None


class UUIDModel(models.Model):
    """Abstract model with UUID primary key."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class Meta:
        abstract = True


class AuditModel(TimestampedModel):
    """Abstract model with audit trail functionality."""
    
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created'
    )
    updated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated'
    )
    
    class Meta:
        abstract = True


class BaseModel(UUIDModel, SoftDeleteModel, AuditModel):
    """
    Base model with all common functionality:
    - UUID primary key
    - Timestamps
    - Soft delete
    - Audit trail
    """
    
    class Meta:
        abstract = True
    
    def __str__(self):
        """String representation using name field if available."""
        if hasattr(self, 'name') and self.name:
            return self.name
        return f"{self.__class__.__name__}({self.id})"


class JSONField(models.JSONField):
    """Enhanced JSON field with validation."""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', dict)
        super().__init__(*args, **kwargs)


# Enums for common choices
class PlanTier(models.TextChoices):
    """User plan tiers."""
    FREE = 'free', 'Free'
    PRO = 'pro', 'Pro'
    ENTERPRISE = 'enterprise', 'Enterprise'


class ProcessingStatus(models.TextChoices):
    """Processing status for async operations."""
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'


class ContentType(models.TextChoices):
    """Content types for knowledge sources."""
    PDF = 'pdf', 'PDF Document'
    DOCX = 'docx', 'Word Document'
    TXT = 'txt', 'Text File'
    URL = 'url', 'Web Page'
    VIDEO = 'video', 'Video'


class MessageRole(models.TextChoices):
    """Chat message roles."""
    USER = 'user', 'User'
    ASSISTANT = 'assistant', 'Assistant'
    SYSTEM = 'system', 'System'