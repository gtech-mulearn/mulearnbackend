from django.urls import path

from . import kkem_views

# app_name will help us do a reverse look-up latter.
urlpatterns = [ 
    path('login/', kkem_views.KKEMIntegrationLogin.as_view(), name="login-auth"),
    path('authorization/', kkem_views.KKEMAuthorizationAPI.as_view(), name="create-auth"),
    path('user/<str:jsid>/', kkem_views.KKEMdetailsFetchAPI.as_view(), name="get-details"),
    path('authorization/<str:token>/', kkem_views.KKEMAuthorizationAPI.as_view(), name="verify-auth"),
    path('users/', kkem_views.KKEMBulkKarmaAPI.as_view(), name="list-user"),
    path('users/<str:mu_id>/', kkem_views.KKEMIndividualKarmaAPI.as_view(), name="get-user"),
]
