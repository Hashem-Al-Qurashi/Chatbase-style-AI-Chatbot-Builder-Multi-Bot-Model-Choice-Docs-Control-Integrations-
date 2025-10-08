"""
Domain services layer implementing business logic.
Provides clean separation between business rules and data access.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import uuid
import logging

from django.db import transaction
from django.utils import timezone
from django.core.cache import cache

from apps.core.repositories import (
    repository_registry,
    FilterCriteria,
    SortCriteria,
    PaginationResult
)
from apps.core.auth import jwt_manager, session_manager, password_security
from apps.core.oauth import oauth_session_manager
from apps.core.rate_limiting import rate_limiter, RateLimitType
from chatbot_saas.config import get_settings


settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class ServiceResult:
    """Standard service result wrapper."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AuthenticationResult:
    """Authentication service result."""
    success: bool
    user_data: Optional[Dict[str, Any]] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    session_id: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


class BaseService(ABC):
    """Base service class with common functionality."""
    
    def __init__(self):
        self.repository_registry = repository_registry
    
    def _create_success_result(self, data: Any = None, metadata: Dict[str, Any] = None) -> ServiceResult:
        """Create successful service result."""
        return ServiceResult(success=True, data=data, metadata=metadata)
    
    def _create_error_result(
        self,
        error: str,
        error_code: str = None,
        data: Any = None
    ) -> ServiceResult:
        """Create error service result."""
        return ServiceResult(
            success=False,
            data=data,
            error=error,
            error_code=error_code
        )


class UserService(BaseService):
    """User management service."""
    
    def __init__(self):
        super().__init__()
        self.user_repository = self.repository_registry.get_user_repository()
    
    def create_user(
        self,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        **kwargs
    ) -> ServiceResult:
        """
        Create new user account.
        
        Args:
            email: User email
            password: User password
            first_name: User first name
            last_name: User last name
            **kwargs: Additional user data
            
        Returns:
            ServiceResult: Creation result with user data
        """
        try:
            # Validate email uniqueness
            if self.user_repository.get_by_email(email):
                return self._create_error_result(
                    "Email already registered",
                    "EMAIL_EXISTS"
                )
            
            # Validate password strength
            is_valid, password_errors = password_security.validate_password_strength(password)
            if not is_valid:
                return self._create_error_result(
                    "; ".join(password_errors),
                    "WEAK_PASSWORD"
                )
            
            # Hash password
            hashed_password = password_security.hash_password(password)
            
            # Create user
            user_data = {
                "email": email,
                "password": hashed_password,
                "first_name": first_name,
                "last_name": last_name,
                "is_active": True,
                **kwargs
            }
            
            with transaction.atomic():
                user = self.user_repository.create(user_data)
            
            # Return user data (excluding password)
            user_dict = {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "date_joined": user.date_joined.isoformat() if hasattr(user, 'date_joined') else None
            }
            
            logger.info(f"User created successfully: {email}")
            return self._create_success_result(user_dict)
            
        except Exception as e:
            logger.error(f"User creation failed: {str(e)}")
            return self._create_error_result(
                "User creation failed",
                "CREATION_ERROR"
            )
    
    def authenticate_user(self, email: str, password: str) -> AuthenticationResult:
        """
        Authenticate user with email and password.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            AuthenticationResult: Authentication result
        """
        try:
            # Get user by email
            user = self.user_repository.get_by_email(email)
            if not user:
                return AuthenticationResult(
                    success=False,
                    error="Invalid credentials",
                    error_code="INVALID_CREDENTIALS"
                )
            
            # Check if user is active
            if not user.is_active:
                return AuthenticationResult(
                    success=False,
                    error="Account is deactivated",
                    error_code="ACCOUNT_DEACTIVATED"
                )
            
            # Verify password
            if not password_security.verify_password(password, user.password):
                return AuthenticationResult(
                    success=False,
                    error="Invalid credentials",
                    error_code="INVALID_CREDENTIALS"
                )
            
            # Generate tokens
            access_token, refresh_token = jwt_manager.generate_tokens(
                user_id=str(user.id),
                email=user.email,
                scopes=["read", "write"]
            )
            
            # Create session
            session_id = session_manager.create_session(
                user_id=str(user.id),
                device_info={},  # This should come from request
                ip_address=""   # This should come from request
            )
            
            user_data = {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active
            }
            
            logger.info(f"User authenticated successfully: {email}")
            return AuthenticationResult(
                success=True,
                user_data=user_data,
                access_token=access_token,
                refresh_token=refresh_token,
                session_id=session_id
            )
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return AuthenticationResult(
                success=False,
                error="Authentication failed",
                error_code="AUTH_ERROR"
            )
    
    def update_user(self, user_id: str, data: Dict[str, Any]) -> ServiceResult:
        """
        Update user information.
        
        Args:
            user_id: User ID
            data: Update data
            
        Returns:
            ServiceResult: Update result
        """
        try:
            # Handle password updates separately
            if "password" in data:
                new_password = data.pop("password")
                is_valid, password_errors = password_security.validate_password_strength(new_password)
                if not is_valid:
                    return self._create_error_result(
                        "; ".join(password_errors),
                        "WEAK_PASSWORD"
                    )
                data["password"] = password_security.hash_password(new_password)
            
            # Update user
            user = self.user_repository.update(user_id, data)
            if not user:
                return self._create_error_result(
                    "User not found",
                    "USER_NOT_FOUND"
                )
            
            user_dict = {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active
            }
            
            return self._create_success_result(user_dict)
            
        except Exception as e:
            logger.error(f"User update failed: {str(e)}")
            return self._create_error_result(
                "User update failed",
                "UPDATE_ERROR"
            )


class KnowledgeSourceService(BaseService):
    """Knowledge source management service."""
    
    def __init__(self):
        super().__init__()
        self.source_repository = self.repository_registry.get_knowledge_source_repository()
        self.document_repository = self.repository_registry.get_document_repository()
    
    def create_knowledge_base(
        self,
        user_id: str,
        name: str,
        description: str = "",
        privacy_level: str = "private",
        **kwargs
    ) -> ServiceResult:
        """
        Create new knowledge base.
        
        Args:
            user_id: Owner user ID
            name: Knowledge base name
            description: Knowledge base description
            privacy_level: Privacy level (private, citable, public)
            **kwargs: Additional data
            
        Returns:
            ServiceResult: Creation result
        """
        try:
            # Validate privacy level
            valid_privacy_levels = ["private", "citable", "public"]
            if privacy_level not in valid_privacy_levels:
                return self._create_error_result(
                    f"Invalid privacy level. Must be one of: {', '.join(valid_privacy_levels)}",
                    "INVALID_PRIVACY_LEVEL"
                )
            
            kb_data = {
                "user_id": user_id,
                "name": name,
                "description": description,
                "privacy_level": privacy_level,
                "is_active": True,
                **kwargs
            }
            
            with transaction.atomic():
                kb = self.kb_repository.create(kb_data)
            
            kb_dict = {
                "id": str(kb.id),
                "name": kb.name,
                "description": kb.description,
                "privacy_level": kb.privacy_level,
                "is_active": kb.is_active,
                "created_at": kb.created_at.isoformat() if hasattr(kb, 'created_at') else None
            }
            
            logger.info(f"Knowledge base created: {name} by user {user_id}")
            return self._create_success_result(kb_dict)
            
        except Exception as e:
            logger.error(f"Knowledge base creation failed: {str(e)}")
            return self._create_error_result(
                "Knowledge base creation failed",
                "CREATION_ERROR"
            )
    
    def get_user_knowledge_bases(self, user_id: str) -> ServiceResult:
        """
        Get knowledge bases for user.
        
        Args:
            user_id: User ID
            
        Returns:
            ServiceResult: List of knowledge bases
        """
        try:
            knowledge_bases = self.kb_repository.get_by_user(user_id)
            
            kb_list = []
            for kb in knowledge_bases:
                # Get document count
                doc_count = self.document_repository.count([
                    FilterCriteria("knowledge_base_id", "eq", kb.id)
                ])
                
                kb_dict = {
                    "id": str(kb.id),
                    "name": kb.name,
                    "description": kb.description,
                    "privacy_level": kb.privacy_level,
                    "is_active": kb.is_active,
                    "document_count": doc_count,
                    "created_at": kb.created_at.isoformat() if hasattr(kb, 'created_at') else None
                }
                kb_list.append(kb_dict)
            
            return self._create_success_result(kb_list)
            
        except Exception as e:
            logger.error(f"Failed to get knowledge bases for user {user_id}: {str(e)}")
            return self._create_error_result(
                "Failed to retrieve knowledge bases",
                "RETRIEVAL_ERROR"
            )


class DocumentService(BaseService):
    """Document management service."""
    
    def __init__(self):
        super().__init__()
        self.document_repository = self.repository_registry.get_document_repository()
        self.source_repository = self.repository_registry.get_knowledge_source_repository()
    
    def upload_document(
        self,
        user_id: str,
        knowledge_base_id: str,
        filename: str,
        file_url: str,
        content_type: str,
        file_size: int,
        **kwargs
    ) -> ServiceResult:
        """
        Upload document to knowledge base.
        
        Args:
            user_id: User ID
            knowledge_base_id: Knowledge base ID
            filename: Original filename
            file_url: Storage URL
            content_type: MIME type
            file_size: File size in bytes
            **kwargs: Additional metadata
            
        Returns:
            ServiceResult: Upload result
        """
        try:
            # Verify knowledge base ownership
            kb = self.kb_repository.get_by_id(knowledge_base_id)
            if not kb or str(kb.user_id) != user_id:
                return self._create_error_result(
                    "Knowledge base not found or access denied",
                    "ACCESS_DENIED"
                )
            
            # Validate file size
            max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # Convert to bytes
            if file_size > max_size:
                return self._create_error_result(
                    f"File size exceeds maximum limit of {settings.MAX_FILE_SIZE_MB}MB",
                    "FILE_TOO_LARGE"
                )
            
            # Validate content type
            allowed_types = [
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "text/plain",
                "text/markdown"
            ]
            if content_type not in allowed_types:
                return self._create_error_result(
                    "Unsupported file type",
                    "UNSUPPORTED_FILE_TYPE"
                )
            
            doc_data = {
                "knowledge_base_id": knowledge_base_id,
                "filename": filename,
                "file_url": file_url,
                "content_type": content_type,
                "file_size": file_size,
                "status": "uploaded",
                "privacy_level": kb.privacy_level,  # Inherit from knowledge base
                **kwargs
            }
            
            with transaction.atomic():
                document = self.document_repository.create(doc_data)
            
            doc_dict = {
                "id": str(document.id),
                "filename": document.filename,
                "content_type": document.content_type,
                "file_size": document.file_size,
                "status": document.status,
                "privacy_level": document.privacy_level,
                "created_at": document.created_at.isoformat() if hasattr(document, 'created_at') else None
            }
            
            logger.info(f"Document uploaded: {filename} to KB {knowledge_base_id}")
            return self._create_success_result(doc_dict)
            
        except Exception as e:
            logger.error(f"Document upload failed: {str(e)}")
            return self._create_error_result(
                "Document upload failed",
                "UPLOAD_ERROR"
            )
    
    def get_knowledge_base_documents(
        self,
        user_id: str,
        knowledge_base_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> ServiceResult:
        """
        Get documents for knowledge base.
        
        Args:
            user_id: User ID
            knowledge_base_id: Knowledge base ID
            page: Page number
            page_size: Items per page
            
        Returns:
            ServiceResult: Paginated documents
        """
        try:
            # Verify knowledge base access
            kb = self.kb_repository.get_by_id(knowledge_base_id)
            if not kb or str(kb.user_id) != user_id:
                return self._create_error_result(
                    "Knowledge base not found or access denied",
                    "ACCESS_DENIED"
                )
            
            # Get paginated documents
            result = self.document_repository.find_paginated(
                page=page,
                page_size=page_size,
                filters=[FilterCriteria("knowledge_base_id", "eq", knowledge_base_id)],
                sorts=[SortCriteria("created_at", "desc")]
            )
            
            # Convert to dict format
            documents = []
            for doc in result.items:
                doc_dict = {
                    "id": str(doc.id),
                    "filename": doc.filename,
                    "content_type": doc.content_type,
                    "file_size": doc.file_size,
                    "status": doc.status,
                    "privacy_level": doc.privacy_level,
                    "created_at": doc.created_at.isoformat() if hasattr(doc, 'created_at') else None
                }
                documents.append(doc_dict)
            
            response_data = {
                "documents": documents,
                "pagination": {
                    "page": result.page,
                    "page_size": result.page_size,
                    "total_count": result.total_count,
                    "total_pages": result.total_pages,
                    "has_next": result.has_next,
                    "has_previous": result.has_previous
                }
            }
            
            return self._create_success_result(response_data)
            
        except Exception as e:
            logger.error(f"Failed to get documents for KB {knowledge_base_id}: {str(e)}")
            return self._create_error_result(
                "Failed to retrieve documents",
                "RETRIEVAL_ERROR"
            )


class ChatbotService(BaseService):
    """Chatbot management service."""
    
    def __init__(self):
        super().__init__()
        self.chatbot_repository = self.repository_registry.get_chatbot_repository()
        self.source_repository = self.repository_registry.get_knowledge_source_repository()
    
    def create_chatbot(
        self,
        user_id: str,
        name: str,
        description: str = "",
        knowledge_base_ids: Optional[List[str]] = None,
        **kwargs
    ) -> ServiceResult:
        """
        Create new chatbot.
        
        Args:
            user_id: Owner user ID
            name: Chatbot name
            description: Chatbot description
            knowledge_base_ids: List of knowledge base IDs
            **kwargs: Additional configuration
            
        Returns:
            ServiceResult: Creation result
        """
        try:
            # Validate knowledge base access if provided
            if knowledge_base_ids:
                for kb_id in knowledge_base_ids:
                    kb = self.kb_repository.get_by_id(kb_id)
                    if not kb or str(kb.user_id) != user_id:
                        return self._create_error_result(
                            f"Knowledge base {kb_id} not found or access denied",
                            "KB_ACCESS_DENIED"
                        )
            
            chatbot_data = {
                "user_id": user_id,
                "name": name,
                "description": description,
                "is_active": True,
                "knowledge_base_ids": knowledge_base_ids or [],
                **kwargs
            }
            
            with transaction.atomic():
                chatbot = self.chatbot_repository.create(chatbot_data)
            
            chatbot_dict = {
                "id": str(chatbot.id),
                "name": chatbot.name,
                "description": chatbot.description,
                "is_active": chatbot.is_active,
                "knowledge_base_ids": chatbot.knowledge_base_ids if hasattr(chatbot, 'knowledge_base_ids') else [],
                "created_at": chatbot.created_at.isoformat() if hasattr(chatbot, 'created_at') else None
            }
            
            logger.info(f"Chatbot created: {name} by user {user_id}")
            return self._create_success_result(chatbot_dict)
            
        except Exception as e:
            logger.error(f"Chatbot creation failed: {str(e)}")
            return self._create_error_result(
                "Chatbot creation failed",
                "CREATION_ERROR"
            )


# Service registry for dependency injection
class ServiceRegistry:
    """Registry for service instances."""
    
    def __init__(self):
        self._services = {}
    
    def register(self, name: str, service: BaseService) -> None:
        """Register service instance."""
        self._services[name] = service
    
    def get(self, name: str) -> BaseService:
        """Get service instance."""
        if name not in self._services:
            raise ValueError(f"Service '{name}' not registered")
        return self._services[name]
    
    def get_user_service(self) -> UserService:
        """Get user service."""
        return self.get("user")
    
    def get_knowledge_source_service(self) -> KnowledgeSourceService:
        """Get knowledge source service."""
        return self.get("knowledge_source")
    
    def get_document_service(self) -> DocumentService:
        """Get document service."""
        return self.get("document")
    
    def get_chatbot_service(self) -> ChatbotService:
        """Get chatbot service."""
        return self.get("chatbot")


# Global service registry
service_registry = ServiceRegistry()

# Register default services
service_registry.register("user", UserService())
service_registry.register("knowledge_source", KnowledgeSourceService())
service_registry.register("document", DocumentService())
service_registry.register("chatbot", ChatbotService())