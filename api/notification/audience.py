from dataclasses import dataclass, field
from typing import List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# AudienceSpec — describes WHO should receive a notification
#
# Producers never pass raw user ID lists to dispatch().
# They declare the audience semantically using the Audience factory:
#
#   Audience.user("some-user-uuid")          → one specific user
#   Audience.users(["uuid1", "uuid2"])       → explicit list of users
#   Audience.lc_members("lc-uuid")          → all accepted members of an LC
#   Audience.lc_lead("lc-uuid")             → only the lead(s) of an LC
#
# AudienceResolver then resolves this into a concrete set of user_id strings.
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AudienceSpec:
    type:     str                           # "USER", "USERS", "LC_MEMBERS", "LC_LEAD", "EVENT_SCOPE"
    ids:      List[str] = field(default_factory=list)   # pre-resolved IDs (USER / USERS)
    lc_id:   Optional[str] = None          # for LC_MEMBERS and LC_LEAD
    event_id: Optional[str] = None         # for EVENT_SCOPE


# ─────────────────────────────────────────────────────────────────────────────
# Audience — factory that creates AudienceSpec objects
#
# Producers call these static methods to declare their audience.
# No DB queries happen here — resolution is deferred to AudienceResolver.
# ─────────────────────────────────────────────────────────────────────────────

class Audience:

    @staticmethod
    def user(user_id: str) -> AudienceSpec:
        """Single user. Most common — approvals, rejections, personal alerts."""
        return AudienceSpec(type="USER", ids=[str(user_id)])

    @staticmethod
    def users(user_ids: List[str]) -> AudienceSpec:
        """Explicit list of users. Used when the producer already has the IDs."""
        return AudienceSpec(type="USERS", ids=[str(uid) for uid in user_ids])

    @staticmethod
    def lc_members(lc_id: str) -> AudienceSpec:
        """
        All accepted (approved) members of a Learning Circle.
        Used for: LC_MEETING_SCHEDULED (all members except creator).
        The actor_id passed to dispatch() removes the creator automatically.
        """
        return AudienceSpec(type="LC_MEMBERS", lc_id=str(lc_id))

    @staticmethod
    def lc_lead(lc_id: str) -> AudienceSpec:
        """
        The lead(s) of a Learning Circle.
        Used for: LC_JOIN_REQUEST (notify the lead when someone requests to join).
        """
        return AudienceSpec(type="LC_LEAD", lc_id=str(lc_id))

    @staticmethod
    def admins() -> AudienceSpec:
        """
        All users holding the platform ADMIN role. Used for review-queue
        notifications (new company registration, etc.) — the same
        UserRoleLink query several producers already hand-roll inline.
        """
        return AudienceSpec(type="ADMINS")

    @staticmethod
    def event_scope(event_id: str) -> AudienceSpec:
        """
        All users in the scope of a published event, resolved at dispatch time:

          CAMPUS       → all verified members of event.scope_org
          IG           → all active members of event.organiser_ig
          CAMPUS_IG    → all active members of the campus IG chapter (organiser_ci_id)
          COMPANY      → all users linked to the organiser company org
          GLOBAL/ADMIN → all active platform users

        Used for: EVENT_PUBLISHED fan-out.
        The actor (publisher/approver) is excluded automatically by dispatch().
        """
        return AudienceSpec(type="EVENT_SCOPE", event_id=str(event_id))

    @staticmethod
    def event_interested(event_id: str) -> AudienceSpec:
        """
        Everyone who has expressed interest ("I'm Going") in an event.
        Used for: EVENT_CANCELLED — a different, usually smaller and more
        specific audience than event_scope (which is the event's whole
        campus/IG/company, most of whom never clicked "I'm Going").
        """
        return AudienceSpec(type="EVENT_INTERESTED", event_id=str(event_id))

    @staticmethod
    def all() -> AudienceSpec:
        """
        Every active platform user. Used for: media-content shows with no
        reliable structured audience to target (Salt Mango Tree, Inspiration
        Station Radio, Grab Your Superpowers — their `campus` field is free
        text, not an FK, so there's no real set to resolve). Large by
        construction — always paired with a broadcast_target() mapping so it
        fans out to one shared row instead of one write per user.
        """
        return AudienceSpec(type="ALL_USERS")

    @staticmethod
    def ig_via_media_content_links(link_ids: List[str]) -> AudienceSpec:
        """
        Members of the Interest Group(s) tagged on a MediaContent record
        (Office Hours). `link_ids` are IgMediaContentLink row ids (what
        MediaContent.interest_groups actually stores), not raw IG ids —
        resolved to IGs, then to learners, at dispatch time.
        """
        return AudienceSpec(type="MEDIA_CONTENT_IG", ids=[str(i) for i in link_ids])


# ─────────────────────────────────────────────────────────────────────────────
# AudienceResolver — resolves an AudienceSpec into a set of user_id strings
#
# This is where the DB queries happen.
# dispatch() calls resolver.resolve(audience, actor_id) once per dispatch.
#
# actor_id is always excluded from the result — the person who triggered
# the action never receives their own notification.
# ─────────────────────────────────────────────────────────────────────────────

class AudienceResolver:

    def resolve(self, spec: AudienceSpec, actor_id: Optional[str] = None) -> set:
        """
        Resolves an AudienceSpec into a concrete set of user_id strings.

        Args:
            spec:     The audience declaration from the producer.
            actor_id: The user who triggered the action. Always excluded.

        Returns:
            A set of user_id strings. Empty set = no one to notify.
        """
        ids = self._fetch_ids(spec)

        # Remove the actor — they never receive their own notification
        if actor_id:
            ids.discard(str(actor_id))

        return ids

    def _fetch_ids(self, spec: AudienceSpec) -> set:
        """
        Runs the appropriate DB query for each audience type.
        Lazily imports models to avoid circular imports at module load time.
        """

        # ── USER / USERS ──────────────────────────────────────────────────────
        # No DB query needed — IDs are already known by the producer.

        if spec.type == "USER":
            return set(spec.ids)

        if spec.type == "USERS":
            return set(spec.ids)

        # ── ADMINS ────────────────────────────────────────────────────────────
        # All users holding the platform ADMIN role.

        if spec.type == "ADMINS":
            from db.user import UserRoleLink
            from utils.types import RoleType
            return set(
                str(uid) for uid in
                UserRoleLink.objects
                    .filter(role__title=RoleType.ADMIN.value, is_active=True)
                    .values_list("user_id", flat=True)
            )

        # ── LC_MEMBERS ────────────────────────────────────────────────────────
        # All members of the LC whose join was accepted (accepted=True).
        # Excludes pending/invited members who haven't been approved yet.

        if spec.type == "LC_MEMBERS":
            from db.learning_circle import UserCircleLink
            return set(
                str(uid) for uid in
                UserCircleLink.objects
                    .filter(circle_id=spec.lc_id, accepted=True)
                    .values_list("user_id", flat=True)
            )

        # ── LC_LEAD ───────────────────────────────────────────────────────────
        # Only the lead(s) of the LC (lead=True).
        # An LC can have one lead. Returns a set in case of future multi-lead support.

        if spec.type == "LC_LEAD":
            from db.learning_circle import UserCircleLink
            return set(
                str(uid) for uid in
                UserCircleLink.objects
                    .filter(circle_id=spec.lc_id, lead=True, accepted=True)
                    .values_list("user_id", flat=True)
            )

        # ── EVENT_SCOPE ───────────────────────────────────────────────────────
        # Resolves recipients based on event scope and organiser type.
        # Queries the appropriate membership table for the event's audience.

        if spec.type == "EVENT_SCOPE":
            from db.events import Event
            event = Event.objects.filter(id=spec.event_id).first()
            if not event:
                return set()

            organiser_type = event.organiser_type

            # Campus event → all verified org members
            if organiser_type == Event.OrganiserType.CAMPUS:
                from db.organization import UserOrganizationLink
                return set(
                    str(uid) for uid in
                    UserOrganizationLink.objects
                        .filter(org_id=event.scope_org_id, verified=True)
                        .values_list("user_id", flat=True)
                )

            # Global IG event → all active IG members
            if organiser_type == Event.OrganiserType.GLOBAL_IG:
                from db.task import UserIgLink
                return set(
                    str(uid) for uid in
                    UserIgLink.objects
                        .filter(ig_id=event.organiser_ig_id, is_active=True)
                        .values_list("user_id", flat=True)
                )

            # Campus IG event → all active members of the campus IG chapter
            # organiser_ci_id is a "campus_ig" composite ID (no dedicated join table yet)
            # We approximate with: users in the campus org who are also active in that IG
            if organiser_type == Event.OrganiserType.CAMPUS_IG:
                from db.organization import UserOrganizationLink
                from db.task import UserIgLink
                campus_user_ids = set(
                    str(uid) for uid in
                    UserOrganizationLink.objects
                        .filter(org_id=event.scope_org_id, verified=True)
                        .values_list("user_id", flat=True)
                )
                ig_user_ids = set(
                    str(uid) for uid in
                    UserIgLink.objects
                        .filter(ig_id=event.organiser_ig_id, is_active=True)
                        .values_list("user_id", flat=True)
                ) if event.organiser_ig_id else set()
                # Intersection: users who are in BOTH the campus AND the IG
                return campus_user_ids & ig_user_ids if ig_user_ids else campus_user_ids

            # Company event → all users linked to the company's organiser org
            if organiser_type == Event.OrganiserType.COMPANY:
                from db.organization import UserOrganizationLink
                return set(
                    str(uid) for uid in
                    UserOrganizationLink.objects
                        .filter(org_id=event.organiser_org_id, verified=True)
                        .values_list("user_id", flat=True)
                )

            # Admin / Global scope → all active platform users.
            # User.objects is ActiveUserManager — it already excludes
            # suspended users, so no extra filter is needed (User has no
            # is_active field; that was a bug — filtering on it crashes
            # with FieldError the first time this branch actually runs).
            # Chunked fan-out handled by dispatch() for large audiences.
            from db.user import User
            return set(
                str(uid) for uid in
                User.objects.values_list("id", flat=True)
            )

        # ── EVENT_INTERESTED ──────────────────────────────────────────────────
        # Everyone with an EventInterest row for this event.

        if spec.type == "EVENT_INTERESTED":
            from db.events import EventInterest
            return set(
                str(uid) for uid in
                EventInterest.objects
                    .filter(event_id=spec.event_id)
                    .values_list("user_id", flat=True)
            )

        # ── ALL_USERS ─────────────────────────────────────────────────────────
        # Every active platform user. User.objects is ActiveUserManager —
        # it already excludes suspended users, so no extra filter is needed
        # (User has no is_active field).

        if spec.type == "ALL_USERS":
            from db.user import User
            return set(
                str(uid) for uid in
                User.objects.values_list("id", flat=True)
            )

        # ── MEDIA_CONTENT_IG ──────────────────────────────────────────────────
        # Learners of the IG(s) a MediaContent record (Office Hours) is
        # tagged with. spec.ids holds IgMediaContentLink row ids — resolve
        # those to IG ids first, then to learners.

        if spec.type == "MEDIA_CONTENT_IG":
            from db.events import IgMediaContentLink
            from db.task import UserIgLink
            if not spec.ids:
                return set()
            ig_ids = IgMediaContentLink.objects.filter(
                id__in=spec.ids
            ).values_list("interest_group_id", flat=True)
            return set(
                str(uid) for uid in
                UserIgLink.objects.filter(
                    ig_id__in=ig_ids,
                    assignment_type=UserIgLink.AssignmentType.LEARNER,
                    is_active=True,
                ).values_list("user_id", flat=True)
            )

        # ── Unknown type ──────────────────────────────────────────────────────
        return set()

    # ─────────────────────────────────────────────────────────────────────────
    # count() — cheap recipient count for dispatch()'s size branch.
    #
    # Never materializes the full id set for large audiences (that's the
    # whole point of the branch — a global send shouldn't have to build a
    # 20k-element Python set just to decide how to write itself). Falls back
    # to len(_fetch_ids()) only where an intersection can't be counted with a
    # single query (CAMPUS_IG), which is inherently a small audience anyway.
    # ─────────────────────────────────────────────────────────────────────────

    def count(self, spec: AudienceSpec, actor_id: Optional[str] = None) -> int:
        """
        Approximate recipient count — off-by-one from actor exclusion is
        acceptable since this only feeds a threshold comparison, never the
        actual write.
        """
        n = self._count_ids(spec)
        if actor_id and n:
            n -= 1
        return max(n, 0)

    def _count_ids(self, spec: AudienceSpec) -> int:
        if spec.type in ("USER", "USERS"):
            return len(spec.ids)

        if spec.type == "LC_MEMBERS":
            from db.learning_circle import UserCircleLink
            return UserCircleLink.objects.filter(circle_id=spec.lc_id, accepted=True).count()

        if spec.type == "LC_LEAD":
            from db.learning_circle import UserCircleLink
            return UserCircleLink.objects.filter(circle_id=spec.lc_id, lead=True, accepted=True).count()

        if spec.type == "EVENT_SCOPE":
            from db.events import Event
            event = Event.objects.filter(id=spec.event_id).first()
            if not event:
                return 0

            organiser_type = event.organiser_type

            if organiser_type == Event.OrganiserType.CAMPUS:
                from db.organization import UserOrganizationLink
                return UserOrganizationLink.objects.filter(
                    org_id=event.scope_org_id, verified=True
                ).count()

            if organiser_type == Event.OrganiserType.GLOBAL_IG:
                from db.task import UserIgLink
                return UserIgLink.objects.filter(
                    ig_id=event.organiser_ig_id, is_active=True
                ).count()

            if organiser_type == Event.OrganiserType.CAMPUS_IG:
                # Intersection of two sets — cheapest correct option here is
                # the exact resolved set, which is fine: campus-IG chapters
                # are small by construction (one campus x one IG).
                return len(self._fetch_ids(spec))

            if organiser_type == Event.OrganiserType.COMPANY:
                from db.organization import UserOrganizationLink
                return UserOrganizationLink.objects.filter(
                    org_id=event.organiser_org_id, verified=True
                ).count()

            # Admin / Global scope → all active platform users.
            # User.objects (ActiveUserManager) already excludes suspended
            # users — see the matching note in _fetch_ids above.
            from db.user import User
            return User.objects.count()

        if spec.type == "EVENT_INTERESTED":
            from db.events import EventInterest
            return EventInterest.objects.filter(event_id=spec.event_id).count()

        if spec.type == "ALL_USERS":
            from db.user import User
            return User.objects.count()

        if spec.type == "MEDIA_CONTENT_IG":
            return len(self._fetch_ids(spec))

        return 0

    # ─────────────────────────────────────────────────────────────────────────
    # broadcast_target() — maps an AudienceSpec to the (target_type, target_id)
    # BroadcastNotification uses for read-time audience matching (see
    # _resolve_user_broadcasts in notification_view.py).
    #
    # Returns None when the spec has no broadcast equivalent — those audiences
    # always go through the per-recipient path regardless of size. That's
    # true today for USER/USERS/LC_MEMBERS/LC_LEAD (inherently small — a
    # learning circle's membership is never a mass-fanout case) and for
    # COMPANY-organised events (no company-membership target_type exists in
    # BroadcastNotification's audience matching, so there's no single row
    # that could stand in for "everyone linked to this company org").
    # ─────────────────────────────────────────────────────────────────────────

    def broadcast_target(self, spec: AudienceSpec) -> Optional[tuple]:
        if spec.type == "EVENT_INTERESTED":
            # 'event_interest' is already a fully-supported target_type in
            # _broadcast_audience_q (notification_view.py) — a popular
            # event's interest list is not inherently small the way
            # LC_MEMBERS/USER audiences are, so this needs the same
            # single-row-fan-out protection EVENT_SCOPE already gets.
            return ("event_interest", spec.event_id)

        if spec.type == "ALL_USERS":
            # 'global' always matches unconditionally in _broadcast_audience_q
            # — no target_id needed, same as the ADMIN/GLOBAL event-scope case
            # below. This is the one genuinely large-by-default audience in
            # the system, so it needs this protection more than any other.
            return ("global", None)

        if spec.type != "EVENT_SCOPE":
            return None

        from db.events import Event
        event = Event.objects.filter(id=spec.event_id).first()
        if not event:
            return None

        organiser_type = event.organiser_type

        if organiser_type == Event.OrganiserType.CAMPUS and event.scope_org_id:
            return ("campus", str(event.scope_org_id))

        if organiser_type == Event.OrganiserType.GLOBAL_IG and event.organiser_ig_id:
            return ("interest_group", str(event.organiser_ig_id))

        if organiser_type == Event.OrganiserType.CAMPUS_IG and event.organiser_ci_id:
            return ("campus_ig", str(event.organiser_ci_id))

        if organiser_type == Event.OrganiserType.ADMIN:
            return ("global", None)

        return None
