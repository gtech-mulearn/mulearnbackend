from django.urls import path,include
urlpatterns = [
        path("jobs/", include("api.dashboard.company.jobs.urls")),
        path("profile/", include("api.dashboard.company.profile.urls")),
        path("jobs/", include("api.dashboard.company.jobs.urls")),
]

