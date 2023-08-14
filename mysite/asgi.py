"""
ASGI config for mysite project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os
import atexit
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

import chat.routing
import app.routing


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django_asgi_app = get_asgi_application()
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                chat.routing.websocket_urlpatterns + app.routing.websocket_urlpatterns
            )
        ),
    }
)

import chat.models


def cleanup_function():
    room_member = chat.models.RoomMember.objects.all()
    for room in room_member:
        room.channel_names.clear()
        room.save(update_fields=["channel_names"])
    print("Program is exiting. Cleanup function is called")


atexit.register(cleanup_function)
