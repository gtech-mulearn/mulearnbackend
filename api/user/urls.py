from django.urls import path
from .user_views import TestApi

urlpatterns = [
    path('test', TestApi.as_view()),
]
