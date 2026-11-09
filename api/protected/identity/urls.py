from django.urls import path

from . import views

urlpatterns = [
    path("provision-member/", views.ProvisionMemberAPI.as_view()),
    path("signup-code/", views.SignupCodeAPI.as_view()),
    path("signup-code/verify/", views.SignupCodeVerifyAPI.as_view()),
]
