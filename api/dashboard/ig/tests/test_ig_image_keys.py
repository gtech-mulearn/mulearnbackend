"""IG image key rules: what may be attached to an Interest Group.

No DB: the "already used by another IG" lookup and the bucket check are
replaced with stand-ins, so what is under test is the order of the checks and
the message each failure gives.
"""
import pytest

from api.dashboard.ig import dash_ig_view
from db.task import InterestGroup
from utils import media_keys

UUID = "7f3c9e2a-1b4d-4c8e-9a10-5d2e6b7c8f90"
COVER_KEY = f"interest_group/cover/{UUID}.webp"


@pytest.fixture
def checks(monkeypatch):
    """Stand-ins for the DB lookup and the bucket HEAD; tests flip them."""
    state = {"in_use": False, "exists": True, "unavailable": False, "calls": []}

    def fake_in_use(key, exclude_ig_id=None):
        state["calls"].append(("in_use", key, exclude_ig_id))
        return state["in_use"]

    def fake_exists(key):
        state["calls"].append(("exists", key))
        if state["unavailable"]:
            raise media_keys.MediaCheckUnavailable("down")
        return state["exists"]

    monkeypatch.setattr(dash_ig_view, "_ig_key_in_use", fake_in_use)
    monkeypatch.setattr(dash_ig_view.media_keys, "object_exists", fake_exists)
    return state


def test_accepts_a_valid_unused_existing_key(checks):
    assert dash_ig_view._validate_ig_image_key(COVER_KEY, "cover", ig_id="ig-1") is None
    assert ("in_use", COVER_KEY, "ig-1") in checks["calls"]


def test_rejects_malformed_key_without_db_or_network(checks):
    error = dash_ig_view._validate_ig_image_key("../etc/passwd", "cover")
    assert error == "Invalid image key for this upload type"
    assert checks["calls"] == []


def test_rejects_key_from_the_other_image_type(checks):
    error = dash_ig_view._validate_ig_image_key(COVER_KEY, "icon")
    assert error == "Invalid image key for this upload type"


def test_rejects_key_used_by_another_ig_before_hitting_the_bucket(checks):
    checks["in_use"] = True
    error = dash_ig_view._validate_ig_image_key(COVER_KEY, "cover", ig_id="ig-1")
    assert error == "This image is already used by another Interest Group"
    assert not any(c[0] == "exists" for c in checks["calls"])


def test_rejects_key_whose_object_does_not_exist(checks):
    checks["exists"] = False
    error = dash_ig_view._validate_ig_image_key(COVER_KEY, "cover")
    assert error == "Image not found. Please upload it again"


def test_refuses_when_the_bucket_cannot_be_checked(checks):
    checks["unavailable"] = True
    error = dash_ig_view._validate_ig_image_key(COVER_KEY, "cover")
    assert error == "Could not verify the image right now. Please try again"


@pytest.mark.parametrize("image_type", ["cover", "icon"])
def test_legacy_image_path_matches_the_old_upload_location(image_type):
    ig = InterestGroup(id="ig-1")
    assert ig.legacy_image_path(image_type) == f"interest_group/{image_type}/ig-1.png"


def test_image_url_prefers_the_key_over_a_legacy_file(settings):
    settings.R2_PUBLIC_BASE_URL = "https://media.example.org"
    ig = InterestGroup(id="ig-1", cover_image_key=COVER_KEY)
    assert ig.cover_image == f"https://media.example.org/{COVER_KEY}"
