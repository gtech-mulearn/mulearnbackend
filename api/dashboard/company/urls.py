from django.urls import path
from . import company_views, job_views, mulearner_views, analytics_views, task_views

urlpatterns = [
    path("register/",                 company_views.CompanyRegistrationAPI.as_view()),
    path("summary/",                  company_views.CompanyAdminSummaryAPI.as_view()),
    path("status/",                   company_views.CompanyStatusAPI.as_view()),
    path("profile/",                  company_views.CompanyProfileAPI.as_view()),
    path("profile/public/<str:slug>/",company_views.PublicCompanyProfileAPI.as_view()),
    path("profile/public/<str:slug>/jobs/", job_views.PublicCompanyJobListAPI.as_view()),
    path("list/",                     company_views.CompanyListAPI.as_view()),
    path("jobs/",                     job_views.CompanyJobAPI.as_view()),
    path("jobs/all/",                 job_views.PublicJobAPI.as_view()),
    path("jobs/<str:job_id>/",        job_views.CompanyJobDetailAPI.as_view()),
    path("jobs/<str:job_id>/apply/",  job_views.JobApplicationAPI.as_view()),
    path("jobs/<str:job_id>/applications/", job_views.JobApplicationAPI.as_view()),
    path("applications/me/",          job_views.UserAppliedJobsAPI.as_view()),
    path("applications/<str:app_id>/status/", job_views.ApplicationStatusAPI.as_view()),
    path("applications/<str:app_id>/withdraw/", job_views.UserApplicationWithdrawAPI.as_view()),
    path("applications/<str:app_id>/resubmit/", job_views.UserApplicationResubmitAPI.as_view()),
    path("mulearners/",               mulearner_views.CompanyMulearnerDirectoryAPI.as_view()),
    path("analytics/gigs/",           analytics_views.CompanyGigAnalyticsAPI.as_view()),
    
    # Task Management for Company
    path("tasks/",                    task_views.CompanyTaskListCreateAPI.as_view(), name='company-task-list-create'),
    path("tasks/<str:task_id>/",      task_views.CompanyTaskDetailAPI.as_view(), name='company-task-detail'),
    
    path("<str:company_id>/",         company_views.CompanyDetailAPI.as_view()),
    path("verify/<str:company_id>/",  company_views.CompanyVerifyAPI.as_view()),
]
