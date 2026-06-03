from django.urls import path
from . import leave_views

urlpatterns = [
    path("", leave_views.InternLeaveRequestAPI.as_view(), name="intern-leave-request"),
    path("history/", leave_views.InternLeaveHistoryAPI.as_view(), name="intern-leave-history"),
    path("balance/", leave_views.InternLeaveBalanceAPI.as_view(), name="intern-leave-balance"),
]
