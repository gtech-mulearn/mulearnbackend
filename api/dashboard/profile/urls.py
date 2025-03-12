from django.urls import path

from . import profile_view

urlpatterns = [
    path('', profile_view.UserProfileEditView.as_view()),
    path('badges/<str:muid>', profile_view.BadgesAPI.as_view()),
    path('user-profile/', profile_view.UserProfileAPI.as_view()),
    path('ig-edit/', profile_view.UserIgEditView.as_view()),
    path('user-profile/<str:muid>/', profile_view.UserProfileAPI.as_view()),
    # path('edit-user-profile/', profile_view.UserProfileAPI.as_view()),
    path('user-log/', profile_view.UserLogAPI.as_view()),
    path('user-log/<str:muid>/', profile_view.UserLogAPI.as_view()),
    path('share-user-profile/', profile_view.ShareUserProfileAPI.as_view()),
    path('share-user-profile/<str:uuid>/', profile_view.ShareUserProfileAPI.as_view()),
    path('rank/<str:muid>/', profile_view.UserRankAPI.as_view()),
    path('get-user-levels/', profile_view.UserLevelsAPI.as_view()),
    path('get-user-levels/<str:muid>/', profile_view.UserLevelsAPI.as_view()),
    path('socials/edit/', profile_view.SocialsAPI.as_view()),
    path('socials/', profile_view.GetSocialsAPI.as_view()),
    path('socials/<str:muid>/', profile_view.GetSocialsAPI.as_view()),
    path('qrcode-get/<str:uuid>/', profile_view.QrcodeRetrieveAPI.as_view()),
    path('change-password/', profile_view.ResetPasswordAPI.as_view()),
    path('userterm-approved/<str:muid>/',profile_view.UsertermAPI.as_view())
]
