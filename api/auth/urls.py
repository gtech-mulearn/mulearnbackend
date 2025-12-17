from django.urls import path

from . import auth_views

urlpatterns = [
    path('google-mobile/', auth_views.GoogleMobileAuthProxyAPI.as_view(), name='google_mobile_proxy'),
    path('apple-mobile/', auth_views.AppleMobileAuthProxyAPI.as_view(), name='apple_mobile_proxy'),
    path('refresh-token/', auth_views.RefreshTokenProxyAPI.as_view(), name='refresh_token_proxy'),
]
