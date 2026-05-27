from django.urls import path

from .views import (
    CompanyMemberAddAPIView,
    CompanyMemberListAPIView,
    CompanyMemberRemoveAPIView,
)

urlpatterns = [
    path("", CompanyMemberListAPIView.as_view(), name="company-member-list"),
    path("add/", CompanyMemberAddAPIView.as_view(), name="company-member-add"),
    path("<str:link_id>/remove/", CompanyMemberRemoveAPIView.as_view(), name="company-member-remove"),
]
