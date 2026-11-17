"""
Helpers for image keys issued by the media worker (mulearn-media-worker).

The worker validates, compresses and stores the image in R2, then returns a
key like "interest_group/cover/<uuid>.webp". The backend never touches the
image bytes: it only checks that a key looks like one the worker would issue
for the given module and that the object really exists, stores it in the
database, and turns it back into a public URL when the image is read.
"""
import re

import requests
from django.conf import settings

from utils.media_modules import MEDIA_MODULES

_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

# HEAD request to the public bucket URL; kept short because it runs on the
# request path when a key is attached.
OBJECT_CHECK_TIMEOUT_SECONDS = 5


class MediaCheckUnavailable(Exception):
    """The public bucket could not be reached, so existence is unknown."""


def validate_key(module, key):
    """True only if `key` is exactly "<folder for module>/<uuid>.webp"."""
    folder = MEDIA_MODULES.get(module)
    if not folder or not isinstance(key, str):
        return False
    return re.fullmatch(rf"{re.escape(folder)}/{_UUID}\.webp", key) is not None


def public_url(key):
    """Public URL for a stored key, or None when there is no key."""
    if not key:
        return None
    return f"{settings.R2_PUBLIC_BASE_URL.rstrip('/')}/{key}"


def object_exists(key):
    """
    True if the object behind `key` is publicly readable, False if the bucket
    says it is not there (404/403). Raises MediaCheckUnavailable when the
    bucket cannot be reached or answers unexpectedly, so callers can refuse
    the request instead of storing a key that may point nowhere.
    """
    try:
        res = requests.head(
            public_url(key),
            timeout=OBJECT_CHECK_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        raise MediaCheckUnavailable(str(exc)) from exc
    if res.status_code == 200:
        return True
    if res.status_code in (403, 404):
        return False
    raise MediaCheckUnavailable(f"unexpected status {res.status_code}")
