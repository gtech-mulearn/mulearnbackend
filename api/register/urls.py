from django.urls import path

from .register_views import (
    CountryAPI,
    StateAPI,
    DistrictAPI,
    LearningCircleUserView,
    RegisterData,
    CollegeAPI,
    CompanyAPI,
    CommunityAPI,
    RoleAPI,
    AreaOfInterestAPI,
    ForgotPasswordAPI,
    ResetPasswordConfirmAPI,
    ResetPasswordVerifyTokenAPI,
    UserEmailVerification,
    UserInfo,
)

from . import register_views

urlpatterns = [
    path("", RegisterData.as_view()),
    path("role/list/", RoleAPI.as_view()),
    path("country/list/", CountryAPI.as_view()),
    path("state/list/", StateAPI.as_view()),
    path("district/list/", DistrictAPI.as_view()),
    path("college/list/", CollegeAPI.as_view()),
    path("company/list/", CompanyAPI.as_view()),
    path("community/list/", CommunityAPI.as_view()),
    path("area-of-interest/list/", AreaOfInterestAPI.as_view()),
    path("forgot-password/", ForgotPasswordAPI.as_view()),
    path("reset-password/verify-token/<str:token>/", ResetPasswordVerifyTokenAPI.as_view()),
    path("reset-password/<str:token>/", ResetPasswordConfirmAPI.as_view()),
    path("lc/user-validation/", LearningCircleUserView.as_view()),
    path('email-verification/', UserEmailVerification.as_view()),
    path('info/', UserInfo.as_view()),
    path('user-country/', register_views.UserCountryAPI.as_view()),
    path('user-state/', register_views.UserStateAPI.as_view()),
    path('user-zone/', register_views.UserZoneAPI.as_view()),
    path('user-district/', register_views.UserDistrictAPI.as_view()),
    path('user-organization/', register_views.UserOrganizationAPI.as_view()),
]
