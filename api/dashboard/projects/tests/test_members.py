import pytest
from rest_framework.test import APIClient


URL = lambda pid: f"/api/v1/dashboard/projects/{pid}/members/"
ITEM_URL = lambda pid, mid: f"/api/v1/dashboard/projects/{pid}/members/{mid}/"


@pytest.mark.django_db
def test_add_member_requires_auth(project_fixture, other_user_fixture):
    resp = APIClient().post(URL(project_fixture.id),
                            {"muid": other_user_fixture.muid}, format="json")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_owner_adds_linked_member_by_muid(project_fixture, other_user_fixture, auth_client):
    resp = auth_client.post(URL(project_fixture.id),
                            {"muid": other_user_fixture.muid, "role": "lead"}, format="json")
    assert resp.status_code == 200, resp.json()
    body = resp.json()["response"]["Member"]
    assert body["is_linked"] is True
    assert body["user_id"] == other_user_fixture.id
    assert body["muid"] == other_user_fixture.muid
    assert body["full_name"] == other_user_fixture.full_name
    assert body["external_name"] is None
    assert body["role"] == "lead"


@pytest.mark.django_db
def test_owner_adds_external_member(project_fixture, auth_client):
    resp = auth_client.post(URL(project_fixture.id),
                            {"external_name": "Jane Pixel", "role": "designer"}, format="json")
    assert resp.status_code == 200, resp.json()
    body = resp.json()["response"]["Member"]
    assert body["is_linked"] is False
    assert body["user_id"] is None
    assert body["external_name"] == "Jane Pixel"
    assert body["full_name"] == "Jane Pixel"


@pytest.mark.django_db
def test_neither_identity_returns_400(project_fixture, auth_client):
    resp = auth_client.post(URL(project_fixture.id), {"role": "lead"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_both_identities_returns_400(project_fixture, other_user_fixture, auth_client):
    resp = auth_client.post(URL(project_fixture.id),
        {"muid": other_user_fixture.muid, "external_name": "X"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_non_owner_cannot_add_member(project_fixture, other_user_fixture, other_auth_client):
    resp = other_auth_client.post(URL(project_fixture.id),
                                   {"muid": other_user_fixture.muid}, format="json")
    assert resp.status_code in (400, 403)


@pytest.mark.django_db
def test_duplicate_linked_member_returns_400(project_fixture, other_user_fixture, auth_client):
    auth_client.post(URL(project_fixture.id), {"muid": other_user_fixture.muid}, format="json")
    second = auth_client.post(URL(project_fixture.id), {"muid": other_user_fixture.muid}, format="json")
    assert second.status_code == 400


@pytest.mark.django_db
def test_duplicate_external_name_allowed(project_fixture, auth_client):
    first = auth_client.post(URL(project_fixture.id), {"external_name": "Jane"}, format="json")
    second = auth_client.post(URL(project_fixture.id), {"external_name": "Jane"}, format="json")
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["response"]["Member"]["id"] != second.json()["response"]["Member"]["id"]


@pytest.mark.django_db
def test_owner_removes_member(project_fixture, other_user_fixture, auth_client):
    create = auth_client.post(URL(project_fixture.id), {"muid": other_user_fixture.muid}, format="json")
    member_id = create.json()["response"]["Member"]["id"]
    delete = auth_client.delete(ITEM_URL(project_fixture.id, member_id))
    assert delete.status_code == 200


@pytest.mark.django_db
def test_list_members_includes_linked_and_external(project_fixture, other_user_fixture, auth_client):
    auth_client.post(URL(project_fixture.id), {"muid": other_user_fixture.muid}, format="json")
    auth_client.post(URL(project_fixture.id), {"external_name": "Jane"}, format="json")
    resp = auth_client.get(URL(project_fixture.id))
    assert resp.status_code == 200
    members = resp.json()["response"]["Members"]
    assert len(members) == 2
    is_linked = {m["is_linked"] for m in members}
    assert is_linked == {True, False}
