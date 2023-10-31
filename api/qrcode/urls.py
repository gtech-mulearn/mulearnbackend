from django.urls import path
from . import qrcode_views

urlpatterns = [
    # Other URL patterns
    path('generate_qr_code/', qrcode_views.QrcodeManagmentAPI.as_view(), name='generate_qr_code'),
]