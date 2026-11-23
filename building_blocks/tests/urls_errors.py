"""A test-only URLconf for the exception handler's Django-level paths (issue 0019)."""

from django.core.exceptions import SuspiciousOperation
from django.urls import path
from rest_framework.views import APIView


class Crash(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        raise RuntimeError("boom")


class Suspicious(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        raise SuspiciousOperation("bad input")


urlpatterns = [
    path("crash/", Crash.as_view()),
    path("suspicious/", Suspicious.as_view()),
]

handler500 = "building_blocks.api.exceptions.server_error"
