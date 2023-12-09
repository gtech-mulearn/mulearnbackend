from django.urls import path

from . import organisation_views

urlpatterns = [
    # path('add', portal_views.AddPortal.as_view()),
    path('institutes/create/', organisation_views.InstitutionPostUpdateDeleteAPI.as_view()),
    path('institutes/edit/<str:org_code>/', organisation_views.InstitutionPostUpdateDeleteAPI.as_view()),
    path('institutes/delete/<str:org_code>/', organisation_views.InstitutionPostUpdateDeleteAPI.as_view()),
    path('institutes/<str:org_type>/csv/', organisation_views.InstitutionCSVAPI.as_view()),
    path('institutes/info/<str:org_code>/', organisation_views.InstitutionDetailsAPI.as_view()),
    path('institutes/prefill/<str:org_code>/', organisation_views.InstitutionPrefillAPI.as_view()),
    path('institutes/<str:org_type>/', organisation_views.InstitutionAPI.as_view()),
    path('institutes/<str:org_type>/<str:district_id>/', organisation_views.InstitutionAPI.as_view()),
    path('institutes/org/affiliation/show/', organisation_views.AffiliationGetPostUpdateDeleteAPI.as_view()),
    path('institutes/org/affiliation/create/', organisation_views.AffiliationGetPostUpdateDeleteAPI.as_view()),
    path('institutes/org/affiliation/edit/<str:affiliation_id>/', organisation_views.AffiliationGetPostUpdateDeleteAPI.as_view()),
    path('institutes/org/affiliation/delete/<str:affiliation_id>/', organisation_views.AffiliationGetPostUpdateDeleteAPI.as_view()),
    path('departments/', organisation_views.DepartmentAPI.as_view()),
    path('departments/create/', organisation_views.DepartmentAPI.as_view()),
    path('departments/edit/<str:department_id>/', organisation_views.DepartmentAPI.as_view()),
    path('departments/delete/<str:department_id>/', organisation_views.DepartmentAPI.as_view()),
    path('affiliation/list/', organisation_views.AffiliationListAPI.as_view()),
    path('merge_organizations/<str:organisation_id>/', organisation_views.OrganizationMergerView.as_view()),
    path('karma-type/create/', organisation_views.OrganizationKarmaTypeGetPostPatchDeleteAPI.as_view()),
    path('karma-log/create/', organisation_views.OrganizationKarmaLogGetPostPatchDeleteAPI.as_view()),
    path('base-template/', organisation_views.OrganisationBaseTemplateAPI.as_view()),
    path('import/', organisation_views.OrganisationImportAPI.as_view()),
]
