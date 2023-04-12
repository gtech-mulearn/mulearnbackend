from django.urls import path
from . import d_user_views

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('', d_user_views.HelloWorld.as_view()),
]
