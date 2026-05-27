from django.urls import path
from .jobs_views import (
    CreateCompanyJobAPIView,
    UpdateCompanyJobAPIView,
    ListCompanyJobsAPIView,
    CreateJobRuleAPIView,
    UpdateJobRuleAPIView,
    DeleteJobRuleAPIView,
    GetCompanyJobDetailsAPIView,
)
from .application_views import (
    ApplyToJobAPIView,
    CompanyJobApplicationsListAPIView,
    CompanyUpdateApplicationStatusAPIView,
)

urlpatterns = [
    path('', ListCompanyJobsAPIView.as_view(), name='list-company-jobs'),
    path('create/', CreateCompanyJobAPIView.as_view(), name='create-company-job'),
    path('<str:job_id>/details/', GetCompanyJobDetailsAPIView.as_view(), name='get-company-job-details'),
    path('<str:job_id>/', UpdateCompanyJobAPIView.as_view(), name='update-company-job'),
    path('<str:job_id>/rules/create/', CreateJobRuleAPIView.as_view(), name='create-company-job-rule'),
    path('<str:job_id>/rules/<str:rule_id>/', UpdateJobRuleAPIView.as_view(), name='update-job-rule'),
    path('<str:job_id>/rules/<str:rule_id>/delete/', DeleteJobRuleAPIView.as_view(), name='delete-job-rule'),
    # Application endpoints
    path('<str:job_id>/apply/', ApplyToJobAPIView.as_view(), name='apply-to-job'),
    path('<str:job_id>/applications/', CompanyJobApplicationsListAPIView.as_view(), name='company-job-applications'),
    path('<str:job_id>/applications/<str:app_id>/', CompanyUpdateApplicationStatusAPIView.as_view(), name='update-application-status'),
]