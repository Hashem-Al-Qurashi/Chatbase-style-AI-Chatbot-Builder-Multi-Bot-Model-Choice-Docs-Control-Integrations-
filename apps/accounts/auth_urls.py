"""
Authentication URL configuration implementing DEVELOPMENT_STRATEGY.md Task 2.
Maps authentication endpoints to their respective view functions.
"""

from django.urls import path
from . import auth_views
from . import api_views

app_name = 'auth'

urlpatterns = [
    # Task 2 Subtask 1: User Registration Endpoint
    path('register/', auth_views.register, name='register'),
    
    # Task 2 Subtask 2: User Login Endpoint  
    path('login/', auth_views.login, name='login'),
    
    # Task 2 Subtask 3: Token Refresh Endpoint
    path('refresh/', auth_views.refresh_token, name='refresh'),
    
    # Task 2 Subtask 4: User Profile Endpoints
    path('me/', auth_views.current_user, name='current_user'),
    path('me/update/', auth_views.update_profile, name='update_profile'),
    path('logout/', auth_views.logout, name='logout'),
    
    # Task 3: OAuth2 Google Integration Endpoints
    path('oauth2/authorize/', api_views.oauth2_authorize, name='oauth2_authorize'),
    path('oauth2/callback/', api_views.oauth2_callback, name='oauth2_callback'),
    
    # Legacy endpoint for OAuth callback (used by core OAuth module)
    path('oauth/callback/', api_views.oauth2_callback, name='oauth_callback'),
    
    # Task 5: Password Reset Flow Endpoints
    path('password-reset/', auth_views.password_reset_request, name='password_reset_request'),
    path('password-reset/confirm/', auth_views.password_reset_confirm, name='password_reset_confirm'),
]