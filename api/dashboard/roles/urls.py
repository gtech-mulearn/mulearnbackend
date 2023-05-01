from django.urls import path
from . import dash_roles_views

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('', dash_roles_views.RolesAPI.as_view(),name="roles-api"),
]
