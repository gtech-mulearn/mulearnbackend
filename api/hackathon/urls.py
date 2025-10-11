from django.urls import path

from . import hackathon_views

urlpatterns = [
    path('list-hackathons/', hackathon_views.HackathonManagementAPI.as_view()),
    path('list-hackathons/upcoming/', hackathon_views.HackathonManagementAPI.as_view()),
    path('list-hackathons/<str:hackathon_id>/', hackathon_views.HackathonManagementAPI.as_view()),
    path('info/<str:hackathon_id>/', hackathon_views.HackathonInfoAPI.as_view()),

    path('create-hackathon/', hackathon_views.HackathonManagementAPI.as_view()),
    path('edit-hackathon/<str:hackathon_id>/', hackathon_views.HackathonManagementAPI.as_view()),
    path('delete-hackathon/<str:hackathon_id>/', hackathon_views.HackathonManagementAPI.as_view()),
    path('publish-hackathon/<str:hackathon_id>/', hackathon_views.HackathonPublishingAPI.as_view()),

    path('submit-hackathon/', hackathon_views.HackathonSubmissionAPI.as_view()),

    path("list-organiser-hackathons/<str:hackathon_id>/", hackathon_views.HackathonOrganiserAPI.as_view()),
    path('add-organiser/<str:hackathon_id>/', hackathon_views.HackathonOrganiserAPI.as_view()),
    path('delete-organiser/<str:organiser_link_id>/', hackathon_views.HackathonOrganiserAPI.as_view()),
    path('list-applicants/', hackathon_views.ListApplicantsAPI.as_view()),
    path('list-applicants/<str:hackathon_id>/', hackathon_views.ListApplicantsAPI.as_view()),
    path('list-form/<str:hackathon_id>/', hackathon_views.ListHackathonFormAPI.as_view()),

    path('list-organisations/', hackathon_views.ListOrganisations.as_view()),
    path('list-districts/', hackathon_views.ListDistricts.as_view()),

    path('list-default-form-fields/', hackathon_views.GetDefaultFieldsAPI.as_view()),

]
