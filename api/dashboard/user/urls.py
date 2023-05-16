from django.urls import path
from .dash_user_views import UserAPI


urlpatterns = [
    path('', UserAPI.as_view(), name='user-api'),
]
