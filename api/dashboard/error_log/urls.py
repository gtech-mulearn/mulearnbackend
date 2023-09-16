from django.urls import path

from . import error_view

urlpatterns = [
    path('', error_view.ErrorLogAPI.as_view()),
]
