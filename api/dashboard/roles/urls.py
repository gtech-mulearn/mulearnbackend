from django.urls import path
from . import roles_views

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('', roles_views.RolesAPI.as_view(),name="roles-api"),
]
