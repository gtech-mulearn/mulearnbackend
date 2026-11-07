from django.urls import path, include

urlpatterns = [
    path('organisation/', include('api.protected.organisation.urls')),
]
