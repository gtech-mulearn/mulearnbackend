import pytest
from rest_framework.test import APIClient
from db.user import User
from db.projects import Project


@pytest.fixture
def user_fixture(db):
    return User.objects.create(id="u-owner-1", muid="MU-OWNER", full_name="Owner User", email="owner@test.com")


@pytest.fixture
def other_user_fixture(db):
    return User.objects.create(id="u-other-1", muid="MU-OTHER", full_name="Other User", email="other@test.com")


@pytest.fixture
def auth_client(user_fixture):
    client = APIClient()
    client.force_authenticate(user=user_fixture)
    return client


@pytest.fixture
def other_auth_client(other_user_fixture):
    client = APIClient()
    client.force_authenticate(user=other_user_fixture)
    return client


@pytest.fixture
def project_fixture(user_fixture):
    return Project.objects.create(
        id="p-1", title="Demo", description="d",
        status="published", created_by=user_fixture, updated_by=user_fixture,
    )


@pytest.fixture
def skill_fixture(user_fixture):
    from db.skill import Skill
    return Skill.objects.create(id="sk-1", name="Python", code="PY",
                                created_by=user_fixture, updated_by=user_fixture)
