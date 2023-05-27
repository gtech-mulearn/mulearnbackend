from django.urls import path
from . import dash_user_views


urlpatterns = [
    
    path('verification/', dash_user_views.UserVerificationAPI.as_view(), name='list-verification'),
    path('verification/<str:link_id>/', dash_user_views.UserVerificationAPI.as_view(), name='edit-verification'),
    path('verification/<str:link_id>/', dash_user_views.UserVerificationAPI.as_view(), name='delete-verification'),
    
    path('info/', dash_user_views.UserInfoAPI.as_view()),
    path("forgot-password/", dash_user_views.ForgotPasswordAPI.as_view(), name="forgot-password"),
    path("reset-password/verify-token/<str:token>/", dash_user_views.ResetPasswordVerifyTokenAPI.as_view()),
    path("reset-password/<str:token>/", dash_user_views.ResetPasswordConfirmAPI.as_view()),
    path('', dash_user_views.UserAPI.as_view(), name='list-user'),
    path('csv/', dash_user_views.UserManagementCSV.as_view(), name="csv-user"),
    path('<str:user_id>/', dash_user_views.UserAPI.as_view(), name="edit-user"),
    path('<str:user_id>/', dash_user_views.UserAPI.as_view(), name="delete-user"),
    
]
