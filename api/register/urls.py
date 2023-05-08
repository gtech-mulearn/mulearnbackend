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
    TestAPI,
    UserInfo,
)

urlpatterns = [
    path("register/", RegisterData.as_view()),
    # path('register/country/list', CountryAPI.as_view()),
    path("register/role/list/", RoleAPI.as_view()),
    path("register/college/list/", CollegeAPI.as_view()),
    path("register/company/list/", CompanyAPI.as_view()),
    path("register/community/list/", CommunityAPI.as_view()),
    path("register/area-of-interest/list/", AreaOfInterestAPI.as_view()),
    path("forgot-password/", ForgotPasswordAPI.as_view()),
    path("reset-password/verify-token/<str:token>/", ResetPasswordVerifyTokenAPI.as_view()),
    path("reset-password/<str:token>/", ResetPasswordConfirmAPI.as_view()),
    path("lc/user-validation/", LearningCircleUserView.as_view()),
    path('email-verification/', UserEmailVerification.as_view()),
    path('test/', TestAPI.as_view()),
    path('info/', UserInfo.as_view()),
]
