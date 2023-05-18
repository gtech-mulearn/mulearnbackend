from django.urls import path
from . import organisation_views

urlpatterns = [
    # path('add', portal_views.AddPortal.as_view()),
    path('institutes/add', organisation_views.PostInstitution.as_view()),
    # /safe is added so that if /update/<str:code> is sent with DELETE request type, it will delete the request
    path('institutes/update/safe/<str:org_code>', organisation_views.PostInstitution.as_view()),
    path('institutes/delete/<str:org_code>', organisation_views.PostInstitution.as_view()),
    path('institutes/all_inst', organisation_views.Institutions.as_view()),
    path('institutes/<str:org_code>', organisation_views.Institutions.as_view()),
    path('institutes/show/<str:organisation_type>', organisation_views.GetInstitutions.as_view()),
]
