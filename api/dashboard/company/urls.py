from django.urls import path,include

from .analytics_views import CompanyDashboardSummaryAPIView, CompanyTalentPoolAnalyticsAPIView

urlpatterns = [
    path("home-summary/", CompanyDashboardSummaryAPIView.as_view(), name="company-home-summary"),
    path("talent-pool/analytics/", CompanyTalentPoolAnalyticsAPIView.as_view(), name="company-talent-pool-analytics"),
    path("", include("api.dashboard.company.onboarding.urls")),
    path("profile/", include("api.dashboard.company.profile.urls")),
    path("jobs/", include("api.dashboard.company.jobs.urls")),
    path("learners/", include("api.dashboard.company.learners.urls")),
    path("applications/", include("api.dashboard.company.applications.urls")),
    path("tasks/", include("api.dashboard.company.tasks.urls")),
    path("members/", include("api.dashboard.company.members.urls")),
]
