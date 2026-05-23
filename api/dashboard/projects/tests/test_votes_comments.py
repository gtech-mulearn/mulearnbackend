import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_vote_requires_authentication(project_fixture):
    client = APIClient()
    resp = client.post("/api/v1/dashboard/projects/vote/",
                       {"vote": "upvote", "project": project_fixture.id}, format="json")
    assert resp.status_code in (401, 403), resp.json()


@pytest.mark.django_db
def test_vote_records_user(project_fixture, auth_client, user_fixture):
    resp = auth_client.post("/api/v1/dashboard/projects/vote/",
                            {"vote": "upvote", "project": project_fixture.id}, format="json")
    assert resp.status_code == 200, resp.json()
    body = resp.json()["response"]["Vote"]
    assert body["user_id"] == user_fixture.id
    assert body["vote"] == "upvote"


@pytest.mark.django_db
def test_vote_is_unique_per_user_project(project_fixture, auth_client):
    auth_client.post("/api/v1/dashboard/projects/vote/",
                     {"vote": "upvote", "project": project_fixture.id}, format="json")
    second = auth_client.post("/api/v1/dashboard/projects/vote/",
                              {"vote": "downvote", "project": project_fixture.id}, format="json")
    assert second.status_code == 200
    assert second.json()["response"]["Vote"]["vote"] == "downvote"


@pytest.mark.django_db
def test_comment_requires_authentication(project_fixture):
    client = APIClient()
    resp = client.post("/api/v1/dashboard/projects/comment/",
                       {"comment": "hi", "project": project_fixture.id}, format="json")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_comment_records_user(project_fixture, auth_client, user_fixture):
    resp = auth_client.post("/api/v1/dashboard/projects/comment/",
                            {"comment": "great", "project": project_fixture.id}, format="json")
    assert resp.status_code == 200
    assert resp.json()["response"]["Comment"]["user_id"] == user_fixture.id
