from django.urls import path
from . import company_views, job_views, mulearner_views, analytics_views, task_views, feedback_views, collaboration_views, ig_sponsorship_views, event_template_views

urlpatterns = [
    path("register/",                 company_views.CompanyRegistrationAPI.as_view()),
    path("summary/",                  company_views.CompanyAdminSummaryAPI.as_view()),
    path("home-summary/",             analytics_views.CompanyDashboardSummaryAPIView.as_view()),
    path("status/",                   company_views.CompanyStatusAPI.as_view()),
    path("profile/",                  company_views.CompanyProfileAPI.as_view()),
    path("profile/public/<str:slug>/",company_views.PublicCompanyProfileAPI.as_view()),
    path("profile/public/<str:slug>/jobs/", job_views.PublicCompanyJobListAPI.as_view()),
    path("list/",                     company_views.CompanyListAPI.as_view()),
    path("jobs/",                     job_views.CompanyJobAPI.as_view()),
    path("jobs/all/",                 job_views.PublicJobAPI.as_view()),
    path("jobs/<str:job_id>/",        job_views.CompanyJobDetailAPI.as_view()),
    path("jobs/<str:job_id>/approve/", job_views.CompanyJobApproveAPI.as_view()),
    path("jobs/<str:job_id>/reject/",  job_views.CompanyJobRejectAPI.as_view()),
    path("jobs/<str:job_id>/view/",   job_views.TrackJobViewAPIView.as_view()),
    path("jobs/<str:job_id>/analytics/", job_views.CompanyJobEngagementAnalyticsAPIView.as_view()),
    path("jobs/<str:job_id>/apply/",  job_views.JobApplicationAPI.as_view()),
    path("jobs/<str:job_id>/applications/", job_views.JobApplicationAPI.as_view()),
    path("applications/me/",          job_views.UserAppliedJobsAPI.as_view()),
    path("applications/<str:app_id>/status/", job_views.ApplicationStatusAPI.as_view()),
    path("applications/<str:app_id>/withdraw/", job_views.UserApplicationWithdrawAPI.as_view()),
    path("applications/<str:app_id>/resubmit/", job_views.UserApplicationResubmitAPI.as_view()),
    path("mulearners/",               mulearner_views.CompanyMulearnerDirectoryAPI.as_view()),
    path("mulearners/shortlist/",              mulearner_views.CompanyTalentShortlistAPI.as_view()),
    path("mulearners/shortlist/<str:user_id>/", mulearner_views.CompanyTalentShortlistAPI.as_view()),
    path("analytics/gigs/",           analytics_views.CompanyGigAnalyticsAPI.as_view()),
    path("analytics/tasks/",          analytics_views.CompanyTaskAnalyticsAPI.as_view()),
    path("talent-pool/analytics/",    analytics_views.CompanyTalentPoolAnalyticsAPIView.as_view()),
    path("analytics/campus/",         analytics_views.CompanyCampusAnalyticsAPIView.as_view()),
    path("talent-pool/insights/",     analytics_views.CompanyTalentPoolInsightsAPIView.as_view()),

    # Feedback & Impact Reporting (PRD §13)
    path("feedback/",                 feedback_views.CompanyFeedbackAPI.as_view()),
    path("feedback/list/",            feedback_views.CompanyFeedbackListAPI.as_view()),
    path("impact-report/",            feedback_views.CompanyImpactReportAPI.as_view()),
    path("impact-report/publish/",    feedback_views.CompanyImpactReportPublishAPI.as_view()),

    # Collaboration / Partnership discovery flow (PRD §10)
    path("collaborations/",                    collaboration_views.CompanyCollaborationListCreateAPI.as_view()),
    path("collaborations/discover/",           collaboration_views.CompanyCollaborationDiscoverAPI.as_view()),
    path("collaborations/<str:collaboration_id>/respond/", collaboration_views.CompanyCollaborationRespondAPI.as_view()),
    path("collaborations/<str:collaboration_id>/",         collaboration_views.CompanyCollaborationWithdrawAPI.as_view()),

    # Company-sponsored IG (PRD §7.3)
    path("ig-sponsorship/<str:ig_id>/",         ig_sponsorship_views.IgSponsorshipRequestAPI.as_view()),
    path("ig-sponsorship/<str:ig_id>/review/",  ig_sponsorship_views.IgSponsorshipReviewAPI.as_view()),
    path("ig-sponsorship/<str:ig_id>/metrics/", ig_sponsorship_views.IgSponsorshipMetricsAPI.as_view()),

    # Event templates (PRD §8.3)
    path("events/templates/",                  event_template_views.CompanyEventTemplateListCreateAPI.as_view()),
    path("events/templates/<str:template_id>/", event_template_views.CompanyEventTemplateDetailAPI.as_view()),

    # Company Co-Admin — Delegation (Addon §6.5 / PRD §4.4)
    path("admin-link/",                       company_views.CompanyAdminLinkCreateAPI.as_view()),
    path("admin-link/list/",                  company_views.CompanyAdminLinkListAPI.as_view()),
    path("admin-link/<str:link_id>/respond/", company_views.CompanyAdminLinkAcceptAPI.as_view()),
    path("admin-link/<str:link_id>/leave/",   company_views.CompanyAdminLinkLeaveAPI.as_view()),
    path("admin-link/<str:link_id>/",         company_views.CompanyAdminLinkRevokeAPI.as_view()),

    # Company Mentor — Nomination
    path("mentor/nominate/",          company_views.CompanyMentorNominateAPI.as_view()),
    path("mentor/apply/",             company_views.CompanyMentorApplyAPI.as_view()),
    path("mentor/list/",              company_views.CompanyMentorListAPI.as_view()),

    # Task Management for Company
    path("tasks/",                    task_views.CompanyTaskListCreateAPI.as_view(), name='company-task-list-create'),
    path("tasks/templates/",          task_views.CompanyTaskTemplateListCreateAPI.as_view()),
    path("tasks/templates/<str:template_id>/", task_views.CompanyTaskTemplateDetailAPI.as_view()),
    path("tasks/<str:task_id>/",      task_views.CompanyTaskDetailAPI.as_view(), name='company-task-detail'),

    # Company Deactivation / Reactivation (PRD §4.2/§4.3)
    path("deactivate/",                    company_views.CompanyDeactivateAPI.as_view()),
    path("<str:company_id>/deactivate/",   company_views.CompanyAdminDeactivateAPI.as_view()),
    path("<str:company_id>/reactivate/",   company_views.CompanyReactivateAPI.as_view()),

    path("<str:company_id>/",         company_views.CompanyDetailAPI.as_view()),
    path("verify/<str:company_id>/",  company_views.CompanyVerifyAPI.as_view()),
]
