from django.urls import path
from . import common_consumer

urlpatterns = [
    path("landing-stats/", common_consumer.GlobalCount.as_asgi())
]