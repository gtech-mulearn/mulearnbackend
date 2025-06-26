
from django.urls import path
from .qseverse_views import (
    IssueVerifiableCredentialView,
    GetAllConnectedUsersView,
    GetConnectedUserView,
    GetQSCredentialsView
)

urlpatterns = [
    path("issue-vc/", IssueVerifiableCredentialView.as_view()),
    path("connected-users/", GetAllConnectedUsersView.as_view()),
    path("connected-users/search", GetConnectedUserView.as_view()),
    path("qs-credentials/", GetQSCredentialsView.as_view()),
]
