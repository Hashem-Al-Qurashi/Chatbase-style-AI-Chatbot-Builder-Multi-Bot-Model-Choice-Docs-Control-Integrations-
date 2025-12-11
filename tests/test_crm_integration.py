"""
Unit Tests for CRM Integration
Tests email detection, HubSpot service, and webhook functionality
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from apps.chatbots.models import Chatbot
from apps.conversations.models import Conversation, Message
from apps.core.crm_service import EmailExtractor, HubSpotService, CRMService

User = get_user_model()


class EmailExtractionTests(TestCase):
    """Test email extraction from conversation text"""
    
    def test_extract_simple_email(self):
        text = "Hi, my email is john.doe@example.com, please contact me"
        email = EmailExtractor.extract_email(text)
        self.assertEqual(email, "john.doe@example.com")
    
    def test_extract_email_case_insensitive(self):
        text = "Contact me at SARAH.SMITH@COMPANY.COM for more info"
        email = EmailExtractor.extract_email(text)
        self.assertEqual(email, "SARAH.SMITH@COMPANY.COM")
    
    def test_no_email_found(self):
        text = "Hi, I need help with pricing information"
        email = EmailExtractor.extract_email(text)
        self.assertIsNone(email)
    
    def test_extract_first_email_multiple(self):
        text = "My emails are john@test.com and jane@example.com"
        email = EmailExtractor.extract_email(text)
        self.assertEqual(email, "john@test.com")
    
    def test_extract_name_simple(self):
        text = "Hi, I'm John Doe and my email is john@example.com"
        name = EmailExtractor.extract_name_near_email(text, "john@example.com")
        self.assertEqual(name, "John Doe")
    
    def test_extract_name_my_name_is(self):
        text = "My name is Sarah Smith, email sarah@company.com"
        name = EmailExtractor.extract_name_near_email(text, "sarah@company.com")
        self.assertEqual(name, "Sarah Smith")
    
    def test_no_name_found(self):
        text = "Here's my email: contact@company.com"
        name = EmailExtractor.extract_name_near_email(text, "contact@company.com")
        self.assertIsNone(name)


class HubSpotServiceTests(TestCase):
    """Test HubSpot service functionality"""
    
    def setUp(self):
        self.valid_url = "https://forms.hubspot.com/uploads/form/v2/12345/test-form-guid"
        self.invalid_url = "https://example.com/form"
    
    def test_valid_hubspot_url(self):
        """Test that valid HubSpot URLs are accepted"""
        service = HubSpotService(self.valid_url)
        self.assertEqual(service.webhook_url, self.valid_url)
    
    def test_invalid_hubspot_url_raises_error(self):
        """Test that invalid URLs raise ValidationError"""
        with self.assertRaises(Exception):
            HubSpotService(self.invalid_url)
    
    def test_empty_url_raises_error(self):
        """Test that empty URL raises ValidationError"""
        with self.assertRaises(Exception):
            HubSpotService("")
    
    @patch('requests.post')
    def test_send_lead_success(self, mock_post):
        """Test successful lead submission to HubSpot"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        service = HubSpotService(self.valid_url)
        lead_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "message": "Hi, I need help",
            "chatbot_name": "Support Bot"
        }
        
        result = service.send_lead(lead_data)
        self.assertTrue(result)
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_send_lead_failure(self, mock_post):
        """Test failed lead submission to HubSpot"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid form data"
        mock_post.return_value = mock_response
        
        service = HubSpotService(self.valid_url)
        lead_data = {"email": "test@example.com"}
        
        result = service.send_lead(lead_data)
        self.assertFalse(result)
    
    @patch('requests.post')
    def test_test_connection_success(self, mock_post):
        """Test successful connection test"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        service = HubSpotService(self.valid_url)
        result = service.test_connection()
        
        self.assertTrue(result['success'])
        self.assertIn("successful", result['message'].lower())


class CRMIntegrationAPITests(APITestCase):
    """Test CRM integration API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        self.chatbot = Chatbot.objects.create(
            user=self.user,
            name='Test Chatbot',
            description='Test chatbot for CRM integration',
            public_url_slug='test-crm-bot'
        )
    
    def test_get_crm_settings_default(self):
        """Test getting default CRM settings"""
        url = f'/api/v1/chatbots/{self.chatbot.id}/crm/settings/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data['crm_enabled'])
        self.assertEqual(data['crm_provider'], 'hubspot')
        self.assertEqual(data['status'], 'not_configured')
    
    def test_update_crm_settings_valid(self):
        """Test updating CRM settings with valid data"""
        url = f'/api/v1/chatbots/{self.chatbot.id}/crm/settings/'
        data = {
            'crm_enabled': True,
            'crm_provider': 'hubspot',
            'webhook_url': 'https://forms.hubspot.com/uploads/form/v2/12345/test-guid',
            'api_key': 'test-api-key'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.chatbot.refresh_from_db()
        self.assertTrue(self.chatbot.crm_enabled)
        self.assertEqual(self.chatbot.crm_webhook_url, data['webhook_url'])
    
    def test_update_crm_settings_invalid_provider(self):
        """Test updating CRM settings with invalid provider"""
        url = f'/api/v1/chatbots/{self.chatbot.id}/crm/settings/'
        data = {
            'crm_enabled': True,
            'crm_provider': 'invalid_crm',
            'webhook_url': 'https://forms.hubspot.com/uploads/form/v2/12345/test-guid'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_enable_crm_without_url(self):
        """Test enabling CRM without providing webhook URL"""
        url = f'/api/v1/chatbots/{self.chatbot.id}/crm/settings/'
        data = {'crm_enabled': True}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('apps.core.crm_service.HubSpotService.test_connection')
    def test_crm_connection_test_success(self, mock_test):
        """Test successful CRM connection test"""
        mock_test.return_value = {'success': True, 'message': 'Connection successful'}
        
        url = f'/api/v1/chatbots/{self.chatbot.id}/crm/test/'
        data = {
            'provider': 'hubspot',
            'webhook_url': 'https://forms.hubspot.com/uploads/form/v2/12345/test-guid'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()['success'])
    
    @patch('apps.core.crm_service.HubSpotService.test_connection')
    def test_crm_connection_test_failure(self, mock_test):
        """Test failed CRM connection test"""
        mock_test.return_value = {'success': False, 'message': 'Connection failed'}
        
        url = f'/api/v1/chatbots/{self.chatbot.id}/crm/test/'
        data = {
            'provider': 'hubspot',
            'webhook_url': 'https://forms.hubspot.com/uploads/form/v2/12345/test-guid'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.json()['success'])


class CRMWorkflowTests(TestCase):
    """Test complete CRM workflow integration"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        self.chatbot = Chatbot.objects.create(
            user=self.user,
            name='CRM Test Bot',
            description='Bot for testing CRM integration',
            public_url_slug='crm-test-bot',
            crm_enabled=True,
            crm_provider='hubspot',
            crm_webhook_url='https://forms.hubspot.com/uploads/form/v2/12345/test-guid'
        )
        
        self.conversation = Conversation.objects.create(
            chatbot=self.chatbot,
            metadata={'source': 'widget'}
        )
    
    def test_crm_trigger_with_email(self):
        """Test that CRM is triggered when email is detected"""
        # Create user message with email
        Message.objects.create(
            conversation=self.conversation,
            role='user',
            content='Hi, I need help. My email is john.doe@example.com'
        )
        
        # Create bot response
        Message.objects.create(
            conversation=self.conversation,
            role='assistant',
            content='Hello John! I can help you with that.'
        )
        
        with patch('apps.core.crm_service.HubSpotService.send_lead') as mock_send:
            mock_send.return_value = True
            
            # Process conversation for CRM
            result = CRMService.process_conversation_for_crm(self.conversation, self.chatbot)
            
            self.assertTrue(result)
            mock_send.assert_called_once()
            
            # Check that lead data was prepared correctly
            call_args = mock_send.call_args[0][0]
            self.assertEqual(call_args['email'], 'john.doe@example.com')
            self.assertEqual(call_args['chatbot_name'], 'CRM Test Bot')
    
    def test_crm_not_triggered_without_email(self):
        """Test that CRM is not triggered when no email is detected"""
        # Create user message without email
        Message.objects.create(
            conversation=self.conversation,
            role='user',
            content='Hi, I need help with pricing'
        )
        
        with patch('apps.core.crm_service.HubSpotService.send_lead') as mock_send:
            # Process conversation for CRM
            result = CRMService.process_conversation_for_crm(self.conversation, self.chatbot)
            
            self.assertFalse(result)
            mock_send.assert_not_called()
    
    def test_crm_disabled_chatbot(self):
        """Test that CRM is not triggered when disabled"""
        self.chatbot.crm_enabled = False
        self.chatbot.save()
        
        Message.objects.create(
            conversation=self.conversation,
            role='user',
            content='My email is test@example.com'
        )
        
        with patch('apps.core.crm_service.HubSpotService.send_lead') as mock_send:
            result = CRMService.process_conversation_for_crm(self.conversation, self.chatbot)
            
            self.assertFalse(result)
            mock_send.assert_not_called()


class CRMMetadataTests(TestCase):
    """Test CRM metadata tracking in conversations"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.chatbot = Chatbot.objects.create(
            user=self.user,
            name='Metadata Test Bot',
            public_url_slug='metadata-test-bot',
            crm_enabled=True,
            crm_provider='hubspot',
            crm_webhook_url='https://forms.hubspot.com/uploads/form/v2/12345/test-guid'
        )
        
        self.conversation = Conversation.objects.create(
            chatbot=self.chatbot,
            metadata={'source': 'widget'}
        )
    
    @patch('apps.core.crm_service.HubSpotService.send_lead')
    def test_crm_metadata_saved_on_success(self, mock_send):
        """Test that CRM metadata is saved when lead is sent successfully"""
        mock_send.return_value = True
        
        Message.objects.create(
            conversation=self.conversation,
            role='user',
            content='Please contact me at success@test.com'
        )
        
        CRMService.process_conversation_for_crm(self.conversation, self.chatbot)
        
        self.conversation.refresh_from_db()
        crm_data = self.conversation.metadata.get('crm_integration')
        
        self.assertIsNotNone(crm_data)
        self.assertTrue(crm_data['attempted'])
        self.assertTrue(crm_data['success'])
        self.assertEqual(crm_data['email_captured'], 'success@test.com')
        self.assertEqual(crm_data['provider'], 'hubspot')
    
    @patch('apps.core.crm_service.HubSpotService.send_lead')
    def test_crm_metadata_saved_on_failure(self, mock_send):
        """Test that CRM metadata is saved when lead submission fails"""
        mock_send.return_value = False
        
        Message.objects.create(
            conversation=self.conversation,
            role='user',
            content='Contact me at failure@test.com'
        )
        
        CRMService.process_conversation_for_crm(self.conversation, self.chatbot)
        
        self.conversation.refresh_from_db()
        crm_data = self.conversation.metadata.get('crm_integration')
        
        self.assertIsNotNone(crm_data)
        self.assertTrue(crm_data['attempted'])
        self.assertFalse(crm_data['success'])
        self.assertEqual(crm_data['email_captured'], 'failure@test.com')


# Integration test markers for pytest
@pytest.mark.integration
class HubSpotIntegrationTests(TestCase):
    """Integration tests for HubSpot (requires real endpoint for full testing)"""
    
    def setUp(self):
        # These tests require actual HubSpot form URL for full integration testing
        self.hubspot_test_url = "https://forms.hubspot.com/uploads/form/v2/TEST_PORTAL/TEST_FORM"
    
    @pytest.mark.skip("Requires real HubSpot endpoint")
    def test_real_hubspot_connection(self):
        """Test actual HubSpot connection (skip by default)"""
        service = HubSpotService(self.hubspot_test_url)
        result = service.test_connection()
        # This would test against a real HubSpot form
        # Skip by default to avoid hitting real endpoints in tests
    
    @pytest.mark.skip("Requires real HubSpot endpoint") 
    def test_real_lead_submission(self):
        """Test actual lead submission to HubSpot (skip by default)"""
        service = HubSpotService(self.hubspot_test_url)
        lead_data = {
            "email": "integration.test@example.com",
            "first_name": "Integration",
            "last_name": "Test",
            "message": "This is an integration test lead"
        }
        result = service.send_lead(lead_data)
        # This would submit a real lead to HubSpot
        # Skip by default to avoid creating test data in real CRM