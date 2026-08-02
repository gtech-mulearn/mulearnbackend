from django.urls import path

from . import career_lab_views

urlpatterns = [
    path("hiring/", career_lab_views.HiringAPI.as_view()),
    path("hiring/csv/", career_lab_views.HiringCSVAPI.as_view()),
    path("hiring/<str:hiring_id>/", career_lab_views.HiringDetailAPI.as_view()),
]
