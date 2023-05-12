from django.urls import path, include

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('portal/', include('api.portal.urls')),
]