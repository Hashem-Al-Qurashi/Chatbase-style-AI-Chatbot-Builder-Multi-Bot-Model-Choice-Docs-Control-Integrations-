"""
URL configuration for knowledge app.
Defines endpoints for knowledge source management.
"""

from django.urls import path
from . import api_views

app_name = 'knowledge'

urlpatterns = [
    # Document upload endpoint
    path('document/', api_views.upload_document, name='upload_document'),
    
    # URL processing endpoint
    path('url/', api_views.process_url, name='process_url'),
    
    # YouTube processing endpoint
    path('youtube/', api_views.process_youtube, name='process_youtube'),
]