from django.urls import path
from .jobs_views import CreateCompanyJobAPI

urlpatterns = [
    path('create/', CreateCompanyJobAPI.as_view(), name='create-company-job'),
]