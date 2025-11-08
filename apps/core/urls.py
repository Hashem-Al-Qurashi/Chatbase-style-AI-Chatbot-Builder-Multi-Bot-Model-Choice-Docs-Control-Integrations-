"""
URL configuration for core app health checks and monitoring.
"""

from django.urls import path
from . import health, views

urlpatterns = [
    # Basic health check for load balancers
    path('health/', health.basic_health, name='basic_health'),
    
    # Detailed health check with all components
    path('api/health/', health.detailed_health, name='detailed_health'),
    
    # Component-specific health checks
    path('api/health/<str:component>/', health.component_health, name='component_health'),
    
    # Kubernetes-style checks
    path('api/health/readiness/', health.readiness_check, name='readiness_check'),
    path('api/health/liveness/', health.liveness_check, name='liveness_check'),
    
    # Streaming service health
    path('api/health/streaming/', views.StreamingHealthView.as_view(), name='streaming_health'),
    
    # Prometheus metrics
    path('metrics/', health.metrics, name='metrics'),
    
    # WebSocket test interface
    path('websocket-test/', views.websocket_test_view, name='websocket_test'),
    
    # Simple ping
    path('ping/', views.ping_view, name='ping'),
]