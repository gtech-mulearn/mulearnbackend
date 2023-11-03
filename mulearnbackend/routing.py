from django.urls import path, include
from channels.routing import URLRouter
from api import routing as api_routing

urlpatterns = [
    path("ws/v1/", URLRouter(api_routing.urlpatterns))
]