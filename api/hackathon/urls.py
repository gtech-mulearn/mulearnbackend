from django.urls import path

from . import hackathon_views

urlpatterns = [
    path('list-hackathons/', hackathon_views.HackathonManagementAPI.as_view()),
]
