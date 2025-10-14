"""
URL configuration for chatbot_saas project.
Simplified version for development.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def home_view(request):
    """Simple home page."""
    return JsonResponse({
        'message': 'Django Chatbot SaaS API',
        'status': 'development',
        'version': '0.1.0'
    })

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', home_view, name='home'),
    # Main API endpoints
    path('api/v1/', include('apps.api.urls')),
    # Authentication endpoints
    path('auth/', include('apps.accounts.auth_urls', namespace='auth')),
    # Health checks
    path('health/', lambda request: JsonResponse({'status': 'ok'}), name='health'),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)