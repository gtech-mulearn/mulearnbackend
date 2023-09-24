from django.urls import path

from . import referral_view

urlpatterns = [
    path('', referral_view.ReferralListAPI.as_view(), name='show-referrals'),
    path('send-referral/', referral_view.Referral.as_view(), name='send-referral')
]
