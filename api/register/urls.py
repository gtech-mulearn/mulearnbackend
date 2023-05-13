from django.urls import path

from .register_views import (
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

urlpatterns = [
    path("", RegisterData.as_view()),
    # path('register/country/list', CountryAPI.as_view()),
    path("role/list/", RoleAPI.as_view()),
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
]
