from django.urls import path
from .user_views import RegisterJWTValidate, RegisterData, CollegeAPI, CompanyAPI, CommunityAPI, RoleAPI, AreaOfInterestAPI,ForgotPassword,ForgotPasswordConfirm

urlpatterns = [
    path('register/jwt/validate', RegisterJWTValidate.as_view()),
    path('register/', RegisterData.as_view()),
    # path('register/country/list', CountryAPI.as_view()),
    path('register/role/list', RoleAPI.as_view()),
    path('register/college/list', CollegeAPI.as_view()),
    path('register/company/list', CompanyAPI.as_view()),
    path('register/comunity/list', CommunityAPI.as_view()),
    path('register/areaofinterst/list', AreaOfInterestAPI.as_view()),
    path('register/reset-password',ForgotPassword.as_view()),
    path('register/reset-password-confirm/<int:user_id>/',ForgotPasswordConfirm.as_view()),

]
