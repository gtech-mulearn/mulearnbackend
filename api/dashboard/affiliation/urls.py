from django.urls import path

from . import affiliation_views

urlpatterns = [
    path('',affiliation_views.AffiliationView.as_view()),
    path('create/',affiliation_views.AffiliationView.as_view()),
    path('edit/<str:affiliation_id>/',affiliation_views.AffiliationView.as_view()),
    path('delete/<str:affiliation_id>/',affiliation_views.AffiliationView.as_view())
]
