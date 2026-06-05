from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from db.mentor import MentorshipSession
import uuid

MAX_RECURRENCE_COUNT = 50

def generate_recurring_sessions(parent_session: MentorshipSession):
    """
    Generate future MentorshipSession instances based on the recurrence rules
    of the given parent_session.
    
    Returns a list of created child sessions.
    """
    if not parent_session.is_recurring:
        return []

    if not parent_session.recurrence_type or not parent_session.recurrence_interval or not parent_session.recurrence_end_date:
        return []

    child_sessions = []
    
    # Calculate duration of the session
    duration = parent_session.ends_at - parent_session.starts_at
    
    current_start = parent_session.starts_at
    end_date = parent_session.recurrence_end_date
    interval = parent_session.recurrence_interval
    r_type = parent_session.recurrence_type

    # Start loop
    count = 0
    while count < MAX_RECURRENCE_COUNT:
        if r_type == MentorshipSession.RecurrenceType.DAILY:
            current_start += timedelta(days=interval)
        elif r_type == MentorshipSession.RecurrenceType.WEEKLY:
            current_start += timedelta(weeks=interval)
        elif r_type == MentorshipSession.RecurrenceType.MONTHLY:
            current_start += relativedelta(months=interval)
        else:
            break

        # Check if we exceeded the end date
        # We compare the date part only as recurrence_end_date is a DateField
        if current_start.date() > end_date:
            break

        current_end = current_start + duration

        # Create child instance
        child_session = MentorshipSession(
            id=str(uuid.uuid4()),
            session_type=parent_session.session_type,
            entity_id=parent_session.entity_id,
            title=parent_session.title,
            description=parent_session.description,
            mode=parent_session.mode,
            starts_at=current_start,
            ends_at=current_end,
            meeting_link=parent_session.meeting_link,
            venue=parent_session.venue,
            status=parent_session.status,
            max_participants=parent_session.max_participants,
            is_deleted=parent_session.is_deleted,
            
            is_recurring=True,
            recurrence_type=parent_session.recurrence_type,
            recurrence_interval=parent_session.recurrence_interval,
            recurrence_end_date=parent_session.recurrence_end_date,
            parent_session_id=parent_session.id,
            
            created_by_id=parent_session.created_by_id,
            updated_by_id=parent_session.updated_by_id,
            # We don't auto-approve children if parent is pending, but since parent just got created, status is PENDING_APPROVAL.
        )
        child_sessions.append(child_session)
        count += 1

    if child_sessions:
        MentorshipSession.objects.bulk_create(child_sessions)

    return child_sessions
