from django.urls import path

from . import hackathon_views

urlpatterns = [
    path('list-hackathons/', hackathon_views.HackathonManagementAPI.as_view()),
    path('create-hackathon/', hackathon_views.HackathonManagementAPI.as_view()),
    path('edit-hackathon/<str:hackathon_id>/', hackathon_views.HackathonManagementAPI.as_view()),
    path('delete-hackathon/<str:hackathon_id>/', hackathon_views.HackathonManagementAPI.as_view()),

    path('list-default-form-fields/', hackathon_views.GetDefaultFieldsAPI.as_view()),

]
