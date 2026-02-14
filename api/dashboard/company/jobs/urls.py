from django.urls import path
from .jobs_views import CreateCompanyJobAPIView, UpdateCompanyJobAPIView, ListCompanyJobsAPIView, CreateJobRuleAPIView

urlpatterns = [
    path('', ListCompanyJobsAPIView.as_view(), name='list-company-jobs'),
    path('create/', CreateCompanyJobAPIView.as_view(), name='create-company-job'),
    path('<str:job_id>/', UpdateCompanyJobAPIView.as_view(), name='update-company-job'),
    path('<str:job_id>/rules/create/', CreateJobRuleAPIView.as_view(), name='create-company-job-rule'),

]