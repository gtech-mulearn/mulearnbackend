from django.urls import path
from . import achievement_views

urlpatterns = [
    path('list/', achievement_views.AchievementListAPIView.as_view(), name='achievement-list'),
    path('create/', achievement_views.AchievementCreateAPIView.as_view(), name='achievements-create'),
    path('update/<str:achievement_id>/', achievement_views.AchievementUpdateAPIView.as_view(), name='achievements-update'),
    path('delete/<str:achievement_id>/', achievement_views.AchievementDeleteAPIView.as_view(), name='achievements-delete'),
    path('list/user/<str:muid>/', achievement_views.UserAchievementsListAPIView.as_view(), name='achievements-user'),
    path('issue-vc/', achievement_views.UserAchievementsIssueAPIView.as_view(), name='achievements-issue'),
    path('bulk-issue/', achievement_views.AchievementIssueBulkAPIView.as_view(), name='achievements-bulk-issue'),
    path('bulk-issue/template/', achievement_views.AchievementBulkImportTemplateAPIView.as_view(), name='achievements-bulk-issue-template'),
    path('issued-log/', achievement_views.AchievementLogListAPIView.as_view(), name='achievements-issued-log'),
]