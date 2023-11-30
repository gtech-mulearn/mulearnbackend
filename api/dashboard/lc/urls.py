from django.urls import path

from . import dash_lc_view

urlpatterns = [
    path('', dash_lc_view.LearningCircleListApi.as_view(), name='main'),
    path('add-member/', dash_lc_view.AddMemberAPI.as_view(), name='add-member'),
    path('list/', dash_lc_view.LearningCircleMainApi.as_view(), name='list'),
    path('data/', dash_lc_view.LearningCircleDataAPI.as_view(), name='data'),
    path('list-all/', dash_lc_view.TotalLearningCircleListApi.as_view(), name='list-all'),
    path('create/', dash_lc_view.LearningCircleCreateApi.as_view(), name='create'),
    path('schedule-meet/<str:circle_id>/', dash_lc_view.ScheduleMeetAPI.as_view(), name='schedule-meet'),
    path('ig-task/<str:ig_id>/', dash_lc_view.IgTaskDetailsAPI.as_view(), name='ig-task'),
    path('list-members/<str:circle_id>/', dash_lc_view.LearningCircleListMembersApi.as_view(), name='list-members'),
    # path('invite/', dash_lc_view.LearningCircleInviteLeadAPI.as_view()),
    path('list-all/<str:circle_code>/', dash_lc_view.TotalLearningCircleListApi.as_view(), name='list-all'),
    path('join/<str:circle_id>/', dash_lc_view.LearningCircleJoinApi.as_view(), name='join'),
    path('<str:circle_id>/<str:member_id>/', dash_lc_view.LearningCircleHomeApi.as_view()),
    path('<str:circle_id>/', dash_lc_view.LearningCircleHomeApi.as_view()),
    # meet record
    path('meet-record/list-all/<str:circle_id>/', dash_lc_view.MeetRecordsGetPostPatchDeleteAPI.as_view(), name='list-all-meet-record'),  # optim
    path('meet-record/show/<str:meet_id>/', dash_lc_view.MeetRecordsGetPostPatchDeleteAPI.as_view(), name='show-all-meet-record'),
    path('meet-record/edit/<str:circle_id>/', dash_lc_view.MeetRecordsGetPostPatchDeleteAPI.as_view(), name='edit-meet-record'),     # optim
    path('meet-record/create/<str:circle_id>/', dash_lc_view.MeetRecordsGetPostPatchDeleteAPI.as_view(), name='create-meet-record'),   # optim

    path('member/invite/<str:circle_id>/<str:muid>/', dash_lc_view.LearningCircleInviteMemberAPI.as_view(), name='invite-member'),
    path('member/invite/status/<str:circle_id>/<str:muid>/<str:status>/', dash_lc_view.LearningCircleInvitationStatus.as_view(), name='invite-member-status'),
    path('lead/<str:circle_id>/<str:lead_id>/', dash_lc_view.LearningCircleLeadTransfer.as_view(), name='lead'),
    ]
