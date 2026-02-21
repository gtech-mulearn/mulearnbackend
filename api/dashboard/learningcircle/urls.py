from django.urls import path

from . import learningcircle_views

urlpatterns = [
    path("create/", learningcircle_views.LearningCircleView.as_view()),
    path("list/", learningcircle_views.LearningCircleView.as_view()),
    path("info/<str:circle_id>/", learningcircle_views.LearningCircleView.as_view()),
    path("members/<str:circle_id>/",learningcircle_views.LearningCircleMemberDetailsView.as_view()), 
    path("edit/<str:circle_id>/", learningcircle_views.LearningCircleView.as_view()),
    path("delete/<str:circle_id>/", learningcircle_views.LearningCircleView.as_view()),
    path("meeting/create/<str:circle_id>/", learningcircle_views.LearningCircleMeetingView.as_view()),
    path("meeting/list-public/", learningcircle_views.LearningCircleMeetingPublicListView.as_view()),
    path("meeting/list/", learningcircle_views.LearningCircleMeetingListAPI.as_view()),
    path(
        "meeting/list/<str:circle_id>/",
        learningcircle_views.LearningCircleMeetingListView.as_view(),
    ),
    path(
        "meeting/edit/<str:meet_id>/",
        learningcircle_views.LearningCircleMeetingView.as_view(),
    ),
    path(
        "meeting/info/<str:meet_id>/",
        learningcircle_views.LearningCircleMeetingInfoAPI.as_view(),
    ),
    path(
        "meeting/delete/<str:meet_id>/",
        learningcircle_views.LearningCircleMeetingView.as_view(),
    ),
    path(
        "meeting/join/<str:meet_id>/",
        learningcircle_views.LearningCircleJoinAPI.as_view(),
    ),
    path(
        "meeting/rsvp/<str:meet_id>/",
        learningcircle_views.LearningCircleRSVPAPI.as_view(),
    ),
    path(
        "meeting/leave/<str:meet_id>/",
        learningcircle_views.LearningCircleJoinAPI.as_view(),
    ),
    path(
        "meeting/attendee-report/<str:meet_id>/",
        learningcircle_views.LearningCircleAttendeeReportAPI.as_view(),
    ),
    path(
        "meeting/report/<str:meet_id>/",
        learningcircle_views.LearningCircleReportAPI.as_view(),
    ),
    #  New Endpoints 
    path("user-circles/", learningcircle_views.UserCircleListAPI.as_view()),
    path("join/<str:circle_id>/", learningcircle_views.CircleJoinAPI.as_view()),
    path("members/add/<str:circle_id>/", learningcircle_views.CircleMemberAddAPI.as_view()),
    # Specific invite routes MUST come before the generic invite/<circle_id>/ to avoid swallowing
    path("invite/status/", learningcircle_views.CircleInviteStatusAPI.as_view()),
    path("invite/status/<str:link_id>/", learningcircle_views.CircleInviteStatusAPI.as_view()),
    path("invite/sent/<str:circle_id>/", learningcircle_views.CircleSentInvitesAPI.as_view()),
    path("invite/<str:circle_id>/", learningcircle_views.CircleInviteAPI.as_view()),
    path("transfer-lead/<str:circle_id>/", learningcircle_views.CircleTransferLeadAPI.as_view()),
]
