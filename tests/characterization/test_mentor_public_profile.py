"""GET /api/v1/dashboard/mentor/public/profile/<id>/ for a mentor that doesn't exist: a legacy failure envelope."""

import pytest

pytestmark = [pytest.mark.mysql, pytest.mark.django_db]


def test_an_unknown_mentor_is_not_found(make_user, api_client, assert_envelope, golden):
    user = make_user(roles=["Student"], muid="mentor-seeker@mulearn")

    response = api_client(user).get("/api/v1/dashboard/mentor/public/profile/00000000-0000-4000-8000-00000000abcd/")

    # Legacy: the body says statusCode 404, while the HTTP status stays 400.
    assert_envelope(response, has_error=True, status_code=404, http_status=400)
    golden(response, "mentor_public_profile_not_found")
