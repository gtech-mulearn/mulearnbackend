from django.urls import path

from . import profile_view

urlpatterns = [
    path('user-profile/', profile_view.UserProfileAPI.as_view()),
    path('edit-user-profile/', profile_view.UserProfileAPI.as_view()),
    path('user-log/', profile_view.UserLogAPI.as_view()),
]
