"""modules.urls is mounted under /api/v1/ after every legacy include (issue 0023)."""

from django.urls import URLResolver

import api.urls


def test_modules_urls_are_mounted_last():
    last = api.urls.urlpatterns[-1]

    assert isinstance(last, URLResolver)
    assert last.urlconf_name.__name__ == "modules.urls"
    assert str(last.pattern) == ""
