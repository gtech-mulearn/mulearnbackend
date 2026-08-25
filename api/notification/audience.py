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
    type:    str                           # "USER", "USERS", "LC_MEMBERS", "LC_LEAD"
    ids:     List[str] = field(default_factory=list)   # pre-resolved IDs (USER / USERS)
    lc_id:  Optional[str] = None          # for LC_MEMBERS and LC_LEAD


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

        # ── Unknown type ──────────────────────────────────────────────────────
        return set()
