from django.urls import path
from .dash_user_views import UserAPI


urlpatterns = [
    path('', UserAPI.as_view(), name='list-user'),
    path('<str:user_id>/', UserAPI.as_view(), name="edit-user"),
    path('<str:user_id>/', UserAPI.as_view(), name="delete-user")
]
