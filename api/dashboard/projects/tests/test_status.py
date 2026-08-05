import pytest


@pytest.mark.django_db
def test_owner_can_publish_draft(auth_client, project_fixture):
    project_fixture.status = "draft"
    project_fixture.save()
    resp = auth_client.patch(f"/api/v1/dashboard/projects/{project_fixture.id}/status/",
                             {"status": "published"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["response"]["Project"]["status"] == "published"


@pytest.mark.django_db
def test_non_owner_cannot_change_status(other_auth_client, project_fixture):
    resp = other_auth_client.patch(f"/api/v1/dashboard/projects/{project_fixture.id}/status/",
                                   {"status": "archived"}, format="json")
    assert resp.status_code in (400, 403)


@pytest.mark.django_db
def test_invalid_status_rejected(auth_client, project_fixture):
    resp = auth_client.patch(f"/api/v1/dashboard/projects/{project_fixture.id}/status/",
                             {"status": "deleted"}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_create_project_persists_links_and_skills(auth_client, skill_fixture):
    import json
    resp = auth_client.post("/api/v1/dashboard/projects/", {
        "title": "X", "description": "y", "status": "published",
        "links_json": json.dumps([{"label": "GitHub", "url": "https://github.com/x/y"},
                                  {"label": "Demo", "url": "https://demo.example"}]),
        "skill_ids_json": json.dumps([skill_fixture.id]),
    }, format="multipart")
    assert resp.status_code == 200, resp.json()
    body = resp.json()["response"]["Project"]
    assert len(body["links"]) == 2
    assert body["skills"][0]["id"] == skill_fixture.id
