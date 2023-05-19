from django.urls import path
from .yip_views import GetInstitutions


urlpatterns = [
    path('organisation/institutes/<str:organisation_type>/', GetInstitutions.as_view()),
]
