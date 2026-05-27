from django.urls import path
from . import launchpad_views
from .launchpad_views import (
    HireRequestsAPI, RegisterCompanyAPI, RegisterRecruiterAPI, CompanyListAPI, AddJobAPI, 
    LoginCompanyAPI, LoginRecruiterAPI, GetCompanyInfoAPI, GetRecruiterInfoAPI,
    RefreshTokenAPI, CompanyVerifyAPI, ListJobsAPI, VerifyTaskAPI, ListLaunchpadStudentsAPI,
    SendJobInvitationsAPI, StudentJobInvitationsAPI, StudentApplyToJobAPI, AcceptedStudentsAPI,
    ScheduleInterviewAPI, ApplicationFinalDecisionAPI, CompanyListVerifiedAPI, DeleteCompanyAPI,JobAPI,ForgotPasswordAPI, ResetPasswordAPI, VerifyResetTokenAPI, ChangePasswordAPI,
    DeleteCompanyAPI, JobAnalyticsAPI, JobTrendsAnalyticsAPI, JobsSummaryAnalyticsAPI,
)

urlpatterns = [
    path('register-company/', RegisterCompanyAPI.as_view()),
    path('register-recruiter/', RegisterRecruiterAPI.as_view()),
    path('company-list/', CompanyListAPI.as_view()),
    path('company-list-verified/', CompanyListVerifiedAPI.as_view()),
    path("login-company/", LoginCompanyAPI.as_view()),
    path("login-recruiter/", LoginRecruiterAPI.as_view()),
    path('refresh-token/', RefreshTokenAPI.as_view()),
    path('add-job/', AddJobAPI.as_view()),
    path('job/<str:job_id>/', JobAPI.as_view()),
    path('company-info/', GetCompanyInfoAPI.as_view()),
    path('recruiter-info/', GetRecruiterInfoAPI.as_view()),
    path('company-verify/', CompanyVerifyAPI.as_view()),
    path('list-jobs/', ListJobsAPI.as_view()),
    path('verify-task/', VerifyTaskAPI.as_view()),
    path('list-launchpad-students/<str:job_id>/', ListLaunchpadStudentsAPI.as_view()),
    path('hire-requests/', HireRequestsAPI.as_view(), name='hire-requests'),
    path('send-job-invitations/', SendJobInvitationsAPI.as_view()),
    path('student/job-invitations/', StudentJobInvitationsAPI.as_view(), name='student-job-invitations'),
    path('student/apply-to-job/', StudentApplyToJobAPI.as_view(), name='student-apply-to-job'),
    path('accepted-students/', AcceptedStudentsAPI.as_view(), name='accepted-students'),
    path('accepted-students/<str:job_id>/', AcceptedStudentsAPI.as_view(), name='accepted-students'),
    path('schedule-interview/', ScheduleInterviewAPI.as_view(), name='schedule-interview'),
    path('application-final-decision/', ApplicationFinalDecisionAPI.as_view(), name='application-final-decision'),
    path('delete-company/', DeleteCompanyAPI.as_view()),
    path('analytics/jobs-summary/', JobsSummaryAnalyticsAPI.as_view()),
    path('analytics/jobs/<str:job_id>/', JobAnalyticsAPI.as_view()),
    path('analytics/trends/', JobTrendsAnalyticsAPI.as_view()),
    #<----------------------- old launchpad -------------------------->
    path("leaderboard/", launchpad_views.Leaderboard.as_view()),
    path(
        "task-completed-leaderboard/",
        launchpad_views.TaskCompletedLeaderboard.as_view(),
    ),
    path("list-participants/", launchpad_views.ListParticipantsAPI.as_view()),
    path("launchpad-details/", launchpad_views.LaunchpadDetailsCount.as_view()),
    path("college-data/", launchpad_views.CollegeData.as_view()),
    path("user-college-link/", launchpad_views.LaunchPadUser.as_view()),
    path("user-college-link/<str:email>", launchpad_views.LaunchPadUser.as_view()),
    path(
        "user-college-link-public/<str:email>",
        launchpad_views.LaunchPadUserPublic.as_view(),
    ),
    path("user-profile/", launchpad_views.UserProfile.as_view()),
    path("user-college-data/", launchpad_views.UserBasedCollegeData.as_view()),
    path("bulk-user-college-link/", launchpad_views.BulkLaunchpadUser.as_view()),
    path("list-participants-admin/", launchpad_views.LaunchPadListAdmin.as_view()),
    path("user-details/<str:launchpad_id>/", launchpad_views.UserProfileAPI.as_view()),
    path("socials/<str:launchpad_id>/", launchpad_views.GetSocialsAPI.as_view()),
    path("user-log/<str:launchpad_id>/", launchpad_views.UserLogAPI.as_view()),
    path(
        "get-user-levels/<str:launchpad_id>/", launchpad_views.UserLevelsAPI.as_view()
    ),
    path("ig-leaderboard/", launchpad_views.IGLeaderboardView.as_view()),
    
    path('forgot-password/', ForgotPasswordAPI.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordAPI.as_view(), name='reset-password'),
    path('verify-reset-token/', VerifyResetTokenAPI.as_view(), name='verify-reset-token'),
    path('change-password/', ChangePasswordAPI.as_view(), name='change-password'),
    
]
