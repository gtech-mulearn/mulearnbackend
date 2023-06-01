from django.urls import path
from . import organisation_views

urlpatterns = [
    # path('add', portal_views.AddPortal.as_view()),
    path('institutes/add', organisation_views.PostInstitutionAPI.as_view()),
    path('institutes/<str:org_code>', organisation_views.PostInstitutionAPI.as_view()),
    path('institutes/info/all_inst', organisation_views.InstitutionsAPI.as_view()),
    path('institutes/info/<str:org_code>', organisation_views.InstitutionsAPI.as_view()),
    path('institutes/show/<str:organisation_type>', organisation_views.GetInstitutionsAPI.as_view()),
    path('institutes/org/affiliation', organisation_views.AffiliationAPI.as_view()),
]
