from django.urls import path, include
import debug_toolbar
# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('register/', include('api.register.urls')),
    path('organisation/', include('api.dashboard.organisation.urls')),
    path('leaderboard/', include('api.leaderboard.urls')),
    path('dashboard/', include('api.dashboard.urls')),
    path('integrations/', include('api.integrations.urls')),
    path('url-shortener/', include('api.url_shortener.urls')),
    path('location/', include('api.dashboard.location.urls')),
    path('protected/', include('api.protected.urls')),
    path('hackathon/', include('api.hackathon.urls')),
    path('notification/', include('api.notification.urls')),
    path('referral/', include('api.referral.urls')),

    path("__debug__/", include(debug_toolbar.urls)),
]
