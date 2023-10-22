from django.urls import path

from . import affiliation_views

urlpatterns = [
    path('',affiliation_views.AffiliationGetView.as_view()),
    path('create/',affiliation_views.AffiliationAddView.as_view()),
    path('edit/<str:affiliation_id>/',affiliation_views.AffiliationEditView.as_view()),
    path('delete/<str:affiliation_id>/',affiliation_views.AffiliationDeleteView.as_view())
]
