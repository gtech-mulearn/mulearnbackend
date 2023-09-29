from django.urls import path

from . import common_views

urlpatterns=[
     path('<str:log_type>/',common_views.CommonAPI.as_view()),
     path('view/<str:log_type>/',common_views.ViewCommonAPI.as_view()),
     path('clear/<str:log_type>/',common_views.ClearCommonAPI.as_view()),
]

