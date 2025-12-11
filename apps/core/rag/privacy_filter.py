"""
Privacy Filter for RAG Pipeline - Layer 3 Protection.

This module implements the final layer of privacy protection by post-processing
LLM responses to detect and sanitize any privacy violations.

CRITICAL: This is the last line of defense against privacy leaks.
All responses must pass through this filter before being returned to users.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

from .context_builder import ContextData
from apps.core.monitoring import track_metric

logger = logging.getLogger(__name__)


class ViolationType(Enum):
    """Types of privacy violations."""
    PRIVATE_SOURCE_REFERENCE = "private_source_reference"
    PRIVATE_CONTENT_LEAK = "private_content_leak"
    PRIVATE_ID_EXPOSURE = "private_id_exposure"
    UNAUTHORIZED_CITATION = "unauthorized_citation"
    SYSTEM_PROMPT_LEAK = "system_prompt_leak"


@dataclass
class PrivacyViolation:
    """Privacy violation details."""
    violation_type: ViolationType
    description: str
    confidence: float  # 0.0 to 1.0
    location: str  # Where in the response
    suggested_replacement: Optional[str] = None


@dataclass
class FilterResult:
    """Result from privacy filtering."""
    passed: bool
    violations: List[PrivacyViolation]
    sanitized_response: str
    original_response: str
    confidence_score: float
    filter_time: float


class PrivateContentDetector:
    """ML-based detector for private content leaks."""
    
    def __init__(self):
        """Initialize content detector."""
        self.min_phrase_length = 3
        self.similarity_threshold = 0.8
    
    def detect_leak(
        self,
        response: str,
        context: ContextData,
        confidence_threshold: float = 0.7
    ) -> List[PrivacyViolation]:
        """
        Detect potential private content leaks using pattern matching.
        
        Args:
            response: Generated response to check
            context: Context data with private sources
            confidence_threshold: Minimum confidence for detection
            
        Returns:
            List[PrivacyViolation]: Detected violations
        """
        violations = []
        
        if not context.private_sources:
            return violations
        
        response_lower = response.lower()
        
        for source in context.private_sources:
            if not source.content:
                continue
            
            # Check for direct quotes or near-exact matches
            violations.extend(
                self._check_direct_quotes(response, source, confidence_threshold)
            )
            
            # Check for unique phrases
            violations.extend(
                self._check_unique_phrases(response, source, confidence_threshold)
            )
            
            # Check for identifiable information
            violations.extend(
                self._check_identifiable_info(response, source, confidence_threshold)
            )
        
        return violations
    
    def _check_direct_quotes(
        self,
        response: str,
        source,
        threshold: float
    ) -> List[PrivacyViolation]:
        """Check for direct quotes from private sources."""
        violations = []
        
        # Look for phrases of 5+ words
        source_words = source.content.split()
        if len(source_words) < 5:
            return violations
        
        for i in range(len(source_words) - 4):
            phrase = " ".join(source_words[i:i+5])
            if len(phrase) < 20:  # Skip very short phrases
                continue
            
            if phrase.lower() in response.lower():
                violations.append(PrivacyViolation(
                    violation_type=ViolationType.PRIVATE_CONTENT_LEAK,
                    description=f"Direct quote from private source detected: '{phrase[:50]}...'",
                    confidence=0.95,
                    location=f"Source: {source.source_id}",
                    suggested_replacement="[Information removed for privacy]"
                ))
        
        return violations
    
    def _check_unique_phrases(
        self,
        response: str,
        source,
        threshold: float
    ) -> List[PrivacyViolation]:
        """Check for unique phrases that might identify private content."""
        violations = []
        
        # Extract potential unique identifiers
        unique_patterns = [
            r'\b[A-Z]{2,}\d{3,}\b',  # Codes like ABC123
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN-like patterns
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Emails
            r'\b\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b',  # Currency amounts
        ]
        
        for pattern in unique_patterns:
            matches_source = re.findall(pattern, source.content)
            matches_response = re.findall(pattern, response)
            
            common_matches = set(matches_source).intersection(set(matches_response))
            
            for match in common_matches:
                violations.append(PrivacyViolation(
                    violation_type=ViolationType.PRIVATE_CONTENT_LEAK,
                    description=f"Unique identifier from private source: {match}",
                    confidence=0.9,
                    location=f"Source: {source.source_id}",
                    suggested_replacement="[REDACTED]"
                ))
        
        return violations
    
    def _check_identifiable_info(
        self,
        response: str,
        source,
        threshold: float
    ) -> List[PrivacyViolation]:
        """Check for personally identifiable information."""
        violations = []
        
        # Common PII patterns
        pii_patterns = {
            "phone": r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
            "credit_card": r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b',
            "address": r'\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)\b'
        }
        
        for pii_type, pattern in pii_patterns.items():
            if re.search(pattern, source.content) and re.search(pattern, response):
                violations.append(PrivacyViolation(
                    violation_type=ViolationType.PRIVATE_CONTENT_LEAK,
                    description=f"Potential {pii_type} leaked from private source",
                    confidence=0.8,
                    location=f"Source: {source.source_id}",
                    suggested_replacement=f"[{pii_type.upper()} REDACTED]"
                ))
        
        return violations


class ResponseSanitizer:
    """Sanitize responses to remove privacy violations."""
    
    @staticmethod
    def sanitize_response(
        response: str,
        violations: List[PrivacyViolation]
    ) -> str:
        """
        Remove privacy violations from response.
        
        Args:
            response: Original response
            violations: Detected violations
            
        Returns:
            str: Sanitized response
        """
        sanitized = response
        
        for violation in violations:
            if violation.suggested_replacement:
                # Try to find and replace the violating content
                if violation.violation_type == ViolationType.PRIVATE_CONTENT_LEAK:
                    # Extract the problematic phrase from description
                    if "'" in violation.description:
                        phrase = violation.description.split("'")[1]
                        if phrase in sanitized:
                            sanitized = sanitized.replace(phrase, violation.suggested_replacement)
                
                elif violation.violation_type == ViolationType.PRIVATE_SOURCE_REFERENCE:
                    # Remove only explicit private source markers, not content words
                    private_markers = [
                        r'\[PRIVATE\]',
                        r'\[INTERNAL\]',
                        r'\[RESTRICTED\]'
                    ]
                    for marker in private_markers:
                        sanitized = re.sub(marker, '', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    @staticmethod
    def remove_system_artifacts(response: str) -> str:
        """
        Remove system artifacts from response.
        
        Args:
            response: Response to clean
            
        Returns:
            str: Cleaned response
        """
        # Remove system markers that might have leaked
        artifacts = [
            r'\[CITABLE-\d+\]',
            r'\[PRIVATE\]',
            r'CRITICAL PRIVACY RULES',
            r'NEVER VIOLATE THESE',
            r'Context:',
            r'User Question:'
        ]
        
        cleaned = response
        for artifact in artifacts:
            cleaned = re.sub(artifact, '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned


class ViolationLogger:
    """Log privacy violations for audit and monitoring."""
    
    @staticmethod
    def log_violations(
        violations: List[PrivacyViolation],
        response: str,
        context: ContextData,
        user_id: str = None,
        chatbot_id: str = None
    ):
        """
        Log privacy violations for audit.
        
        Args:
            violations: Detected violations
            response: Original response
            context: Context data
            user_id: User ID (optional)
            chatbot_id: Chatbot ID (optional)
        """
        for violation in violations:
            audit_data = {
                "violation_type": violation.violation_type.value,
                "description": violation.description,
                "confidence": violation.confidence,
                "location": violation.location,
                "user_id": user_id,
                "chatbot_id": chatbot_id,
                "context_token_count": context.token_count,
                "private_source_count": context.private_count,
                "citable_source_count": context.citable_count
            }
            
            # Log as warning for audit trail
            logger.warning(f"Privacy violation detected: {audit_data}")
            
            # Track metrics for monitoring
            track_metric("privacy.violation", 1)
            track_metric(f"privacy.violation.{violation.violation_type.value}", 1)
            track_metric("privacy.violation.confidence", violation.confidence)


class PrivacyFilter:
    """
    Main privacy filter implementing Layer 3 protection.
    
    This filter performs post-processing validation of LLM responses
    to catch any privacy leaks that escaped earlier layers.
    """
    
    def __init__(self):
        """Initialize privacy filter."""
        self.content_detector = PrivateContentDetector()
        self.sanitizer = ResponseSanitizer()
        self.violation_logger = ViolationLogger()
        
        logger.info("Initialized PrivacyFilter for Layer 3 protection")
    
    def validate_response(
        self,
        response: str,
        context: ContextData,
        user_id: str = None,
        chatbot_id: str = None,
        strict_mode: bool = True
    ) -> FilterResult:
        """
        Validate response for privacy compliance.
        
        Args:
            response: Generated response to validate
            context: Context data used for generation
            user_id: User ID for audit logging
            chatbot_id: Chatbot ID for audit logging
            strict_mode: If True, fail on any privacy violation
            
        Returns:
            FilterResult: Validation results and sanitized response
        """
        import time
        start_time = time.time()
        
        violations = []
        original_response = response
        
        try:
            # Check for private source IDs or markers
            violations.extend(self._check_private_ids(response, context))
            
            # Check for private source references
            violations.extend(self._check_private_references(response))
            
            # Check for content leaks using ML detection
            violations.extend(
                self.content_detector.detect_leak(response, context)
            )
            
            # Check for system prompt leakage
            violations.extend(self._check_system_prompt_leak(response))
            
            # Calculate overall confidence
            if violations:
                avg_confidence = sum(v.confidence for v in violations) / len(violations)
            else:
                avg_confidence = 1.0
            
            # Determine if response passes
            high_confidence_violations = [v for v in violations if v.confidence >= 0.8]
            
            if strict_mode:
                passed = len(violations) == 0
            else:
                passed = len(high_confidence_violations) == 0
            
            # Sanitize response if violations found
            if violations:
                sanitized_response = self.sanitizer.sanitize_response(response, violations)
                sanitized_response = self.sanitizer.remove_system_artifacts(sanitized_response)
                
                # Log violations for audit
                self.violation_logger.log_violations(
                    violations, response, context, user_id, chatbot_id
                )
            else:
                sanitized_response = self.sanitizer.remove_system_artifacts(response)
            
            filter_time = time.time() - start_time
            
            # Track metrics
            track_metric("privacy_filter.processing_time", filter_time)
            track_metric("privacy_filter.violations_count", len(violations))
            track_metric("privacy_filter.passed", 1 if passed else 0)
            
            if not passed:
                logger.warning(
                    f"Privacy filter failed: {len(violations)} violations detected "
                    f"(confidence: {avg_confidence:.2f})"
                )
            
            return FilterResult(
                passed=passed,
                violations=violations,
                sanitized_response=sanitized_response,
                original_response=original_response,
                confidence_score=avg_confidence,
                filter_time=filter_time
            )
            
        except Exception as e:
            logger.error(f"Privacy filter error: {str(e)}")
            # In case of error, err on the side of caution
            return FilterResult(
                passed=False,
                violations=[PrivacyViolation(
                    violation_type=ViolationType.SYSTEM_PROMPT_LEAK,
                    description=f"Privacy filter error: {str(e)}",
                    confidence=1.0,
                    location="filter_error"
                )],
                sanitized_response="I apologize, but I cannot provide a response at this time.",
                original_response=original_response,
                confidence_score=0.0,
                filter_time=time.time() - start_time
            )
    
    def _check_private_ids(
        self,
        response: str,
        context: ContextData
    ) -> List[PrivacyViolation]:
        """Check for private source IDs in response."""
        violations = []
        
        # Check for [PRIVATE] markers
        if "[PRIVATE]" in response:
            violations.append(PrivacyViolation(
                violation_type=ViolationType.PRIVATE_SOURCE_REFERENCE,
                description="Response contains [PRIVATE] source markers",
                confidence=1.0,
                location="response_text",
                suggested_replacement=""
            ))
        
        # Check for private source IDs
        for source in context.private_sources:
            if source.source_id in response:
                violations.append(PrivacyViolation(
                    violation_type=ViolationType.PRIVATE_ID_EXPOSURE,
                    description=f"Private source ID exposed: {source.source_id}",
                    confidence=0.95,
                    location="response_text",
                    suggested_replacement=""
                ))
        
        return violations
    
    def _check_private_references(self, response: str) -> List[PrivacyViolation]:
        """Check for references to private concepts."""
        violations = []
        
        # Only check for EXPLICIT references to private sources, not content words
        private_indicators = [
            "[PRIVATE]", "[INTERNAL]", "[RESTRICTED]",
            "private source says", "internal document states",
            "according to private", "from restricted sources"
        ]
        
        response_lower = response.lower()
        
        for indicator in private_indicators:
            if indicator.lower() in response_lower:
                violations.append(PrivacyViolation(
                    violation_type=ViolationType.PRIVATE_SOURCE_REFERENCE,
                    description=f"Reference to private source indicator: '{indicator}'",
                    confidence=0.9,
                    location="response_text",
                    suggested_replacement=""
                ))
        
        return violations
    
    def _check_system_prompt_leak(self, response: str) -> List[PrivacyViolation]:
        """Check for system prompt leakage."""
        violations = []
        
        system_indicators = [
            "CRITICAL PRIVACY RULES",
            "NEVER VIOLATE THESE",
            "Context:",
            "User Question:",
            "I am a helpful AI assistant for",
            "citable sources",
            "privacy rules"
        ]
        
        for indicator in system_indicators:
            if indicator in response:
                violations.append(PrivacyViolation(
                    violation_type=ViolationType.SYSTEM_PROMPT_LEAK,
                    description=f"System prompt leaked: '{indicator}'",
                    confidence=0.9,
                    location="response_text",
                    suggested_replacement=""
                ))
        
        return violations


# Global privacy filter instance
_privacy_filter: Optional[PrivacyFilter] = None


def get_privacy_filter() -> PrivacyFilter:
    """
    Get or create global privacy filter instance.
    
    Returns:
        PrivacyFilter: Privacy filter instance
    """
    global _privacy_filter
    
    if _privacy_filter is None:
        _privacy_filter = PrivacyFilter()
    
    return _privacy_filter