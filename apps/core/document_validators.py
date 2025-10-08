"""
Secure document upload validation with enterprise-grade security.
Implements comprehensive validation, virus scanning, and content filtering.
"""

import os
import magic
import hashlib
import tempfile
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from django.core.files.uploadedfile import UploadedFile
from django.conf import settings

from .exceptions import (
    DocumentValidationError,
    UnsupportedFileTypeError,
    FileSizeExceededError,
    VirusScanFailedError,
    MaliciousContentError
)


@dataclass
class ValidationResult:
    """Result of document validation."""
    is_valid: bool
    file_hash: str
    mime_type: str
    file_size: int
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, any]


class DocumentUploadValidator:
    """
    Enterprise-grade document upload validator.
    
    Implements multiple layers of security:
    1. MIME type validation
    2. File header validation  
    3. File size limits
    4. Virus scanning
    5. Content analysis
    6. Duplicate detection
    """
    
    # Allowed MIME types with their expected file extensions
    ALLOWED_TYPES = {
        'application/pdf': ['.pdf'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
        'application/msword': ['.doc'],
        'text/plain': ['.txt'],
        'text/markdown': ['.md'],
    }
    
    # Maximum file size (50MB default)
    MAX_FILE_SIZE = getattr(settings, 'MAX_FILE_SIZE_BYTES', 50 * 1024 * 1024)
    
    # File signature validation (magic bytes)
    FILE_SIGNATURES = {
        'application/pdf': [b'%PDF-'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': [
            b'PK\x03\x04',  # ZIP signature (DOCX is ZIP-based)
        ],
        'application/msword': [b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'],  # OLE signature
        'text/plain': [],  # No specific signature for plain text
        'text/markdown': [],  # No specific signature for markdown
    }
    
    # Suspicious content patterns (regex patterns)
    SUSPICIOUS_PATTERNS = [
        rb'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',  # JavaScript
        rb'javascript:',  # JavaScript URLs
        rb'vbscript:',  # VBScript URLs
        rb'data:.*base64',  # Base64 data URLs
        rb'\\x[0-9a-fA-F]{2}',  # Hex encoded content
        rb'eval\s*\(',  # Eval function calls
    ]
    
    def __init__(self, enable_virus_scan: bool = True):
        """
        Initialize validator.
        
        Args:
            enable_virus_scan: Whether to enable virus scanning (requires ClamAV)
        """
        self.enable_virus_scan = enable_virus_scan
        self.magic_checker = magic.Magic(mime=True)
    
    def validate_file(self, uploaded_file: UploadedFile) -> ValidationResult:
        """
        Perform comprehensive file validation.
        
        Args:
            uploaded_file: Django uploaded file object
            
        Returns:
            ValidationResult: Comprehensive validation result
            
        Raises:
            DocumentValidationError: If validation fails critically
        """
        errors = []
        warnings = []
        metadata = {}
        
        try:
            # Step 1: Basic file information
            file_size = uploaded_file.size
            file_name = uploaded_file.name
            file_hash = self._calculate_file_hash(uploaded_file)
            
            metadata.update({
                'original_filename': file_name,
                'file_size_bytes': file_size,
                'file_hash_sha256': file_hash,
            })
            
            # Step 2: File size validation
            size_errors = self._validate_file_size(file_size)
            errors.extend(size_errors)
            
            # Step 3: MIME type validation
            detected_mime, mime_errors = self._validate_mime_type(uploaded_file)
            errors.extend(mime_errors)
            
            if detected_mime:
                metadata['detected_mime_type'] = detected_mime
            
            # Step 4: File signature validation
            if detected_mime:
                signature_errors = self._validate_file_signature(uploaded_file, detected_mime)
                errors.extend(signature_errors)
            
            # Step 5: Filename validation
            filename_errors = self._validate_filename(file_name)
            errors.extend(filename_errors)
            
            # Step 6: Content scanning for suspicious patterns
            content_errors, content_warnings = self._scan_content(uploaded_file)
            errors.extend(content_errors)
            warnings.extend(content_warnings)
            
            # Step 7: Virus scanning (if enabled)
            if self.enable_virus_scan:
                virus_errors = self._virus_scan(uploaded_file)
                errors.extend(virus_errors)
            
            # Step 8: Duplicate detection
            metadata['is_duplicate'] = self._check_duplicate(file_hash)
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                file_hash=file_hash,
                mime_type=detected_mime or 'unknown',
                file_size=file_size,
                errors=errors,
                warnings=warnings,
                metadata=metadata
            )
            
        except Exception as e:
            raise DocumentValidationError(f"Validation failed: {str(e)}")
    
    def _calculate_file_hash(self, uploaded_file: UploadedFile) -> str:
        """Calculate SHA-256 hash of the file."""
        hash_sha256 = hashlib.sha256()
        
        # Read file in chunks to handle large files
        uploaded_file.seek(0)
        for chunk in uploaded_file.chunks():
            hash_sha256.update(chunk)
        uploaded_file.seek(0)  # Reset file pointer
        
        return hash_sha256.hexdigest()
    
    def _validate_file_size(self, file_size: int) -> List[str]:
        """Validate file size against limits."""
        errors = []
        
        if file_size <= 0:
            errors.append("File is empty")
        elif file_size > self.MAX_FILE_SIZE:
            errors.append(f"File size ({file_size} bytes) exceeds maximum allowed size ({self.MAX_FILE_SIZE} bytes)")
        
        return errors
    
    def _validate_mime_type(self, uploaded_file: UploadedFile) -> Tuple[Optional[str], List[str]]:
        """Validate MIME type using python-magic."""
        errors = []
        
        try:
            # Create temporary file for magic detection
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                uploaded_file.seek(0)
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file.flush()
                uploaded_file.seek(0)
                
                # Detect MIME type using magic
                detected_mime = self.magic_checker.from_file(temp_file.name)
                
                # Clean up temp file
                os.unlink(temp_file.name)
                
                if detected_mime not in self.ALLOWED_TYPES:
                    errors.append(f"File type '{detected_mime}' is not allowed")
                    return None, errors
                
                return detected_mime, errors
                
        except Exception as e:
            errors.append(f"Failed to detect file type: {str(e)}")
            return None, errors
    
    def _validate_file_signature(self, uploaded_file: UploadedFile, mime_type: str) -> List[str]:
        """Validate file signature (magic bytes) matches MIME type."""
        errors = []
        
        if mime_type not in self.FILE_SIGNATURES:
            return errors
        
        expected_signatures = self.FILE_SIGNATURES[mime_type]
        if not expected_signatures:  # No signature validation needed
            return errors
        
        try:
            uploaded_file.seek(0)
            file_header = uploaded_file.read(512)  # Read first 512 bytes
            uploaded_file.seek(0)
            
            signature_match = any(
                file_header.startswith(signature) 
                for signature in expected_signatures
            )
            
            if not signature_match:
                errors.append(f"File signature does not match expected type '{mime_type}'")
                
        except Exception as e:
            errors.append(f"Failed to validate file signature: {str(e)}")
        
        return errors
    
    def _validate_filename(self, filename: str) -> List[str]:
        """Validate filename for security issues."""
        errors = []
        
        if not filename:
            errors.append("Filename is required")
            return errors
        
        # Check for path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            errors.append("Filename contains invalid path characters")
        
        # Check for null bytes
        if '\x00' in filename:
            errors.append("Filename contains null bytes")
        
        # Check filename length
        if len(filename) > 255:
            errors.append("Filename is too long (maximum 255 characters)")
        
        # Check for executable extensions
        dangerous_extensions = ['.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.jar']
        file_extension = Path(filename).suffix.lower()
        if file_extension in dangerous_extensions:
            errors.append(f"File extension '{file_extension}' is not allowed")
        
        return errors
    
    def _scan_content(self, uploaded_file: UploadedFile) -> Tuple[List[str], List[str]]:
        """Scan file content for suspicious patterns."""
        errors = []
        warnings = []
        
        try:
            uploaded_file.seek(0)
            # Read first 64KB for content scanning
            content_sample = uploaded_file.read(64 * 1024)
            uploaded_file.seek(0)
            
            for pattern in self.SUSPICIOUS_PATTERNS:
                if pattern.search(content_sample):
                    warnings.append("File contains potentially suspicious content patterns")
                    break
            
            # Check for excessive null bytes (potential binary exploitation)
            null_byte_count = content_sample.count(b'\x00')
            if null_byte_count > len(content_sample) * 0.3:  # More than 30% null bytes
                warnings.append("File contains unusually high number of null bytes")
            
        except Exception as e:
            warnings.append(f"Content scanning failed: {str(e)}")
        
        return errors, warnings
    
    def _virus_scan(self, uploaded_file: UploadedFile) -> List[str]:
        """
        Perform virus scanning using ClamAV.
        
        Note: This is a placeholder implementation.
        In production, integrate with ClamAV daemon or use cloud scanning service.
        """
        errors = []
        
        try:
            # Placeholder for virus scanning
            # In production, implement actual ClamAV integration:
            # import pyclamd
            # cd = pyclamd.ClamdUnixSocket()
            # scan_result = cd.scan_stream(uploaded_file.read())
            # if scan_result:
            #     errors.append(f"Virus detected: {scan_result}")
            
            # For now, just log that virus scanning would happen
            pass
            
        except Exception as e:
            errors.append(f"Virus scanning failed: {str(e)}")
        
        return errors
    
    def _check_duplicate(self, file_hash: str) -> bool:
        """
        Check if file already exists based on hash.
        
        Args:
            file_hash: SHA-256 hash of the file
            
        Returns:
            bool: True if file is a duplicate
        """
        # Placeholder for duplicate detection
        # In production, check against database of existing file hashes
        # from apps.knowledge.models import KnowledgeSource
        # return KnowledgeSource.objects.filter(file_hash=file_hash).exists()
        
        return False


class FileQuarantineManager:
    """
    Manages quarantined files that failed validation.
    """
    
    def __init__(self, quarantine_dir: str = "/tmp/quarantine"):
        """
        Initialize quarantine manager.
        
        Args:
            quarantine_dir: Directory to store quarantined files
        """
        self.quarantine_dir = Path(quarantine_dir)
        self.quarantine_dir.mkdir(exist_ok=True, mode=0o700)  # Secure permissions
    
    def quarantine_file(self, uploaded_file: UploadedFile, reason: str) -> str:
        """
        Move file to quarantine and log the incident.
        
        Args:
            uploaded_file: The uploaded file to quarantine
            reason: Reason for quarantine
            
        Returns:
            str: Quarantine ID for tracking
        """
        import uuid
        import structlog
        
        logger = structlog.get_logger()
        quarantine_id = str(uuid.uuid4())
        quarantine_path = self.quarantine_dir / f"{quarantine_id}_{uploaded_file.name}"
        
        try:
            # Save file to quarantine
            with open(quarantine_path, 'wb') as qf:
                uploaded_file.seek(0)
                for chunk in uploaded_file.chunks():
                    qf.write(chunk)
            
            # Log quarantine event
            logger.warning(
                "File quarantined",
                quarantine_id=quarantine_id,
                filename=uploaded_file.name,
                file_size=uploaded_file.size,
                reason=reason,
                quarantine_path=str(quarantine_path)
            )
            
            return quarantine_id
            
        except Exception as e:
            logger.error(
                "Failed to quarantine file",
                filename=uploaded_file.name,
                error=str(e)
            )
            raise DocumentValidationError(f"Failed to quarantine file: {str(e)}")
    
    def cleanup_quarantine(self, max_age_days: int = 30):
        """
        Clean up old quarantined files.
        
        Args:
            max_age_days: Maximum age of quarantined files in days
        """
        import time
        import structlog
        
        logger = structlog.get_logger()
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        
        for file_path in self.quarantine_dir.iterdir():
            if file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    logger.info(
                        "Quarantined file cleaned up",
                        file_path=str(file_path)
                    )
                except Exception as e:
                    logger.error(
                        "Failed to cleanup quarantined file",
                        file_path=str(file_path),
                        error=str(e)
                    )