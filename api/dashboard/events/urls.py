from django.urls import path

from . import events_views

urlpatterns = [
    path('', events_views.EventAPI.as_view()),
    path('<str:event_id>/', events_views.EventAPI.as_view()),
    path('manage/company/', events_views.CompanyEventAPI.as_view()),
    path('manage/company/<str:event_id>/', events_views.CompanyEventAPI.as_view()),
]