"""
URL configuration for conversations app.
Defines chat endpoints for both authenticated and public users.
"""

from django.urls import path
from . import api_views

app_name = 'conversations'

urlpatterns = [
    # Private authenticated chat for dashboard users
    path('private/<uuid:chatbot_id>/', api_views.private_chat_message, name='private_chat_message'),
    
    # Public chat endpoints for embedded widget
    path('public/<slug:slug>/', api_views.public_chat_message, name='public_chat_message'),
    path('public/<slug:slug>/config/', api_views.chatbot_widget_config, name='widget_config'),
    path('public/<slug:slug>/lead/', api_views.capture_lead, name='capture_lead'),
    path('public/<slug:slug>/feedback/', api_views.conversation_feedback, name='conversation_feedback'),
    path('public/<slug:slug>/message-feedback/', api_views.message_feedback, name='message_feedback'),
]