"""
Repository pattern implementation for data access layer.
Provides clean abstraction over database operations with type safety.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, TypeVar, Generic, Union
from dataclasses import dataclass
from datetime import datetime
import uuid

from django.db import models, transaction
from django.core.paginator import Paginator
from django.db.models import QuerySet, Q


T = TypeVar('T', bound=models.Model)


@dataclass
class PaginationResult(Generic[T]):
    """Paginated query result."""
    items: List[T]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


@dataclass
class FilterCriteria:
    """Generic filter criteria for queries."""
    field: str
    operator: str  # eq, ne, gt, gte, lt, lte, in, contains, icontains, startswith, endswith
    value: Any


@dataclass
class SortCriteria:
    """Sort criteria for queries."""
    field: str
    direction: str = "asc"  # asc, desc


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository with common CRUD operations.
    """
    
    def __init__(self, model_class: type[T]):
        self.model_class = model_class
    
    def get_by_id(self, id: Union[str, uuid.UUID, int]) -> Optional[T]:
        """
        Get entity by ID.
        
        Args:
            id: Entity ID
            
        Returns:
            Optional[T]: Entity or None if not found
        """
        try:
            return self.model_class.objects.get(id=id)
        except self.model_class.DoesNotExist:
            return None
    
    def get_by_criteria(self, criteria: Dict[str, Any]) -> Optional[T]:
        """
        Get single entity by criteria.
        
        Args:
            criteria: Filter criteria
            
        Returns:
            Optional[T]: Entity or None if not found
        """
        try:
            return self.model_class.objects.get(**criteria)
        except (self.model_class.DoesNotExist, self.model_class.MultipleObjectsReturned):
            return None
    
    def find_all(
        self,
        filters: Optional[List[FilterCriteria]] = None,
        sorts: Optional[List[SortCriteria]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[T]:
        """
        Find entities with filtering and sorting.
        
        Args:
            filters: Filter criteria
            sorts: Sort criteria
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List[T]: Matching entities
        """
        queryset = self.model_class.objects.all()
        
        # Apply filters
        if filters:
            queryset = self._apply_filters(queryset, filters)
        
        # Apply sorting
        if sorts:
            queryset = self._apply_sorts(queryset, sorts)
        
        # Apply pagination
        if offset:
            queryset = queryset[offset:]
        if limit:
            queryset = queryset[:limit]
        
        return list(queryset)
    
    def find_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[List[FilterCriteria]] = None,
        sorts: Optional[List[SortCriteria]] = None
    ) -> PaginationResult[T]:
        """
        Find entities with pagination.
        
        Args:
            page: Page number (1-based)
            page_size: Number of items per page
            filters: Filter criteria
            sorts: Sort criteria
            
        Returns:
            PaginationResult[T]: Paginated results
        """
        queryset = self.model_class.objects.all()
        
        # Apply filters
        if filters:
            queryset = self._apply_filters(queryset, filters)
        
        # Apply sorting
        if sorts:
            queryset = self._apply_sorts(queryset, sorts)
        
        # Paginate
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        return PaginationResult(
            items=list(page_obj.object_list),
            total_count=paginator.count,
            page=page_obj.number,
            page_size=page_size,
            total_pages=paginator.num_pages,
            has_next=page_obj.has_next(),
            has_previous=page_obj.has_previous()
        )
    
    def count(self, filters: Optional[List[FilterCriteria]] = None) -> int:
        """
        Count entities matching criteria.
        
        Args:
            filters: Filter criteria
            
        Returns:
            int: Count of matching entities
        """
        queryset = self.model_class.objects.all()
        
        if filters:
            queryset = self._apply_filters(queryset, filters)
        
        return queryset.count()
    
    def exists(self, criteria: Dict[str, Any]) -> bool:
        """
        Check if entity exists with given criteria.
        
        Args:
            criteria: Filter criteria
            
        Returns:
            bool: True if entity exists
        """
        return self.model_class.objects.filter(**criteria).exists()
    
    def create(self, data: Dict[str, Any]) -> T:
        """
        Create new entity.
        
        Args:
            data: Entity data
            
        Returns:
            T: Created entity
        """
        return self.model_class.objects.create(**data)
    
    def bulk_create(self, data_list: List[Dict[str, Any]]) -> List[T]:
        """
        Create multiple entities in bulk.
        
        Args:
            data_list: List of entity data
            
        Returns:
            List[T]: Created entities
        """
        entities = [self.model_class(**data) for data in data_list]
        return self.model_class.objects.bulk_create(entities)
    
    def update(self, id: Union[str, uuid.UUID, int], data: Dict[str, Any]) -> Optional[T]:
        """
        Update entity by ID.
        
        Args:
            id: Entity ID
            data: Update data
            
        Returns:
            Optional[T]: Updated entity or None if not found
        """
        try:
            entity = self.model_class.objects.get(id=id)
            for key, value in data.items():
                setattr(entity, key, value)
            entity.save()
            return entity
        except self.model_class.DoesNotExist:
            return None
    
    def update_by_criteria(
        self,
        criteria: Dict[str, Any],
        data: Dict[str, Any]
    ) -> int:
        """
        Update entities matching criteria.
        
        Args:
            criteria: Filter criteria
            data: Update data
            
        Returns:
            int: Number of updated entities
        """
        return self.model_class.objects.filter(**criteria).update(**data)
    
    def delete(self, id: Union[str, uuid.UUID, int]) -> bool:
        """
        Delete entity by ID.
        
        Args:
            id: Entity ID
            
        Returns:
            bool: True if entity was deleted
        """
        try:
            entity = self.model_class.objects.get(id=id)
            entity.delete()
            return True
        except self.model_class.DoesNotExist:
            return False
    
    def delete_by_criteria(self, criteria: Dict[str, Any]) -> int:
        """
        Delete entities matching criteria.
        
        Args:
            criteria: Filter criteria
            
        Returns:
            int: Number of deleted entities
        """
        deleted, _ = self.model_class.objects.filter(**criteria).delete()
        return deleted
    
    def _apply_filters(self, queryset: QuerySet[T], filters: List[FilterCriteria]) -> QuerySet[T]:
        """Apply filter criteria to queryset."""
        for filter_criteria in filters:
            field = filter_criteria.field
            operator = filter_criteria.operator
            value = filter_criteria.value
            
            if operator == "eq":
                queryset = queryset.filter(**{field: value})
            elif operator == "ne":
                queryset = queryset.exclude(**{field: value})
            elif operator == "gt":
                queryset = queryset.filter(**{f"{field}__gt": value})
            elif operator == "gte":
                queryset = queryset.filter(**{f"{field}__gte": value})
            elif operator == "lt":
                queryset = queryset.filter(**{f"{field}__lt": value})
            elif operator == "lte":
                queryset = queryset.filter(**{f"{field}__lte": value})
            elif operator == "in":
                queryset = queryset.filter(**{f"{field}__in": value})
            elif operator == "contains":
                queryset = queryset.filter(**{f"{field}__contains": value})
            elif operator == "icontains":
                queryset = queryset.filter(**{f"{field}__icontains": value})
            elif operator == "startswith":
                queryset = queryset.filter(**{f"{field}__startswith": value})
            elif operator == "endswith":
                queryset = queryset.filter(**{f"{field}__endswith": value})
            elif operator == "isnull":
                queryset = queryset.filter(**{f"{field}__isnull": value})
            
        return queryset
    
    def _apply_sorts(self, queryset: QuerySet[T], sorts: List[SortCriteria]) -> QuerySet[T]:
        """Apply sort criteria to queryset."""
        order_fields = []
        
        for sort_criteria in sorts:
            field = sort_criteria.field
            direction = sort_criteria.direction
            
            if direction == "desc":
                field = f"-{field}"
            
            order_fields.append(field)
        
        if order_fields:
            queryset = queryset.order_by(*order_fields)
        
        return queryset


class UserRepository(BaseRepository):
    """Repository for User entities."""
    
    def __init__(self):
        from django.contrib.auth import get_user_model
        super().__init__(get_user_model())
    
    def get_by_email(self, email: str) -> Optional[models.Model]:
        """Get user by email."""
        return self.get_by_criteria({"email": email})
    
    def get_active_users(self) -> List[models.Model]:
        """Get all active users."""
        return self.find_all([FilterCriteria("is_active", "eq", True)])
    
    def search_by_name_or_email(self, query: str) -> List[models.Model]:
        """Search users by name or email."""
        from django.db.models import Q
        
        queryset = self.model_class.objects.filter(
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
        return list(queryset)


class KnowledgeSourceRepository(BaseRepository):
    """Repository for KnowledgeSource entities."""
    
    def __init__(self):
        from apps.knowledge.models import KnowledgeSource
        super().__init__(KnowledgeSource)
    
    def get_by_chatbot(self, chatbot_id: Union[str, int]) -> List[models.Model]:
        """Get knowledge sources by chatbot."""
        return self.find_all([FilterCriteria("chatbot_id", "eq", chatbot_id)])
    
    def get_citable_sources(self, chatbot_id: Union[str, int]) -> List[models.Model]:
        """Get citable knowledge sources."""
        return self.find_all([
            FilterCriteria("chatbot_id", "eq", chatbot_id),
            FilterCriteria("is_citable", "eq", True)
        ])


class DocumentRepository(BaseRepository):
    """Repository for Document entities (alias for KnowledgeSource)."""
    
    def __init__(self):
        from apps.knowledge.models import KnowledgeSource
        super().__init__(KnowledgeSource)
    
    def get_by_knowledge_base(self, kb_id: Union[str, int]) -> List[models.Model]:
        """Get documents by knowledge base."""
        return self.find_all([FilterCriteria("knowledge_base_id", "eq", kb_id)])
    
    def get_by_status(self, status: str) -> List[models.Model]:
        """Get documents by processing status."""
        return self.find_all([FilterCriteria("status", "eq", status)])
    
    def get_processable_documents(self) -> List[models.Model]:
        """Get documents ready for processing."""
        return self.find_all([
            FilterCriteria("status", "in", ["uploaded", "processing_failed"])
        ])


class DocumentChunkRepository(BaseRepository):
    """Repository for DocumentChunk entities (alias for KnowledgeChunk)."""
    
    def __init__(self):
        from apps.knowledge.models import KnowledgeChunk
        super().__init__(KnowledgeChunk)
    
    def get_by_document(self, document_id: Union[str, int]) -> List[models.Model]:
        """Get chunks by document."""
        return self.find_all([FilterCriteria("document_id", "eq", document_id)])
    
    def get_citable_chunks(
        self,
        knowledge_base_id: Union[str, int]
    ) -> List[models.Model]:
        """Get chunks that can be cited."""
        return self.find_all([
            FilterCriteria("document__knowledge_base_id", "eq", knowledge_base_id),
            FilterCriteria("document__privacy_level", "in", ["public", "citable"])
        ])
    
    def get_chunks_with_embeddings(
        self,
        knowledge_base_id: Union[str, int]
    ) -> List[models.Model]:
        """Get chunks that have embeddings."""
        return self.find_all([
            FilterCriteria("document__knowledge_base_id", "eq", knowledge_base_id),
            FilterCriteria("embedding_id", "ne", None)
        ])


class ChatbotRepository(BaseRepository):
    """Repository for Chatbot entities."""
    
    def __init__(self):
        from apps.chatbots.models import Chatbot
        super().__init__(Chatbot)
    
    def get_by_user(self, user_id: Union[str, int]) -> List[models.Model]:
        """Get chatbots by user."""
        return self.find_all([FilterCriteria("user_id", "eq", user_id)])
    
    def get_active_chatbots(self) -> List[models.Model]:
        """Get active chatbots."""
        return self.find_all([FilterCriteria("is_active", "eq", True)])


class ConversationRepository(BaseRepository):
    """Repository for Conversation entities."""
    
    def __init__(self):
        from apps.conversations.models import Conversation
        super().__init__(Conversation)
    
    def get_by_chatbot(self, chatbot_id: Union[str, int]) -> List[models.Model]:
        """Get conversations by chatbot."""
        return self.find_all([FilterCriteria("chatbot_id", "eq", chatbot_id)])
    
    def get_recent_conversations(
        self,
        user_id: Union[str, int],
        days: int = 7
    ) -> List[models.Model]:
        """Get recent conversations for user."""
        from django.utils import timezone
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        return self.find_all([
            FilterCriteria("chatbot__user_id", "eq", user_id),
            FilterCriteria("created_at", "gte", cutoff_date)
        ])


class MessageRepository(BaseRepository):
    """Repository for Message entities."""
    
    def __init__(self):
        from apps.conversations.models import Message
        super().__init__(Message)
    
    def get_by_conversation(self, conversation_id: Union[str, int]) -> List[models.Model]:
        """Get messages by conversation."""
        return self.find_all(
            [FilterCriteria("conversation_id", "eq", conversation_id)],
            [SortCriteria("created_at", "asc")]
        )
    
    def get_conversation_history(
        self,
        conversation_id: Union[str, int],
        limit: int = 50
    ) -> List[models.Model]:
        """Get recent conversation history."""
        return self.find_all(
            [FilterCriteria("conversation_id", "eq", conversation_id)],
            [SortCriteria("created_at", "desc")],
            limit=limit
        )


# Repository registry for dependency injection
class RepositoryRegistry:
    """Registry for repository instances."""
    
    def __init__(self):
        self._repositories = {}
    
    def register(self, name: str, repository: BaseRepository) -> None:
        """Register repository instance."""
        self._repositories[name] = repository
    
    def get(self, name: str) -> BaseRepository:
        """Get repository instance."""
        if name not in self._repositories:
            raise ValueError(f"Repository '{name}' not registered")
        return self._repositories[name]
    
    def get_user_repository(self) -> UserRepository:
        """Get user repository."""
        return self.get("user")
    
    def get_knowledge_source_repository(self) -> KnowledgeSourceRepository:
        """Get knowledge source repository."""
        return self.get("knowledge_source")
    
    def get_document_repository(self) -> DocumentRepository:
        """Get document repository."""
        return self.get("document")
    
    def get_document_chunk_repository(self) -> DocumentChunkRepository:
        """Get document chunk repository."""
        return self.get("document_chunk")
    
    def get_chatbot_repository(self) -> ChatbotRepository:
        """Get chatbot repository."""
        return self.get("chatbot")
    
    def get_conversation_repository(self) -> ConversationRepository:
        """Get conversation repository."""
        return self.get("conversation")
    
    def get_message_repository(self) -> MessageRepository:
        """Get message repository."""
        return self.get("message")


# Global repository registry
repository_registry = RepositoryRegistry()

# Register default repositories
repository_registry.register("user", UserRepository())
repository_registry.register("knowledge_source", KnowledgeSourceRepository())
repository_registry.register("document", DocumentRepository())
repository_registry.register("document_chunk", DocumentChunkRepository())
repository_registry.register("chatbot", ChatbotRepository())
repository_registry.register("conversation", ConversationRepository())
repository_registry.register("message", MessageRepository())