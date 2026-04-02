from django.urls import path

from .profile_views import CompanyProfileAPIView, PublicCompanyProfileAPIView

urlpatterns = [
    path("", CompanyProfileAPIView.as_view(), name="company-profile"),
    path(
        "public/<slug:slug>/",
        PublicCompanyProfileAPIView.as_view(),
        name="public-company-profile",
    ),
]

