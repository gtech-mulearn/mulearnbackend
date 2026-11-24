"""PUT /api/v1/dashboard/profile/socials/edit/ must not 500.

DB-free: the ORM is mocked (the `db.*` models are unmanaged).
"""
from unittest.mock import MagicMock, patch

from rest_framework.serializers import ModelSerializer
from rest_framework.test import APIRequestFactory

from api.dashboard.profile import profile_serializer, profile_view

EMPTY = {
    "github": "",
    "facebook": "",
    "instagram": "",
    "linkedin": "",
    "dribble": "",
    "behance": "",
    "stackoverflow": "",
    "medium": "",
    "hackerrank": "",
}


def _put(data):
    request = APIRequestFactory().put("/socials/edit/", data, format="json")
    request.data = data
    return request


@patch.object(profile_view, "JWTUtils")
@patch.object(profile_view, "Socials")
@patch.object(profile_view, "LinkSocials")
def test_an_account_without_a_socials_row_gets_one(link, socials, jwt):
    """Accounts created outside registration have no row; save() used to
    fall into create() with no user (IntegrityError: user_id cannot be null)."""
    jwt.fetch_user_id.return_value = "u1"
    socials.objects.filter.return_value.first.return_value = None
    serializer = link.return_value
    serializer.instance = None
    serializer.is_valid.return_value = True

    response = profile_view.SocialsAPI().put(_put({**EMPTY, "github": "me"}))

    socials.objects.create.assert_called_once_with(
        user_id="u1", created_by_id="u1", updated_by_id="u1"
    )
    assert serializer.instance is socials.objects.create.return_value
    serializer.save.assert_called_once_with()
    assert response.status_code == 200


@patch.object(profile_view, "JWTUtils")
@patch.object(profile_view, "Socials")
@patch.object(profile_view, "LinkSocials")
def test_an_invalid_body_creates_no_row(link, socials, jwt):
    jwt.fetch_user_id.return_value = "u1"
    socials.objects.filter.return_value.first.return_value = None
    serializer = link.return_value
    serializer.instance = None
    serializer.is_valid.return_value = False
    serializer.errors = {"github": ["too long"]}

    profile_view.SocialsAPI().put(_put({**EMPTY, "github": "x" * 61}))

    socials.objects.create.assert_not_called()
    serializer.save.assert_not_called()


@patch.object(ModelSerializer, "update", return_value="saved")
@patch.object(profile_serializer, "Wallet")
@patch.object(profile_serializer, "KarmaActivityLog")
@patch.object(profile_serializer, "TaskList")
@patch.object(profile_serializer, "JWTUtils")
def test_removing_a_link_that_earned_no_karma_takes_none_back(
    jwt, tasks, logs, wallet, _update
):
    """`.first().delete()` raised AttributeError when no log existed."""
    jwt.fetch_user_id.return_value = "u1"
    logs.objects.filter.return_value.first.return_value = None
    instance = MagicMock(github="old-handle")

    result = profile_serializer.LinkSocials(context={"request": object()}).update(
        instance, {"github": ""}
    )

    assert result == "saved"
    wallet.objects.filter.return_value.update.assert_not_called()


@patch.object(ModelSerializer, "update", return_value="saved")
@patch.object(profile_serializer, "F")
@patch.object(profile_serializer, "Wallet")
@patch.object(profile_serializer, "KarmaActivityLog")
@patch.object(profile_serializer, "TaskList")
@patch.object(profile_serializer, "JWTUtils")
def test_removing_a_link_that_earned_karma_takes_it_back(
    jwt, tasks, logs, wallet, f, _update
):
    jwt.fetch_user_id.return_value = "u1"
    log = logs.objects.filter.return_value.first.return_value
    instance = MagicMock(github="old-handle")

    profile_serializer.LinkSocials(context={"request": object()}).update(
        instance, {"github": ""}
    )

    log.delete.assert_called_once_with()
    wallet.objects.filter.assert_called_once_with(user_id="u1")
    f.return_value.__add__.assert_called_once_with(-20)
