"""
Main API URL configuration implementing the full architecture specification.
"""

from django.urls import path, include
from rest_framework import routers
from django.http import JsonResponse

# Import actual ViewSets 
from apps.chatbots.api_views import ChatbotViewSet
from apps.knowledge.api_views import KnowledgeSourceViewSet, KnowledgeChunkViewSet
from apps.conversations.api_views import ConversationViewSet
from apps.chatbots import crm_views
from apps.billing.api_views_chatbase import PricingViewSet, BillingViewSet as ChatbaseBillingViewSet
from apps.billing.checkout_views import create_checkout_session, get_checkout_plans

# Placeholder ViewSets for other apps
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

class PlaceholderViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]  # Allow public access for testing
    
    def list(self, request):
        return Response({'todo': 'implement_viewset', 'action': 'list'})
    
    def create(self, request):
        return Response({'todo': 'implement_viewset', 'action': 'create'})
    
    def retrieve(self, request, pk=None):
        return Response({'todo': 'implement_viewset', 'action': 'retrieve', 'pk': pk})
    
    def update(self, request, pk=None):
        return Response({'todo': 'implement_viewset', 'action': 'update', 'pk': pk})
    
    def destroy(self, request, pk=None):
        return Response({'todo': 'implement_viewset', 'action': 'destroy', 'pk': pk})

# Use placeholder for other ViewSets
UserViewSet = OrganizationViewSet = TeamMemberViewSet = PlaceholderViewSet
MessageViewSet = PlaceholderViewSet
WebhookViewSet = PlaceholderViewSet

# Create DRF router
router = routers.DefaultRouter()

# Register ViewSets as per architecture specification
router.register(r'users', UserViewSet, basename='user')
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'team-members', TeamMemberViewSet, basename='teammember')
router.register(r'chatbots', ChatbotViewSet, basename='chatbot')
router.register(r'knowledge-sources', KnowledgeSourceViewSet, basename='knowledgesource')
router.register(r'knowledge-chunks', KnowledgeChunkViewSet, basename='knowledgechunk')
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'billing', ChatbaseBillingViewSet, basename='billing')
router.register(r'pricing', PricingViewSet, basename='pricing')
router.register(r'webhooks', WebhookViewSet, basename='webhook')

app_name = 'api'

urlpatterns = [
    # Health check endpoint
    path('health/', lambda request: JsonResponse({'status': 'ok'}), name='health'),
    
    # Widget endpoints - Public API for embeddable widgets
    path('widget/', include('widget.urls', namespace='widget')),
    
    # CRM integration endpoints
    path('chatbots/<uuid:chatbot_id>/crm/', include([
        path('settings/', crm_views.chatbot_crm_settings, name='crm_settings'),
        path('test/', crm_views.test_crm_connection, name='crm_test'),
    ])),
    
    # Authentication endpoints (implementing DEVELOPMENT_STRATEGY.md Task 2)
    path('auth/', include('apps.accounts.auth_urls')),
    
    # Chat endpoints - RAG-powered chat with privacy enforcement
    path('chat/', include('apps.conversations.urls')),
    
    # Knowledge source upload endpoints
    path('knowledge/', include([
        path('upload/', include('apps.knowledge.urls')),
    ])),
    
    # Stripe checkout endpoints  
    path('checkout/', include([
        path('create/', create_checkout_session, name='create_checkout'),
        path('plans/', get_checkout_plans, name='checkout_plans'),
    ])),
    
    # Webhook endpoints
    path('webhooks/', include([
        path('stripe/', lambda request: JsonResponse({'todo': 'implement_stripe_webhook'}), name='stripe_webhook'),
        path('crm/', lambda request: JsonResponse({'todo': 'implement_crm_webhook'}), name='crm_webhook'),
    ])),
    
    # Main ViewSet routes
    path('', include(router.urls)),
]