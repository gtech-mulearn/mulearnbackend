from django.urls import path

from . import error_view

urlpatterns = [
    path('<str:log_name>/', error_view.DownloadErrorLogAPI.as_view()),
    path('view/<str:log_name>/', error_view.ViewErrorLogAPI.as_view()),
    path('clear/<str:log_name>/', error_view.ClearErrorLogAPI.as_view()),
]
