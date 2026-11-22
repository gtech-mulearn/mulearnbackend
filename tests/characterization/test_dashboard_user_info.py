"""GET /api/v1/dashboard/user/info/, as it behaves today: the harness end to end on the MySQL tier."""

import pytest

pytestmark = [pytest.mark.mysql, pytest.mark.django_db]

URL = "/api/v1/dashboard/user/info/"


def test_a_signed_in_user_gets_their_info(make_user, api_client, assert_envelope, golden, django_assert_num_queries):
    user = make_user(
        roles=["Student"], muid="info-person@mulearn", full_name="Info Person", email="info-person@example.com"
    )

    with django_assert_num_queries(7):
        response = api_client(user).get(URL)

    assert_envelope(response, has_error=False, status_code=200)
    golden(response, "dashboard_user_info")
