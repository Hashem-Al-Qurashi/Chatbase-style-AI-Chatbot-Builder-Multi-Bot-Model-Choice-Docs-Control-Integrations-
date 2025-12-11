"""
CRM Integration API Views
Handles CRM settings and testing for chatbots
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from .models import Chatbot
from apps.core.crm_service import CRMService, CRMIntegrationError

import logging
import structlog

logger = structlog.get_logger()


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def chatbot_crm_settings(request, chatbot_id):
    """
    Get or update CRM settings for a chatbot
    
    GET /api/v1/chatbots/{id}/crm/settings/
    POST /api/v1/chatbots/{id}/crm/settings/
    """
    # Get chatbot and verify ownership
    chatbot = get_object_or_404(
        Chatbot,
        id=chatbot_id,
        user=request.user
    )
    
    if request.method == 'GET':
        # Return current CRM settings
        return Response({
            'crm_enabled': chatbot.crm_enabled,
            'crm_provider': chatbot.crm_provider,
            'crm_webhook_url': chatbot.crm_webhook_url or '',
            'has_api_key': bool(chatbot.crm_webhook_secret),
            'status': 'configured' if chatbot.crm_webhook_url else 'not_configured'
        })
    
    elif request.method == 'POST':
        # Update CRM settings
        try:
            crm_enabled = request.data.get('crm_enabled', False)
            crm_provider = request.data.get('crm_provider', 'hubspot')
            webhook_url = request.data.get('webhook_url', '').strip()
            api_key = request.data.get('api_key', '').strip()
            
            # Validate provider
            valid_providers = ['hubspot', 'zoho', 'salesforce']
            if crm_provider not in valid_providers:
                return Response(
                    {'error': f'Invalid CRM provider. Must be one of: {valid_providers}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # If enabling CRM, validate webhook URL
            if crm_enabled and not webhook_url:
                return Response(
                    {'error': 'Webhook URL is required when enabling CRM integration'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate URL format if provided
            if webhook_url:
                try:
                    service = CRMService.get_service(crm_provider, webhook_url, api_key)
                except (ValidationError, CRMIntegrationError) as e:
                    return Response(
                        {'error': str(e)}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Update chatbot settings
            chatbot.crm_enabled = crm_enabled
            chatbot.crm_provider = crm_provider
            chatbot.crm_webhook_url = webhook_url if webhook_url else None
            chatbot.crm_webhook_secret = api_key if api_key else None
            chatbot.save()
            
            logger.info(f"Updated CRM settings for chatbot {chatbot.name}: {crm_provider} {'enabled' if crm_enabled else 'disabled'}")
            
            return Response({
                'message': 'CRM settings updated successfully',
                'crm_enabled': chatbot.crm_enabled,
                'crm_provider': chatbot.crm_provider,
                'status': 'configured' if chatbot.crm_webhook_url else 'not_configured'
            })
            
        except Exception as e:
            logger.error(f"Error updating CRM settings: {str(e)}")
            return Response(
                {'error': 'Failed to update CRM settings'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_crm_connection(request, chatbot_id):
    """
    Test CRM connection for a chatbot
    
    POST /api/v1/chatbots/{id}/crm/test/
    Body: {
        "provider": "hubspot",
        "webhook_url": "https://forms.hubspot.com/...",
        "api_key": "optional_key"
    }
    """
    # Get chatbot and verify ownership
    chatbot = get_object_or_404(
        Chatbot,
        id=chatbot_id,
        user=request.user
    )
    
    try:
        provider = request.data.get('provider', 'hubspot')
        webhook_url = request.data.get('webhook_url', '').strip()
        api_key = request.data.get('api_key', '').strip()
        
        if not webhook_url:
            return Response(
                {'error': 'Webhook URL is required for testing'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get CRM service and test connection
        crm_service = CRMService.get_service(provider, webhook_url, api_key)
        test_result = crm_service.test_connection()
        
        logger.info(f"CRM connection test for chatbot {chatbot.name}: {test_result}")
        
        if test_result['success']:
            return Response({
                'success': True,
                'message': test_result['message']
            })
        else:
            return Response({
                'success': False,
                'message': test_result['message']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except (ValidationError, CRMIntegrationError) as e:
        return Response(
            {'success': False, 'message': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error testing CRM connection: {str(e)}")
        return Response(
            {'success': False, 'message': 'Failed to test connection'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )