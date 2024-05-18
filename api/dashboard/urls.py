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
    path('projects/', include('api.dashboard.projects.urls')),
    path('lc/', include('api.dashboard.lc.urls')),
    path('referral/', include('api.dashboard.referral.urls')),
    path('college/', include('api.dashboard.college.urls')),
    path('karma-voucher/', include('api.dashboard.karma_voucher.urls')),
    path('location/', include('api.dashboard.location.urls')),
    path('organisation/', include('api.dashboard.organisation.urls')),
    path('dynamic-management/', include('api.dashboard.dynamic_management.urls')),
    path('error-log/', include('api.dashboard.error_log.urls')),

    path('affiliation/', include('api.dashboard.affiliation.urls')),
    path('channels/', include('api.dashboard.channels.urls')),
    path('discord-moderator/', include('api.dashboard.discord_moderator.urls')),
    path('events/', include('api.dashboard.events.urls')),

    path('coupon/', include('api.dashboard.coupon.urls')),

]
