from django.urls import path

from . import affiliation_views

urlpatterns = [
    path("", affiliation_views.AffiliationCRUDAPI.as_view()),
    path("create/", affiliation_views.AffiliationCRUDAPI.as_view()),
    path("edit/<str:affliation_id>/", affiliation_views.AffiliationCRUDAPI.as_view()),
    path("delete/<str:affliation_id>/", affiliation_views.AffiliationCRUDAPI.as_view()),
    
]