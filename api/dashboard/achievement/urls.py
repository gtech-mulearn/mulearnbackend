from django.urls import path
from . import achievement_views

urlpatterns = [
    # ===== USER-FACING ENDPOINTS =====
    # List all achievements
    path('list/', achievement_views.AchievementListAPIView.as_view(), name='achievement-list'),
    # View eligible achievements for current user (ready to claim)
    path('eligible/', achievement_views.EligibleAchievementsAPIView.as_view(), name='achievement-eligible'),
    # Claim an achievement (user action)
    path('claim/<str:achievement_id>/', achievement_views.ClaimAchievementAPIView.as_view(), name='achievement-claim'),
    # View user's claimed achievements
    path('list/user/<str:muid>/', achievement_views.UserAchievementsListAPIView.as_view(), name='achievements-user'),
    # View progress towards all achievements
    path('progress/', achievement_views.UserProgressAPIView.as_view(), name='achievement-progress'),

    # ===== ADMIN ENDPOINTS =====
    # Achievement CRUD
    path('create/', achievement_views.AchievementCreateAPIView.as_view(), name='achievements-create'),
    path('update/<str:achievement_id>/', achievement_views.AchievementUpdateAPIView.as_view(), name='achievements-update'),
    path('delete/<str:achievement_id>/', achievement_views.AchievementDeleteAPIView.as_view(), name='achievements-delete'),

    # Rule Management
    path('rules/', achievement_views.AchievementRuleListAPIView.as_view(), name='achievement-rules-list'),
    path('rules/create/', achievement_views.AchievementRuleCreateAPIView.as_view(), name='achievement-rules-create'),
    path('rules/<str:rule_id>/', achievement_views.AchievementRuleDetailAPIView.as_view(), name='achievement-rules-detail'),
    path('rules/<str:rule_id>/deactivate/', achievement_views.AchievementRuleDeactivateAPIView.as_view(), name='achievement-rules-deactivate'),

    # Simulation & Debug
    path('simulate/<str:muid>/', achievement_views.SimulateRulesAPIView.as_view(), name='achievement-simulate'),
    path('debug/<str:muid>/<str:achievement_id>/', achievement_views.DebugAchievementAPIView.as_view(), name='achievement-debug'),

    # Manual Operations (Admin only)
    path('manual-issue/', achievement_views.ManualIssueAPIView.as_view(), name='achievement-manual-issue'),
    path('revoke/', achievement_views.RevokeAchievementAPIView.as_view(), name='achievement-revoke'),

    # Audit Logs
    path('audit/<str:muid>/', achievement_views.AuditLogAPIView.as_view(), name='achievement-audit'),

    # Legacy endpoint (for VC issuance)
    path('issue-vc/', achievement_views.UserAchievementsIssueAPIView.as_view(), name='achievements-issue'),
    path('bulk-issue/', achievement_views.AchievementIssueBulkAPIView.as_view(), name='achievements-bulk-issue'),
    path('bulk-issue/template/', achievement_views.AchievementBulkImportTemplateAPIView.as_view(), name='achievements-bulk-issue-template'),
    path('issued-log/', achievement_views.AchievementLogListAPIView.as_view(), name='achievements-issued-log'),
    path('bulk-claim/', achievement_views.BulkClaimTaskAchievementAPIView.as_view(), name='achievement-bulk-claim'),
]
