from django.urls import path

from api.protected.organisation import organisation_views

urlpatterns = [
    path('institutes/<str:organisation_type>/', organisation_views.GetInstitutionsAPI.as_view()),
]
