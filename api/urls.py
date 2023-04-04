from django.urls import path, include

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('portal/', include('api.portal.urls')),
    path('user/', include('api.user.urls')),
    path('organisation/', include('api.organisation.urls'))
]
