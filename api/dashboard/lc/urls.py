from django.urls import path

from . import dash_lc_view

urlpatterns = [
    path('user-list/', dash_lc_view.UserLearningCircleListApi.as_view(), name='main'),  # list all lc's of user
    path('<str:circle_id>/details/', dash_lc_view.LearningCircleDetailsApi.as_view(), name='lc-detailed'),  # individual ls details
    path('<str:circle_id>/schedule-meet/', dash_lc_view.ScheduleMeetAPI.as_view(), name='schedule-meet'),
    path('<str:circle_id>/report/create/', dash_lc_view.SingleReportDetailAPI.as_view(), name='create-report'),
    path('<str:circle_id>/report/<str:report_id>/show/', dash_lc_view.SingleReportDetailAPI.as_view(), name='show-report'),
    path('<str:circle_id>/add-member/', dash_lc_view.AddMemberAPI.as_view(), name='add-member'),
    path('create/', dash_lc_view.LearningCircleCreateApi.as_view(), name='create'),
    path('join/<str:circle_id>/', dash_lc_view.LearningCircleJoinApi.as_view(), name='join'),
    path('<str:circle_id>/ig-progress/', dash_lc_view.IgTaskDetailsAPI.as_view(), name='ig-progress'), # ig progress api
    path('<str:circle_id>/lead-transfer/<str:new_lead_id>/', dash_lc_view.LearningCircleLeadTransfer.as_view(), name='lead-transfer'),

    # rework user accept, reject api

    # TODO: new api for note updation
    # path('<str:circle_id>/note/edit/', dash_lc_view.LearningCircleLeadTransfer.as_view(), name='edit-note'),

    path('<str:circle_id>/<str:member_id>/', dash_lc_view.LearningCircleDetailsApi.as_view()),  # user accept or reject, also for removal
    path('list/', dash_lc_view.LearningCircleMainApi.as_view(), name='list'), # public page listing
    path('list-all/', dash_lc_view.TotalLearningCircleListApi.as_view(), name='list-all'), # dashboard search listing
    path('list-all/<str:circle_code>/', dash_lc_view.TotalLearningCircleListApi.as_view(), name='list-all-search'), # dashboard search listing

    # path('data/', dash_lc_view.LearningCircleDataAPI.as_view(), name='data'),
    # path('list-members/<str:circle_id>/', dash_lc_view.LearningCircleListMembersApi.as_view(), name='list-members'),
    # path('invite/', dash_lc_view.LearningCircleInviteLeadAPI.as_view()),
    # path('meet-record/list-all/<str:circle_id>/', dash_lc_view.SingleReportDetailAPI.as_view(), name='list-all-meet-record'),  # optim
    # path('meet-record/edit/<str:circle_id>/', dash_lc_view.SingleReportDetailAPI.as_view(), name='edit-meet-record'),       # optim
    # path('member/invite/<str:circle_id>/<str:muid>/', dash_lc_view.LearningCircleInviteMemberAPI.as_view(), name='invite-member'),
    # path('member/invite/status/<str:circle_id>/<str:muid>/<str:status>/', dash_lc_view.LearningCircleInvitationStatus.as_view(), name='invite-member-status'),
    ]
