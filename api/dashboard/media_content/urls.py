from django.urls import path

from . import views

urlpatterns = [
    # ── Office Hours ─────────────────────────────────────────────────────────
    path('office-hours/',                    views.OfficeHoursListCreateAPI.as_view()),
    path('office-hours/<str:record_id>/',    views.OfficeHoursDetailAPI.as_view()),

    # ── Salt Mango Tree ──────────────────────────────────────────────────────
    path('salt-mango-tree/',                 views.SaltMangoTreeListCreateAPI.as_view()),
    path('salt-mango-tree/<str:record_id>/', views.SaltMangoTreeDetailAPI.as_view()),

    # ── Inspiration Station Radio ────────────────────────────────────────────
    path('inspiration-station/',                 views.InspirationStationListCreateAPI.as_view()),
    path('inspiration-station/<str:record_id>/', views.InspirationStationDetailAPI.as_view()),
]
