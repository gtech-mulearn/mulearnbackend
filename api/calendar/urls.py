from django.urls import path
from . import calendar_view

urlpatterns = [
    path('ig-mentor/<str:ig_id>/sessions/', calendar_view.IGMentorSessionCalendar.as_view()),
    path('campus-mentor/<str:campus_id>/sessions/', calendar_view.CampusMentorSessionCalendar.as_view()),
    path('company/<str:company_org_id>/sessions/', calendar_view.CompanySessionCalendar.as_view()),
    path('events/', calendar_view.EventCalendar.as_view()),
    path('ig/<str:ig_id>/events/', calendar_view.IGEventCalendar.as_view()),
    path('campus/<str:campus_id>/events/', calendar_view.CampusEventCalendar.as_view()),
    path('company/<str:company_id>/events/', calendar_view.CompanyEventCalendar.as_view()),
]
