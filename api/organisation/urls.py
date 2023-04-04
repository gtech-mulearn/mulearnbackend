from django.urls import path
from . import organisation_views

urlpatterns = [
    # path('add', portal_views.AddPortal.as_view()),
    path('institutes/<str:organisation_type>/', organisation_views.GetInstitutions.as_view()),
]
