from django.urls import path

from . import organisation_views

urlpatterns = [
    # path('add', portal_views.AddPortal.as_view()),
    path('institutes/csv/<str:org_type>/', organisation_views.InstitutionCSV.as_view()),
    path('institutes/add/', organisation_views.InstitutionPostUpdateDeleteAPI.as_view()),
    path('institutes/<str:org_code>/', organisation_views.InstitutionPostUpdateDeleteAPI.as_view()),
    path('institutes/info/all/<str:org_type>/', organisation_views.GetAllInstitutionAPI.as_view()),
    path('institutes/info/<str:org_code>/', organisation_views.GetInstitutionDetailsAPI.as_view()),
    path('institutes/show/<str:organisation_type>/', organisation_views.GetInstitutionsAPI.as_view()),
    path('institutes/show/<str:organisation_type>/<str:district_id>/', organisation_views.GetInstitutionsAPI.as_view()),
    path('institutes/org/affiliation/', organisation_views.AffiliationAPI.as_view()),
    path('institutes/names/<str:organisation_type>/', organisation_views.GetInstitutionsNamesAPI.as_view()),

    path('departments/', organisation_views.DepartmentAPI.as_view(), name="Create Department"),
    path('departments/<str:dept_id>/', organisation_views.DepartmentAPI.as_view(), name="Get Department by ID"),
    path('departments/edit/<str:department_id>/', organisation_views.DepartmentAPI.as_view(), name="Edit Departments"),
    path('departments/delete/<str:department_id>/', organisation_views.DepartmentAPI.as_view(), name="Delete Department"),
]
