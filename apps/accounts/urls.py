"""
URL configuration for accounts app.
"""

from django.urls import path
from apps.accounts import api_views

app_name = 'accounts'

urlpatterns = [
    # User management endpoints
    path('register/', api_views.register, name='register'),
    path('login/', api_views.login, name='login'),
    path('logout/', api_views.logout, name='logout'),
    
    # Password reset endpoints
    path('password-reset/', api_views.password_reset_request, name='password_reset_request'),
    path('password-reset/confirm/', api_views.password_reset_confirm, name='password_reset_confirm'),
    
    # OAuth2 endpoints
    path('oauth2/authorize/', api_views.oauth2_authorize, name='oauth2_authorize'),
    path('oauth2/callback/', api_views.oauth2_callback, name='oauth2_callback'),
    
    # For compatibility with core OAuth module redirect URI generation
    path('oauth/callback/', api_views.oauth2_callback, name='oauth_callback'),
]