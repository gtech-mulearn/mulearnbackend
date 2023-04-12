from django.urls import path
from . import portal_views

urlpatterns = [
    # path('add', portal_views.AddPortal.as_view()),
    path('mu-id/validate/', portal_views.MuidValidateAPI.as_view()),
    path('user/authorize/', portal_views.UserMailTokenValidationAPI.as_view()),
    path('profile/karma/', portal_views.GetKarmaAPI.as_view()),
    path('profile/user/<str:muid>/', portal_views.UserDetailsApi.as_view()),
    path('get-unverified-users/', portal_views.GetUnverifiedUsers.as_view()),
]
