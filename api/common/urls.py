from django.urls import path

from . import common_views

urlpatterns=[
     path('<str:log_type>/',common_views.CommonAPI.as_view(), name='common-log-download'),
]

