from django.urls import path

from . import campus_views

urlpatterns = [
    path(
        "<str:campus_id>/execom/",
        campus_views.CampusExecomAPI.as_view(),
        name="campus-execom",
    ),
    path(
        "<str:campus_id>/execom/<str:uid>/",
        campus_views.CampusExecomAPI.as_view(),
        name="campus-execom-delete",
    ),
]
