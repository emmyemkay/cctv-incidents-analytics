from django.urls import path
from .consumers import IncidentStreamConsumer

websocket_urlpatterns = [path("ws/incidents/", IncidentStreamConsumer.as_asgi())]
