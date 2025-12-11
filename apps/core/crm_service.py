"""
CRM Integration Service
Handles webhook integrations with HubSpot, Zoho, and Salesforce
"""

import requests
import re
import structlog
from typing import Dict, Optional, List
from datetime import datetime
from django.conf import settings
from django.core.exceptions import ValidationError

logger = structlog.get_logger()


class CRMIntegrationError(Exception):
    """Custom exception for CRM integration errors"""
    pass


class EmailExtractor:
    """Utility class for extracting emails from conversation text"""
    
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    @classmethod
    def extract_email(cls, text: str) -> Optional[str]:
        """Extract the first valid email from text"""
        if not text:
            return None
            
        emails = re.findall(cls.EMAIL_PATTERN, text, re.IGNORECASE)
        return emails[0] if emails else None
    
    @classmethod
    def extract_name_near_email(cls, text: str, email: str) -> Optional[str]:
        """Try to extract a name near the email in the text"""
        if not text or not email:
            return None
        
        # Simple heuristics for name extraction
        # Look for patterns like "I'm John" or "My name is Sarah"
        name_patterns = [
            r"(?:i'?m|my name is|i am|name'?s)\s+([a-zA-Z\s]{2,20})",
            r"([a-zA-Z]{2,15})\s+[a-zA-Z]{2,15}@",  # Name before email
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                name = matches[0].strip()
                if len(name) > 1 and name.lower() not in ['email', 'address', 'contact']:
                    return name.title()
        
        return None


class HubSpotService:
    """Service for HubSpot Forms API integration"""
    
    def __init__(self, webhook_url: str, api_key: Optional[str] = None):
        self.webhook_url = webhook_url
        self.api_key = api_key
        self.validate_url()
    
    def validate_url(self):
        """Validate that the URL is a valid HubSpot forms URL"""
        if not self.webhook_url:
            raise ValidationError("HubSpot webhook URL is required")
        
        # Check if it's a HubSpot forms URL
        if "forms.hubspot.com" not in self.webhook_url:
            raise ValidationError("URL must be a HubSpot forms endpoint")
        
        # Validate format: https://forms.hubspot.com/uploads/form/v2/{portal_id}/{form_guid}
        hubspot_pattern = r"https://forms\.hubspot\.com/uploads/form/v2/\d+/[a-zA-Z0-9\-]+"
        if not re.match(hubspot_pattern, self.webhook_url):
            raise ValidationError("Invalid HubSpot forms URL format. Expected: https://forms.hubspot.com/uploads/form/v2/PORTAL_ID/FORM_GUID")
    
    def send_lead(self, lead_data: Dict) -> bool:
        """
        Send lead data to HubSpot Forms API
        
        Args:
            lead_data: Dictionary containing lead information
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Prepare HubSpot-specific payload
            payload = {
                "fields": [
                    {"name": "email", "value": lead_data.get("email", "")},
                    {"name": "firstname", "value": lead_data.get("first_name", "")},
                    {"name": "lastname", "value": lead_data.get("last_name", "")},
                    {"name": "message", "value": lead_data.get("message", "")},
                    {"name": "phone", "value": lead_data.get("phone", "")},
                    {"name": "company", "value": lead_data.get("company", "")},
                    {"name": "hs_lead_status", "value": "NEW"},
                    {"name": "hs_persona", "value": "chatbot_lead"},
                    {"name": "lifecyclestage", "value": "lead"}
                ],
                "context": {
                    "hutk": "",  # HubSpot tracking cookie (if available)
                    "pageUri": lead_data.get("page_url", ""),
                    "pageName": lead_data.get("page_title", "Chatbot Conversation")
                },
                "legalConsentOptions": {
                    "consent": {
                        "consentToProcess": True,
                        "text": "I agree to allow this website to store and process my personal data.",
                        "communications": [
                            {
                                "value": True,
                                "subscriptionTypeId": 999,
                                "text": "I agree to receive marketing communications."
                            }
                        ]
                    }
                }
            }
            
            # Add custom properties for chatbot-specific data
            payload["fields"].extend([
                {"name": "chatbot_name", "value": lead_data.get("chatbot_name", "")},
                {"name": "conversation_id", "value": lead_data.get("conversation_id", "")},
                {"name": "lead_source", "value": "AI Chatbot Widget"},
                {"name": "acquisition_date", "value": datetime.now().isoformat()}
            ])
            
            # Remove empty fields
            payload["fields"] = [field for field in payload["fields"] if field["value"]]
            
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Chatbot-SaaS/1.0"
            }
            
            # Add API key if provided
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            logger.info(f"Sending lead to HubSpot: {lead_data.get('email')}")
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"Successfully sent lead to HubSpot: {lead_data.get('email')}")
                return True
            else:
                logger.error(f"HubSpot API error: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending to HubSpot: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending to HubSpot: {str(e)}")
            return False
    
    def test_connection(self) -> Dict:
        """
        Test the HubSpot connection with a dummy payload
        
        Returns:
            Dict: {"success": bool, "message": str}
        """
        try:
            test_payload = {
                "fields": [
                    {"name": "email", "value": "test@example.com"},
                    {"name": "firstname", "value": "Test"},
                    {"name": "lastname", "value": "User"},
                    {"name": "message", "value": "This is a test connection from Chatbot SaaS"},
                    {"name": "lead_source", "value": "API Test"}
                ]
            }
            
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Chatbot-SaaS/1.0 (Test)"
            }
            
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            response = requests.post(
                self.webhook_url,
                json=test_payload,
                headers=headers,
                timeout=5
            )
            
            if response.status_code in [200, 204]:
                return {
                    "success": True,
                    "message": "Connection successful! Test lead sent to HubSpot."
                }
            else:
                return {
                    "success": False,
                    "message": f"Connection failed: HTTP {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "message": "Connection timeout. Please check your URL."
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "message": f"Network error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}"
            }


class CRMService:
    """Main CRM service that handles different providers"""
    
    @staticmethod
    def get_service(provider: str, webhook_url: str, api_key: Optional[str] = None):
        """Factory method to get the appropriate CRM service"""
        if provider.lower() == "hubspot":
            return HubSpotService(webhook_url, api_key)
        else:
            raise CRMIntegrationError(f"Unsupported CRM provider: {provider}")
    
    @staticmethod
    def process_conversation_for_crm(conversation, chatbot):
        """
        Process a conversation and send to CRM if email is detected
        
        Args:
            conversation: Conversation model instance
            chatbot: Chatbot model instance with CRM settings
        """
        if not chatbot.crm_enabled or not chatbot.crm_webhook_url:
            return False
        
        try:
            # Get all messages from the conversation
            from apps.conversations.models import Message
            messages = Message.objects.filter(conversation=conversation).order_by('created_at')
            
            # Look for email in user messages
            email = None
            full_conversation = ""
            user_name = None
            
            for message in messages:
                full_conversation += f"{message.role}: {message.content}\n"
                
                if message.role == 'user':
                    # Try to extract email from this message
                    message_email = EmailExtractor.extract_email(message.content)
                    if message_email and not email:
                        email = message_email
                        # Try to extract name from the same message
                        user_name = EmailExtractor.extract_name_near_email(message.content, email)
            
            # Only proceed if email was found
            if not email:
                logger.debug(f"No email found in conversation {conversation.id}, skipping CRM")
                return False
            
            # Prepare lead data
            lead_data = {
                "email": email,
                "first_name": user_name.split()[0] if user_name else "",
                "last_name": " ".join(user_name.split()[1:]) if user_name and len(user_name.split()) > 1 else "",
                "message": full_conversation.strip(),
                "chatbot_name": chatbot.name,
                "conversation_id": str(conversation.id),
                "page_url": conversation.metadata.get("page_url", ""),
                "page_title": conversation.metadata.get("page_title", ""),
                "user_agent": conversation.metadata.get("user_agent", ""),
                "timestamp": conversation.created_at.isoformat()
            }
            
            # Get CRM service and send lead
            crm_service = CRMService.get_service(
                chatbot.crm_provider,
                chatbot.crm_webhook_url,
                chatbot.crm_webhook_secret
            )
            
            success = crm_service.send_lead(lead_data)
            
            # Log the result in conversation metadata
            conversation.metadata = conversation.metadata or {}
            conversation.metadata["crm_integration"] = {
                "attempted": True,
                "success": success,
                "email_captured": email,
                "timestamp": datetime.now().isoformat(),
                "provider": chatbot.crm_provider
            }
            conversation.save()
            
            if success:
                logger.info(f"Successfully sent lead to {chatbot.crm_provider}: {email}")
            else:
                logger.warning(f"Failed to send lead to {chatbot.crm_provider}: {email}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing conversation for CRM: {str(e)}")
            return False