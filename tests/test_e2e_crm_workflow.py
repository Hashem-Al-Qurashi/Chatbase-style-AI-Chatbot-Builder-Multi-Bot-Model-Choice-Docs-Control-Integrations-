"""
End-to-End Tests for Complete CRM Integration Workflow
Tests the entire flow from widget chat to CRM lead creation
"""

import pytest
from unittest.mock import patch, Mock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.chatbots.models import Chatbot
from apps.conversations.models import Conversation, Message

User = get_user_model()


class E2ECRMWorkflowTests(TransactionTestCase):
    """End-to-end tests for complete CRM workflow"""
    
    def setUp(self):
        """Set up test data for E2E testing"""
        self.user = User.objects.create_user(
            email='crm@example.com',
            password='testpass123',
            first_name='CRM',
            last_name='User'
        )
        
        # Create chatbot with CRM enabled
        self.chatbot = Chatbot.objects.create(
            user=self.user,
            name='E2E CRM Test Bot',
            description='End-to-end testing for CRM integration',
            public_url_slug='e2e-crm-test-bot',
            status='ready',
            crm_enabled=True,
            crm_provider='hubspot',
            crm_webhook_url='https://forms.hubspot.com/uploads/form/v2/TEST_PORTAL/TEST_FORM'
        )
        
        self.client = APIClient()
    
    @patch('requests.post')
    def test_complete_widget_to_crm_workflow(self, mock_post):
        """Test complete workflow: Widget chat → Email detection → CRM submission"""
        
        # Mock successful HubSpot response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Step 1: Get widget configuration
        config_response = self.client.get(f'/api/v1/widget/config/{self.chatbot.public_url_slug}/')
        self.assertEqual(config_response.status_code, status.HTTP_200_OK)
        
        # Step 2: Send first message (no email)
        chat_data_1 = {
            'message': 'Hi, I need help with your services'
        }
        
        chat_response_1 = self.client.post(
            f'/api/v1/widget/chat/{self.chatbot.public_url_slug}/',
            chat_data_1,
            format='json'
        )
        
        self.assertEqual(chat_response_1.status_code, status.HTTP_200_OK)
        conversation_id = chat_response_1.json()['conversation_id']
        
        # Verify CRM was not triggered (no email)
        mock_post.assert_not_called()
        
        # Step 3: Send second message with email
        chat_data_2 = {
            'message': 'My email is john.customer@example.com, please send me more info',
            'conversation_id': conversation_id
        }
        
        chat_response_2 = self.client.post(
            f'/api/v1/widget/chat/{self.chatbot.public_url_slug}/',
            chat_data_2,
            format='json'
        )
        
        self.assertEqual(chat_response_2.status_code, status.HTTP_200_OK)
        
        # Verify CRM was triggered
        mock_post.assert_called_once()
        
        # Verify the data sent to HubSpot
        call_args = mock_post.call_args
        sent_data = call_args[1]['json']  # Get the JSON payload
        
        # Check that email was extracted and sent
        email_field = next(field for field in sent_data['fields'] if field['name'] == 'email')
        self.assertEqual(email_field['value'], 'john.customer@example.com')
        
        # Check that chatbot name was included
        chatbot_field = next(field for field in sent_data['fields'] if field['name'] == 'chatbot_name')
        self.assertEqual(chatbot_field['value'], 'E2E CRM Test Bot')
        
        # Step 4: Verify conversation metadata was updated
        conversation = Conversation.objects.get(id=conversation_id)
        crm_metadata = conversation.metadata.get('crm_integration')
        
        self.assertIsNotNone(crm_metadata)
        self.assertTrue(crm_metadata['attempted'])
        self.assertTrue(crm_metadata['success'])
        self.assertEqual(crm_metadata['email_captured'], 'john.customer@example.com')
    
    @patch('requests.post')
    def test_crm_workflow_with_name_extraction(self, mock_post):
        """Test workflow with name extraction from conversation"""
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Send message with name and email
        chat_data = {
            'message': "Hi, I'm Sarah Johnson and my email is sarah.johnson@company.com. I'm interested in your product pricing."
        }
        
        chat_response = self.client.post(
            f'/api/v1/widget/chat/{self.chatbot.public_url_slug}/',
            chat_data,
            format='json'
        )
        
        self.assertEqual(chat_response.status_code, status.HTTP_200_OK)
        
        # Verify CRM was triggered with name extraction
        mock_post.assert_called_once()
        
        sent_data = mock_post.call_args[1]['json']
        
        # Check extracted email
        email_field = next(field for field in sent_data['fields'] if field['name'] == 'email')
        self.assertEqual(email_field['value'], 'sarah.johnson@company.com')
        
        # Check extracted first name
        firstname_field = next(field for field in sent_data['fields'] if field['name'] == 'firstname')
        self.assertEqual(firstname_field['value'], 'Sarah')
        
        # Check extracted last name
        lastname_field = next(field for field in sent_data['fields'] if field['name'] == 'lastname')
        self.assertEqual(lastname_field['value'], 'Johnson')
    
    def test_crm_workflow_disabled_integration(self):
        """Test that CRM is not triggered when integration is disabled"""
        
        # Disable CRM for this test
        self.chatbot.crm_enabled = False
        self.chatbot.save()
        
        with patch('requests.post') as mock_post:
            chat_data = {
                'message': 'My email is test@example.com, please contact me'
            }
            
            chat_response = self.client.post(
                f'/api/v1/widget/chat/{self.chatbot.public_url_slug}/',
                chat_data,
                format='json'
            )
            
            self.assertEqual(chat_response.status_code, status.HTTP_200_OK)
            
            # Verify CRM was not triggered
            mock_post.assert_not_called()
    
    @patch('requests.post')
    def test_crm_failure_handling(self, mock_post):
        """Test that chat continues to work even if CRM fails"""
        
        # Mock HubSpot failure
        mock_post.side_effect = Exception("Network error")
        
        chat_data = {
            'message': 'Please contact me at error.test@example.com'
        }
        
        # Chat should still work even if CRM fails
        chat_response = self.client.post(
            f'/api/v1/widget/chat/{self.chatbot.public_url_slug}/',
            chat_data,
            format='json'
        )
        
        self.assertEqual(chat_response.status_code, status.HTTP_200_OK)
        self.assertIn('response', chat_response.json())
        
        # Verify CRM was attempted but failed gracefully
        conversation_id = chat_response.json()['conversation_id']
        conversation = Conversation.objects.get(id=conversation_id)
        
        # Conversation should still exist and be functional
        self.assertIsNotNone(conversation)
        self.assertEqual(conversation.chatbot, self.chatbot)


class CRMAPIEndpointTests(TestCase):
    """Test CRM API endpoints for dashboard functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='api@example.com',
            password='testpass123'
        )
        
        self.chatbot = Chatbot.objects.create(
            user=self.user,
            name='API Test Bot',
            public_url_slug='api-test-bot'
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_get_default_crm_settings(self):
        """Test getting default CRM settings via API"""
        url = f'/api/v1/chatbots/{self.chatbot.id}/crm/settings/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertFalse(data['crm_enabled'])
        self.assertEqual(data['crm_provider'], 'hubspot')
        self.assertEqual(data['crm_webhook_url'], '')
        self.assertFalse(data['has_api_key'])
        self.assertEqual(data['status'], 'not_configured')
    
    def test_save_hubspot_settings(self):
        """Test saving HubSpot settings via API"""
        url = f'/api/v1/chatbots/{self.chatbot.id}/crm/settings/'
        data = {
            'crm_enabled': True,
            'crm_provider': 'hubspot',
            'webhook_url': 'https://forms.hubspot.com/uploads/form/v2/12345/test-form',
            'api_key': 'test-api-key-12345'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify settings were saved
        self.chatbot.refresh_from_db()
        self.assertTrue(self.chatbot.crm_enabled)
        self.assertEqual(self.chatbot.crm_provider, 'hubspot')
        self.assertEqual(self.chatbot.crm_webhook_url, data['webhook_url'])
        self.assertEqual(self.chatbot.crm_webhook_secret, data['api_key'])
    
    @patch('apps.core.crm_service.HubSpotService.test_connection')
    def test_connection_test_endpoint(self, mock_test):
        """Test CRM connection test endpoint"""
        mock_test.return_value = {'success': True, 'message': 'Test successful'}
        
        url = f'/api/v1/chatbots/{self.chatbot.id}/crm/test/'
        data = {
            'provider': 'hubspot',
            'webhook_url': 'https://forms.hubspot.com/uploads/form/v2/12345/test-form',
            'api_key': 'test-key'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()['success'])
        mock_test.assert_called_once()
    
    def test_unauthorized_access_crm_settings(self):
        """Test that unauthorized users cannot access CRM settings"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        
        self.client.force_authenticate(user=other_user)
        
        url = f'/api/v1/chatbots/{self.chatbot.id}/crm/settings/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# Performance test for CRM processing
class CRMPerformanceTests(TestCase):
    """Test CRM performance and edge cases"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='perf@example.com',
            password='testpass123'
        )
        
        self.chatbot = Chatbot.objects.create(
            user=self.user,
            name='Performance Test Bot',
            public_url_slug='perf-test-bot',
            crm_enabled=True,
            crm_provider='hubspot',
            crm_webhook_url='https://forms.hubspot.com/uploads/form/v2/12345/test-form'
        )
    
    def test_multiple_emails_in_conversation(self):
        """Test behavior when multiple emails are in conversation"""
        conversation = Conversation.objects.create(
            chatbot=self.chatbot,
            metadata={'source': 'widget'}
        )
        
        # Message with multiple emails
        Message.objects.create(
            conversation=conversation,
            role='user',
            content='My emails are primary@example.com and secondary@example.com'
        )
        
        with patch('apps.core.crm_service.HubSpotService.send_lead') as mock_send:
            mock_send.return_value = True
            
            result = self.chatbot.process_conversation_for_crm(conversation, self.chatbot)
            
            # Should use the first email found
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            self.assertEqual(call_args['email'], 'primary@example.com')
    
    def test_long_conversation_email_detection(self):
        """Test email detection in long conversations"""
        conversation = Conversation.objects.create(
            chatbot=self.chatbot,
            metadata={'source': 'widget'}
        )
        
        # Create a longer conversation
        messages = [
            ('user', 'Hi, I need help with your pricing'),
            ('assistant', 'I can help with pricing. What would you like to know?'),
            ('user', 'What are your enterprise plans?'),
            ('assistant', 'Our enterprise plans start at $299/month...'),
            ('user', 'Sounds good! Please send me more details to my email: enterprise.client@bigcorp.com'),
            ('assistant', 'I\'ll be happy to send you more information!')
        ]
        
        for role, content in messages:
            Message.objects.create(
                conversation=conversation,
                role=role,
                content=content
            )
        
        with patch('apps.core.crm_service.HubSpotService.send_lead') as mock_send:
            mock_send.return_value = True
            
            from apps.core.crm_service import CRMService
            result = CRMService.process_conversation_for_crm(conversation, self.chatbot)
            
            self.assertTrue(result)
            mock_send.assert_called_once()
            
            # Verify email was detected correctly
            call_args = mock_send.call_args[0][0]
            self.assertEqual(call_args['email'], 'enterprise.client@bigcorp.com')
            self.assertIn('enterprise.client@bigcorp.com', call_args['message'])
    
    def test_widget_chat_api_with_crm_integration(self):
        """Test the widget chat API endpoint with CRM integration enabled"""
        
        with patch('apps.core.crm_service.HubSpotService.send_lead') as mock_send:
            mock_send.return_value = True
            
            # First message without email
            response_1 = self.client.post(
                f'/api/v1/widget/chat/{self.chatbot.public_url_slug}/',
                {'message': 'Hello, I have a question about your product'},
                format='json'
            )
            
            self.assertEqual(response_1.status_code, status.HTTP_200_OK)
            conversation_id = response_1.json()['conversation_id']
            
            # CRM should not be triggered yet
            mock_send.assert_not_called()
            
            # Second message with email
            response_2 = self.client.post(
                f'/api/v1/widget/chat/{self.chatbot.public_url_slug}/',
                {
                    'message': 'My name is Alex Customer and you can reach me at alex@customer.com',
                    'conversation_id': conversation_id
                },
                format='json'
            )
            
            self.assertEqual(response_2.status_code, status.HTTP_200_OK)
            
            # CRM should now be triggered
            mock_send.assert_called_once()
            
            # Verify conversation exists and has correct metadata
            conversation = Conversation.objects.get(id=conversation_id)
            self.assertIsNotNone(conversation.metadata.get('crm_integration'))
            self.assertTrue(conversation.metadata['crm_integration']['attempted'])
    
    def test_crm_settings_api_endpoints(self):
        """Test CRM settings API endpoints work correctly"""
        
        # Test authenticated access to CRM settings
        self.client.force_authenticate(user=self.user)
        
        # Get current settings
        settings_url = f'/api/v1/chatbots/{self.chatbot.id}/crm/settings/'
        get_response = self.client.get(settings_url)
        
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        
        # Update settings
        new_settings = {
            'crm_enabled': True,
            'crm_provider': 'hubspot',
            'webhook_url': 'https://forms.hubspot.com/uploads/form/v2/NEW_PORTAL/NEW_FORM',
            'api_key': 'new-test-api-key'
        }
        
        post_response = self.client.post(settings_url, new_settings, format='json')
        self.assertEqual(post_response.status_code, status.HTTP_200_OK)
        
        # Verify settings were saved
        updated_chatbot = Chatbot.objects.get(id=self.chatbot.id)
        self.assertTrue(updated_chatbot.crm_enabled)
        self.assertEqual(updated_chatbot.crm_webhook_url, new_settings['webhook_url'])
    
    @patch('apps.core.crm_service.HubSpotService.test_connection')
    def test_crm_connection_test_api(self, mock_test):
        """Test CRM connection test API endpoint"""
        
        mock_test.return_value = {'success': True, 'message': 'Connection successful'}
        
        self.client.force_authenticate(user=self.user)
        
        test_url = f'/api/v1/chatbots/{self.chatbot.id}/crm/test/'
        test_data = {
            'provider': 'hubspot',
            'webhook_url': 'https://forms.hubspot.com/uploads/form/v2/12345/test-form'
        }
        
        response = self.client.post(test_url, test_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()['success'])
        mock_test.assert_called_once()


# Load testing placeholder (for future implementation)
@pytest.mark.slow
class CRMLoadTests(TestCase):
    """Load tests for CRM integration (marked as slow)"""
    
    @pytest.mark.skip("Load testing - run manually")
    def test_concurrent_crm_submissions(self):
        """Test multiple simultaneous CRM submissions"""
        # This would test concurrent webhook calls
        # Skip by default as it requires load testing setup
        pass
    
    @pytest.mark.skip("Load testing - run manually") 
    def test_crm_rate_limiting(self):
        """Test CRM rate limiting behavior"""
        # This would test rate limiting for CRM webhooks
        # Skip by default as it requires specific rate limiting setup
        pass