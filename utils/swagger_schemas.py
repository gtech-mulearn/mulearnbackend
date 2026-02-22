"""
drf-spectacular schema extensions for Events and Campus Dashboard APIs.

Imported by apps.py or urls.py to register @extend_schema_view decorators
on existing view classes without modifying their source files.
"""

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse, inline_serializer
from rest_framework import serializers


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Inline serializers for schema docs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SuccessMessage = inline_serializer("SuccessMessage", {
    "statusCode": serializers.IntegerField(default=200),
    "hasError": serializers.BooleanField(default=False),
    "message": serializers.DictField(),
})

ErrorMessage = inline_serializer("ErrorMessage", {
    "statusCode": serializers.IntegerField(default=400),
    "hasError": serializers.BooleanField(default=True),
    "message": serializers.DictField(),
})

EventListItem = inline_serializer("EventListItem", {
    "id": serializers.CharField(),
    "title": serializers.CharField(),
    "slug": serializers.CharField(),
    "cover_image": serializers.CharField(allow_null=True),
    "event_type": serializers.CharField(),
    "status": serializers.CharField(),
    "start_datetime": serializers.DateTimeField(),
    "end_datetime": serializers.DateTimeField(),
    "is_featured": serializers.BooleanField(),
    "interest_count": serializers.IntegerField(),
    "venue_type": serializers.CharField(allow_null=True),
    "organiser_type": serializers.CharField(),
    "organiser_name": serializers.CharField(allow_null=True),
    "tags": serializers.ListField(child=serializers.CharField()),
})

EventVenue = inline_serializer("EventVenue", {
    "venue_type": serializers.ChoiceField(choices=["offline", "online", "hybrid"]),
    "address": serializers.CharField(allow_null=True),
    "city": serializers.CharField(allow_null=True),
    "maps_url": serializers.CharField(allow_null=True),
    "online_link": serializers.CharField(allow_null=True),
    "platform": serializers.CharField(allow_null=True),
})

EventScope = inline_serializer("EventScopeSchema", {
    "scope": serializers.ChoiceField(choices=["campus", "campus_ig", "global_ig", "global", "company"]),
    "target_org_id": serializers.CharField(allow_null=True),
    "target_ig_id": serializers.CharField(allow_null=True),
    "target_ci_org_id": serializers.CharField(allow_null=True),
    "target_ci_ig_id": serializers.CharField(allow_null=True),
})

EventOrganiserInput = inline_serializer("EventOrganiserInput", {
    "organiser_type": serializers.ChoiceField(choices=["admin", "global_ig", "campus", "campus_ig", "company"]),
    "ig_id": serializers.CharField(allow_null=True, required=False),
    "org_id": serializers.CharField(allow_null=True, required=False),
    "ci_org_id": serializers.CharField(allow_null=True, required=False),
    "ci_ig_id": serializers.CharField(allow_null=True, required=False),
})

EventCreateInput = inline_serializer("EventCreateInput", {
    "title": serializers.CharField(),
    "description": serializers.CharField(),
    "cover_image": serializers.CharField(allow_null=True, required=False),
    "banner_image": serializers.CharField(allow_null=True, required=False),
    "event_type": serializers.ChoiceField(choices=["hackathon", "workshop", "meetup", "conference", "bootcamp", "competition", "other"]),
    "start_datetime": serializers.DateTimeField(),
    "end_datetime": serializers.DateTimeField(),
    "registration_url": serializers.CharField(allow_null=True, required=False),
    "registration_deadline": serializers.DateTimeField(allow_null=True, required=False),
    "min_karma": serializers.IntegerField(default=0, required=False),
    "tags": serializers.ListField(child=serializers.CharField(), required=False),
})

ExecomMember = inline_serializer("ExecomMember", {
    "execom_id": serializers.CharField(),
    "user_id": serializers.CharField(),
    "full_name": serializers.CharField(),
    "muid": serializers.CharField(),
    "profile_pic": serializers.CharField(allow_null=True),
    "role_id": serializers.CharField(),
    "role_title": serializers.CharField(),
})

ExecomAddInput = inline_serializer("ExecomAddInput", {
    "user_muid": serializers.CharField(help_text="μLearn ID (muid) of the user to assign"),
    "role_id": serializers.CharField(help_text="UUID of a CampusExecomRole (admin-created)"),
})

LeaderboardItem = inline_serializer("LeaderboardItem", {
    "user_id": serializers.CharField(),
    "full_name": serializers.CharField(),
    "muid": serializers.CharField(),
    "profile_pic": serializers.CharField(allow_null=True),
    "karma": serializers.IntegerField(),
    "rank": serializers.IntegerField(),
    "level": serializers.CharField(),
    "join_date": serializers.CharField(),
    "last_karma_at": serializers.CharField(),
    "graduation_year": serializers.CharField(allow_null=True),
    "department": serializers.CharField(allow_null=True),
    "is_alumni": serializers.BooleanField(),
    "ig_count": serializers.IntegerField(),
})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Apply schema extensions to Event views
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def apply_event_schema_extensions():
    """Call from EventConfig.ready() or events.urls to register schemas."""

    from api.events.public_views import (
        EventListAPI, EventFeaturedAPI, EventDetailAPI, EventInterestAPI,
    )
    from api.events.manage_views import (
        ManageEventListCreateAPI, ManageEventDetailAPI, ManageEventPublishAPI,
        ManageEventCoOwnerAPI, ManageEventCoOwnerRemoveAPI,
        ManageEventCollaboratorAPI, ManageEventCollaboratorRemoveAPI,
        ManageEventCollaboratorAcceptAPI, ManageEventCollaboratorRejectAPI,
    )
    from api.events.admin_views import (
        AdminEventListAPI, AdminEventApproveAPI, AdminEventRejectAPI, AdminEventFeatureAPI,
    )
    from api.events.meta_views import (
        OrganizerOptionsAPI, CollaborationTargetsAPI,
    )
    from api.events.scoped_views import (
        IGEventFeedAPI, ClusterEventFeedAPI, CampusEventFeedAPI,
        CampusIGEventFeedAPI, CompanyEventFeedAPI,
    )

    EVENT_TYPE_PARAM = OpenApiParameter("event_type", str, description="hackathon | workshop | meetup | conference | bootcamp | competition | other")
    CLUSTER_PARAM = OpenApiParameter("cluster", str, description="coder | maker | manager | creative")
    PAGE_PARAM = OpenApiParameter("page", int, description="Page number (default 1)")

    # ── Public ─────────────────────────────────────
    extend_schema_view(
        get=extend_schema(
            summary="List published events",
            description="Paginated public event feed. Optional JWT for viewer-specific data. Filters: event_type, cluster, ig, campus, company.",
            parameters=[PAGE_PARAM, EVENT_TYPE_PARAM, CLUSTER_PARAM,
                        OpenApiParameter("ig", str, description="Filter by Interest Group UUID"),
                        OpenApiParameter("campus", str, description="Filter by Campus org UUID"),
                        OpenApiParameter("company", str, description="Filter by Company org UUID")],
            responses={200: OpenApiResponse(description="Paginated event list")},
            tags=["Events — Public"],
        ),
    )(EventListAPI)

    extend_schema_view(
        get=extend_schema(
            summary="Featured events",
            description="Homepage slider — latest featured events. No auth required.",
            responses={200: OpenApiResponse(description="List of featured events")},
            tags=["Events — Public"],
        ),
    )(EventFeaturedAPI)

    extend_schema_view(
        get=extend_schema(
            summary="Event detail",
            description="Full event detail page. Optional JWT — includes viewer_interest if authenticated.",
            responses={200: OpenApiResponse(description="Full event detail"), 404: ErrorMessage},
            tags=["Events — Public"],
        ),
    )(EventDetailAPI)

    extend_schema_view(
        post=extend_schema(
            summary="Mark interest (I'm Going)",
            description="Toggle 'I'm Going' on an event. JWT required.",
            responses={200: SuccessMessage, 400: ErrorMessage},
            tags=["Events — Public"],
        ),
        delete=extend_schema(
            summary="Remove interest",
            description="Remove 'I'm Going' from an event. JWT required.",
            responses={200: SuccessMessage},
            tags=["Events — Public"],
        ),
    )(EventInterestAPI)

    # ── Manage ─────────────────────────────────────
    extend_schema_view(
        get=extend_schema(
            summary="List my events",
            description="Events the authenticated user owns or co-owns, all statuses.",
            parameters=[PAGE_PARAM],
            responses={200: OpenApiResponse(description="Paginated event list")},
            tags=["Events — Manage"],
        ),
        post=extend_schema(
            summary="Create event",
            description="Create a new event. Initial status determined by organiser_type + user roles. Requires: title, description, event_type, start_datetime, end_datetime, venue, scope, organiser.",
            request=EventCreateInput,
            responses={200: OpenApiResponse(description="Full event detail"), 400: ErrorMessage},
            tags=["Events — Manage"],
        ),
    )(ManageEventListCreateAPI)

    extend_schema_view(
        get=extend_schema(summary="Get managed event detail", description="Full event detail for management view, includes edit_history. Owner/co-owner required.", tags=["Events — Manage"]),
        put=extend_schema(summary="Full event update", description="Full update — all required fields must be present. Creates audit log entry.", request=EventCreateInput, tags=["Events — Manage"]),
        patch=extend_schema(summary="Partial event update", description="Partial update — only changed fields required.", tags=["Events — Manage"]),
        delete=extend_schema(summary="Cancel event", description="Soft-delete (cancel) the event. Sets deleted_at timestamp.", responses={200: SuccessMessage}, tags=["Events — Manage"]),
    )(ManageEventDetailAPI)

    extend_schema_view(
        post=extend_schema(
            summary="Publish / submit event",
            description="Submit event for approval or direct-publish (depends on organiser_type). Only works from draft status.",
            responses={200: SuccessMessage, 400: ErrorMessage},
            tags=["Events — Manage"],
        ),
    )(ManageEventPublishAPI)

    extend_schema_view(
        get=extend_schema(summary="List co-owners", description="List all co-owners of the event.", tags=["Events — Co-owners"]),
        post=extend_schema(summary="Add co-owners", description="Add one or more co-owners. Body: [{ user_id, role }]. Roles: co_owner | editor | viewer.", tags=["Events — Co-owners"]),
    )(ManageEventCoOwnerAPI)

    extend_schema_view(
        delete=extend_schema(summary="Remove co-owner", description="Remove a co-owner by co_owner_id.", responses={200: SuccessMessage}, tags=["Events — Co-owners"]),
    )(ManageEventCoOwnerRemoveAPI)

    extend_schema_view(
        get=extend_schema(summary="List collaborators", description="List all collaborator invites and their statuses.", tags=["Events — Collaborators"]),
        post=extend_schema(summary="Invite collaborators", description="Invite collaborators. Body: [{ collaborator_type, ig_id/org_id, role_label }]. Types: ig | campus | campus_ig | company.", tags=["Events — Collaborators"]),
    )(ManageEventCollaboratorAPI)

    extend_schema_view(
        delete=extend_schema(summary="Remove collaborator", description="Remove a collaborator invite.", responses={200: SuccessMessage}, tags=["Events — Collaborators"]),
    )(ManageEventCollaboratorRemoveAPI)

    extend_schema_view(
        post=extend_schema(summary="Accept collaboration invite", description="Accept a collaboration invite. Must be a lead/authority of the invited entity.", responses={200: SuccessMessage, 403: ErrorMessage}, tags=["Events — Collaborators"]),
    )(ManageEventCollaboratorAcceptAPI)

    extend_schema_view(
        post=extend_schema(summary="Reject collaboration invite", description="Reject with optional reason. Body: { reason: string }.", responses={200: SuccessMessage}, tags=["Events — Collaborators"]),
    )(ManageEventCollaboratorRejectAPI)

    # ── Admin ──────────────────────────────────────
    extend_schema_view(
        get=extend_schema(
            summary="List all events (admin)",
            description="All events across all statuses. Admin role required. Optional status filter.",
            parameters=[OpenApiParameter("status", str, description="Filter: draft | pending_campus_approval | pending_approval | pending_mentor_approval | published | ongoing | completed | cancelled")],
            tags=["Events — Admin"],
        ),
    )(AdminEventListAPI)

    extend_schema_view(
        post=extend_schema(summary="Approve event", description="Multi-level approval: Campus Lead → IG Lead → Admin, depending on organiser_type.", responses={200: SuccessMessage, 403: ErrorMessage}, tags=["Events — Admin"]),
    )(AdminEventApproveAPI)

    extend_schema_view(
        post=extend_schema(summary="Reject event", description="Reject a pending event → returns to draft.", responses={200: SuccessMessage, 403: ErrorMessage}, tags=["Events — Admin"]),
    )(AdminEventRejectAPI)

    extend_schema_view(
        patch=extend_schema(summary="Toggle featured", description="Toggle homepage featured status on a published event. Admin role required.", responses={200: SuccessMessage}, tags=["Events — Admin"]),
    )(AdminEventFeatureAPI)

    # ── Meta ───────────────────────────────────────
    extend_schema_view(
        get=extend_schema(
            summary="Organizer options",
            description="Returns entities the authenticated user can create events as, based on their roles and org/IG memberships.",
            tags=["Events — Meta"],
        ),
    )(OrganizerOptionsAPI)

    extend_schema_view(
        get=extend_schema(
            summary="Collaboration targets",
            description="Searchable entities (IGs, campuses, companies) that can be invited as collaborators.",
            parameters=[
                OpenApiParameter("search", str, description="Search term for entity names"),
                OpenApiParameter("type", str, description="Filter: ig | campus | company (empty = all)"),
            ],
            tags=["Events — Meta"],
        ),
    )(CollaborationTargetsAPI)

    # ── Scoped feeds ───────────────────────────────
    extend_schema_view(get=extend_schema(summary="IG events", description="Events related to a specific Interest Group.", tags=["Events — Scoped Feeds"]))(IGEventFeedAPI)
    extend_schema_view(get=extend_schema(summary="Cluster events", description="Events from all IGs in a cluster. Values: coder | maker | manager | creative.", tags=["Events — Scoped Feeds"]))(ClusterEventFeedAPI)
    extend_schema_view(get=extend_schema(summary="Campus events", description="Events related to a specific campus.", tags=["Events — Scoped Feeds"]))(CampusEventFeedAPI)
    extend_schema_view(
        get=extend_schema(
            summary="Campus IG events",
            description="Events for a specific campus×IG chapter.",
            parameters=[OpenApiParameter("org_id", str, required=True, description="Campus org UUID"), OpenApiParameter("ig_id", str, required=True, description="Interest Group UUID")],
            tags=["Events — Scoped Feeds"],
        ),
    )(CampusIGEventFeedAPI)
    extend_schema_view(get=extend_schema(summary="Company events", description="Events related to a specific company.", tags=["Events — Scoped Feeds"]))(CompanyEventFeedAPI)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Apply schema extensions to Campus Dashboard views
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def apply_campus_schema_extensions():
    """Call from CampusConfig.ready() or campus urls to register schemas."""

    from api.dashboard.campus.campus_views import (
        CampusLeaderboardAPI, CampusKarmaByClusterAPI,
        CampusEventsAPI, CampusEventDistributionAPI,
        CampusExecomAPI, CampusIGChapterAPI, CampusSocialLinkAPI,
    )

    PAGE_PARAM = OpenApiParameter("page", int, description="Page number")

    extend_schema_view(
        get=extend_schema(
            summary="Campus leaderboard",
            description="Paginated, filterable student leaderboard ranked by karma. Auth: Campus Lead / Lead Enabler.",
            parameters=[
                PAGE_PARAM,
                OpenApiParameter("pass_out_year", str, description="Filter by graduation year"),
                OpenApiParameter("ig_id", str, description="Filter by Interest Group UUID"),
                OpenApiParameter("cluster", str, description="Filter by IG cluster"),
                OpenApiParameter("is_alumni", str, description="true/false"),
            ],
            responses={200: OpenApiResponse(description="Paginated leaderboard")},
            tags=["Campus Dashboard — Analytics"],
        ),
    )(CampusLeaderboardAPI)

    extend_schema_view(
        get=extend_schema(
            summary="Karma by cluster",
            description="Total karma per IG cluster (coder, maker, manager, creative). Auth: Campus Lead / Lead Enabler.",
            tags=["Campus Dashboard — Analytics"],
        ),
    )(CampusKarmaByClusterAPI)

    extend_schema_view(
        get=extend_schema(
            summary="Campus event feed",
            description="Paginated events scoped to or organized by this campus. Filterable by status, event_type, scope, date range.",
            parameters=[
                PAGE_PARAM,
                OpenApiParameter("status", str, description="Comma-separated: draft | published | ongoing | completed | cancelled"),
                OpenApiParameter("event_type", str, description="hackathon | workshop | meetup | conference | bootcamp | competition | other"),
                OpenApiParameter("scope", str, description="campus | campus_ig"),
                OpenApiParameter("start_date", str, description="YYYY-MM-DD"),
                OpenApiParameter("end_date", str, description="YYYY-MM-DD"),
            ],
            tags=["Campus Dashboard — Events"],
        ),
    )(CampusEventsAPI)

    extend_schema_view(
        get=extend_schema(
            summary="Event distribution by tag",
            description="Event count grouped by tag name for this campus.",
            tags=["Campus Dashboard — Events"],
        ),
    )(CampusEventDistributionAPI)

    extend_schema_view(
        get=extend_schema(
            summary="List execom members",
            description="All campus execom assignments ordered by role priority. Auth: Campus Lead / Lead Enabler.",
            responses={200: ExecomMember},
            tags=["Campus Dashboard — Execom"],
        ),
        post=extend_schema(
            summary="Add execom member",
            description="Assign a campus member to an admin-defined execom role. Auth: Campus Lead only.",
            request=ExecomAddInput,
            responses={200: SuccessMessage, 400: ErrorMessage},
            tags=["Campus Dashboard — Execom"],
        ),
        delete=extend_schema(
            summary="Remove execom member",
            description="Remove an execom assignment by campus_execom.id. Auth: Campus Lead only.",
            responses={200: SuccessMessage, 400: ErrorMessage},
            tags=["Campus Dashboard — Execom"],
        ),
    )(CampusExecomAPI)

    extend_schema_view(
        get=extend_schema(summary="List IG chapters", description="All campus IG chapters with lead info and member counts.", tags=["Campus Dashboard — IG Chapters"]),
        post=extend_schema(summary="Create IG chapter", description="Create a new campus IG chapter. Body: { ig_id, lead_user_muid, is_active }.", responses={200: SuccessMessage, 400: ErrorMessage}, tags=["Campus Dashboard — IG Chapters"]),
        patch=extend_schema(summary="Update IG chapter", description="Update chapter lead or active status.", responses={200: SuccessMessage}, tags=["Campus Dashboard — IG Chapters"]),
        delete=extend_schema(summary="Delete IG chapter", description="Delete a campus IG chapter.", responses={200: SuccessMessage}, tags=["Campus Dashboard — IG Chapters"]),
    )(CampusIGChapterAPI)

    extend_schema_view(
        get=extend_schema(summary="List social links", description="All social links for this campus.", tags=["Campus Dashboard — Social Links"]),
        post=extend_schema(summary="Create/update social link", description="Upsert a social link. platform: instagram | linkedin | twitter | youtube | website | facebook | github | other.", responses={200: SuccessMessage, 400: ErrorMessage}, tags=["Campus Dashboard — Social Links"]),
        delete=extend_schema(summary="Delete social link", description="Delete a social link by its ID.", responses={200: SuccessMessage}, tags=["Campus Dashboard — Social Links"]),
    )(CampusSocialLinkAPI)
