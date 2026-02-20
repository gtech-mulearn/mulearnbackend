<<<<<<< HEAD
from django.urls import path,include
urlpatterns = [
        path("jobs/", include("api.dashboard.company.jobs.urls")),
]

=======
from django.urls import path

from . import company_views

urlpatterns = [
    path("profile/", company_views.CompanyProfileView.as_view()),
    path("<str:slug>/approve/", company_views.CompanyApproveView.as_view()),
    path("<str:slug>/", company_views.CompanySlugView.as_view()),
]
>>>>>>> dda433f4 (feat(company): implement Company module with lifecycle workflow and admin approval)
