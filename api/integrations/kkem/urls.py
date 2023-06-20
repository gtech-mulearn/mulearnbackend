from django.urls import path

from . import kkem_views

# app_name will help us do a reverse look-up latter.
urlpatterns = [ 
    path('authorization/', kkem_views.KKEMAuthorizationAPI.as_view(), name="create-auth"),
]
