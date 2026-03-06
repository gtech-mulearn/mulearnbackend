from db.organization import UserOrganizationLink
from utils.types import OrganizationType


def get_user_college_link(user_id):
    return UserOrganizationLink.objects.filter(
        user_id=user_id,
        org__org_type=OrganizationType.COLLEGE.value
    ).first()


def validate_campus_member(user_id, org):
    return UserOrganizationLink.objects.filter(
        user_id=user_id,
        org=org,
        org__org_type=OrganizationType.COLLEGE.value,
        is_alumni=False,
    ).first()


def get_campus_events_qs(org):
    from api.dashboard.events.serializers import get_live_events
    from db.events import Event
    base = get_live_events()
    return (
        base.filter(scope=Event.Scope.CAMPUS, scope_org=org)
        | base.filter(scope=Event.Scope.CAMPUS_IG, scope_org=org)
    ).distinct()