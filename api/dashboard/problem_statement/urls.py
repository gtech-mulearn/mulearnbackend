from django.urls import path

from . import learner_views, manage_views as m

# Fixed prefixes (company/, admin/) come before the catch-all <statement_id>/.
urlpatterns = [
    path("company/", m.CompanyProblemStatementListAPI.as_view()),
    path("company/<str:statement_id>/", m.CompanyProblemStatementDetailAPI.as_view()),
    path("company/<str:statement_id>/publish/", m.CompanyProblemStatementPublishAPI.as_view()),
    path("company/<str:statement_id>/unpublish/", m.CompanyProblemStatementUnpublishAPI.as_view()),
    path("company/<str:statement_id>/interactions/", m.CompanyProblemStatementInteractionsAPI.as_view()),

    path("admin/", m.AdminProblemStatementListAPI.as_view()),
    path("admin/<str:statement_id>/", m.AdminProblemStatementDetailAPI.as_view()),
    path("admin/<str:statement_id>/publish/", m.AdminProblemStatementPublishAPI.as_view()),
    path("admin/<str:statement_id>/unpublish/", m.AdminProblemStatementUnpublishAPI.as_view()),
    path("admin/<str:statement_id>/interactions/", m.AdminProblemStatementInteractionsAPI.as_view()),
    path("admin/<str:statement_id>/interactions/<str:user_id>/",
         m.AdminProblemStatementInteractionDetailAPI.as_view()),

    path("", learner_views.ProblemStatementListAPI.as_view()),
    path("<str:statement_id>/", learner_views.ProblemStatementDetailAPI.as_view()),
    path("<str:statement_id>/interaction/", learner_views.ProblemStatementInteractionAPI.as_view()),
    path("<str:statement_id>/interaction/counts/",
         learner_views.ProblemStatementInteractionCountsAPI.as_view()),
]
