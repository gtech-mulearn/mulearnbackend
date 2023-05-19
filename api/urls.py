from django.urls import path, include

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('portal/', include('api.portal.urls')),
    path('register/', include('api.register.urls')),
    path('organisation/', include('api.organisation.urls')),
    path('leaderboard/', include('api.leaderboard.urls')),
    path('dashboard/', include('api.dashboard.urls')),
    path('url-shortener/', include('api.url_shortener.urls')),
    path('location/', include('api.location.urls')),
    path('yip/',include('api.yip.urls'))
]
