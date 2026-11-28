"""
Team membership and scoping for the intern module.

Rows in user_intern_team_link: one per stint in a team, never reopened.
- join_date / end_date: the tenure, set by the Admin or Lead who adds the intern
  (join_date can't be in the past). While the row is current, end_date is the
  planned end; once ended (reassign or deactivation) it is the actual last day.
- current (is_current=True): the person's team now.
    - ACTIVE or ON_LEAVE while today is inside the tenure;
    - before join_date: added but not started (no access yet);
    - after end_date: the daily tenure job sets INACTIVE (roles kept) and notifies
      the team's Lead(s) and Admins; an Admin extends the end date (back to ACTIVE)
      or deactivates them.
- ended (is_current=False): INACTIVE. Deactivated (roles removed) or reassigned
  (a new current row exists in the new team); exit_reason says which.

At most one current row per person. The DB index isn't unique (0/1 values), so
every helper that creates or ends a row locks all of the person's rows first.

A member of a team is someone whose current row is in that team and who holds
Intern or Intern Lead. A working member is also inside their tenure today and not
INACTIVE: only they can submit timesheets, leave and reviews, and only a working
Lead has Lead access. Records (timesheets, monthly reviews, tasks, leave) store the
team_id they were created in.

Status: only approved leave changes it now (ON_LEAVE, then back to the earlier
status), plus the tenure end (INACTIVE). Manual status changes are paused. On a
reassign the status moves with the person.

History: every Admin/Lead action on an intern (onboard, Lead added/removed, end
date changed, deactivate, reassign) writes one intern_history row in the same
transaction as the change (record_history). Cron events (tenure end) are recorded
as the system admin with action_by_role SYSTEM.

Scoping:
- scope_people(): rows a caller may manage. Admin: every current row. Lead:
  current rows in their own team.
- scope_history(): rows a caller may read, ended ones included.
- scope_records(): records a caller may read, by the record's team_id.
"""
from datetime import date

from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from db.intern import InternHistory, InternLeaveRequest, InternTeam, UserInternTeamLink
from db.user import Role, User, UserRoleLink
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils
from utils.types import (
    InternActorRole, InternHistoryAction, InternHistoryEntity, InternLeaveStatus, InternStatus, RoleType,
)

INTERN_ROLE = RoleType.INTERN.value
LEAD_ROLE = RoleType.INTERN_LEAD.value
MEMBER_ROLES = [INTERN_ROLE, LEAD_ROLE]
ACTIVE = InternStatus.ACTIVE.value
INACTIVE = InternStatus.INACTIVE.value
ON_LEAVE = InternStatus.ON_LEAVE.value
EXIT_REASON_ROLE_REMOVED = "Intern role removed"


class OnboardError(Exception):
    """Raised by the membership helpers with a message that is safe to show the caller."""


# ----------------------------------------------------------------- building blocks

def holds_role_subquery(titles, user_ref='user_id'):
    return Exists(
        UserRoleLink.objects.filter(user_id=OuterRef(user_ref), role__title__in=titles)
    )


def current_rows(queryset):
    """Keeps current membership rows (drops ended history rows)."""
    return queryset.filter(is_current=True)


def members_only(queryset):
    """Keeps current rows whose person holds Intern or Intern Lead."""
    return current_rows(queryset).filter(holds_role_subquery(MEMBER_ROLES))


def ist_today():
    """Today's date in IST: every tenure date is compared with this."""
    return DateTimeUtils.get_ist_today()


def in_tenure(queryset, on=None):
    """Keeps rows whose tenure covers `on` (default today): join_date <= day <= end_date."""
    day = on or ist_today()
    return queryset.filter(join_date__lte=day, end_date__gte=day)


def working_members(queryset):
    """Current members inside their tenure today who aren't INACTIVE (ON_LEAVE included)."""
    return in_tenure(members_only(queryset)).exclude(intern_status=INACTIVE)


def tenure_state(link, today=None):
    """UPCOMING (before join_date), ACTIVE (inside the tenure) or ENDED (after end_date)."""
    today = today or ist_today()
    if link.join_date and link.join_date > today:
        return 'UPCOMING'
    if link.end_date and link.end_date < today:
        return 'ENDED'
    return 'ACTIVE'


def working_membership_error(link, today=None):
    """
    Why the person in current row `link` can't submit timesheets, leave or reviews
    right now, or None if they can. Doesn't wait for the nightly tenure job.
    """
    if link is None:
        return "Not an active intern."
    state = tenure_state(link, today)
    if state == 'UPCOMING':
        return f"Your internship starts on {link.join_date:%d %b %Y}."
    if state == 'ENDED':
        return f"Your internship ended on {link.end_date:%d %b %Y}."
    if link.intern_status == INACTIVE:
        return "Not an active intern."
    return None


def parse_date(value):
    """A date from a request body or an Excel cell (date, datetime or 'YYYY-MM-DD'), or None."""
    from datetime import datetime
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None


def validate_tenure(join_date, end_date, today=None):
    """join_date not in the past; end_date on or after join_date. Raises OnboardError."""
    today = today or ist_today()
    if not isinstance(join_date, date) or not isinstance(end_date, date):
        raise OnboardError("join_date and end_date are required (YYYY-MM-DD).")
    if join_date < today:
        raise OnboardError("join_date can't be in the past.")
    if end_date < join_date:
        raise OnboardError("end_date can't be before join_date.")


def active_teams():
    """Teams that can be listed, onboarded into or reassigned into."""
    return InternTeam.objects.filter(is_active=True)


def current_membership(user_id, lock=False):
    """
    The person's current row (with its team), or None. With lock=True, the user row
    and every membership row of the person are locked (SELECT ... FOR UPDATE) so no
    other request can add or end a row for them until the transaction ends, even for
    someone who has no membership rows yet. Call inside transaction.atomic().
    """
    if not lock:
        return (
            UserInternTeamLink.objects.select_related('team')
            .filter(user_id=user_id, is_current=True).first()
        )
    lock_users([user_id])
    # No select_related under FOR UPDATE: it would also lock the joined team row.
    rows = list(UserInternTeamLink.objects.select_for_update().filter(user_id=user_id))
    link = next((row for row in rows if row.is_current), None)
    if link:
        link.team = InternTeam.objects.get(id=link.team_id)
    return link


def lock_users(user_ids):
    """
    Locks the user rows, in id order (so two bulk operations can't deadlock). This
    is the lock that serialises membership changes: FOR UPDATE on the membership
    table locks nothing for a person who has no rows yet, and its index isn't unique.
    """
    list(User.every.select_for_update().filter(id__in=sorted(set(user_ids))).order_by('id').values_list('id', flat=True))


def covering_membership(user_id, day):
    """
    The membership row whose tenure covers `day` (the latest stint if two do, as on
    a reassign day), with its team, or None.
    """
    return (
        UserInternTeamLink.objects.select_related('team')
        .filter(user_id=user_id, join_date__lte=day, end_date__gte=day)
        .order_by('-join_date', '-is_current', '-created_at')
        .first()
    )


def inactive_by_choice(link):
    """
    True when a current row is INACTIVE because a Lead or Admin marked it (or
    because it was already INACTIVE when its tenure ended), not because the tenure
    ending itself made it INACTIVE.
    """
    if link.intern_status != INACTIVE:
        return False
    if tenure_state(link) != 'ENDED':
        return True
    end = link.end_date.isoformat()
    for old in InternHistory.objects.filter(
        entity_id=str(link.id), action=InternHistoryAction.TENURE_ENDED.value,
    ).values_list('old_data', flat=True):
        if (old or {}).get('end_date') == end:
            return old.get('status') == INACTIVE
    # No tenure-end record for this end date: it was INACTIVE before the job ran.
    return True


def timesheet_gate(link, user_id, entry_date):
    """
    (team_id, None) when the intern may submit or edit the timesheet for entry_date,
    else (None, message). `link` is their current row. The day must fall inside a
    tenure (so the last day's timesheet can still be entered the next day, but no
    day before they joined), and the entry belongs to the team that covered it.
    """
    if link is None:
        return None, "Not an active intern."
    if tenure_state(link) == 'UPCOMING':
        return None, f"Your internship starts on {link.join_date:%d %b %Y}."
    if inactive_by_choice(link):
        return None, "Not an active intern."
    row = covering_membership(user_id, entry_date)
    if row is None:
        if entry_date < link.join_date:
            return None, "You weren't in the program on that date."
        return None, f"Your internship ended on {link.end_date:%d %b %Y}."
    return row.team_id, None


def active_membership(user_id):
    """The current row if the person is an active intern (not INACTIVE, holds a role), else None."""
    return (
        UserInternTeamLink.objects.select_related('team')
        .filter(user_id=user_id, is_current=True).exclude(intern_status=INACTIVE)
        .filter(holds_role_subquery(MEMBER_ROLES))
        .first()
    )


def team_ref(team):
    """How a team is shown on a record: {id, name, code, is_active}, or None."""
    if team is None:
        return None
    return {"id": team.id, "name": team.name, "code": team.code, "is_active": team.is_active}


def user_ref(user):
    """How a person is shown on a record (e.g. who reviewed it): {id, full_name, muid}, or None."""
    if user is None:
        return None
    return {"id": user.id, "full_name": user.full_name, "muid": user.muid}


def is_admin(request):
    return RoleType.ADMIN.value in JWTUtils.fetch_role(request)


# ----------------------------------------------------------------- history

def actor_role(request):
    """action_by_role for intern_history: ADMIN or LEAD, from the caller's token."""
    return InternActorRole.ADMIN.value if is_admin(request) else InternActorRole.LEAD.value


def _history_row(action, link, actor_id, role, old=None, new=None, reason=None,
                 team_id=None, from_team_id=None):
    return InternHistory(
        entity_type=InternHistoryEntity.MEMBERSHIP.value,
        entity_id=str(link.id),
        action=action,
        user_id=link.user_id,
        team_id=team_id or link.team_id,
        from_team_id=from_team_id,
        old_data=old,
        new_data=new,
        reason=reason,
        action_by_id=actor_id,
        action_by_role=role,
    )


def record_history(action, link, actor_id, role, **kwargs):
    """Writes one intern_history row about membership `link`. Call inside the change's transaction."""
    _history_row(action, link, actor_id, role, **kwargs).save()


def system_history_row(action, link, **kwargs):
    """A history row for a cron event: no actor (action_by null), role SYSTEM."""
    return _history_row(action, link, None, InternActorRole.SYSTEM.value, **kwargs)


def _d(value):
    """Dates as text in history data."""
    return value.isoformat() if value else None


# ----------------------------------------------------------------- scoping

def caller_team_id(request):
    """
    The team a Lead manages: the team of their current row, but only while that
    row is inside its tenure, isn't INACTIVE, and the database (not just the token)
    still gives them Intern Lead. A removed, moved, finished or not-yet-started
    Lead's token reaches no team (or only their new one). None otherwise.
    """
    return (
        in_tenure(UserInternTeamLink.objects.filter(user_id=JWTUtils.fetch_user_id(request), is_current=True))
        .exclude(intern_status=INACTIVE)
        .filter(holds_role_subquery([LEAD_ROLE]))
        .values_list('team_id', flat=True)
        .first()
    )


def _lead_filter(queryset, request, team_field):
    if is_admin(request):
        return queryset
    team_id = caller_team_id(request)
    if not team_id:
        return queryset.none()
    return queryset.filter(**{team_field: team_id})


def scope_people(queryset, request):
    """Current membership rows the caller may manage (Admin: all; Lead: own team)."""
    return _lead_filter(current_rows(queryset), request, 'team_id')


def scope_history(queryset, request):
    """Membership rows, ended ones included, the caller may read (Admin: all; Lead: own team's)."""
    return _lead_filter(queryset, request, 'team_id')


def scope_records(queryset, request, team_field='team_id'):
    """
    Timesheets, monthly reviews, tasks or leave the caller may read: everything for
    an Admin; for a Lead, records created in their team, including those of people
    who have since moved to another team.
    """
    return _lead_filter(queryset, request, team_field)


def include_former(request):
    """True when the caller passed include_former=true (records of people who left the team)."""
    return request.query_params.get('include_former', '').lower() in ('true', '1')


def by_current_members(queryset, team_field='team_id', user_field='user_id'):
    """
    Keeps records whose person is still a current member of the team the record
    belongs to (members marked INACTIVE count; deactivated or moved people don't).
    The default for the management lists; include_former=true skips it.
    """
    return queryset.filter(Exists(
        UserInternTeamLink.objects.filter(
            user_id=OuterRef(user_field), team_id=OuterRef(team_field), is_current=True,
        )
    ))


# Kept for the endpoints not yet moved to the explicit names: current rows only.
scope_links = scope_people


def self_review_error(request, owner_user_id, what):
    """A Lead may not approve or verify their own record; Admins may. Returns a message or None."""
    if is_admin(request) or str(owner_user_id) != str(JWTUtils.fetch_user_id(request)):
        return None
    return f"You can't review your own {what}."


# ----------------------------------------------------------------- roles

def user_role_titles(user_id, titles=None):
    qs = UserRoleLink.objects.filter(user_id=user_id)
    if titles:
        qs = qs.filter(role__title__in=titles)
    return set(qs.values_list('role__title', flat=True))


def grant_roles(user_id, titles, actor_id):
    """Adds each role the user doesn't already hold. Idempotent."""
    held = user_role_titles(user_id, titles)
    for title in titles:
        if title in held:
            continue
        role = Role.objects.filter(title=title).first()
        if not role:
            raise OnboardError(f"Role '{title}' does not exist in the system.")
        UserRoleLink.objects.create(
            user_id=user_id, role=role, verified=True, is_active=True, created_by_id=actor_id
        )


def revoke_roles(user_id, titles):
    UserRoleLink.objects.filter(user_id=user_id, role__title__in=titles).delete()


# ----------------------------------------------------------------- membership changes

def _lock_active_team(team):
    """
    Locks `team`'s row (SELECT ... FOR UPDATE) and refuses it if it is inactive.
    Team deactivation locks the same row first, so it either sees the new current
    row (and refuses, or ends it) or runs after this transaction and this one sees
    is_active False. Call inside transaction.atomic(), after locking the person.
    """
    locked = InternTeam.objects.select_for_update().filter(id=team.id).first()
    if locked is None or not locked.is_active:
        raise OnboardError(f"{team.name} ({team.code}) is inactive. Activate it first.")


def end_membership(link, actor_id, exit_reason):
    """
    Closes a current row as history: INACTIVE, is_current False, exit_reason set.
    Roles are not touched (deactivation removes them separately; a reassign keeps
    them). Call inside transaction.atomic() with the person's rows locked.
    """
    link.intern_status = INACTIVE
    link.is_current = False
    link.exit_reason = exit_reason
    # end_date becomes the actual last day; a tenure that already ended keeps its date.
    today = ist_today()
    link.end_date = min(link.end_date, today) if link.end_date else today
    link.updated_by_id = actor_id
    link.save(update_fields=['intern_status', 'is_current', 'exit_reason', 'end_date', 'updated_by', 'updated_at'])


def _join_team(user_id, team, actor_id, join_date, end_date, status=ACTIVE, previous_status=None, status_reason=None):
    """
    Makes `team` the person's current team with a new row (rows are never
    reopened). Call with the person's rows locked and no current row left.
    """
    return UserInternTeamLink.objects.create(
        user_id=user_id, team=team, intern_status=status, previous_intern_status=previous_status,
        status_reason=status_reason, is_current=True, join_date=join_date, end_date=end_date,
        created_by_id=actor_id, updated_by_id=actor_id,
    )


def deactivate_membership(link, actor_id, exit_reason, *, role):
    """Removes the person from the program: ends `link`, removes Intern and Intern Lead, records it."""
    old_status = link.intern_status
    end_membership(link, actor_id, exit_reason)
    revoke_roles(link.user_id, MEMBER_ROLES)
    record_history(
        InternHistoryAction.DEACTIVATED.value, link, actor_id, role,
        old={"status": old_status, "is_current": True},
        new={"status": INACTIVE, "is_current": False},
        reason=exit_reason,
    )


def onboard_intern(user, team, actor_id, make_lead=False, *, role, join_date, end_date):
    """
    Puts `user` into `team` as an intern (and Lead when make_lead) with the tenure
    join_date..end_date. Call inside transaction.atomic().

    - `team` inactive, or bad dates (join_date in the past, end before join): refused.
    - No current row (new, or deactivated earlier): a new current ACTIVE row.
    - Current row with an intern role: refused (already an intern, not started yet,
      or tenure ended: extend it or deactivate them first).
    - Leftover current row without an intern role (from before deactivation ended
      rows): it is ended, then a new row is created.

    Records ONBOARDED with the dates (and LEAD_ADDED with make_lead).
    Returns (link, True).
    """
    validate_tenure(join_date, end_date)
    # The person first, then the team: the same order as import_intern and reassign.
    link = current_membership(user.id, lock=True)
    _lock_active_team(team)
    has_role = bool(user_role_titles(user.id, MEMBER_ROLES))

    if link and has_role:
        name = user.full_name or user.muid
        state = tenure_state(link)
        if state == 'ENDED':
            raise OnboardError(
                f"{name}'s internship in {link.team.name} ended on {link.end_date:%d %b %Y}. "
                "Extend it or deactivate them first."
            )
        if state == 'UPCOMING':
            raise OnboardError(f"{name} is already added to {link.team.name}, starting on {link.join_date:%d %b %Y}.")
        raise OnboardError(f"This user is already an active intern in {link.team.name}.")

    if link:
        end_membership(link, actor_id, link.exit_reason or EXIT_REASON_ROLE_REMOVED)
    new_link = _join_team(user.id, team, actor_id, join_date, end_date)
    was_lead = LEAD_ROLE in user_role_titles(user.id, [LEAD_ROLE])
    grant_roles(user.id, [INTERN_ROLE, LEAD_ROLE] if make_lead else [INTERN_ROLE], actor_id)
    record_history(
        InternHistoryAction.ONBOARDED.value, new_link, actor_id, role,
        new={"status": ACTIVE, "join_date": _d(join_date), "end_date": _d(end_date)},
    )
    if make_lead and not was_lead:
        record_history(
            InternHistoryAction.LEAD_ADDED.value, new_link, actor_id, role,
            old={"is_lead": False}, new={"is_lead": True},
        )
    return new_link, True


def move_membership(link, team, actor_id, *, role, end_date):
    """
    Reassigns the person in current row `link` to `team`. The old row ends today
    (INACTIVE, exit_reason "Reassigned to <team>"); a new current row starts today
    in `team` with the given end_date, and the person's status moves with them
    (ON_LEAVE stays ON_LEAVE, with the same earlier status). PENDING leave moves to
    `team`; timesheets, monthly reviews, tasks and decided leave stay with the old
    team. Roles are not touched, so a Lead now leads `team`. Refused for someone
    who hasn't started yet or whose tenure has ended.
    Records REASSIGNED (team_id = new team, from_team_id = old).
    Call inside transaction.atomic() with the person's rows locked.
    Returns (new_link, pending_leave_moved).
    """
    _lock_active_team(team)
    today = ist_today()
    state = tenure_state(link, today)
    if state == 'UPCOMING':
        raise OnboardError(f"This intern hasn't started yet (starts {link.join_date:%d %b %Y}).")
    if state == 'ENDED' or link.intern_status == INACTIVE:
        raise OnboardError(
            f"This intern's tenure ended on {link.end_date:%d %b %Y}. Extend it or deactivate them first."
        )
    if not isinstance(end_date, date) or end_date < today:
        raise OnboardError("end_date is required and can't be in the past.")

    old_team_id = link.team_id
    status, previous, reason = link.intern_status, link.previous_intern_status, link.status_reason
    exit_reason = f"Reassigned to {team.name}"
    end_membership(link, actor_id, exit_reason)
    new_link = _join_team(link.user_id, team, actor_id, today, end_date,
                          status=status, previous_status=previous, status_reason=reason)
    record_history(
        InternHistoryAction.REASSIGNED.value, new_link, actor_id, role,
        # Ids as text: a new row's id is still a uuid.UUID, which the JSON column can't store.
        old={"team_link_id": str(link.id), "status": status, "end_date": _d(link.end_date)},
        new={"team_link_id": str(new_link.id), "status": status, "join_date": _d(today), "end_date": _d(end_date)},
        reason=exit_reason, team_id=team.id, from_team_id=old_team_id,
    )
    # Leave from before teams has no team_id yet; a pending one is the person's too.
    moved = (
        InternLeaveRequest.objects
        .filter(user_id=link.user_id, status=InternLeaveStatus.PENDING.value)
        .filter(Q(team_id=old_team_id) | Q(team__isnull=True))
        .update(team=team, updated_by_id=actor_id, updated_at=timezone.now())
    )
    return new_link, moved


def change_end_date(link, new_end, actor_id, *, role, admin):
    """
    Changes the planned end of current row `link`. Admin: any date from today on;
    extending a finished intern (tenure ended, INACTIVE) makes them ACTIVE again.
    Lead (the view checks it's their own team and not a Lead or themselves): only
    later, and only for working interns. Approved leave is left as it is. Records
    END_DATE_CHANGED. Call inside transaction.atomic() with the row locked.
    """
    today = ist_today()
    if not isinstance(new_end, date):
        raise OnboardError("end_date must be a date (YYYY-MM-DD).")
    if new_end < today:
        raise OnboardError("end_date can't be in the past.")
    if link.join_date and new_end < link.join_date:
        raise OnboardError("end_date can't be before join_date.")
    state = tenure_state(link, today)
    # Extending reactivates only an intern whose tenure ended. One a Lead or Admin
    # marked INACTIVE stays INACTIVE until their status is set back by hand.
    reactivate = state == 'ENDED' and not inactive_by_choice(link)
    if not admin:
        if state != 'ACTIVE' or link.intern_status == INACTIVE:
            raise OnboardError("Leads can only extend interns who are working now.")
        if link.end_date and new_end <= link.end_date:
            raise OnboardError("Leads can only move the end date later.")

    old_end, old_status = link.end_date, link.intern_status
    link.end_date = new_end
    fields = ['end_date', 'updated_by', 'updated_at']
    if reactivate:
        link.intern_status = ACTIVE
        link.previous_intern_status = None
        link.status_reason = f"Tenure extended to {new_end:%d %b %Y}"
        fields += ['intern_status', 'previous_intern_status', 'status_reason']
    link.updated_by_id = actor_id
    link.save(update_fields=fields)
    record_history(
        InternHistoryAction.END_DATE_CHANGED.value, link, actor_id, role,
        old={"end_date": _d(old_end), "status": old_status},
        new={"end_date": _d(new_end), "status": link.intern_status},
    )


def promote_to_lead(link, actor_id, *, role):
    """
    Makes the member in current row `link` a Lead of the team they're already in:
    only the Intern Lead role is added (Intern too, if it's missing). The row,
    team and status are not touched. Call inside transaction.atomic() with the
    row locked, after any status change on it has been applied.
    """
    if link.intern_status == INACTIVE:
        raise OnboardError("Reactivate this intern before making them a Lead.")
    was_lead = LEAD_ROLE in user_role_titles(link.user_id, [LEAD_ROLE])
    grant_roles(link.user_id, [INTERN_ROLE, LEAD_ROLE], actor_id)
    if not was_lead:
        record_history(
            InternHistoryAction.LEAD_ADDED.value, link, actor_id, role,
            old={"is_lead": False}, new={"is_lead": True},
        )


def remove_lead(link, actor_id, *, role):
    """Takes Intern Lead away from the member in `link` (they stay an intern) and records it."""
    if LEAD_ROLE not in user_role_titles(link.user_id, [LEAD_ROLE]):
        return
    revoke_roles(link.user_id, [LEAD_ROLE])
    record_history(
        InternHistoryAction.LEAD_REMOVED.value, link, actor_id, role,
        old={"is_lead": True}, new={"is_lead": False},
    )


def record_lead_removed(user_ids, actor_id, *, role):
    """
    History for Intern Lead taken away through the role endpoints (the role rows
    are already deleted): one LEAD_REMOVED row per person with a current membership.
    """
    rows = [
        _history_row(InternHistoryAction.LEAD_REMOVED.value, link, actor_id, role,
                     old={"is_lead": True}, new={"is_lead": False})
        for link in UserInternTeamLink.objects.filter(user_id__in=list(user_ids), is_current=True)
    ]
    InternHistory.objects.bulk_create(rows)


def change_status(link, new_status, reason, actor_id, *, role):
    """
    Sets the member's intern_status (marking INACTIVE keeps their roles) with the
    required reason and records STATUS_CHANGED. Saves nothing when the status is
    unchanged; the caller saves the row.
    """
    old_status = link.intern_status
    if old_status == ON_LEAVE and new_status != ON_LEAVE:
        link.previous_intern_status = None
    link.intern_status = new_status
    link.status_reason = reason
    if old_status != new_status:
        record_history(
            InternHistoryAction.STATUS_CHANGED.value, link, actor_id, role,
            old={"status": old_status}, new={"status": new_status}, reason=reason,
        )


def import_intern(user, team, actor_id, make_lead=False, *, role, join_date=None, end_date=None):
    """
    One bulk import row (also used by the role endpoints). Call inside transaction.atomic().

    - Not a member (no current row, or no intern role): onboard into `team` (as
      Lead when make_lead), exactly like onboard_intern; join_date and end_date
      are required for this.
    - Member whose current team is `team`, not INACTIVE, and make_lead: promote.
    - Anything else is refused: an import never moves someone between teams,
      never adds a second membership and never demotes a Lead.

    Returns 'onboarded' or 'promoted'.
    """
    link = current_membership(user.id, lock=True)
    roles = user_role_titles(user.id, MEMBER_ROLES)
    if not (link and roles):
        onboard_intern(user, team, actor_id, make_lead=make_lead, role=role,
                       join_date=join_date, end_date=end_date)
        return 'onboarded'

    if link.intern_status == INACTIVE or tenure_state(link) != 'ACTIVE':
        # onboard_intern raises the "tenure ended" / "not started" message.
        onboard_intern(user, team, actor_id, make_lead=make_lead, role=role,
                       join_date=join_date or ist_today(), end_date=end_date or ist_today())
    if link.team_id != team.id:
        raise OnboardError(
            f"This user is already an active intern in {link.team.name}. "
            "Use interns/reassign/ to move them."
        )
    if not make_lead:
        raise OnboardError(f"This user is already an active intern in {link.team.name}.")
    if LEAD_ROLE in roles:
        raise OnboardError(f"This user is already a Lead of {link.team.name}.")
    promote_to_lead(link, actor_id, role=role)
    return 'promoted'


def assign_member_role(user, role_title, team, actor_id, missing_team_message, *, role,
                       join_date=None, end_date=None):
    """
    Gives `user` the Intern or Intern Lead role through the role endpoints, with
    the same per-person rules as the bulk import (import_intern). `team` may be
    None only when the user is already an active intern: their current team is
    used, so promoting needs no team. Call inside transaction.atomic().

    Returns (outcome, team) with outcome 'onboarded' or 'promoted'.
    """
    if team is None:
        link = active_membership(user.id)
        if link is None:
            raise OnboardError(missing_team_message)
        team = link.team
    outcome = import_intern(user, team, actor_id, make_lead=(role_title == LEAD_ROLE), role=role,
                            join_date=join_date, end_date=end_date)
    return outcome, team


def deactivate_members(user_ids, actor_id, *, role):
    """
    Cleanup when the Intern role is taken away through the role endpoints: the
    same result as deactivating (current row ended with exit_reason "Intern role
    removed", Intern Lead removed too). Ended rows are not touched. Removing only
    Intern Lead needs no cleanup: the person stays an intern in their team.
    Call inside transaction.atomic().
    """
    user_ids = list(user_ids)
    if not user_ids:
        return
    lock_users(user_ids)
    current = list(UserInternTeamLink.objects.filter(user_id__in=user_ids, is_current=True))
    InternHistory.objects.bulk_create([
        _history_row(
            InternHistoryAction.DEACTIVATED.value, link, actor_id, role,
            old={"status": link.intern_status, "is_current": True},
            new={"status": INACTIVE, "is_current": False},
            reason=EXIT_REASON_ROLE_REMOVED,
        )
        for link in current
    ])
    today = ist_today()
    for link in current:
        link.intern_status = INACTIVE
        link.is_current = False
        link.exit_reason = EXIT_REASON_ROLE_REMOVED
        link.end_date = min(link.end_date, today) if link.end_date else today
        link.updated_by_id = actor_id
        link.save(update_fields=['intern_status', 'is_current', 'exit_reason', 'end_date', 'updated_by', 'updated_at'])
    UserRoleLink.objects.filter(user_id__in=user_ids, role__title=LEAD_ROLE).delete()
