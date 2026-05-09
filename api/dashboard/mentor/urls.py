from django.urls import path, include

urlpatterns = [
    path("persona/", include("api.dashboard.mentor.persona.urls")),
    path("profile/", include("api.dashboard.mentor.profile.urls")),
    path("overview/", include("api.dashboard.mentor.overview.urls")),
    path("availability/", include("api.dashboard.mentor.availability.urls")),
]
