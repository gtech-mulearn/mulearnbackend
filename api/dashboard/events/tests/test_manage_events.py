import pytest
from rest_framework.test import APIClient
from db.events import Event
from db.organization import Organization
from db.user import User, Role
from utils.types import RoleType
from unittest.mock import patch
from db.task import Category

@pytest.fixture
def user_fixture(db):
    return User.objects.create(id="u-event-owner", muid="MU-EVENT-OWNER", full_name="Event Owner User", email="owner2@test.com")

@pytest.fixture
def auth_client(user_fixture):
    client = APIClient()
    client.force_authenticate(user=user_fixture)
    return client

@pytest.fixture
def category_fixture(db):
    return Category.objects.create(id="cat-event", title="Event Cat", entity_type=Category.EntityType.EVENT)

@pytest.fixture
def campus_fixture(db):
    return Organization.objects.create(id="org-campus-1", title="Campus 1", org_type=Organization.OrganizationType.COLLEGE.value, code="CMP1")

@pytest.fixture
def other_campus_fixture(db):
    return Organization.objects.create(id="org-campus-2", title="Campus 2", org_type=Organization.OrganizationType.COLLEGE.value, code="CMP2")

@pytest.mark.django_db
@patch('utils.permission.JWTUtils.fetch_role')
@patch('utils.permission.JWTUtils.fetch_user_id')
@patch('utils.permission.CustomizePermission.has_permission')
def test_campus_scope_validation_success(mock_has_perm, mock_fetch_user_id, mock_fetch_role, auth_client, user_fixture, campus_fixture, category_fixture):
    mock_has_perm.return_value = True
    mock_fetch_user_id.return_value = user_fixture.id
    mock_fetch_role.return_value = [RoleType.CAMPUS_LEAD.value]

    payload = {
        "title": "Campus Event",
        "description": "Event for our campus",
        "start_datetime": "2030-01-01T10:00:00Z",
        "end_datetime": "2030-01-01T12:00:00Z",
        "venue_type": Event.VenueType.ONLINE.value,
        "organiser_type": Event.OrganiserType.CAMPUS.value,
        "organiser_org": campus_fixture.id,
        "scope": Event.Scope.CAMPUS.value,
        "scope_org": campus_fixture.id,
    }
    
    resp = auth_client.post("/api/v1/dashboard/events/manage/", data=payload, format="json")
    
    # Should be 200 OK since orgs match
    assert resp.status_code == 200
    assert resp.json().get("statusCode") == 200

@pytest.mark.django_db
@patch('utils.permission.JWTUtils.fetch_role')
@patch('utils.permission.JWTUtils.fetch_user_id')
@patch('utils.permission.CustomizePermission.has_permission')
def test_campus_scope_validation_failure(mock_has_perm, mock_fetch_user_id, mock_fetch_role, auth_client, user_fixture, campus_fixture, other_campus_fixture, category_fixture):
    mock_has_perm.return_value = True
    mock_fetch_user_id.return_value = user_fixture.id
    mock_fetch_role.return_value = [RoleType.CAMPUS_LEAD.value]

    payload = {
        "title": "Cross Campus Event",
        "description": "Trying to create for another campus",
        "start_datetime": "2030-01-01T10:00:00Z",
        "end_datetime": "2030-01-01T12:00:00Z",
        "venue_type": Event.VenueType.ONLINE.value,
        "organiser_type": Event.OrganiserType.CAMPUS.value,
        "organiser_org": campus_fixture.id,
        "scope": Event.Scope.CAMPUS.value,
        "scope_org": other_campus_fixture.id,  # Mismatch!
    }
    
    resp = auth_client.post("/api/v1/dashboard/events/manage/", data=payload, format="json")
    
    # Should fail with 400 Bad Request since orgs mismatch
    assert resp.status_code == 400
    assert "scope_org" in resp.json()["message"]["general"]
    assert resp.json()["message"]["general"]["scope_org"][0] == "Campus scoped events can only target the organiser's own campus."
