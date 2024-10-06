from django.urls import path

from . import register_views

urlpatterns = [
    path("", register_views.RegisterDataAPI.as_view()),
    path("validate/", register_views.UserRegisterValidateAPI.as_view()),
    path("role/list/", register_views.RoleAPI.as_view()),
    path("colleges/", register_views.CollegesAPI.as_view()),
    path("department/list/", register_views.DepartmentAPI.as_view()),
    path("location/", register_views.LocationSearchView.as_view()),
    path("country/list/", register_views.CountryAPI.as_view()),
    path("state/list/", register_views.StateAPI.as_view()),
    path("district/list/", register_views.DistrictAPI.as_view()),
    path("college/list/", register_views.CollegeAPI.as_view()),
    path("company/list/", register_views.CompanyAPI.as_view()),
    path("community/list/", register_views.CommunityAPI.as_view()),
    path("schools/list/", register_views.SchoolAPI.as_view()),
    path("area-of-interest/list/", register_views.AreaOfInterestAPI.as_view()),
    path("lc/user-validation/", register_views.LearningCircleUserViewAPI.as_view()),
    path("email-verification/", register_views.UserEmailVerificationAPI.as_view()),
    path("user-country/", register_views.UserCountryAPI.as_view()),
    path("user-state/", register_views.UserStateAPI.as_view()),
    path("user-zone/", register_views.UserZoneAPI.as_view()),
    path("interests /", register_views.UserInterestAPI.as_view()),
    # path("connect-discord/", register_views.ConnectDiscordAPI.as_view()),
]
