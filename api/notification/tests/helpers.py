"""Shared request helper for the notification and push endpoint tests."""
from rest_framework.test import APIRequestFactory

from utils.tests.unmanaged_db import bearer


def hit(view_cls, method, path, user, roles, data=None, **kwargs):
    """Call a view as `user` carrying a signed JWT with `roles`."""
    factory = APIRequestFactory()
    request = getattr(factory, method)(
        path, data, format="json", HTTP_AUTHORIZATION=bearer(user, roles)
    )
    return view_cls.as_view()(request, **kwargs)
