from django.urls import path

from . import karma_voucher_view

urlpatterns = [
    path('', karma_voucher_view.VoucherLogAPI.as_view()),
    path('import/', karma_voucher_view.ImportVoucherLogAPI.as_view()),
]