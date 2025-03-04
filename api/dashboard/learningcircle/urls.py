from django.urls import path

from . import learningcircle_views

urlpatterns = [
    path("create/", learningcircle_views.LearningCircleView.as_view()),
    path("list/", learningcircle_views.LearningCircleView.as_view()),
    path("info/<str:circle_id>/", learningcircle_views.LearningCircleView.as_view()),
    path("edit/<str:circle_id>/", learningcircle_views.LearningCircleView.as_view()),
    path("delete/<str:circle_id>/", learningcircle_views.LearningCircleView.as_view()),
    path("meeting/create/", learningcircle_views.LearningCircleMeetingView.as_view()),
    path("meeting/list/", learningcircle_views.LearningCircleMeetingListAPI.as_view()),
    path(
        "meeting/list/<str:circle_id>/",
        learningcircle_views.LearningCircleMeetingView.as_view(),
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
]
