from django.urls import path

from api.protected.organisation import organisation_views

urlpatterns = [
    path('institutes/<str:organisation_type>/<str:district_name>/', organisation_views.GetInstitutionsAPI.as_view()),
    path('get-institutes/<str:organisation_type>/<str:district_name>/',
         organisation_views.RetrieveInstitutesAPI.as_view()),
]
