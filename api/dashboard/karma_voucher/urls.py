from django.urls import path

from . import karma_voucher_view

urlpatterns = [
    path('', karma_voucher_view.VoucherLogAPI.as_view()),
    path('import/', karma_voucher_view.ImportVoucherLogAPI.as_view()),
    path('export/', karma_voucher_view.ExportVoucherLogAPI.as_view()),

    path('create/', karma_voucher_view.VoucherLogAPI.as_view()),
    path('update/<str:voucher_id>/', karma_voucher_view.VoucherLogAPI.as_view()),
    path('delete/<str:voucher_id>/', karma_voucher_view.VoucherLogAPI.as_view()),

    path('base-template/', karma_voucher_view.VoucherBaseTemplateAPI.as_view()),
]   