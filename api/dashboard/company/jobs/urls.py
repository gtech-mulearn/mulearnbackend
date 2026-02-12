from django.urls import path
from .jobs_views import CreateCompanyJobAPIView
urlpatterns = [ path('create/', CreateCompanyJobAPIView.as_view(), name='create-company-job'), ]