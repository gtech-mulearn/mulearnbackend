from django.urls import path, include

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('user/', include('api.dashboard.user.urls')),
    path('zonal/', include('api.dashboard.zonal.urls')),
    path('district/', include('api.dashboard.district.urls')),
    path('campus/', include('api.dashboard.campus.urls')),
    path('roles/', include('api.dashboard.roles.urls')),
    path('ig/', include('api.dashboard.ig.urls')),
    path('task/', include('api.dashboard.task.urls')),
    path('profile/', include('api.dashboard.profile.urls')),
]
