from django.urls import path
from .views import (
    RazorPayOrderAPI,
    RazorPayVerification,
    RazorPaySubscriptionAPI,
    RazorPaySubscriptionVerification,
    BankTransferAPI
)

urlpatterns = [
    # One-time payments
    path('order/', RazorPayOrderAPI.as_view(), name='donate-order'),
    path('verify/', RazorPayVerification.as_view(), name='donate-verify'),
    
    # Recurring payments (subscriptions)
    path('subscription/create/', RazorPaySubscriptionAPI.as_view(), name='donate-subscription-create'),
    path('subscription/verify/', RazorPaySubscriptionVerification.as_view(), name='donate-subscription-verify'),
    
    # Bank transfer (for donations >= 5L)
    path('bank-transfer/', BankTransferAPI.as_view(), name='donate-bank-transfer'),
]