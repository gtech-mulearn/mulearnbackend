from django.urls import path

from . import dash_lc_view

urlpatterns = [
    path('', dash_lc_view.LearningCircleListApi.as_view()),
    path('list/', dash_lc_view.LearningCircleMainApi.as_view()),
    path('data/', dash_lc_view.LearningCircleDataAPI.as_view()),
    path('list-all/', dash_lc_view.TotalLearningCircleListApi.as_view()),
    path('create/', dash_lc_view.LearningCircleCreateApi.as_view()),
    path('list-members/<str:circle_id>/', dash_lc_view.LearningCircleListMembersApi.as_view()),
    # path('invite/', dash_lc_view.LearningCircleInviteLeadAPI.as_view()),
    path('list-all/<str:circle_code>/', dash_lc_view.TotalLearningCircleListApi.as_view()),
    path('join/<str:circle_id>/', dash_lc_view.LearningCircleJoinApi.as_view()),
    path('<str:circle_id>/<str:member_id>/', dash_lc_view.LearningCircleHomeApi.as_view()),
    path('<str:circle_id>/', dash_lc_view.LearningCircleHomeApi.as_view()),
    path('meeting-log/<str:meet_id>/', dash_lc_view.MeetGetPostPatchDeleteAPI.as_view()),
    path('meet/edit/<str:circle_id>/', dash_lc_view.MeetGetPostPatchDeleteAPI.as_view()),     # optim
    path('meet/create/<str:circle_id>/', dash_lc_view.MeetGetPostPatchDeleteAPI.as_view()),   # optim
    path('member/invite/<str:circle_id>/<str:muid>/', dash_lc_view.LearningCircleInviteMemberAPI.as_view()),
    path('member/invite/status/<str:circle_id>/<str:muid>/<str:status>/', dash_lc_view.LearningCircleInvitationStatus.as_view()),
    path('lead/<str:circle_id>/<str:lead_id>/', dash_lc_view.LearningCircleLeadTransfer.as_view()),
    ]
