"""
Comprehensive integration tests for the API.
Tests critical user flows and system integration.
"""

import pytest
import json
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, Mock

from apps.chatbots.models import Chatbot, ChatbotSettings
from apps.conversations.models import Conversation, Message
from apps.knowledge.models import KnowledgeSource, KnowledgeChunk
from apps.accounts.models import Organization, TeamMember
from apps.billing.models import Subscription

User = get_user_model()


class ChatbotIntegrationTest(APITestCase):
    """Test complete chatbot lifecycle."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        self.organization = Organization.objects.create(
            name='Test Org',
            owner=self.user
        )
        
        TeamMember.objects.create(
            organization=self.organization,
            user=self.user,
            role='owner',
            is_active=True
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_chatbot_creation_and_training_flow(self):
        """Test complete chatbot creation, knowledge upload, and training."""
        
        # 1. Create chatbot
        chatbot_data = {
            'name': 'Test Chatbot',
            'description': 'A test chatbot',
            'theme_color': '#2563EB',
            'welcome_message': 'Hello! How can I help?',
            'temperature': 0.7,
            'max_tokens': 500,
            'enable_citations': True
        }
        
        response = self.client.post('/api/v1/chatbots/', chatbot_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        chatbot_id = response.data['id']
        chatbot = Chatbot.objects.get(id=chatbot_id)
        
        # Verify chatbot creation
        self.assertEqual(chatbot.name, 'Test Chatbot')
        self.assertEqual(chatbot.user, self.user)
        self.assertTrue(hasattr(chatbot, 'settings'))
        
        # 2. Upload knowledge source
        with patch('apps.core.tasks.process_document_task.delay') as mock_task:
            knowledge_data = {
                'chatbot_id': chatbot_id,
                'name': 'Test Document',
                'description': 'Test knowledge source',
                'is_citable': True
            }
            
            # Simulate file upload
            from django.core.files.uploadedfile import SimpleUploadedFile
            test_file = SimpleUploadedFile(
                "test.txt",
                b"This is test content for the chatbot to learn from.",
                content_type="text/plain"
            )
            knowledge_data['file'] = test_file
            
            response = self.client.post('/api/v1/knowledge/upload/', knowledge_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            
            # Verify task was called
            mock_task.assert_called_once()
            
            knowledge_source = KnowledgeSource.objects.get(id=response.data['id'])
            self.assertEqual(knowledge_source.chatbot, chatbot)
            self.assertEqual(knowledge_source.source_type, 'document')
        
        # 3. Simulate knowledge processing completion
        knowledge_source.processing_status = 'completed'
        knowledge_source.save()
        
        # Create a test chunk
        KnowledgeChunk.objects.create(
            source=knowledge_source,
            content="This is test content for the chatbot.",
            chunk_index=0,
            chunk_hash="test_hash",
            is_citable=True
        )
        
        # 4. Train chatbot
        with patch('apps.core.tasks.train_chatbot_task.delay') as mock_train:
            response = self.client.post(f'/api/v1/chatbots/{chatbot_id}/train/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_train.assert_called_once()
        
        # 5. Simulate training completion
        chatbot.status = 'completed'
        chatbot.save()
        
        # 6. Test chatbot response
        with patch('apps.core.services.ChatService.generate_response') as mock_chat:
            mock_chat.return_value = {
                'message': 'Hello! I can help you with that.',
                'sources': [],
                'processing_time': 150
            }
            
            test_data = {
                'message': 'Hello, how are you?',
                'include_sources': True
            }
            
            response = self.client.post(f'/api/v1/chatbots/{chatbot_id}/test/', test_data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('response', response.data)
            mock_chat.assert_called_once()
    
    def test_chatbot_settings_management(self):
        """Test chatbot settings CRUD operations."""
        
        # Create chatbot
        chatbot = Chatbot.objects.create(
            user=self.user,
            name='Settings Test Bot',
            status='completed'
        )
        
        ChatbotSettings.objects.create(chatbot=chatbot)
        
        # Get settings
        response = self.client.get(f'/api/v1/chatbots/{chatbot.id}/settings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Update settings
        settings_data = {
            'system_prompt': 'You are a helpful assistant.',
            'enable_lead_capture': True,
            'lead_capture_trigger': 'after_messages',
            'rate_limit_messages_per_hour': 100
        }
        
        response = self.client.patch(f'/api/v1/chatbots/{chatbot.id}/update_settings/', settings_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify update
        chatbot.refresh_from_db()
        settings = chatbot.settings
        self.assertEqual(settings.system_prompt, 'You are a helpful assistant.')
        self.assertTrue(settings.enable_lead_capture)
        self.assertEqual(settings.lead_capture_trigger, 'after_messages')


class PublicChatIntegrationTest(TransactionTestCase):
    """Test public chat widget functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.chatbot = Chatbot.objects.create(
            user=self.user,
            name='Public Test Bot',
            public_url_slug='test-bot',
            status='completed',
            welcome_message='Hello! How can I help you today?'
        )
        
        ChatbotSettings.objects.create(
            chatbot=self.chatbot,
            enable_lead_capture=True,
            lead_capture_trigger='after_messages'
        )
        
        self.client = APIClient()
    
    def test_public_chat_flow(self):
        """Test complete public chat conversation flow."""
        
        # 1. Get widget config
        response = self.client.get(f'/api/v1/chat/{self.chatbot.public_url_slug}/config/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Public Test Bot')
        
        # 2. Send first message
        with patch('apps.core.services.ChatService.generate_response') as mock_chat:
            mock_chat.return_value = {
                'message': 'Hello! How can I help you?',
                'sources': [],
                'processing_time': 100
            }
            
            message_data = {
                'message': 'Hello, I need help with your product.'
            }
            
            response = self.client.post(
                f'/api/v1/chat/{self.chatbot.public_url_slug}/message/',
                message_data
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('session_id', response.data)
            self.assertIn('message', response.data)
            
            session_id = response.data['session_id']
        
        # 3. Continue conversation
        with patch('apps.core.services.ChatService.generate_response') as mock_chat:
            mock_chat.return_value = {
                'message': 'I can help with that! What specific questions do you have?',
                'sources': [],
                'processing_time': 120
            }
            
            message_data = {
                'message': 'What are your pricing plans?',
                'session_id': session_id
            }
            
            response = self.client.post(
                f'/api/v1/chat/{self.chatbot.public_url_slug}/message/',
                message_data
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 4. Capture lead
        lead_data = {
            'email': 'lead@example.com',
            'name': 'John Doe',
            'phone': '+1234567890',
            'session_id': session_id
        }
        
        with patch('apps.core.tasks.send_lead_to_crm_task.delay') as mock_crm:
            response = self.client.post(
                f'/api/v1/chat/{self.chatbot.public_url_slug}/lead/',
                lead_data
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 5. Submit feedback
        feedback_data = {
            'rating': 5,
            'feedback': 'Great experience!',
            'session_id': session_id
        }
        
        response = self.client.post(
            f'/api/v1/chat/{self.chatbot.public_url_slug}/feedback/',
            feedback_data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify conversation was created
        conversation = Conversation.objects.get(session_id=session_id)
        self.assertEqual(conversation.chatbot, self.chatbot)
        self.assertEqual(conversation.lead_email, 'lead@example.com')
        self.assertEqual(conversation.user_satisfaction, 5)
        
        # Verify messages were created
        messages = conversation.messages.all()
        self.assertEqual(messages.count(), 4)  # 2 user + 2 assistant messages
    
    def test_rate_limiting(self):
        """Test rate limiting on public endpoints."""
        
        # Simulate multiple rapid requests
        message_data = {'message': 'Test message'}
        
        # First few requests should succeed
        for i in range(5):
            response = self.client.post(
                f'/api/v1/chat/{self.chatbot.public_url_slug}/message/',
                message_data
            )
            if i < 3:
                self.assertIn(response.status_code, [200, 201])
            else:
                # Should hit rate limit
                if response.status_code == 429:
                    break
        
        # Verify rate limit response
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class AuthenticationIntegrationTest(APITestCase):
    """Test authentication flows."""
    
    def test_user_registration_and_login_flow(self):
        """Test complete user registration and authentication."""
        
        # 1. Register user
        registration_data = {
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'User'
        }
        
        response = self.client.post('/api/v1/auth/register/', registration_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access_token', response.data)
        self.assertIn('user', response.data)
        
        # Verify user creation
        user = User.objects.get(email='newuser@example.com')
        self.assertEqual(user.first_name, 'New')
        
        # Verify organization creation
        self.assertTrue(user.team_memberships.filter(role='owner').exists())
        
        # 2. Login
        login_data = {
            'email': 'newuser@example.com',
            'password': 'SecurePass123!'
        }
        
        response = self.client.post('/api/v1/auth/login/', login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        
        # 3. Access protected endpoint
        access_token = response.data['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'newuser@example.com')
    
    def test_oauth2_flow(self):
        """Test OAuth2 authentication flow."""
        
        # 1. Get authorization URL
        response = self.client.get('/api/v1/auth/oauth2/authorize/', {
            'provider': 'google',
            'redirect_uri': 'http://localhost:3000/auth/callback'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('authorization_url', response.data)
        
        # 2. Simulate OAuth callback
        with patch('apps.core.services.AuthenticationService.authenticate_oauth') as mock_auth:
            mock_auth.return_value = Mock(
                success=True,
                user_data={
                    'email': 'oauth@example.com',
                    'first_name': 'OAuth',
                    'last_name': 'User',
                    'provider': 'google'
                }
            )
            
            callback_data = {
                'code': 'test_auth_code',
                'state': 'test_state'
            }
            
            response = self.client.post('/api/v1/auth/oauth2/callback/', callback_data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('access_token', response.data)
            self.assertTrue(response.data['created'])


class WebhookIntegrationTest(TransactionTestCase):
    """Test webhook integrations."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.organization = Organization.objects.create(
            name='Test Org',
            owner=self.user
        )
        
        self.client = APIClient()
    
    @patch('stripe.Webhook.construct_event')
    def test_stripe_webhook_subscription_created(self, mock_stripe):
        """Test Stripe webhook for subscription creation."""
        
        # Mock Stripe event
        mock_event = {
            'id': 'evt_test123',
            'type': 'customer.subscription.created',
            'data': {
                'object': {
                    'id': 'sub_test123',
                    'customer': 'cus_test123',
                    'status': 'active',
                    'current_period_start': 1234567890,
                    'current_period_end': 1234567890 + 2592000  # +30 days
                }
            }
        }
        mock_stripe.return_value = mock_event
        
        # Send webhook
        response = self.client.post(
            '/api/v1/webhooks/stripe/',
            data='test_payload',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_signature'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify subscription was created
        subscription = Subscription.objects.filter(
            stripe_subscription_id='sub_test123'
        ).first()
        self.assertIsNotNone(subscription)
        self.assertEqual(subscription.status, 'active')
    
    def test_crm_webhook_processing(self):
        """Test CRM webhook processing."""
        
        webhook_data = {
            'event_type': 'contact.created',
            'event_id': 'crm_event_123',
            'contact_id': 'contact_456',
            'email': 'webhook@example.com',
            'name': 'Webhook User'
        }
        
        response = self.client.post(
            '/api/v1/webhooks/crm/',
            webhook_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify webhook event was logged
        from apps.webhooks.models import WebhookEvent
        event = WebhookEvent.objects.filter(
            event_type='contact.created',
            provider='crm'
        ).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.status, 'processed')


class PrivacyEnforcementTest(APITestCase):
    """Test privacy controls and data protection."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.chatbot = Chatbot.objects.create(
            user=self.user,
            name='Privacy Test Bot',
            public_url_slug='privacy-bot',
            status='completed'
        )
        
        # Create knowledge sources with different privacy levels
        self.public_source = KnowledgeSource.objects.create(
            chatbot=self.chatbot,
            name='Public Knowledge',
            source_type='document',
            is_citable=True,
            processing_status='completed'
        )
        
        self.private_source = KnowledgeSource.objects.create(
            chatbot=self.chatbot,
            name='Private Knowledge',
            source_type='document',
            is_citable=False,  # Not citable = private
            processing_status='completed'
        )
        
        self.client = APIClient()
    
    def test_privacy_filtering_in_chat(self):
        """Test that private content is not cited in public chat."""
        
        # Create chunks
        public_chunk = KnowledgeChunk.objects.create(
            source=self.public_source,
            content="This is public information that can be cited.",
            chunk_index=0,
            is_citable=True
        )
        
        private_chunk = KnowledgeChunk.objects.create(
            source=self.private_source,
            content="This is private information that cannot be cited.",
            chunk_index=0,
            is_citable=False
        )
        
        with patch('apps.core.services.PrivacyService.filter_private_content') as mock_privacy:
            mock_privacy.return_value = {
                'filtered_chunks': [public_chunk.id],  # Only public chunk
                'privacy_violations': ['private_content_detected']
            }
            
            with patch('apps.core.services.ChatService.generate_response') as mock_chat:
                mock_chat.return_value = {
                    'message': 'Here is the public information you requested.',
                    'sources': [
                        {
                            'chunk_id': str(public_chunk.id),
                            'source_name': 'Public Knowledge',
                            'is_citable': True,
                            'relevance_score': 0.95
                        }
                        # Private chunk should not appear in sources
                    ],
                    'processing_time': 150
                }
                
                message_data = {
                    'message': 'Tell me about your policies'
                }
                
                response = self.client.post(
                    f'/api/v1/chat/{self.chatbot.public_url_slug}/message/',
                    message_data
                )
                
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                
                # Verify only public source is returned
                sources = response.data.get('sources', [])
                source_names = [s['name'] for s in sources]
                self.assertIn('Public Knowledge', source_names)
                self.assertNotIn('Private Knowledge', source_names)
    
    def test_data_retention_compliance(self):
        """Test data retention and deletion compliance."""
        
        # Create conversation with data retention setting
        conversation = Conversation.objects.create(
            chatbot=self.chatbot,
            data_retention_days=7,  # Short retention for testing
            lead_email='test@example.com'
        )
        
        # Verify conversation exists
        self.assertTrue(Conversation.objects.filter(id=conversation.id).exists())
        
        # Simulate data retention cleanup (this would normally be a scheduled task)
        from django.utils import timezone
        from datetime import timedelta
        
        # Backdate the conversation
        old_date = timezone.now() - timedelta(days=8)
        conversation.created_at = old_date
        conversation.save()
        
        # This would be called by a scheduled cleanup task
        expired_conversations = Conversation.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=7)
        )
        
        self.assertEqual(expired_conversations.count(), 1)
        self.assertEqual(expired_conversations.first().id, conversation.id)