from django.urls import path

from . import mentor_views

urlpatterns = [
    # ── Onboarding ────────────────────────────────────────────────────────────
    path("onboarding/", mentor_views.MentorOnboardingAPI.as_view()),

    # ── Mentor roster (admin) ─────────────────────────────────────────────────
    path("list/", mentor_views.MentorListAPI.as_view()),
    path("<str:pk>/verify/", mentor_views.MentorVerifyAPI.as_view()),
    path("list/<str:pk>/tier/", mentor_views.MentorTierUpdateAPI.as_view()),         # [10] admin tier change

    # ── Overview & Leaderboard ────────────────────────────────────────────────
    path("overview/", mentor_views.MentorOverviewAPI.as_view()),
    path("stats/", mentor_views.MentorStatsAPI.as_view()),          # alias → overview
    path("leaderboard/", mentor_views.MentorLeaderboardAPI.as_view()),  # F3

    # ── Global session approval queue (must be before sessions/<pk>/) ─────────
    path("sessions/pending/", mentor_views.GlobalSessionPendingAPI.as_view()),
    path("sessions/<str:pk>/approve/", mentor_views.GlobalSessionApproveAPI.as_view()),

    # ── Sessions ──────────────────────────────────────────────────────────────
    path("sessions/", mentor_views.MentorSessionAPI.as_view()),
    path("sessions/<str:pk>/", mentor_views.MentorSessionDetailAPI.as_view()),
    path("sessions/<str:pk>/status/", mentor_views.MentorSessionStatusAPI.as_view()),
    path("sessions/<str:pk>/participants/", mentor_views.MentorSessionParticipantsAPI.as_view()),
    path("sessions/<str:session_pk>/participants/<str:user_pk>/", mentor_views.MentorSessionParticipantsAPI.as_view()),
    path("sessions/<str:pk>/karma-award/", mentor_views.MentorSessionKarmaAwardAPI.as_view()),  # F1
    path("sessions/<str:pk>/remind/", mentor_views.MentorSessionRemindAPI.as_view()),            # F4
    path("sessions/<str:pk>/attendance/", mentor_views.MentorSessionAttendanceAPI.as_view()),   # [2] bulk attendance
    path("sessions/<str:pk>/clone/", mentor_views.MentorSessionCloneAPI.as_view()),             # [6] session clone

    # ── Task Review Queue ─────────────────────────────────────────────────────
    path("review-queue/", mentor_views.MentorTaskReviewQueueAPI.as_view()),          # F2
    path("review-queue/<str:pk>/", mentor_views.MentorTaskReviewDetailAPI.as_view()), # F2 + [7] GET added

    # ── Availability ──────────────────────────────────────────────────────────
    path("availability/", mentor_views.MentorAvailabilityAPI.as_view()),
    path("availability/calendar/", mentor_views.MentorAvailabilityCalendarAPI.as_view()),
    path("availability/public/", mentor_views.PublicMentorAvailabilityAPI.as_view()),  # [9] public slots (no auth)
    path("availability/<str:pk>/", mentor_views.MentorAvailabilityDetailAPI.as_view()),

    # ── Task requests ─────────────────────────────────────────────────────────
    path("task-requests/", mentor_views.MentorTaskRequestAPI.as_view()),
    path("task-requests/<str:pk>/", mentor_views.MentorTaskRequestDetailAPI.as_view()),  # [8] DELETE added

    # ── Opportunities ─────────────────────────────────────────────────────────
    path("opportunities/", mentor_views.MentorOpportunityAPI.as_view()),
    path("opportunities/<str:pk>/", mentor_views.MentorOpportunityDetailAPI.as_view()),

    # ── Aggregates ────────────────────────────────────────────────────────────
    path("mentees/", mentor_views.MentorMenteesAPI.as_view()),
    path("mentees/<str:user_pk>/", mentor_views.MentorMenteeDetailAPI.as_view()),  # [1] mentee detail
    path("activity-log/", mentor_views.MentorActivityLogAPI.as_view()),

    # ── IG Links (new) ────────────────────────────────────────────────────────
    path("my-igs/", mentor_views.MentorMyIgsAPI.as_view()),
    path("ig-requests/", mentor_views.MentorIgRequestListAPI.as_view()),
    path("ig-requests/<str:pk>/", mentor_views.MentorIgRequestDetailAPI.as_view()),

    # ── Public Endpoints ──────────────────────────────────────────────────────
    path("<str:muid>/public/", mentor_views.PublicMentorCardAPI.as_view()),
    path("<str:muid>/public/sessions/", mentor_views.PublicMentorSessionsAPI.as_view()),  # [5] public session history

    # ── Company Mentor ────────────────────────────────────────────────────────
    path("company/onboarding/",                    mentor_views.CompanyMentorOnboardingAPI.as_view()),
    path("company/onboarding/<str:pk>/",           mentor_views.CompanyMentorOnboardingAPI.as_view()),
    path("company/list/",                          mentor_views.CompanyMentorListAPI.as_view()),
    path("company/<str:pk>/verify/",               mentor_views.CompanyMentorVerifyAPI.as_view()),
    path("company/sessions/",                      mentor_views.CompanyMentorSessionAPI.as_view()),
    path("company/sessions/<str:pk>/",             mentor_views.CompanyMentorSessionDetailAPI.as_view()),
    path("company/opportunities/",                 mentor_views.CompanyMentorOpportunityAPI.as_view()),
    path("company/opportunities/<str:pk>/",        mentor_views.CompanyMentorOpportunityDetailAPI.as_view()),
    path("company/mentees/",                       mentor_views.CompanyMentorMenteesAPI.as_view()),
    path("company/review-queue/",                  mentor_views.CompanyMentorTaskReviewAPI.as_view()),
    path("company/review-queue/<str:pk>/",         mentor_views.CompanyMentorTaskReviewDetailAPI.as_view()),
    path("company/my-orgs/",                       mentor_views.CompanyMentorMyOrgsAPI.as_view()),
    path("company/availability/",                  mentor_views.CompanyMentorAvailabilityAPI.as_view()),

    # ── Campus Mentor ─────────────────────────────────────────────────────────
    path("campus-mentor/onboarding/",              mentor_views.CampusMentorOnboardingAPI.as_view()),
    path("campus-mentor/onboarding/<str:pk>/",     mentor_views.CampusMentorOnboardingAPI.as_view()),
    path("campus-mentor/list/",                    mentor_views.CampusMentorListAPI.as_view()),
    path("campus-mentor/<str:pk>/verify/",         mentor_views.CampusMentorVerifyAPI.as_view()),
    path("campus-mentor/sessions/",                mentor_views.CampusMentorSessionAPI.as_view()),
    path("campus-mentor/sessions/<str:pk>/",       mentor_views.CampusMentorSessionDetailAPI.as_view()),
    path("campus-mentor/opportunities/",           mentor_views.CampusMentorOpportunityAPI.as_view()),
    path("campus-mentor/opportunities/<str:pk>/",  mentor_views.CampusMentorOpportunityDetailAPI.as_view()),
    path("campus-mentor/mentees/",                 mentor_views.CampusMentorMenteesAPI.as_view()),
    path("campus-mentor/review-queue/",            mentor_views.CampusMentorTaskReviewAPI.as_view()),
    path("campus-mentor/review-queue/<str:pk>/",   mentor_views.CampusMentorTaskReviewDetailAPI.as_view()),
    path("campus-mentor/events/",                  mentor_views.CampusMentorEventsAPI.as_view()),
    path("campus-mentor/events/<str:pk>/",         mentor_views.CampusMentorEventDetailAPI.as_view()),
    path("campus-mentor/my-orgs/",                 mentor_views.CampusMentorMyOrgsAPI.as_view()),
    path("campus-mentor/availability/",            mentor_views.CampusMentorAvailabilityAPI.as_view()),
]
