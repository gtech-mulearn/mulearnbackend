from django.urls import path
from .dash_user_views import UserAPI, UserManagementCSV, UserVerificationAPI


urlpatterns = [
    
    path('verification/', UserVerificationAPI.as_view(), name='list-verification'),
    path('verification/<str:link_id>/', UserVerificationAPI.as_view(), name='edit-verification'),
    path('verification/<str:link_id>/', UserVerificationAPI.as_view(), name='delete-verification'),
    
    path('', UserAPI.as_view(), name='list-user'),
    path('csv/', UserManagementCSV.as_view(), name="csv-user"),
    path('<str:user_id>/', UserAPI.as_view(), name="edit-user"),
    path('<str:user_id>/', UserAPI.as_view(), name="delete-user"),
    
]
