"""Media keys: module list, key format, public URLs and the object-exists check.

Pure functions, no DB. requests.head is replaced in the existence tests so
nothing goes over the network.
"""
import re

import pytest
import requests

from utils import media_keys
from utils.media_modules import MEDIA_MODULES

UUID = "7f3c9e2a-1b4d-4c8e-9a10-5d2e6b7c8f90"


# ─────────────────────────────────────────────────────────────
# MEDIA_MODULES
# ─────────────────────────────────────────────────────────────

def test_ig_modules_are_defined():
    assert MEDIA_MODULES["ig_cover"] == "interest_group/cover"
    assert MEDIA_MODULES["ig_icon"] == "interest_group/icon"


@pytest.mark.parametrize("name,folder", list(MEDIA_MODULES.items()))
def test_module_names_and_folders_are_well_formed(name, folder):
    # Same rules the media worker applies to its MEDIA_MODULES.
    assert re.fullmatch(r"[a-z0-9_]+", name)
    assert re.fullmatch(r"[a-z0-9_-]+(/[a-z0-9_-]+)*", folder)


def test_module_folders_are_unique():
    assert len(set(MEDIA_MODULES.values())) == len(MEDIA_MODULES)


# ─────────────────────────────────────────────────────────────
# validate_key
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("module,key", [
    ("ig_cover", f"interest_group/cover/{UUID}.webp"),
    ("ig_icon", f"interest_group/icon/{UUID}.webp"),
])
def test_validate_key_accepts_worker_keys(module, key):
    assert media_keys.validate_key(module, key)


@pytest.mark.parametrize("key", [
    f"interest_group/cover/../{UUID}.webp",
    f"interest_group/cover/{UUID}.png",
    "interest_group/cover/not-a-uuid.webp",
    f"x/interest_group/cover/{UUID}.webp",
    f"interest_group/cover/{UUID}.webp/extra",
    f"interest_group/icon/{UUID}.webp",  # another module's folder
    "",
    None,
    123,
])
def test_validate_key_rejects_other_keys(key):
    assert not media_keys.validate_key("ig_cover", key)


def test_validate_key_rejects_unknown_module():
    assert not media_keys.validate_key("nope", f"interest_group/cover/{UUID}.webp")


# ─────────────────────────────────────────────────────────────
# public_url
# ─────────────────────────────────────────────────────────────

def test_public_url_joins_without_double_slash(settings):
    settings.R2_PUBLIC_BASE_URL = "https://media.example.org/"
    assert media_keys.public_url("a/b.webp") == "https://media.example.org/a/b.webp"


@pytest.mark.parametrize("key", [None, ""])
def test_public_url_is_none_without_key(key):
    assert media_keys.public_url(key) is None


# ─────────────────────────────────────────────────────────────
# object_exists
# ─────────────────────────────────────────────────────────────

class _Res:
    def __init__(self, status_code):
        self.status_code = status_code


def _head_returning(monkeypatch, status=None, raises=None):
    calls = []

    def fake_head(url, **kwargs):
        calls.append((url, kwargs))
        if raises:
            raise raises
        return _Res(status)

    monkeypatch.setattr(media_keys.requests, "head", fake_head)
    return calls


def test_object_exists_true_on_200(monkeypatch, settings):
    settings.R2_PUBLIC_BASE_URL = "https://media.example.org"
    calls = _head_returning(monkeypatch, status=200)
    assert media_keys.object_exists("a/b.webp") is True
    url, kwargs = calls[0]
    assert url == "https://media.example.org/a/b.webp"
    assert kwargs["timeout"] == media_keys.OBJECT_CHECK_TIMEOUT_SECONDS
    assert kwargs["allow_redirects"] is False


@pytest.mark.parametrize("status", [403, 404])
def test_object_exists_false_when_missing(monkeypatch, status):
    _head_returning(monkeypatch, status=status)
    assert media_keys.object_exists("a/b.webp") is False


@pytest.mark.parametrize("status", [301, 500, 503])
def test_object_exists_unavailable_on_unexpected_status(monkeypatch, status):
    _head_returning(monkeypatch, status=status)
    with pytest.raises(media_keys.MediaCheckUnavailable):
        media_keys.object_exists("a/b.webp")


def test_object_exists_unavailable_on_network_error(monkeypatch):
    _head_returning(monkeypatch, raises=requests.ConnectionError("down"))
    with pytest.raises(media_keys.MediaCheckUnavailable):
        media_keys.object_exists("a/b.webp")
