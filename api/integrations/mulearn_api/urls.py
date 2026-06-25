from django.urls import path
from .views import ExternalTaskVerificationAPI

urlpatterns = [
    path('verify-task/', ExternalTaskVerificationAPI.as_view(), name='external-verify-task'),
]
