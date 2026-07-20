import pytest
from datetime import timedelta
import jwt
from django.conf import settings
from rest_framework.test import APIClient
from db.user import User
from db.task import InterestGroup
from db.learning_circle import LearningCircle, UserCircleLink
from utils.utils import DateTimeUtils

def get_auth_token(user_id):
    expiry_dt = DateTimeUtils.get_current_utc_time() + timedelta(days=1)
    expiry_str = expiry_dt.strftime("%Y-%m-%d %H:%M:%S%z")
    payload = {
        "id": user_id,
        "expiry": expiry_str,
        "roles": ["Student"]
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return f"Bearer {token}"

@pytest.fixture
def user_fixture(db):
    return User.objects.create(
        id="user-1",
        muid="USER1@mulearn",
        full_name="Invited User",
        email="invited@test.com",
    )

@pytest.fixture
def inviter_fixture(db):
    return User.objects.create(
        id="user-2",
        muid="USER2@mulearn",
        full_name="Inviter User",
        email="inviter@test.com",
    )

@pytest.fixture
def ig_fixture(db, inviter_fixture):
    return InterestGroup.objects.create(
        id="ig-1",
        name="Python",
        code="PY",
        icon="py",
        created_by=inviter_fixture,
        updated_by=inviter_fixture,
    )

@pytest.fixture
def circle_fixture(db, ig_fixture, inviter_fixture):
    return LearningCircle.objects.create(
        id="circle-1",
        ig=ig_fixture,
        title="Python Circle",
        created_by=inviter_fixture,
    )

@pytest.fixture
def invite_link_fixture(db, user_fixture, circle_fixture, inviter_fixture):
    return UserCircleLink.objects.create(
        id="link-1234",
        user=user_fixture,
        circle=circle_fixture,
        lead=False,
        is_invited=True,
        invited_by=inviter_fixture,
        accepted=None,
    )

@pytest.fixture
def auth_client(user_fixture):
    client = APIClient()
    token = get_auth_token(user_fixture.id)
    client.credentials(HTTP_AUTHORIZATION=token)
    return client

@pytest.mark.django_db
def test_accept_invite_via_body(auth_client, invite_link_fixture):
    url = "/api/v1/dashboard/learningcircle/invite/status/"
    payload = {
        "link_id": invite_link_fixture.id,
        "action": "accept"
    }
    response = auth_client.post(url, payload, format="json")
    assert response.status_code == 200
    assert response.json()["message"]["general"][0] == "Invitation accepted successfully"
    
    # Verify DB update
    invite_link_fixture.refresh_from_db()
    assert invite_link_fixture.accepted is True
    assert invite_link_fixture.accepted_at is not None

@pytest.mark.django_db
def test_reject_invite_via_body(auth_client, invite_link_fixture):
    url = "/api/v1/dashboard/learningcircle/invite/status/"
    payload = {
        "link_id": invite_link_fixture.id,
        "action": "reject"
    }
    response = auth_client.post(url, payload, format="json")
    assert response.status_code == 200
    assert response.json()["message"]["general"][0] == "Invitation rejected successfully"
    
    # Verify DB update
    invite_link_fixture.refresh_from_db()
    assert invite_link_fixture.accepted is False
    assert invite_link_fixture.accepted_at is None

@pytest.mark.django_db
def test_accept_invite_via_url(auth_client, invite_link_fixture):
    url = f"/api/v1/dashboard/learningcircle/invite/status/{invite_link_fixture.id}/"
    payload = {
        "action": "accept"
    }
    response = auth_client.post(url, payload, format="json")
    assert response.status_code == 200
    assert response.json()["message"]["general"][0] == "Invitation accepted successfully"
    
    # Verify DB update
    invite_link_fixture.refresh_from_db()
    assert invite_link_fixture.accepted is True
    assert invite_link_fixture.accepted_at is not None

@pytest.mark.django_db
def test_reject_invite_via_url(auth_client, invite_link_fixture):
    url = f"/api/v1/dashboard/learningcircle/invite/status/{invite_link_fixture.id}/"
    payload = {
        "action": "reject"
    }
    response = auth_client.post(url, payload, format="json")
    assert response.status_code == 200
    assert response.json()["message"]["general"][0] == "Invitation rejected successfully"
    
    # Verify DB update
    invite_link_fixture.refresh_from_db()
    assert invite_link_fixture.accepted is False
    assert invite_link_fixture.accepted_at is None

@pytest.mark.django_db
def test_invite_status_missing_link_id(auth_client):
    url = "/api/v1/dashboard/learningcircle/invite/status/"
    payload = {
        "action": "accept"
    }
    response = auth_client.post(url, payload, format="json")
    assert response.status_code == 400
    assert response.json()["message"]["general"][0] == "link_id is required"

@pytest.mark.django_db
def test_invite_status_invalid_link_id(auth_client):
    url = "/api/v1/dashboard/learningcircle/invite/status/"
    payload = {
        "link_id": "non-existent-link-id",
        "action": "accept"
    }
    response = auth_client.post(url, payload, format="json")
    assert response.status_code == 400
    assert response.json()["message"]["general"][0] == "Invitation not found"
