"""
Widget views for serving chatbot embed.
Provides HTML widget that can be embedded on any website.
"""

from django.shortcuts import render, get_object_or_404
from django.views.decorators.clickjacking import xframe_options_exempt
from django.core.cache import cache
import json

from apps.chatbots.models import Chatbot


@xframe_options_exempt
def chatbot_widget(request, slug):
    """
    Serve chatbot widget HTML.
    This view is exempted from X-Frame-Options to allow embedding.
    """
    # Get chatbot
    chatbot = get_object_or_404(
        Chatbot,
        public_url_slug=slug,
        status='completed'
    )
    
    # Cache chatbot settings for performance
    cache_key = f"chatbot_widget_settings_{slug}"
    settings_data = cache.get(cache_key)
    
    if not settings_data:
        settings = chatbot.settings
        settings_data = {
            'enable_lead_capture': settings.enable_lead_capture,
            'lead_capture_trigger': settings.lead_capture_trigger,
            'lead_capture_message': settings.lead_capture_message,
            'show_powered_by': settings.show_powered_by,
            'custom_css': settings.custom_css,
            'rate_limit_messages_per_hour': settings.rate_limit_messages_per_hour
        }
        cache.set(cache_key, settings_data, 300)  # Cache for 5 minutes
    
    context = {
        'chatbot': chatbot,
        'chatbot_settings_json': json.dumps(settings_data)
    }
    
    response = render(request, 'embed/chatbot_widget.html', context)
    
    # Set headers to allow embedding
    response['X-Frame-Options'] = 'ALLOWALL'
    response['Content-Security-Policy'] = "frame-ancestors *;"
    
    return response