from django.urls import path
from .user_views import RegisterJWTValidte, RegisterData, CollegeAPI, CompanyAPI, ComunityAPI, RoleAPI, AreaOfInterstAPI

urlpatterns = [
    path('register/jwt/validate', RegisterJWTValidte.as_view()),
    path('register/', RegisterData.as_view()),
    # path('register/country/list', CountryAPI.as_view()),
    path('register/role/list', RoleAPI.as_view()),
    path('register/college/list', CollegeAPI.as_view()),
    path('register/company/list', CompanyAPI.as_view()),
    path('register/comunity/list', ComunityAPI.as_view()),
    path('register/areaofinterst/list', AreaOfInterstAPI.as_view())
]
