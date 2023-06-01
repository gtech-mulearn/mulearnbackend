from django.urls import path
from . import profile_view

urlpatterns = [
    # path('add', portal_views.AddPortal.as_view()),
    path('user-profile/', profile_view.UserProfileAPI.as_view()),
    path('edit-user-profile/', profile_view.EditUserDetailsAPI.as_view()),
    path('user-log/', profile_view.UserLogAPI.as_view()),
    path('user-task-log/', profile_view.UserTaskLogAPI.as_view()),
    path('user-ig/', profile_view.UserInterestGroupAPI.as_view()),
    path('user-suggestion/', profile_view.UserSuggestionAPI.as_view())
]
