from django.urls import path, include
from channels.routing import URLRouter
from api.common import routing as common_routing

urlpatterns = [
    path("public/", URLRouter(common_routing.urlpatterns)),
]