from django.urls import path
from . import referral_view

urlpatterns = [
    path('send-referral/', referral_view.Referral.as_view(), name='send-referral'),
]
