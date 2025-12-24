"""
Widget URL configuration
Public endpoints for embeddable chat widgets
"""

from django.urls import path
from . import api_views

app_name = 'widget'

urlpatterns = [
    # Widget configuration endpoint
    path('config/<str:slug>/', api_views.get_widget_config, name='config'),
    
    # Widget chat endpoint
    path('chat/<str:slug>/', api_views.widget_chat, name='chat'),
    
    # Health check
    path('health/', api_views.widget_health, name='health'),
]