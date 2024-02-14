from django.urls import path

from . import coupon_view

urlpatterns = [
    path('verify-coupon/', coupon_view.CouponApi.as_view(), name='verify-coupon'),
]
