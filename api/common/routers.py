from django.urls import path
from . import common_consumer

urlpatterns = [
    path("globalcount/",common_consumer.GlobalCount.as_asgi())
]