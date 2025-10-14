"""
WebSocket routing for conversations app.
Handles real-time chat communication.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Private authenticated chat for dashboard users
    re_path(r'ws/chat/private/(?P<chatbot_id>[0-9a-f-]+)/$', consumers.PrivateChatConsumer.as_asgi()),
    
    # Public chat for embedded widget users  
    re_path(r'ws/chat/public/(?P<slug>[\w-]+)/$', consumers.PublicChatConsumer.as_asgi()),
]