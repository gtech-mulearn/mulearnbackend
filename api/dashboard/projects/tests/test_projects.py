import pytest
from rest_framework.test import APIClient
from db.projects import Project


@pytest.fixture
def draft_project(user_fixture):
    return Project.objects.create(id="p-draft", title="Draft", description="d",
                                  status="draft", created_by=user_fixture, updated_by=user_fixture)


@pytest.fixture
def other_project(other_user_fixture):
    return Project.objects.create(id="p-other", title="Other", description="o",
                                  status="published", created_by=other_user_fixture, updated_by=other_user_fixture)


@pytest.mark.django_db
def test_list_by_muid_owner_sees_all_statuses(auth_client, user_fixture, project_fixture, draft_project):
    resp = auth_client.get(f"/api/v1/dashboard/projects/?muid={user_fixture.muid}")
    ids = [p["id"] for p in resp.json()["response"]["Projects"]]
    assert project_fixture.id in ids
    assert draft_project.id in ids


@pytest.mark.django_db
def test_list_by_muid_public_viewer_only_sees_published(other_auth_client, user_fixture, project_fixture, draft_project):
    resp = other_auth_client.get(f"/api/v1/dashboard/projects/?muid={user_fixture.muid}")
    ids = [p["id"] for p in resp.json()["response"]["Projects"]]
    assert project_fixture.id in ids
    assert draft_project.id not in ids


@pytest.mark.django_db
def test_list_by_muid_includes_member_of_projects(auth_client, other_auth_client, other_user_fixture, project_fixture):
    auth_client.post(f"/api/v1/dashboard/projects/{project_fixture.id}/members/",
                     {"muid": other_user_fixture.muid}, format="json")
    resp = other_auth_client.get(f"/api/v1/dashboard/projects/?muid={other_user_fixture.muid}")
    ids = [p["id"] for p in resp.json()["response"]["Projects"]]
    assert project_fixture.id in ids


@pytest.mark.django_db
def test_status_filter_explicit(auth_client, user_fixture, project_fixture, draft_project):
    resp = auth_client.get(f"/api/v1/dashboard/projects/?muid={user_fixture.muid}&status=draft")
    ids = [p["id"] for p in resp.json()["response"]["Projects"]]
    assert draft_project.id in ids
    assert project_fixture.id not in ids
