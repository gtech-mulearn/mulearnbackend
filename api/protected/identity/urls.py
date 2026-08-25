from django.urls import path

from . import views

urlpatterns = [
    path("provision-member/", views.ProvisionMemberAPI.as_view()),
]
