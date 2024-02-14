from django.urls import path

from . import error_view

urlpatterns = [
    path('', error_view.LoggerAPI.as_view()),
    path('graph/', error_view.ErrorGraphAPI.as_view()),
    path('tab/', error_view.ErrorTabAPI.as_view()),
    path('patch/<str:error_id>/', error_view.LoggerAPI.as_view()),
    path('<str:log_name>/', error_view.DownloadErrorLogAPI.as_view()),
    path('view/<str:log_name>/', error_view.ViewErrorLogAPI.as_view()),
    path('clear/<str:log_name>/', error_view.ClearErrorLogAPI.as_view()),
]
