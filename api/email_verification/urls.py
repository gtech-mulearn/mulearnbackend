from django.urls import path

from . import views

urlpatterns = [
    path("status/", views.EmailVerificationStatusAPI.as_view()),
    path("verify/request/", views.VerifyEmailRequestAPI.as_view()),
    path("verify/confirm/", views.VerifyEmailConfirmAPI.as_view()),
    path("change/request/", views.ChangeEmailRequestAPI.as_view()),
    path("change/confirm/", views.ChangeEmailConfirmAPI.as_view()),
]
