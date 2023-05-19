from django.urls import path

from api.protected.organisation.organisation_views import GetInstitutions

urlpatterns = [
    path('institutes/<str:organisation_type>/', GetInstitutions.as_view()),
]
