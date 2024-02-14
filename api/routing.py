from django.urls import path, include
from channels.routing import URLRouter
from api.common import routing as common_routing
from api.dashboard.lc import dash_lc_routing

urlpatterns = [
    path("public/", URLRouter(common_routing.urlpatterns)),
    path('dashboard/', URLRouter(dash_lc_routing.urlpatterns)),
]
