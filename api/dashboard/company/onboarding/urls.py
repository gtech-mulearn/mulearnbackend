from django.urls import path

from .onboarding_views import (
    CompanyOnboardingStatusAPIView,
    CompanySignupAPIView,
    CompanyVerificationRequestActionAPIView,
    CompanyVerificationRequestListAPIView,
    CompanyVerificationResubmitAPIView,
)

urlpatterns = [
    path("create/", CompanySignupAPIView.as_view(), name="company-signup-create"),
    path(
        "onboarding/status/",
        CompanyOnboardingStatusAPIView.as_view(),
        name="company-onboarding-status",
    ),
    path(
        "verification/requests/",
        CompanyVerificationRequestListAPIView.as_view(),
        name="company-verification-requests",
    ),
    path(
        "verification/requests/<str:company_id>/",
        CompanyVerificationRequestActionAPIView.as_view(),
        name="company-verification-request-action",
    ),
    path(
        "verification/resubmit/",
        CompanyVerificationResubmitAPIView.as_view(),
        name="company-verification-resubmit",
    ),
]

