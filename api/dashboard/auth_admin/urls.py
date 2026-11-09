from django.urls import path

from . import auth_admin_views as views

urlpatterns = [
    path("login-attempts/", views.LoginAttemptsAPI.as_view()),
    path("security-posture/", views.SecurityPostureAPI.as_view()),
    path("signin-policy/", views.SigninPolicyAPI.as_view()),
    path("clients/", views.ClientListAPI.as_view()),
    path("clients/<str:client_id>/", views.ClientDetailAPI.as_view()),
    path("clients/<str:client_id>/disable/", views.ClientDisableAPI.as_view()),
    path("clients/<str:client_id>/enable/", views.ClientEnableAPI.as_view()),
    path("sessions/revoke/", views.SessionRevokeAPI.as_view()),
]
