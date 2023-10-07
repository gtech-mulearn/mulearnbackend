from django.urls import path

from . import kkem_views

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('login/', kkem_views.KKEMIntegrationLogin.as_view(), name="login-auth"),
    path('authorization/', kkem_views.KKEMAuthorizationAPI.as_view(), name="create-auth"),
    path('authorization/<str:token>/', kkem_views.KKEMAuthorizationAPI.as_view(), name="verify-auth"),
    
    path('user/status/<str:encrypted_data>/', kkem_views.KKEMUserStatusAPI.as_view(), name="get-user-status"),
    path('user/<str:encrypted_data>/', kkem_views.KKEMdetailsFetchAPI.as_view(), name="get-details"),
    
    path('users/', kkem_views.KKEMBulkKarmaAPI.as_view(), name="list-user"),
    path('users/<str:muid>/', kkem_views.KKEMIndividualKarmaAPI.as_view(), name="get-user"),
]
