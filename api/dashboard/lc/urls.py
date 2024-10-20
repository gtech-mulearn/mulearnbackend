from django.urls import path

from . import dash_lc_view

urlpatterns = [
    path("meets/list/", dash_lc_view.CircleMeetListAPI.as_view(), name="meets-list"),
    path(
        "meets/list/<str:is_user>/",
        dash_lc_view.CircleMeetListAPI.as_view(),
        name="meets-list-user",
    ),
    path(
        "<str:circle_id>/meet/create/",
        dash_lc_view.CircleMeetAPI.as_view(),
        name="meet-create",
    ),
    path(
        "<str:circle_id>/meet/list/",
        dash_lc_view.CircleMeetAPI.as_view(),
        name="meet-list",
    ),
    path(
        "meets/report/<str:meet_id>/",
        dash_lc_view.CircleMeetReportSubmitAPI.as_view(),
        name="meet-report-submission",
    ),
    path(
        "meets/attendee-report/<str:meet_id>/",
        dash_lc_view.CircleAttendeeReportAPI.as_view(),
        name="meet-report-submission",
    ),
    path(
        "meets/attendee-report/<str:meet_id>/<str:task_id>/",
        dash_lc_view.CircleMeetTaskPOWAPI.as_view(),
        name="meet-report-submission",
    ),
    path(
        "meets/verify-list/",
        dash_lc_view.CircleMeetVerifyAPI.as_view(),
    ),
    path(
        "meets/verify/<str:meet_id>/",
        dash_lc_view.CircleMeetVerifyAPI.as_view(),
    ),
    path(
        "meets/attendees/<str:meet_id>/",
        dash_lc_view.CircleMeetAttendeesListAPI.as_view(),
        name="meet-attendees-list",
    ),
    path(
        "meets/interested/<str:meet_id>/",
        dash_lc_view.CircleMeetInterestedAPI.as_view(),
        name="meet-interested",
    ),
    path(
        "meets/info/<str:meet_id>/",
        dash_lc_view.CircleMeetDetailAPI.as_view(),
        name="meet-info",
    ),
    path(
        "meets/join/<str:meet_code_id>/",
        dash_lc_view.CircleMeetJoinAPI.as_view(),
        name="meet-join",
    ),
    path(
        "user-list/", dash_lc_view.UserLearningCircleListApi.as_view(), name="main"
    ),  # list all lc's of user
    # path("stats/", dash_lc_view.LearningCircleStatsAPI.as_view(), name="data"),
    path(
        "<str:circle_id>/details/",
        dash_lc_view.LearningCircleDetailsApi.as_view(),
        name="lc-detailed",
    ),  # individual ls details
    # dashboard search listing
    path(
        "<str:circle_id>/schedule-meet/",
        dash_lc_view.ScheduleMeetAPI.as_view(),
        name="schedule-meet",
    ),
    # path(
    #     "<str:circle_id>/report/create/",
    #     dash_lc_view.SingleReportDetailAPI.as_view(),
    #     name="create-report",
    # ),
    # path(
    #     "<str:circle_id>/report/create/validate/",
    #     dash_lc_view.ValidateUserMeetCreateAPI.as_view(),
    #     name="validate-report",
    # ),
    # path(
    #     "<str:circle_id>/report/<str:report_id>/show/",
    #     dash_lc_view.SingleReportDetailAPI.as_view(),
    #     name="show-report",
    # ),
    path(
        "<str:circle_id>/add-member/",
        dash_lc_view.AddMemberAPI.as_view(),
        name="add-member",
    ),
    path("create/", dash_lc_view.LearningCircleCreateApi.as_view(), name="create"),
    path(
        "join/<str:circle_id>/",
        dash_lc_view.LearningCircleJoinApi.as_view(),
        name="join",
    ),
    path(
        "<str:circle_id>/ig-progress/",
        dash_lc_view.IgTaskDetailsAPI.as_view(),
        name="ig-progress",
    ),  # ig progress api
    path(
        "<str:circle_id>/lead-transfer/<str:new_lead_id>/",
        dash_lc_view.LearningCircleLeadTransfer.as_view(),
        name="lead-transfer",
    ),
    # # rework user accept, reject api
    # TODO: new api for note updation
    # path('<str:circle_id>/note/edit/', dash_lc_view.LearningCircleLeadTransfer.as_view(), name='edit-note'),
    path(
        "<str:circle_id>/user-accept-reject/<str:member_id>/",
        dash_lc_view.LearningCircleDetailsApi.as_view(),
    ),  # user accept or reject, also for removal
    path(
        "list-all/<str:circle_code>/",
        dash_lc_view.TotalLearningCircleListApi.as_view(),
        name="list-all-search",
    ),
    path(
        "list/", dash_lc_view.LearningCircleMainApi.as_view(), name="list"
    ),  # public page listing
    path(
        "list-all/", dash_lc_view.TotalLearningCircleListApi.as_view(), name="list-all"
    ),  # dashboard search listing
    # path('list-members/<str:circle_id>/', dash_lc_view.LearningCircleListMembersApi.as_view(), name='list-members'),
    # path('invite/', dash_lc_view.LearningCircleInviteLeadAPI.as_view()),
    # path('meet-record/list-all/<str:circle_id>/', dash_lc_view.SingleReportDetailAPI.as_view(), name='list-all-meet-record'),  # optim
    # path('meet-record/edit/<str:circle_id>/', dash_lc_view.SingleReportDetailAPI.as_view(), name='edit-meet-record'),       # optim
    # path('member/invite/<str:circle_id>/<str:muid>/', dash_lc_view.LearningCircleInviteMemberAPI.as_view(), name='invite-member'),
    # path('member/invite/status/<str:circle_id>/<str:muid>/<str:status>/', dash_lc_view.LearningCircleInvitationStatus.as_view(), name='invite-member-status'),
]
