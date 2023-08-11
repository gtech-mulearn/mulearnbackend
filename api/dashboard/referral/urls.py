from django.urls import path
from . import referral_view

urlpatterns = [
    path('send-referral/', referral_view.Referral.as_view(), name='send-referral'),
    path('show-referrals/', referral_view.ReferralListAPI.as_view(), name='show-referrals'),
]
