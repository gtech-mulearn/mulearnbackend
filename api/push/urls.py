from django.urls import path

from . import views

urlpatterns = [
    path("devices/", views.DeviceAPI.as_view(), name="push-devices"),
    path("opened/", views.OpenedAPI.as_view(), name="push-opened"),
    path("preferences/", views.PreferenceAPI.as_view(), name="push-preferences"),
    path("admin/config/", views.AdminConfigAPI.as_view(), name="push-admin-config"),
    path("admin/campaigns/", views.AdminCampaignAPI.as_view(), name="push-admin-campaigns"),
    path(
        "admin/campaigns/<str:campaign_id>/<str:action>/",
        views.AdminCampaignActionAPI.as_view(),
        name="push-admin-campaign-action",
    ),
    path("admin/test/", views.AdminTestAPI.as_view(), name="push-admin-test"),
    path("admin/stats/", views.AdminStatsAPI.as_view(), name="push-admin-stats"),
]
