from django.urls import path,include
urlpatterns = [
    path("", include("api.dashboard.company.onboarding.urls")),
    path("profile/", include("api.dashboard.company.profile.urls")),
    path("jobs/", include("api.dashboard.company.jobs.urls")),
    path("learners/", include("api.dashboard.company.learners.urls")),
    path("applications/", include("api.dashboard.company.applications.urls")),
]

