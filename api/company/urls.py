from django.urls import path, include

urlpatterns = [
    path('jobs/', include('api.company.jobs.urls')),
]