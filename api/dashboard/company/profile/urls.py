from django.urls import path

from .profile_views import (
    CompanyProfileAPIView,
    PublicCompanyJobsAPIView,
    PublicCompanyProfileAPIView,
)

urlpatterns = [
    path("", CompanyProfileAPIView.as_view(), name="company-profile"),
    path(
        "public/<slug:slug>/",
        PublicCompanyProfileAPIView.as_view(),
        name="public-company-profile",
    ),
    path(
        "public/<slug:slug>/jobs/",
        PublicCompanyJobsAPIView.as_view(),
        name="public-company-jobs",
    ),
]

