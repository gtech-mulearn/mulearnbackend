from django.urls import path

from . import affiliation_views

urlpatterns = [
    path("", affiliation_views.AffiliationCRUDAPI.as_view()),
    path("<str:affiliation_id>/", affiliation_views.AffiliationCRUDAPI.as_view()),
]