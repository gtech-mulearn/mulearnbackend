from django.urls import path
from . import manage_views
from . import public_views

urlpatterns = [
    # ── Learner & Public Feed ─────────────────────────────
    path('', public_views.ProblemStatementListAPI.as_view()),
    path('my-interests/', public_views.LearnerMyInterestsAPI.as_view()),

    # ── Company & Admin Management ─────────────────────────────
    path('manage/', manage_views.ManageProblemStatementListCreateAPI.as_view()),
    path('manage/<str:ps_id>/publish/', manage_views.ManageProblemStatementPublishAPI.as_view()),
    path('manage/<str:ps_id>/close/', manage_views.ManageProblemStatementCloseAPI.as_view()),
    path('manage/<str:ps_id>/archive/', manage_views.ManageProblemStatementArchiveAPI.as_view()),
    path('manage/<str:ps_id>/remove/', manage_views.ManageProblemStatementRemoveAPI.as_view()),
    path('manage/<str:ps_id>/', manage_views.ManageProblemStatementDetailAPI.as_view()),

    # ── Learner Item & Interest Routes ─────────────────────────
    path('<str:ps_id>/', public_views.ProblemStatementDetailAPI.as_view()),
    path('<str:ps_id>/interest/', public_views.ProblemStatementInterestAPI.as_view()),
]

