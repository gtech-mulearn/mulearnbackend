from django.urls import path, include

from . import company_views

urlpatterns = [
    path("profile/", company_views.CompanyProfileView.as_view()),
    path("jobs/", include("api.dashboard.company.jobs.urls")),
    path("<str:slug>/approve/", company_views.CompanyApproveView.as_view()),
    path("<str:slug>/", company_views.CompanySlugView.as_view()),
]
