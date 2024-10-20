from django.urls import path

from . import dash_user_views

urlpatterns = [
    path(
        "verification/",
        dash_user_views.UserVerificationAPI.as_view(),
        name="list-verification",
    ),
    path(
        "verification/csv/",
        dash_user_views.UserVerificationCSV.as_view(),
        name="csv-verification",
    ),
    path(
        "verification/<str:link_id>/",
        dash_user_views.UserVerificationAPI.as_view(),
        name="edit-verification",
    ),
    path(
        "verification/<str:link_id>/",
        dash_user_views.UserVerificationAPI.as_view(),
        name="delete-verification",
    ),
    path(
        "organization/", dash_user_views.UserAddOrgAPI.as_view(), name="user-org-link"
    ),
    path(
        "organization/list/",
        dash_user_views.UserAddOrgAPI.as_view(),
        name="get-user-org-link",
    ),
    path("info/", dash_user_views.UserInfoAPI.as_view()),
    path(
        "forgot-password/",
        dash_user_views.ForgotPasswordAPI.as_view(),
        name="forgot-password",
    ),
    path(
        "reset-password/verify-token/<str:token>/",
        dash_user_views.ResetPasswordVerifyTokenAPI.as_view(),
    ),
    path(
        "reset-password/<str:token>/", dash_user_views.ResetPasswordConfirmAPI.as_view()
    ),
    path("profile/update/", dash_user_views.UserProfilePictureView.as_view()),
    path("csv/", dash_user_views.UserManagementCSV.as_view(), name="csv-user"),
    path("", dash_user_views.UserAPI.as_view(), name="list-user"),
    path(
        "<str:user_id>/",
        dash_user_views.UserGetPatchDeleteAPI.as_view(),
        name="detail-user",
    ),
    path(
        "<str:user_id>/",
        dash_user_views.UserGetPatchDeleteAPI.as_view(),
        name="edit-user",
    ),
    path(
        "<str:user_id>/",
        dash_user_views.UserGetPatchDeleteAPI.as_view(),
        name="delete-user",
    ),
]
