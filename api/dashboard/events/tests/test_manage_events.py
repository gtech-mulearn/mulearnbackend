import os
from io import BytesIO

import pytest
from django.conf import settings
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


@pytest.mark.django_db
@patch('api.dashboard.events.manage_views._resolve_publish_authority')
@patch('api.dashboard.events.event_image_utils.save_uploaded_event_image')
@patch('utils.permission.JWTUtils.fetch_role')
@patch('utils.permission.JWTUtils.fetch_user_id')
@patch('utils.permission.CustomizePermission.has_permission')
def test_failed_revival_reschedule_rolls_back_fields_status_and_media(
    mock_has_perm, mock_fetch_user_id, mock_fetch_role,
    mock_save_upload, mock_resolve_authority,
    auth_client, user_fixture, campus_fixture, category_fixture,
):
    """A revival reschedule (completed event pushed back into the future)
    that fails mid-transaction must leave the event's fields, its lifecycle
    status, and any newly-written cover/banner file exactly as they were --
    not a mix of the old status with the new dates, and not an orphaned
    file on disk. Regression test for the non-atomic reschedule + orphaned
    media bugs fixed in ManageEventDetailAPI._update.
    """
    mock_has_perm.return_value = True
    mock_fetch_user_id.return_value = user_fixture.id
    mock_fetch_role.return_value = [RoleType.CAMPUS_LEAD.value]

    event = Event.objects.create(
        id="evt-rollback-1",
        title="Old Workshop",
        slug="old-workshop-rollback",
        description="A workshop that already happened",
        category=category_fixture,
        status=Event.Status.COMPLETED,
        start_datetime="2020-01-01T10:00:00Z",
        end_datetime="2020-01-01T12:00:00Z",
        venue_type=Event.VenueType.ONLINE,
        scope=Event.Scope.CAMPUS,
        scope_org=campus_fixture,
        organiser_type=Event.OrganiserType.CAMPUS,
        organiser_org=campus_fixture,
        event_scope=Event.EventScope.CODER,
        created_by=user_fixture,
        updated_by=user_fixture,
    )

    # Simulate what save_uploaded_event_image would have already written to
    # disk by the time the DB write is attempted.
    new_rel_path = "events/covers/rollback-test.png"
    abs_path = os.path.join(settings.MEDIA_ROOT, new_rel_path.replace('/', os.sep))
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as f:
        f.write(b"fake-png-bytes")
    mock_save_upload.return_value = (new_rel_path, None)

    # Force the mid-transaction authority check to blow up -- stands in for
    # any failure between the field save and the status-resettlement save.
    mock_resolve_authority.side_effect = RuntimeError("boom")

    fake_file = BytesIO(b"fake-png-bytes")
    fake_file.name = "cover.png"

    try:
        auth_client.patch(
            f"/api/v1/dashboard/events/manage/{event.id}/",
            data={
                "start_datetime": "2099-01-01T10:00:00Z",
                "end_datetime": "2099-01-01T12:00:00Z",
                "cover_image": fake_file,
            },
            format="multipart",
        )
    except RuntimeError:
        pass  # the forced failure is allowed to surface as a 500

    event.refresh_from_db()
    assert event.status == Event.Status.COMPLETED
    assert event.start_datetime.year == 2020
    assert event.cover_image != new_rel_path

    assert not os.path.isfile(abs_path), "orphaned cover image was not cleaned up on rollback"
