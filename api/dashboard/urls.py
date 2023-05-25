from django.urls import path, include

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('user/', include('api.dashboard.user.urls')),
    path('campus/', include('api.dashboard.campus.urls')),
    path('roles/', include('api.dashboard.roles.urls')),
    path('ig/', include('api.dashboard.ig.urls')),
    path('task/', include('api.dashboard.task.urls'))
]
