from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path

from geoinsight.core.notifications import AnalyticsConsumer, ConversionConsumer

application = ProtocolTypeRouter(
    {
        'http': get_asgi_application(),
        'websocket': AuthMiddlewareStack(
            URLRouter(
                [
                    path(
                        'ws/analytics/project/<int:project_id>/results/',
                        AnalyticsConsumer.as_asgi(),
                        name='analytics-ws',
                    ),
                    path(
                        'ws/conversion/',
                        ConversionConsumer.as_asgi(),
                        name='conversion-ws',
                    ),
                ]
            )
        ),
    }
)
