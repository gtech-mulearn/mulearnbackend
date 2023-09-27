import debug_toolbar
from django.urls import path, include

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('register/', include('api.register.urls')),
    path('leaderboard/', include('api.leaderboard.urls')),
    path('dash board/', include('api.dashboard.urls')),
    path('integrations/', include('api.integrations.urls')),
    path('url-shortener/', include('api.url_shortener.urls')),
    path('protected/', include('api.protected.urls')),
    path('hackathon/', include('api.hackathon.urls')),
    path('notification/', include('api.notification.urls')),
    path('get-log/', include('api.common.urls')),
    
    path("__debug__/", include(debug_toolbar.urls)),
]
