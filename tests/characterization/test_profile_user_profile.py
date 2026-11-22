"""GET /api/v1/dashboard/profile/user-profile/, as it behaves today (issue 0025's example route)."""

import pytest
from django.db import OperationalError
from rest_framework.test import APIClient

pytestmark = [pytest.mark.mysql, pytest.mark.django_db]

URL = "/api/v1/dashboard/profile/user-profile/"


# The InterestGroup model has a cover_image_key column (backend 62cf57aa, on dev only) that the
# schema of record doesn't: no db-scripts alter adds it, so the route's interest-group prefetch
# fails on the vendored schema. strict=True turns this red as soon as the alter lands and is
# re-vendored; then delete the marker and write the golden file with --update-golden.
MISSING_COLUMN = "interest_group.cover_image_key isn't in schema/latest.sql"


@pytest.mark.xfail(strict=True, raises=OperationalError, reason=MISSING_COLUMN)
def test_a_signed_in_user_gets_their_profile(make_user, api_client, assert_envelope, golden):
    user = make_user(
        roles=["Student"], muid="profile-person@mulearn", full_name="Profile Person", email="profile-person@example.com"
    )

    response = api_client(user).get(URL)

    assert_envelope(response, has_error=False, status_code=200)
    golden(response, "profile_user_profile")


def test_without_a_token_the_profile_is_refused(golden):
    response = APIClient().get(URL)

    # Legacy auth failures answer HTTP 403 with statusCode 1000, and their body has no "response" key.
    assert response.status_code == 403
    golden(response, "profile_user_profile_no_token")
