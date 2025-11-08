"""
Views for core app functionality.
"""

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import os
import asyncio

from .streaming_service import streaming_health_checker


def websocket_test_view(request):
    """Serve the WebSocket test page."""
    # Read the HTML file
    html_path = os.path.join(
        os.path.dirname(__file__), 
        'static', 'core', 'websocket_test.html'
    )
    
    try:
        with open(html_path, 'r') as f:
            html_content = f.read()
        return HttpResponse(html_content, content_type='text/html')
    except FileNotFoundError:
        return HttpResponse(
            '<h1>WebSocket Test Page Not Found</h1>',
            content_type='text/html',
            status=404
        )


class StreamingHealthView(View):
    """Health check endpoint for streaming service."""
    
    async def get(self, request):
        """Get streaming service health status."""
        health_status = await streaming_health_checker.check_health()
        
        # Determine HTTP status code based on health
        status_code = 200 if health_status.get('status') == 'healthy' else 503
        
        return JsonResponse(health_status, status=status_code)
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to handle async views."""
        # For Django < 3.1, we need to handle async views manually
        if hasattr(self, request.method.lower()):
            handler = getattr(self, request.method.lower())
            if asyncio.iscoroutinefunction(handler):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    response = loop.run_until_complete(handler(request, *args, **kwargs))
                finally:
                    loop.close()
                return response
        
        return super().dispatch(request, *args, **kwargs)


@csrf_exempt
def ping_view(request):
    """Simple ping endpoint for basic health checks."""
    from datetime import datetime
    return JsonResponse({
        'status': 'ok',
        'service': 'RAG Core Service',
        'timestamp': str(datetime.utcnow())
    })