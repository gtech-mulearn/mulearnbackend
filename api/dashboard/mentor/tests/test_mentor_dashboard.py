import pytest
from django.urls import reverse
from rest_framework import status
from db.user import User, UserMentor
from db.organization import Organization, UserOrganizationLink
from db.task import InterestGroup, UserIgLink

@pytest.fixture
def mentor_setup():
    mentor_user = User.objects.create(id="mentor1", full_name="Test Mentor", email="mentor@test.com", muid="mentor@mulearn")
    student_user = User.objects.create(id="student1", full_name="Test Student", email="student@test.com", muid="student@mulearn")
    unrelated_user = User.objects.create(id="unrelated1", full_name="Unrelated", email="unrelated@test.com", muid="unrelated@mulearn")

    campus = Organization.objects.create(id="campus1", title="Test Campus", code="TC", org_type="College")
    company = Organization.objects.create(id="company1", title="Test Company", code="TCOMP", org_type="Company")
    ig = InterestGroup.objects.create(id="ig1", name="Test IG", code="TIG")

    UserMentor.objects.create(user=mentor_user, mentor_tier=UserMentor.MentorTier.CAMPUS_MENTOR, org=campus, status=UserMentor.Status.APPROVED, updated_by=mentor_user, created_by=mentor_user)
    UserMentor.objects.create(user=mentor_user, mentor_tier=UserMentor.MentorTier.COMPANY_MENTOR, org=company, status=UserMentor.Status.APPROVED, updated_by=mentor_user, created_by=mentor_user)
    UserIgLink.objects.create(user=mentor_user, ig=ig, assignment_type=UserIgLink.AssignmentType.MENTOR, created_by=mentor_user)

    UserOrganizationLink.objects.create(user=student_user, org=campus, verified=True, created_by=student_user)

    return {"mentor": mentor_user, "unrelated": unrelated_user}

@pytest.mark.django_db
def test_dashboard_multi_scope_returns_array(client, mentor_setup):
    url = reverse('mentor-overview')
    client.force_login(mentor_setup["mentor"])
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    scopes = response.json()['response']['scopes']
    
    assert len(scopes) == 3
    scope_types = [s['scope_type'] for s in scopes]
    assert "CAMPUS_MENTOR" in scope_types
    assert "COMPANY_MENTOR" in scope_types
    assert "IG_MENTOR" in scope_types

    campus_scope = next(s for s in scopes if s['scope_type'] == "CAMPUS_MENTOR")
    assert campus_scope['metrics']['total_learners'] == 1

@pytest.mark.django_db
def test_dashboard_bola_mitigation(client, mentor_setup):
    other_org = Organization.objects.create(id="other_org", title="Other Org", code="OO", org_type="College")
    UserOrganizationLink.objects.create(user=mentor_setup["unrelated"], org=other_org, verified=True, created_by=mentor_setup["unrelated"])
    
    url = reverse('mentor-overview') + f"?org_id={other_org.id}"
    client.force_login(mentor_setup["mentor"])
    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    scopes = response.json()['response']['scopes']
    
    for s in scopes:
        assert s['scope_id'] != other_org.id

@pytest.mark.django_db
def test_unauthorized_dashboard_access(client, mentor_setup):
    url = reverse('mentor-overview')
    client.force_login(mentor_setup["unrelated"])
    response = client.get(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN
