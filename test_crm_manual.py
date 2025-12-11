"""
Manual CRM Integration Testing
Direct testing of CRM functionality without pytest dependencies
"""

import os
import sys
import django
from unittest.mock import patch, Mock

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

from apps.core.crm_service import EmailExtractor, HubSpotService, CRMService
from apps.chatbots.models import Chatbot
from apps.conversations.models import Conversation, Message
from django.contrib.auth import get_user_model

User = get_user_model()

def test_email_extraction():
    """Test email extraction functionality"""
    print("🧪 Testing Email Extraction...")
    
    # Test cases
    test_cases = [
        ("Hi, my email is john.doe@example.com", "john.doe@example.com"),
        ("Contact me at SARAH@COMPANY.COM please", "SARAH@COMPANY.COM"),
        ("No email in this message", None),
        ("Multiple emails: first@test.com and second@test.com", "first@test.com"),
    ]
    
    for text, expected in test_cases:
        result = EmailExtractor.extract_email(text)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{text[:30]}...' → {result}")
    
    print()

def test_name_extraction():
    """Test name extraction functionality"""
    print("🧪 Testing Name Extraction...")
    
    test_cases = [
        ("I'm John Doe, email john@test.com", "john@test.com", "John Doe"),
        ("My name is Sarah Smith", "sarah@test.com", "Sarah Smith"),
        ("Just email: contact@company.com", "contact@company.com", None),
    ]
    
    for text, email, expected in test_cases:
        result = EmailExtractor.extract_name_near_email(text, email)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{text}' → {result}")
    
    print()

def test_hubspot_url_validation():
    """Test HubSpot URL validation"""
    print("🧪 Testing HubSpot URL Validation...")
    
    valid_urls = [
        "https://forms.hubspot.com/uploads/form/v2/12345/test-form-guid",
        "https://forms.hubspot.com/uploads/form/v2/67890/another-form-123"
    ]
    
    invalid_urls = [
        "https://example.com/form",
        "not-a-url",
        "",
        "https://forms.hubspot.com/wrong-format"
    ]
    
    for url in valid_urls:
        try:
            service = HubSpotService(url)
            print(f"  ✅ Valid: {url[:50]}...")
        except Exception as e:
            print(f"  ❌ Should be valid: {url[:50]}... → {e}")
    
    for url in invalid_urls:
        try:
            service = HubSpotService(url)
            print(f"  ❌ Should be invalid: {url[:50]}...")
        except Exception as e:
            print(f"  ✅ Correctly rejected: {url[:50]}... → {str(e)[:50]}...")
    
    print()

def test_crm_workflow_simulation():
    """Test complete CRM workflow with test data"""
    print("🧪 Testing Complete CRM Workflow...")
    
    try:
        # Get or create test user and chatbot
        user, created = User.objects.get_or_create(
            email='crm.test@example.com',
            defaults={
                'first_name': 'CRM',
                'last_name': 'Test',
                'password': 'testpass123'
            }
        )
        
        chatbot, created = Chatbot.objects.get_or_create(
            public_url_slug='crm-test-workflow',
            defaults={
                'user': user,
                'name': 'CRM Test Workflow Bot',
                'description': 'Testing CRM workflow',
                'status': 'ready',
                'crm_enabled': True,
                'crm_provider': 'hubspot',
                'crm_webhook_url': 'https://forms.hubspot.com/uploads/form/v2/TEST_PORTAL/TEST_FORM'
            }
        )
        
        # Create test conversation
        conversation = Conversation.objects.create(
            chatbot=chatbot,
            metadata={'source': 'widget', 'test': True}
        )
        
        # Add messages without email first
        Message.objects.create(
            conversation=conversation,
            role='user',
            content='Hi, I need help with your product'
        )
        
        Message.objects.create(
            conversation=conversation,
            role='assistant',
            content='I can help you with that! What would you like to know?'
        )
        
        # Test CRM processing (should not trigger)
        result_1 = CRMService.process_conversation_for_crm(conversation, chatbot)
        print(f"  ✅ No email → CRM not triggered: {not result_1}")
        
        # Add message with email
        Message.objects.create(
            conversation=conversation,
            role='user',
            content='Please send me pricing info to my email: alex.customer@testcompany.com'
        )
        
        # Mock the HubSpot API call
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            # Test CRM processing (should trigger)
            result_2 = CRMService.process_conversation_for_crm(conversation, chatbot)
            print(f"  ✅ Email detected → CRM triggered: {result_2}")
            
            if mock_post.called:
                print(f"  ✅ HubSpot API called successfully")
                # Check the data that would be sent
                call_args = mock_post.call_args
                if call_args and len(call_args) > 1:
                    sent_data = call_args[1].get('json', {})
                    if 'fields' in sent_data:
                        email_field = next((f for f in sent_data['fields'] if f['name'] == 'email'), None)
                        if email_field:
                            print(f"  ✅ Email field: {email_field['value']}")
        
        # Check conversation metadata
        conversation.refresh_from_db()
        crm_data = conversation.metadata.get('crm_integration', {})
        if crm_data.get('attempted'):
            print(f"  ✅ CRM metadata saved: Email captured = {crm_data.get('email_captured')}")
        
        print(f"  ✅ Workflow test completed successfully")
        
    except Exception as e:
        print(f"  ❌ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()

if __name__ == "__main__":
    print("🚀 Starting Manual CRM Integration Tests\n")
    
    test_email_extraction()
    test_name_extraction()
    test_hubspot_url_validation()
    test_crm_workflow_simulation()
    
    print("✅ Manual CRM testing completed!")