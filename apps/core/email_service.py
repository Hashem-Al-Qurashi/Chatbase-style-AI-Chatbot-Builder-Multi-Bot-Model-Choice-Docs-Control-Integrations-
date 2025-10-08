"""
Email Service for sending password reset and other transactional emails.
Implements background email sending with proper error handling and logging.
"""

import structlog
from typing import Dict, Optional, Any
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings

from chatbot_saas.config import get_settings

logger = structlog.get_logger()
User = get_user_model()
app_settings = get_settings()


class EmailService:
    """
    Service for sending transactional emails with templates and background processing.
    """

    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@chatbot-saas.com')
        self.reply_to = getattr(settings, 'DEFAULT_REPLY_TO', 'support@chatbot-saas.com')

    def send_password_reset_email(
        self,
        user: User,
        reset_token: str,
        ip_address: str,
        request=None
    ) -> bool:
        """
        Send password reset email to user.
        
        Args:
            user: User requesting password reset
            reset_token: JWT reset token
            ip_address: IP address of request origin
            request: Optional HTTP request object for context
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Generate reset URL (this would be the frontend URL in production)
            reset_url = self._generate_reset_url(reset_token, request)
            
            # Prepare template context
            context = {
                'user': user,
                'reset_token': reset_token,
                'reset_url': reset_url,
                'ip_address': ip_address,
                'timestamp': timezone.now(),
                'request': request,
                'expires_in_hours': 1,  # Reset tokens expire in 1 hour
            }
            
            # Render email templates
            subject = f"Password Reset Request - {getattr(settings, 'SITE_NAME', 'Chatbot SaaS')}"
            
            html_content = render_to_string(
                'emails/auth/password_reset.html',
                context
            )
            
            text_content = render_to_string(
                'emails/auth/password_reset.txt',
                context
            )
            
            # Send email
            success = self._send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            if success:
                logger.info(
                    "Password reset email sent successfully",
                    user_id=str(user.id),
                    email=user.email,
                    ip_address=ip_address
                )
            else:
                logger.error(
                    "Failed to send password reset email",
                    user_id=str(user.id),
                    email=user.email,
                    ip_address=ip_address
                )
            
            return success
            
        except Exception as e:
            logger.error(
                "Error sending password reset email",
                error=str(e),
                user_id=str(user.id),
                email=user.email,
                ip_address=ip_address
            )
            return False

    def send_welcome_email(self, user: User, ip_address: str, request=None) -> bool:
        """
        Send welcome email to newly registered user.
        
        Args:
            user: Newly registered user
            ip_address: IP address of registration
            request: Optional HTTP request object
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            # TODO: Implement welcome email template and sending
            # For now, just log that it would be sent
            
            logger.info(
                "Welcome email would be sent",
                user_id=str(user.id),
                email=user.email,
                ip_address=ip_address
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Error sending welcome email",
                error=str(e),
                user_id=str(user.id),
                email=user.email
            )
            return False

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str
    ) -> bool:
        """
        Send email using Django's email backend.
        In development, this logs the email instead of sending.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text email content
            
        Returns:
            bool: True if sent successfully
        """
        try:
            # In development mode, just log the email for testing
            if getattr(settings, 'DEBUG', False):
                logger.info(
                    "Email would be sent (development mode)",
                    to_email=to_email,
                    subject=subject,
                    html_preview=html_content[:200] + "..." if len(html_content) > 200 else html_content,
                    text_preview=text_content[:200] + "..." if len(text_content) > 200 else text_content
                )
                return True
            
            # Create email message
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=[to_email],
                reply_to=[self.reply_to]
            )
            
            # Attach HTML version
            email.attach_alternative(html_content, "text/html")
            
            # Send email
            email.send()
            
            logger.info(
                "Email sent successfully",
                to_email=to_email,
                subject=subject
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to send email",
                error=str(e),
                to_email=to_email,
                subject=subject
            )
            return False

    def _generate_reset_url(self, reset_token: str, request=None) -> str:
        """
        Generate password reset URL.
        
        Args:
            reset_token: JWT reset token
            request: Optional HTTP request for domain context
            
        Returns:
            str: Complete reset URL
        """
        # In production, this would be the frontend application URL
        # For now, use a placeholder that works for API testing
        
        if request:
            protocol = 'https' if request.is_secure() else 'http'
            host = request.get_host()
            base_url = f"{protocol}://{host}"
        else:
            base_url = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:3000')
        
        # Frontend route for password reset
        reset_path = f"/auth/reset-password?token={reset_token}"
        
        return f"{base_url}{reset_path}"

    def send_email_async(self, email_type: str, **kwargs) -> None:
        """
        Send email asynchronously using Celery (placeholder for now).
        
        Args:
            email_type: Type of email to send
            **kwargs: Email-specific parameters
        """
        # TODO: Implement Celery task for background email sending
        # For now, send synchronously
        
        if email_type == 'password_reset':
            self.send_password_reset_email(**kwargs)
        elif email_type == 'welcome':
            self.send_welcome_email(**kwargs)
        else:
            logger.warning(
                "Unknown email type for async sending",
                email_type=email_type
            )


# Global email service instance
email_service = EmailService()


def send_password_reset_email_async(user: User, reset_token: str, ip_address: str, request=None):
    """
    Convenience function for sending password reset email asynchronously.
    This will be converted to a Celery task when background processing is implemented.
    """
    return email_service.send_password_reset_email(user, reset_token, ip_address, request)


def send_welcome_email_async(user: User, ip_address: str, request=None):
    """
    Convenience function for sending welcome email asynchronously.
    This will be converted to a Celery task when background processing is implemented.
    """
    return email_service.send_welcome_email(user, ip_address, request)