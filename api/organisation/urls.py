from django.urls import path
from . import organisation_views, org_api1

urlpatterns = [
    # path('add', portal_views.AddPortal.as_view()),
    path('institutes/org_info/', org_api1.InstitutionsMain.as_view()),
    path('institutes/all_inst/', organisation_views.Institutions.as_view()),
    path('institutes/<str:organisation_type>/', organisation_views.GetInstitutions.as_view()),
    path('institutes/add', organisation_views.PostInstitution.as_view()),
]
