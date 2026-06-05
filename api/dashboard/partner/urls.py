from django.urls import path

from . import views, admin_views

urlpatterns = [
    # Partner-facing (1–6)
    path("register/",                       views.PartnerRegisterAPI.as_view()),
    path("status/",                         views.PartnerStatusAPI.as_view()),
    path("summary/",                        views.PartnerSummaryAPI.as_view()),
    path("profile/",                        views.PartnerProfileAPI.as_view()),
    path("profile/public/<str:slug>/",      views.PublicPartnerProfileAPI.as_view()),
    path("events/",                         views.PartnerEventListAPI.as_view()),

    # Admin (7–8)
    path("admin/list/",                     admin_views.PartnerAdminListAPI.as_view()),
    path("admin/<str:partner_id>/verify/",  admin_views.PartnerAdminVerifyAPI.as_view()),
]
