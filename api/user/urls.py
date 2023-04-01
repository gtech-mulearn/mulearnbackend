from django.urls import path
from .user_views import RegisterJWTValidate, RegisterData, CollegeAPI, CompanyAPI, CommunityAPI, RoleAPI, \
    AreaOfInterestAPI, ForgotPasswordAPI, ResetPasswordConfirmAPI,ResetPasswordVerifyTokenAPI

urlpatterns = [
    path('register/jwt/validate', RegisterJWTValidate.as_view()),
    path('register/', RegisterData.as_view()),
    # path('register/country/list', CountryAPI.as_view()),
    path('register/role/list', RoleAPI.as_view()),
    path('register/college/list', CollegeAPI.as_view()),
    path('register/company/list', CompanyAPI.as_view()),
    path('register/comunity/list', CommunityAPI.as_view()),
    path('register/areaofinterst/list', AreaOfInterestAPI.as_view()),
    path('forgot-password', ForgotPasswordAPI.as_view()),
    path('reset-password/<str:token>/', ResetPasswordConfirmAPI.as_view()),
    path('reset-password/verify-token/<str:token>/', ResetPasswordVerifyTokenAPI.as_view())

]
