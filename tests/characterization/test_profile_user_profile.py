"""GET /api/v1/dashboard/profile/user-profile/, as it behaves today (issue 0025's example route)."""

import pytest
from rest_framework.test import APIClient

from tests.characterization.harness import mint_token

pytestmark = [pytest.mark.mysql, pytest.mark.django_db]

URL = "/api/v1/dashboard/profile/user-profile/"


# The InterestGroup model has a cover_image_key column (backend 62cf57aa, on dev only) that the
# schema of record doesn't: no db-scripts alter adds it, so the route's interest-group prefetch
# fails on the vendored schema. Since issue 0019 the exception handler answers that failure with a
# JSON 500 envelope instead of raising, so the envelope check is what fails. strict=True turns this
# red as soon as the alter lands and is re-vendored; then delete the marker and write the golden
# file with --update-golden.
MISSING_COLUMN = "interest_group.cover_image_key isn't in schema/latest.sql"


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=MISSING_COLUMN)
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


def test_with_an_expired_token_the_profile_is_refused(make_user, golden):
    user = make_user(roles=["Student"], muid="expired-person@mulearn")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {mint_token(user, ['Student'], expires_in_seconds=-60)}")

    response = client.get(URL)

    # An expired token is refused like a missing one: HTTP 403, statusCode 1000, no "response" key.
    assert response.status_code == 403
    golden(response, "profile_user_profile_expired_token")
