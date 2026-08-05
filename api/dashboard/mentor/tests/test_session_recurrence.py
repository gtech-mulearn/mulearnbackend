import pytest
from datetime import datetime, date, timedelta
from django.utils import timezone
from db.user import User, UserRoleLink, Role
from db.mentor import MentorshipSession
from utils.types import RoleType
from api.dashboard.mentor.session_recurrence_helper import generate_recurring_sessions
import uuid

@pytest.fixture
def mentor_user():
    user = User.objects.create(id=str(uuid.uuid4()), full_name="Mentor Test", email="m@t.com", muid="m@mu")
    return user

@pytest.mark.django_db
def test_create_weekly_series(mentor_user):
    start_time = timezone.now() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    
    parent_session = MentorshipSession.objects.create(
        id=str(uuid.uuid4()),
        session_type=MentorshipSession.SessionType.IG_SESSION,
        entity_id="ig1",
        title="Weekly Meeting",
        mode=MentorshipSession.Mode.ONLINE,
        starts_at=start_time,
        ends_at=end_time,
        status=MentorshipSession.Status.PENDING_APPROVAL,
        created_by=mentor_user,
        updated_by=mentor_user,
        
        is_recurring=True,
        recurrence_type=MentorshipSession.RecurrenceType.WEEKLY,
        recurrence_interval=1,
        recurrence_end_date=(start_time + timedelta(days=30)).date()
    )
    
    children, was_truncated = generate_recurring_sessions(parent_session)

    # 30 days = 4 weeks (4 child sessions + 1 parent)
    assert len(children) == 4
    assert was_truncated is False
    for child in children:
        assert child.parent_session_id == parent_session.id
        assert child.is_recurring is True
        assert child.recurrence_type == MentorshipSession.RecurrenceType.WEEKLY

@pytest.mark.django_db
def test_recurrence_hard_cap(mentor_user):
    start_time = timezone.now() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    
    parent_session = MentorshipSession.objects.create(
        id=str(uuid.uuid4()),
        session_type=MentorshipSession.SessionType.IG_SESSION,
        entity_id="ig1",
        title="Daily Meeting",
        mode=MentorshipSession.Mode.ONLINE,
        starts_at=start_time,
        ends_at=end_time,
        status=MentorshipSession.Status.PENDING_APPROVAL,
        created_by=mentor_user,
        updated_by=mentor_user,
        
        is_recurring=True,
        recurrence_type=MentorshipSession.RecurrenceType.DAILY,
        recurrence_interval=1,
        # 5 years ahead
        recurrence_end_date=(start_time + timedelta(days=365*5)).date()
    )
    
    children, was_truncated = generate_recurring_sessions(parent_session)

    # Should be capped at 50
    assert len(children) == 50
    assert was_truncated is True

@pytest.mark.django_db
def test_monthly_edge_case(mentor_user):
    # Jan 31st
    start_time = datetime(2026, 1, 31, 10, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(hours=1)
    
    parent_session = MentorshipSession.objects.create(
        id=str(uuid.uuid4()),
        session_type=MentorshipSession.SessionType.IG_SESSION,
        entity_id="ig1",
        title="Monthly Meeting",
        mode=MentorshipSession.Mode.ONLINE,
        starts_at=start_time,
        ends_at=end_time,
        status=MentorshipSession.Status.PENDING_APPROVAL,
        created_by=mentor_user,
        updated_by=mentor_user,
        
        is_recurring=True,
        recurrence_type=MentorshipSession.RecurrenceType.MONTHLY,
        recurrence_interval=1,
        recurrence_end_date=date(2026, 3, 5)
    )
    
    children, was_truncated = generate_recurring_sessions(parent_session)

    assert len(children) == 1
    assert was_truncated is False
    # First generated session should be Feb 28th 2026
    assert children[0].starts_at.month == 2
    assert children[0].starts_at.day == 28
