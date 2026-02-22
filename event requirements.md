/**
 * ============================================================================
 * μLearn Platform — Events System API Schema
 * Django REST Framework × TypeScript Contract
 * ============================================================================
 *
 * PURPOSE
 * -------
 * This file is the single source of truth for the Events API surface.
 * Backend engineers implement against this contract in Django REST Framework.
 * Frontend engineers consume it for type-safe API calls.
 *
 * HOW TO USE
 * ----------
 * Import types into your API client layer (axios wrappers, React Query hooks, etc.)
 * Each endpoint type defines: params, query, body, and response shapes.
 * All write endpoints (POST/PUT/PATCH) accept a `body` field.
 * All list endpoints return SuccessResponse<PaginatedData<T>>.
 *
 * REGISTRATION NOTE
 * -----------------
 * Event registration is handled ENTIRELY via external platforms
 * (the event's own website, Unstop, Devfolio, Townscript, etc.).
 * μLearn does NOT manage registration forms, capacity, waitlists, or attendance.
 * Each event carries a `registration_url` pointing to the external page.
 * The platform tracks only whether a user has clicked "I'm Going"
 * as a lightweight interest signal for notifications and the personal calendar.
 *
 * GLOBAL CONVENTIONS
 * ------------------
 * - All IDs are UUIDs (string) — never expose numeric PKs to the client
 * - All timestamps are ISO 8601 UTC strings  e.g. "2025-09-01T10:00:00Z"
 * - All dates are ISO 8601 date-only strings e.g. "2025-09-01"
 * - Auth: Authorization: Bearer <token> on all non-public endpoints
 * - Soft deletes: DELETE sets status="cancelled", never hard-deletes
 *
 * PAGINATION PARAMS (query string):
 *   pageIndex  → 1-indexed page number (default: 1)
 *   perPage    → results per page      (default: 10)
 *   search     → full-text search string
 *   sortBy     → field name to sort by; prefix with "-" for descending
 *                e.g. sortBy=-start_datetime
 *
 * RESPONSE ENVELOPE (all endpoints):
 *   {
 *     hasError:   boolean,          // false = success, true = error
 *     statusCode: number,           // mirrors HTTP status code
 *     message: {
 *       general: string[],          // human-readable messages
 *       [field]: string[]           // field-level validation errors
 *     },
 *     response: any                 // payload (see per-endpoint types)
 *   }
 *
 * PAGINATED RESPONSE (response field for list endpoints):
 *   {
 *     data:       T[],              // array of items for this page
 *     pagination: {
 *       count:      number,         // total records across all pages
 *       totalPages: number,
 *       isNext:     boolean,        // true if a next page exists
 *       isPrev:     boolean,        // true if a previous page exists
 *       nextPage:   number | null   // next page number, or null
 *     }
 *   }
 *
 * BASE URL: /api/v1
 */

// ============================================================================
// SECTION 0 — PRIMITIVES & ENUMS
// ============================================================================
// All shared string literal types used across the events system.
// Mirror these 1:1 as Django TextChoices on the Event model.
// ============================================================================

/** Universally Unique Identifier — all model PKs exposed to the API are UUIDs */
export type UUID = string;

/** ISO 8601 datetime in UTC — e.g. "2025-09-01T10:00:00Z" */
export type ISODateTime = string;

/** ISO 8601 date-only string — e.g. "2025-09-01" */
export type ISODate = string;

// ---------------------------------------------------------------------------

/**
 * The format/category of the event.
 * Stored as TextChoices on the Event model. Used for filtering and UI icons.
 *
 * workshop        → structured learning session, usually hands-on
 * webinar         → online-only talk/presentation
 * hackathon       → competitive build event, typically 24–48 hours
 * meetup          → informal community gathering
 * competition     → contest with judging and prizes
 * social_gathering → casual non-technical get-together
 * other           → catch-all; use tags to add a descriptive label
 */
export type EventType =
  | "workshop"
  | "webinar"
  | "hackathon"
  | "meetup"
  | "competition"
  | "social_gathering"
  | "other";

// ---------------------------------------------------------------------------

/**
 * Cluster grouping for Interest Groups.
 * IGs are grouped into one of four high-level clusters for filtering,
 * discovery, and dashboard segmentation.
 *
 * coder    → programming, development, web, mobile, AI/ML, DevOps IGs
 * maker    → hardware, IoT, robotics, 3D printing, electronics IGs
 * manager  → product, project management, entrepreneurship, business IGs
 * creative → design, UI/UX, content, video, illustration IGs
 *
 * Stored as a VARCHAR column `cluster` on the `interest_group` table.
 * Used as a filter on event list endpoints to fetch cluster-specific events.
 */
export type IGCluster = "coder" | "maker" | "manager" | "creative";

// ---------------------------------------------------------------------------

/**
 * Controls who can SEE this event and access its registration URL.
 * Enforced server-side on every read operation.
 *
 * global     → visible to every user on the platform
 * campus     → visible only to members of the target campus
 * ig         → visible only to members of the target Interest Group (all campuses)
 * campus_ig  → visible only to members of one IG chapter within one specific campus
 *
 * NOTE: Campus IG leads can create campus_ig events and optionally escalate
 * scope to "global", which requires Global IG Lead approval first.
 */
export type EventScope =
  | "global"
  | "campus"
  | "ig"
  | "campus_ig";

// ---------------------------------------------------------------------------

/**
 * Physical/digital nature of the event venue.
 *
 * physical → in-person only; address and maps_url are required
 * online   → fully remote; online_link and platform are required
 * hybrid   → both in-person and online; all venue fields should be provided
 */
export type VenueType = "physical" | "online" | "hybrid";

// ---------------------------------------------------------------------------

/**
 * Lifecycle state of an event. Follows this transition graph:
 *
 * ┌────────────────────────────────────────────────────────────────────────┐
 * │ Campus IG events (two-level approval):                                │
 * │   draft ─► pending_campus_approval ─► pending_approval ─► published  │
 * │              (campus lead)               (GIG lead)                   │
 * │                                                                       │
 * │ GIG Lead–created events (mentor approval):                            │
 * │   draft ─► pending_mentor_approval ─► published                       │
 * │              (mentor role)                                             │
 * │                                                                       │
 * │ All other events (direct publish):                                    │
 * │   draft ─► published                                                  │
 * │                                                                       │
 * │ After publish:                                                        │
 * │   published ─► ongoing ─► completed                                   │
 * │                                                                       │
 * │ Cancellation possible at any stage:                                   │
 * │   draft / pending_* / published / ongoing ─► cancelled                │
 * └────────────────────────────────────────────────────────────────────────┘
 *
 * draft                    → saved but not visible to anyone except the organiser
 * pending_campus_approval  → campus IG event published by CIG Lead or Campus Lead;
 *                            awaiting Campus Lead approval (the campus lead of
 *                            the campus this IG chapter belongs to). If the
 *                            Campus Lead was the creator, this step is auto-skipped.
 * pending_approval         → campus IG event approved by Campus Lead; now awaiting
 *                            approval from the Global IG Lead of that IG before
 *                            going live. Also used for any event requiring admin
 *                            approval (e.g. global-scope escalation).
 * pending_mentor_approval  → event created by a Global IG Lead; awaiting approval
 *                            from a user with the "mentor" role before going live.
 * published                → live and visible to the target audience
 * ongoing                  → event has started (start_datetime passed);
 *                            auto-transitioned by a backend scheduled task
 * completed                → event has ended (end_datetime passed);
 *                            auto-transitioned by a backend scheduled task
 * cancelled                → organiser or admin cancelled; event hidden from all
 *                            feeds; users who clicked "I'm Going" are notified
 *                            automatically
 */
export type EventStatus =
  | "draft"
  | "pending_campus_approval"
  | "pending_approval"
  | "pending_mentor_approval"
  | "published"
  | "ongoing"
  | "completed"
  | "cancelled";

// ---------------------------------------------------------------------------

/**
 * Whether the authenticated viewer has clicked "I'm Going" on an event.
 * A lightweight intent signal — NOT a registration confirmation.
 * Actual registration happens on the external registration platform.
 *
 * interested → viewer clicked "I'm Going"; subscribed to event reminders
 * none       → viewer has not expressed interest
 */
export type ViewerInterestStatus = "interested" | "none";

// ---------------------------------------------------------------------------

/**
 * Role of a co-owner on an event.
 * Co-owners have the SAME level of authority as the event creator/owner.
 * They can edit, publish, cancel, manage collaborators — everything the owner can do.
 *
 * co_owner → full owner-level permissions on the event
 * admin    → full owner-level permissions on the event (alias for clarity in UI)
 *
 * The event creator can add any platform user as a co-owner, regardless of
 * their organisational role. This is a per-event authority grant, not tied
 * to IG/campus/company leadership.
 */
export type EventCoOwnerRole = "co_owner" | "admin";

// ---------------------------------------------------------------------------

/**
 * The type of entity collaborating on an event.
 * Any combination can be present on a single event simultaneously.
 * e.g. one event can have 2 IGs + 3 campuses + 1 campus IG + 2 companies as co-hosts.
 *
 * ig         → a global Interest Group
 * campus     → an institution/college
 * campus_ig  → one IG chapter within one specific campus
 * company    → a partner company or organisation
 */
export type CollaboratorType = "ig" | "campus" | "campus_ig" | "company";

// ---------------------------------------------------------------------------

/**
 * The role/entity type of whoever created and owns the event.
 * Determines default scope, approval requirements, and edit permissions.
 *
 * global_ig → created by a Global IG Lead (cross-campus IG event)
 * campus_ig → created by a Campus IG Lead (campus chapter event; needs GIG Lead approval)
 * campus    → created by a Campus Lead or Enabler (campus-wide event)
 * company   → created by a Company/Partner user
 * admin     → created by a Platform Admin (no approval needed; any scope allowed)
 */
export type OrganizerType = "global_ig" | "campus_ig" | "campus" | "company" | "admin";


// ============================================================================
// SECTION 1 — SHARED RESPONSE OBJECTS (Minimal / Nested shapes)
// ============================================================================
// Lightweight versions of related models embedded inside event responses.
// Intentionally minimal — only the fields needed for display on event cards/pages.
// Full detail of each entity lives in their own respective API modules.
// ============================================================================

// ─────────────────────────────────────────────────────────────────────────────
// RESPONSE ENVELOPE TYPES
// Every endpoint returns data wrapped in one of these shapes.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Pagination metadata returned alongside list data.
 * Mirrors the dict produced by CommonUtils.get_paginated_queryset().
 */
export interface PaginationMeta {
  /** Total number of records across ALL pages */
  count: number;

  /** Total number of pages given the current perPage value */
  totalPages: number;

  /** true if there is a page after the current one */
  isNext: boolean;

  /** true if there is a page before the current one */
  isPrev: boolean;

  /** Page number of the next page. null when isNext = false. */
  nextPage: number | null;
}

/**
 * The `response` field shape for all paginated list endpoints.
 * Produced by CustomResponse.paginated_response(data, pagination).
 */
export interface PaginatedData<T> {
  data: T[];
  pagination: PaginationMeta;
}

/**
 * Top-level success response envelope.
 * Returned by CustomResponse.get_success_response() and paginated_response().
 *
 * For non-list endpoints:  `response` is the resource object (EventDetail, etc.)
 * For list endpoints:      `response` is PaginatedData<T>
 */
export interface SuccessResponse<T = unknown> {
  hasError: false;
  statusCode: 200 | 201;
  message: {
    general: string[];
    [field: string]: string[];
  };
  response: T;
}

/**
 * Top-level failure response envelope.
 * Returned by CustomResponse.get_failure_response() and get_unauthorized_response().
 *
 * `message.general` holds non-field errors.
 * `message[field]` holds field-level validation errors.
 */
export interface FailureResponse {
  hasError: true;
  statusCode: number;
  message: {
    general: string[];
    [field: string]: string[];
  };
  response: Record<string, unknown>;
}

/** Union of all possible top-level response shapes */
export type APIResponse<T = unknown> = SuccessResponse<T> | FailureResponse;

/**
 * Minimal user shape — embedded as created_by, speaker reference, etc.
 * `muid` is the μLearn unique handle (e.g. "john@mulearn").
 * Full user profile lives in the User API module.
 */
export interface MinimalUser {
  id: UUID;
  full_name: string;
  profile_pic: string | null;
  muid: string;
}

/**
 * Minimal Interest Group — embedded wherever an IG is referenced.
 * Full IG detail (forum, members, global analytics) lives in the IG API module.
 */
export interface MinimalIG {
  id: UUID;
  name: string;
  logo: string | null;

  /**
   * Cluster this IG belongs to.
   * Used for cluster-based event filtering and IG grouping.
   * See IGCluster type for possible values.
   */
  cluster: IGCluster;
}

/**
 * Minimal Campus (institution/college) — embedded wherever a campus is referenced.
 * Full campus detail (leaderboard, execom, analytics) lives in the Campus API module.
 */
export interface MinimalCampus {
  id: UUID;
  name: string;
  logo: string | null;
}

/**
 * Minimal Company/Partner — embedded wherever a company is referenced.
 * Full company detail (jobs, talent discovery) lives in the Company API module.
 */
export interface MinimalCompany {
  id: UUID;
  name: string;
  logo: string | null;
}

/**
 * Minimal Campus IG — a specific IG chapter within a specific campus.
 * e.g. "Web Development IG @ College of Engineering, Trivandrum".
 * Campus IG Leads manage these chapters and can create campus_ig events.
 */
export interface MinimalCampusIG {
  id: UUID;
  ig: MinimalIG;
  campus: MinimalCampus;
}

/**
 * Describes the primary organiser of an event.
 * Exactly one of ig / campus_ig / campus / company will be populated,
 * determined by the `type` field. Used for "Organised by:" display.
 */
export interface OrganizerInfo {
  type: OrganizerType;
  ig?: MinimalIG;               // populated when type = "global_ig"
  campus_ig?: MinimalCampusIG;  // populated when type = "campus_ig"
  campus?: MinimalCampus;       // populated when type = "campus"
  company?: MinimalCompany;     // populated when type = "company"
}


// ============================================================================
// SECTION 2 — EVENT CO-OWNERS
// ============================================================================
// Event owners can add other platform users as co-owners with FULL owner-level
// authority over the event. Co-owners can do everything the original creator can:
// edit, publish, cancel, manage collaborators, add/remove other co-owners.
//
// This is DIFFERENT from collaborators (Section 2.1) — collaborators are
// display-only co-hosts (IGs, campuses, companies). Co-owners are individual
// USERS with full edit/manage permissions on this specific event.
//
// USE CASE: An event organiser wants their team members or trusted partners
// to have full management access without being the original creator.
// ============================================================================

/**
 * A user who has been granted co-owner authority on an event.
 * Co-owners have the SAME permissions as the event creator:
 *   • Edit all event fields
 *   • Publish / cancel the event
 *   • Add / remove collaborators
 *   • Add / remove other co-owners
 *   • View full manage detail including edit history
 *
 * The original creator (created_by) is implicitly the primary owner
 * and cannot be removed as a co-owner. Co-owners are added per-event
 * and can be any user on the platform — no org role required.
 */
export interface EventCoOwner {
  id: UUID;

  /** The user granted co-owner access */
  user: MinimalUser;

  /**
   * Display role for the co-owner.
   * co_owner and admin are functionally identical — this is a UI label choice.
   */
  role: EventCoOwnerRole;

  /** When this co-owner was added */
  added_at: ISODateTime;

  /** Who added this co-owner (the event creator or another co-owner) */
  added_by: MinimalUser;
}

/**
 * Input for adding a co-owner to an event.
 * The user_id can be any valid platform user.
 */
export interface EventCoOwnerInput {
  /** UUID of the user to grant co-owner access */
  user_id: UUID;

  /**
   * Role label for display purposes.
   * Defaults to "co_owner" if not specified.
   */
  role?: EventCoOwnerRole;
}


// ============================================================================
// SECTION 2.1 — EVENT COLLABORATION
// ============================================================================
// Events can be co-hosted by any mix of IGs, campuses, campus IGs, and companies.
// Each collaborator must accept the invite before they appear publicly on the event.
// Only the event creator or co-owners can add or remove collaborators.
// Accepted collaborators are shown in a "Co-hosted by" section on the event page.
// ============================================================================

/**
 * A single collaborating entity on an event.
 *
 * INVITE LIFECYCLE:
 *   Creator adds collaborator  → invite_status = "pending"  (invite notification sent)
 *   Collaborator lead accepts  → invite_status = "accepted" (shown publicly on event page)
 *   Collaborator lead rejects  → invite_status = "rejected" (hidden; creator notified)
 *
 * MULTI-TYPE EXAMPLE — a Hackathon with several co-hosts:
 *   [
 *     { collaborator_type: "ig",        ig: { name: "Web Dev IG" },      role_label: "Knowledge Partner" },
 *     { collaborator_type: "campus",    campus: { name: "CET TVM" },     role_label: "Venue Partner"     },
 *     { collaborator_type: "campus_ig", campus_ig: { ig: ..., campus: ...}, role_label: "Co-organizer"   },
 *     { collaborator_type: "company",   company: { name: "TinkerHub" },  role_label: "Sponsor"           }
 *   ]
 *
 * Only ONE of ig / campus / campus_ig / company is populated per record.
 * Always use `collaborator_type` as the discriminator to know which field to read.
 */
export interface EventCollaborator {
  id: UUID;

  /**
   * Discriminator — determines which entity field below is populated.
   * Read this first, then access the appropriate nested field.
   */
  collaborator_type: CollaboratorType;

  ig?: MinimalIG;               // populated when collaborator_type = "ig"
  campus?: MinimalCampus;       // populated when collaborator_type = "campus"
  campus_ig?: MinimalCampusIG;  // populated when collaborator_type = "campus_ig"
  company?: MinimalCompany;     // populated when collaborator_type = "company"

  /**
   * Optional display label shown next to the entity's name/logo on the event page.
   * e.g. "Venue Partner", "Knowledge Partner", "Co-organizer", "Sponsor".
   * Set by the event creator when adding the collaborator.
   * null renders only the entity name with no additional label.
   */
  role_label: string | null;

  /** Current state of this collaboration invite */
  invite_status: "pending" | "accepted" | "rejected";

  /** When the event creator sent this invite */
  invited_at: ISODateTime;

  /** When the collaborator lead accepted or rejected. null if still pending. */
  responded_at: ISODateTime | null;

  /**
   * Reason given when rejecting the invite.
   * Only visible to the event creator — not shown publicly on the event page.
   * null if the invite is pending or accepted.
   */
  rejection_reason: string | null;
}

/**
 * Type-safe discriminated union for collaborator input.
 * TypeScript enforces that you pass ONLY the correct ID field for the chosen type.
 * Django serializer should mirror this with a validate() method that checks
 * exactly one of ig_id / campus_id / campus_ig_id / company_id is present
 * and matches the declared collaborator_type.
 *
 * USAGE EXAMPLES:
 *   { collaborator_type: "ig",        ig_id: "uuid",        role_label: "Knowledge Partner" }
 *   { collaborator_type: "campus",    campus_id: "uuid",    role_label: "Venue Partner" }
 *   { collaborator_type: "campus_ig", campus_ig_id: "uuid", role_label: "Co-organizer" }
 *   { collaborator_type: "company",   company_id: "uuid",   role_label: "Sponsor" }
 */
export type CollaboratorInput =
  | { collaborator_type: "ig";        ig_id: UUID;        role_label?: string | null }
  | { collaborator_type: "campus";    campus_id: UUID;    role_label?: string | null }
  | { collaborator_type: "campus_ig"; campus_ig_id: UUID; role_label?: string | null }
  | { collaborator_type: "company";   company_id: UUID;   role_label?: string | null };


// Section 3 (Speakers & Agenda) removed — events have their own websites.


// ============================================================================
// SECTION 4 — LINKED TASKS
// ============================================================================
// Events can be linked to tasks participants complete to earn karma.
// Tasks appear in the participant's μJourney under the Events tab after they
// click "I'm Going". Task approval uses the platform's existing review workflow.
// ============================================================================

/**
 * A task from task_list that is linked to this event.
 *
 * IMPORTANT — how linking works:
 * The existing `task_list.event` VARCHAR(50) column stores the event's slug
 * or a short identifier. Tasks are linked to an event by setting this field.
 * No new join table is needed.
 *
 * Karma is earned through the normal karma_activity_log flow — not through
 * the events system. Task review and approval is handled by mentors/IG leads
 * via the existing Discord / appraiser workflow.
 *
 * This response shape is a read-only projection of relevant task_list fields.
 */
export interface LinkedTask {
  /** task_list.id */
  id: UUID;

  /** task_list.title */
  title: string;

  /** task_list.description */
  description: string | null;

  /** task_list.hashtag — used for Discord submission tagging */
  hashtag: string;

  /** task_list.karma — points awarded on approval */
  karma: number;

  /**
   * task_list.bonus_time — deadline for bonus karma.
   * Submissions before this datetime earn karma + task_list.bonus_karma.
   * null if no bonus window is set.
   */
  bonus_time: ISODateTime | null;

  /** task_list.bonus_karma — extra karma awarded if submitted before bonus_time */
  bonus_karma: number;

  /** task_list.active — false means the task is no longer accepting submissions */
  active: boolean;

  /** task_list.ig_id → interest group this task belongs to, if any */
  ig: MinimalIG | null;
}


// ============================================================================
// SECTION 5 — VENUE
// ============================================================================
// Describes where and how an event takes place.
// Backend validates required fields are present for each venue type.
// ============================================================================

/**
 * Full venue details for an event.
 *
 * Backend validation rules:
 *   type = "physical" → address and city are required
 *   type = "online"   → online_link and platform are required
 *   type = "hybrid"   → all fields should be provided
 */
export interface EventVenue {
  type: VenueType;

  /** Street address of the physical venue. Required for physical/hybrid. */
  address: string | null;

  /** City name — used for location-based display and discovery */
  city: string | null;

  /** Google Maps or equivalent URL for the physical location */
  maps_url: string | null;

  /** Meeting URL for online/hybrid events — Zoom, Google Meet, Teams link */
  online_link: string | null;

  /** Platform name for the online component — e.g. "Zoom", "Google Meet", "Discord" */
  platform: string | null;
}


// ============================================================================
// SECTION 6 — CORE EVENT MODELS
// ============================================================================
// Two shapes are provided:
//   EventDetail   → full data; returned from detail / create / update endpoints
//   EventListItem → lightweight card data; returned from all list endpoints
//
// Keeping these separate avoids over-fetching on list views which can return
// hundreds of results, while still providing full context on detail/manage pages.
// ============================================================================

/**
 * Full event object — returned from detail, create, and update endpoints.
 *
 * KARMA ELIGIBILITY (min_karma):
 * An eligibility gate — the viewer's TOTAL accumulated karma must be >= min_karma
 * for them to see and access the registration_url.
 * This does NOT deduct karma. It is purely a threshold check.
 *
 *   min_karma = 5000
 *   User with 10,000 karma → eligible   → viewer_can_access_registration = true
 *   User with  3,200 karma → blocked    → viewer_can_access_registration = false
 *                                          viewer_access_blocked_reason =
 *                                          "Requires 5,000 karma. You have 3,200."
 *
 * REGISTRATION:
 * All registration happens externally. The platform surfaces registration_url
 * (set by the organiser) and tracks only "I'm Going" interest clicks.
 */
export interface EventDetail {
  id: UUID;

  /** Event title as set by the organiser */
  title: string;

  /**
   * URL-safe slug auto-generated from the title, used in shareable event URLs.
   * e.g. "Kerala Flutter Hackathon 2025" → "kerala-flutter-hackathon-2025"
   * De-duplicated with a numeric suffix on collision (e.g. "...2025-2").
   */
  slug: string;

  /** Full event description. Stored and rendered as rich text / markdown. */
  description: string;

  /** Cover image URL — shown as the thumbnail on event list cards */
  cover_image: string | null;

  /** Banner image URL — shown as the full-width hero on the event detail page */
  banner_image: string | null;

  /** Event format/category — see EventType for descriptions */
  event_type: EventType;

  /**
   * Audience scope — controls who can see this event and access its registration URL.
   * See EventScope for full visibility rules. Enforced server-side on every read.
   */
  scope: EventScope;

  /** Current lifecycle state — see EventStatus for transition rules and auto-transitions */
  status: EventStatus;

  /** The entity that created and owns this event */
  organizer: OrganizerInfo;

  /** When the event begins. Backend auto-transitions status to "ongoing" at this time. */
  start_datetime: ISODateTime;

  /** When the event ends. Backend auto-transitions status to "completed" at this time. */
  end_datetime: ISODateTime;

  /** Physical/online location details */
  venue: EventVenue;

  /**
   * URL of the external registration page set by the organiser.
   * Points to the event's page on Unstop, Devfolio, Townscript, a custom event
   * website, or any other platform handling actual registration.
   *
   * null for open walk-in events that require no formal registration.
   *
   * This URL is only surfaced when viewer_can_access_registration = true.
   * For public global events, unauthenticated viewers can also see this URL.
   */
  registration_url: string | null;

  /**
   * Registration deadline on the external platform. Informational only —
   * μLearn does not enforce this (the external platform does).
   * Used to show a "Registration closes in X days" badge on the event page.
   * null if the organiser hasn't specified a deadline.
   */
  registration_deadline: ISODateTime | null;

  /**
   * Minimum total karma required to access the registration_url.
   * A threshold eligibility check — karma is NOT deducted.
   * null means no karma requirement; anyone within scope can register.
   *
   * When the viewer doesn't meet this threshold:
   *   viewer_can_access_registration = false
   *   viewer_access_blocked_reason   = "Requires X karma. You have Y."
   */
  min_karma: number | null;

  /**
   * Tasks from task_list that have task_list.event set to this event's identifier.
   * Participants earn karma by completing these tasks through the normal
   * karma_activity_log / Discord appraiser flow.
   * Appear in the user's μJourney → Events tab.
   * Empty array if no tasks are linked to this event.
   */
  linked_tasks: LinkedTask[];

  /**
   * Users who have been granted co-owner authority on this event.
   * Co-owners have the same edit/manage permissions as the event creator.
   * Empty array if no co-owners have been added.
   * Always visible in the manage view; not shown on the public event page.
   */
  co_owners: EventCoOwner[];

  /**
   * Whether this is a multi-entity collaboration event.
   * When true, `collaborators` contains at least one entry.
   */
  is_collaboration: boolean;

  /**
   * Entities co-hosting this event and their invite statuses.
   * PUBLIC event page: only "accepted" collaborators are shown.
   * MANAGE view: all statuses (pending / accepted / rejected) are visible to the creator.
   */
  collaborators: EventCollaborator[];

  /**
   * Specific campus targeted by this event.
   * Populated when scope = "campus". null otherwise.
   */
  target_campus: MinimalCampus | null;

  /**
   * Specific Interest Group targeted by this event.
   * Populated when scope = "ig". null otherwise.
   */
  target_ig: MinimalIG | null;

  /**
   * Specific campus IG chapter targeted by this event.
   * Populated when scope = "campus_ig". null otherwise.
   */
  target_campus_ig: MinimalCampusIG | null;

  /**
   * Whether this event has been curated for the homepage featured slider.
   * Only platform admins can toggle this field.
   */
  is_featured: boolean;

  /**
   * Free-form tags for discovery and filtering.
   * e.g. ["AI", "beginners", "free", "certificate", "industry"]
   */
  tags: string[];

  /**
   * Total number of users who have clicked "I'm Going" for this event.
   * Informational display only — not a registration count.
   */
  interest_count: number;

  /**
   * The authenticated viewer's current interest status.
   * "interested" → viewer clicked "I'm Going" and will receive reminders
   * "none"        → viewer has not expressed interest
   * null          → unauthenticated request
   */
  viewer_interest_status: ViewerInterestStatus | null;

  /**
   * Whether the authenticated viewer is eligible to access the registration_url.
   *
   * false when any of the following are true:
   *   • Viewer's total karma < min_karma (karma threshold not met)
   *   • Event scope doesn't include the viewer (not a campus/IG member)
   *   • Event is cancelled, completed, or not yet published
   *   • registration_deadline has passed
   *
   * true for unauthenticated viewers on public global events with no min_karma.
   */
  viewer_can_access_registration: boolean;

  /**
   * Human-readable explanation of why viewer_can_access_registration is false.
   * null when viewer_can_access_registration is true.
   *
   * Examples:
   *   "This event is open to Web Dev Interest Group members only."
   *   "Requires 5,000 karma. You have 3,200."
   *   "Registration for this event has closed."
   *   "This event has already completed."
   */
  viewer_access_blocked_reason: string | null;

  /** Platform user who created this event */
  created_by: MinimalUser;

  created_at: ISODateTime;
  updated_at: ISODateTime;
}

// ---------------------------------------------------------------------------

/**
 * Lightweight event shape returned from all list endpoints.
 * Contains only what's needed to render an event card in a feed or grid.
 *
 * Intentionally OMITTED (fetch full EventDetail for these):
 *   description, linked_tasks
 *   collaborators detail (only is_collaboration flag is present)
 *   target entity objects
 *   viewer_can_access_registration, viewer_access_blocked_reason
 *   edit history
 */
export interface EventListItem {
  id: UUID;
  title: string;

  /** URL slug for building the link to the event detail page */
  slug: string;

  /** Thumbnail image for the event card */
  cover_image: string | null;

  event_type: EventType;
  scope: EventScope;
  status: EventStatus;

  start_datetime: ISODateTime;
  end_datetime: ISODateTime;

  /** Physical/online nature — drives location icon on event cards */
  venue_type: VenueType;

  /** City of the physical venue. null for fully online events. */
  venue_city: string | null;

  /** Primary organiser info for "Organised by" line on event cards */
  organizer: OrganizerInfo;

  /**
   * Minimum karma required to access the registration URL.
   * null = no karma requirement.
   * Frontend uses this to show a lock icon on cards the viewer doesn't qualify for,
   * without needing to fetch the full EventDetail.
   */
  min_karma: number | null;

  /** true if this event has at least one collaborating co-host entity */
  is_collaboration: boolean;

  /** true if this event is curated for the homepage slider */
  is_featured: boolean;

  tags: string[];

  /** Number of users who clicked "I'm Going" */
  interest_count: number;

  /**
   * The authenticated viewer's current interest status.
   * Used to show "I'm Going ✓" badge on event cards.
   * null for unauthenticated requests.
   */
  viewer_interest_status: ViewerInterestStatus | null;
}


// ============================================================================
// SECTION 7 — REQUEST BODIES (Write Inputs)
// ============================================================================
// Shapes sent from client → server on create / update operations.
//
// NESTED ARRAY UPSERT SEMANTICS (, linked_tasks, collaborators):
//   Include `id` field → UPDATE the existing nested record with this id
//   Omit `id` field   → CREATE a new nested record
//   Omit a record from the array entirely → DELETE it from the event
// Always send the COMPLETE desired state on every update, not just the diff.
// ============================================================================

/**
 * Input for linking an existing task_list record to this event.
 *
 * Linking works by setting task_list.event = event.slug (or a short event ID).
 * The backend should:
 *   1. Validate the task_id belongs to the organiser's IG or org
 *   2. Set task_list.event = event identifier on the task record
 *   3. Unlink by clearing task_list.event = NULL
 *
 * You do NOT create new tasks here — tasks are created separately in the
 * task management flow. This just associates existing tasks with this event.
 */
export interface LinkedTaskInput {
  /** task_list.id of the task to link to this event */
  task_id: UUID;
}

/**
 * Main request body for creating or updating an event.
 * Used by: POST /manage/events/  and  PUT / PATCH /manage/events/:id/
 *
 * ORGANISER FIELD RULES:
 * Pass EXACTLY ONE of organizer_ig_id / organizer_campus_id /
 * organizer_campus_ig_id / organizer_company_id.
 * Backend cross-validates that the authenticated user has the correct role
 * for the chosen organiser entity. Mismatch returns 403 Forbidden.
 *
 * SCOPE × ORGANISER COMPATIBILITY:
 * ┌──────────────────────┬──────────────────────────────────────────┐
 * │ Organiser type       │ Allowed scopes                           │
 * ├──────────────────────┼──────────────────────────────────────────┤
 * │ global_ig (GIG Lead) │ global, ig                               │
 * │ campus_ig (CIG Lead) │ campus_ig, campus, global*               │
 * │ campus (Lead/Enabler)│ campus, global                           │
 * │ company              │ global                                   │
 * │ admin                │ any                                      │
 * └──────────────────────┴──────────────────────────────────────────┘
 * * campus_ig → global scope escalation requires Global IG Lead approval
 *   (event status becomes "pending_approval" instead of "published" on publish)
 *
 * NESTED ARRAYS:
 * linked_tasks, collaborators all use upsert semantics.
 * Always send the complete desired array state — not just changed items.
 */
export interface EventWriteBody {
  title: string;

  /** Rich text / markdown event description */
  description: string;

  /**
   * Cover image: base64-encoded data or a presigned S3 upload key.
   * Displayed as the event card thumbnail in list views.
   */
  cover_image?: string | null;

  /**
   * Banner image: base64-encoded data or a presigned S3 upload key.
   * Displayed as the full-width hero banner on the event detail page.
   */
  banner_image?: string | null;

  event_type: EventType;
  scope: EventScope;

  /**
   * Pass EXACTLY ONE organiser identifier.
   * Backend validates the authenticated user has authority over this entity.
   */
  organizer_ig_id?: UUID;         // use when creating a global IG event
  organizer_campus_id?: UUID;     // use when creating a campus-level event
  organizer_campus_ig_id?: UUID;  // use when creating a campus IG chapter event
  organizer_company_id?: UUID;    // use when creating a company event

  /** Event start time. Must be in the future at creation time. */
  start_datetime: ISODateTime;

  /** Event end time. Must be strictly after start_datetime. */
  end_datetime: ISODateTime;

  venue: {
    type: VenueType;
    address?: string | null;    // required when type is "physical" or "hybrid"
    city?: string | null;
    maps_url?: string | null;
    online_link?: string | null; // required when type is "online" or "hybrid"
    platform?: string | null;    // required when type is "online" or "hybrid"
  };

  /**
   * URL of the external registration page.
   * e.g. the event's Unstop page, Devfolio page, or a custom event website.
   * Must be a valid URL if provided.
   * null for open walk-in events with no formal registration process.
   */
  registration_url?: string | null;

  /**
   * Registration deadline on the external platform. Informational only.
   * Displayed as a countdown ("closes in X days") on the event page.
   * Must be before or equal to start_datetime if provided.
   * null if no known deadline or if no registration is required.
   */
  registration_deadline?: ISODateTime | null;

  /**
   * Minimum total karma required to access the registration_url.
   * A pure eligibility threshold — karma is NOT deducted.
   * null or omit for no karma requirement (anyone in scope can register).
   * Must be a non-negative integer if provided.
   */
  min_karma?: number | null;

  /**
   * IDs of existing task_list records to associate with this event.
   * Backend sets task_list.event = event slug for each listed task_id.
   * Tasks omitted from this array on update will have task_list.event cleared.
   * Pass the complete desired list of task_ids on every update.
   */
  linked_tasks?: LinkedTaskInput[];

  /**
   * Users to grant co-owner authority on this event.
   * Co-owners have the same permissions as the event creator.
   * Can be any platform user — no org role requirement.
   *
   * Example:
   *   [
   *     { user_id: "uuid-1", role: "co_owner" },
   *     { user_id: "uuid-2", role: "admin" }
   *   ]
   */
  co_owners?: EventCoOwnerInput[];

  /**
   * Set to true to enable multi-entity co-hosting.
   * When true, the `collaborators` array should contain at least one entry.
   * Collaboration invite notifications are sent immediately on save.
   */
  is_collaboration: boolean;

  /**
   * Entities to invite as collaborators. Any mix of types is allowed simultaneously.
   * Uses the discriminated CollaboratorInput union — see Section 2.1 for full docs.
   *
   * Example — mixed collaboration:
   *   [
   *     { collaborator_type: "ig",        ig_id: "uuid-1", role_label: "Knowledge Partner" },
   *     { collaborator_type: "campus",    campus_id: "uuid-2", role_label: "Venue Partner" },
   *     { collaborator_type: "campus_ig", campus_ig_id: "uuid-3" },
   *     { collaborator_type: "company",   company_id: "uuid-4", role_label: "Sponsor" }
   *   ]
   */
  collaborators?: CollaboratorInput[];

  /**
   * Target campus UUID — required when scope = "campus".
   * Backend validates organiser has authority over this campus.
   */
  target_campus_id?: UUID | null;

  /**
   * Target IG UUID — required when scope = "ig".
   * Backend validates organiser is a lead of this IG.
   */
  target_ig_id?: UUID | null;

  /**
   * Target campus IG UUID — required when scope = "campus_ig".
   * Backend validates organiser is the lead of this campus IG chapter.
   */
  target_campus_ig_id?: UUID | null;

  /**
   * Free-form tags for categorisation and search.
   * Frontend suggests existing tags; new tags are created in the DB on save.
   * e.g. ["AI", "beginners", "certificate", "industry", "free"]
   */
  tags?: string[];

  /**
   * Admin-only field — silently ignored for all non-admin roles.
   * Featured events appear in the homepage rotating carousel.
   */
  is_featured?: boolean;
}


// ============================================================================
// SECTION 8 — INTEREST ("I'M GOING") SYSTEM
// ============================================================================
// A lightweight expression of intent to attend an event.
// Does NOT register the user on the external registration platform.
// Purpose: event reminders, personal calendar, feed personalisation signals.
// ============================================================================

/**
 * A single "I'm Going" interest record — one user ↔ one event.
 * Toggled via POST /events/:id/interest/ and DELETE /events/:id/interest/
 */
export interface EventInterest {
  id: UUID;

  /** Minimal event info embedded to avoid a separate event fetch */
  event: { id: UUID; title: string; slug: string };

  /** The user who expressed interest */
  user: MinimalUser;

  /** Timestamp when the user clicked "I'm Going" */
  expressed_at: ISODateTime;
}


// ============================================================================
// SECTION 9 — QUERY PARAMS / FILTERS
// ============================================================================
// Shared filter interface accepted by all event list endpoints.
// All params are optional. Multiple filters are combined with AND logic.
// ============================================================================

/**
 * Query parameters accepted by all event list endpoints.
 * All fields are optional and combinable freely.
 *
 * EXAMPLE QUERIES:
 *   Upcoming hackathons at my campus:
 *     ?event_type=hackathon&campus_id=<uuid>&ordering=start_datetime
 *
 *   Events I'm karma-eligible for in a specific IG:
 *     ?ig_id=<uuid>&eligible_only=true&status=published
 *
 *   Featured events for the homepage slider:
 *     ?is_featured=true&status=published&ordering=start_datetime
 *
 *   Past completed events (archive / history view):
 *     ?status=completed&ordering=-start_datetime
 *
 *   Events happening this month:
 *     ?start_date=2025-09-01&end_date=2025-09-30&ordering=start_datetime
 */
export interface EventListQueryParams {
  /**
   * Filter by event format/category.
   * e.g. event_type=hackathon returns only hackathon events.
   */
  event_type?: EventType;

  /**
   * Filter by visibility scope.
   * Omit to return all scopes the viewer is eligible for (most common use case).
   * e.g. scope=campus returns only campus-restricted events.
   */
  scope?: EventScope;

  /**
   * Filter by lifecycle status.
   * Default behaviour (omitted): returns published + ongoing events.
   * Pass status=draft to list drafts (organiser/admin views only).
   * Pass status=completed to browse past events (archive/history).
   */
  status?: EventStatus;

  /** Return events organised by or scoped to this Interest Group */
  ig_id?: UUID;

  /** Return events organised by or scoped to this campus */
  campus_id?: UUID;

  /** Return events organised by this company */
  company_id?: UUID;

  /** Return events organised by or scoped to this campus IG chapter */
  campus_ig_id?: UUID;

  /**
   * Filter by IG cluster.
   * Returns events whose organiser IG or target IG belongs to this cluster.
   * e.g. cluster=coder returns all events from IGs in the "coder" cluster.
   * Can be combined with other filters (campus_id + cluster to get
   * coder-cluster events at a specific campus).
   */
  cluster?: IGCluster;

  /** When true, return only featured events (used for homepage slider data) */
  is_featured?: boolean;

  /**
   * Comma-separated tags to filter by (AND logic).
   * e.g. tags=AI,beginners returns events tagged with BOTH "AI" AND "beginners".
   */
  tags?: string;

  /**
   * When true, returns only events the viewer's karma meets the threshold for.
   * i.e. events where viewer's total karma >= event.min_karma, or min_karma is null.
   *
   * When false or omitted, all scope-visible events are returned regardless of karma.
   * Frontend can use EventListItem.min_karma to render lock icons on ineligible cards.
   *
   * Ignored for unauthenticated requests.
   */
  eligible_only?: boolean;

  /**
   * Return events starting on or after this date (inclusive).
   * Combine with end_date to create a date-range window.
   */
  start_date?: ISODate;

  /** Return events starting on or before this date (inclusive) */
  end_date?: ISODate;

  /**
   * Full-text search across event title and description.
   * Case-insensitive substring match (Django icontains).
   */
  search?: string;

  /**
   * Field to sort results by.
   * Prefix with "-" for descending order.
   * Maps to the `sortBy` query param consumed by CommonUtils.get_paginated_queryset().
   *
   * Backend sort_fields dict maps these values to actual DB column names.
   *   start_datetime   → earliest first (default; upcoming events)
   *   -start_datetime  → latest first   (past events / recent)
   *   created_at       → oldest created first
   *   -created_at      → newest created first
   *   interest_count   → least popular first
   *   -interest_count  → most popular first (trending)
   */
  sortBy?:
    | "start_datetime"
    | "-start_datetime"
    | "created_at"
    | "-created_at"
    | "interest_count"
    | "-interest_count";

  /**
   * 1-indexed page number.
   * Passed as `pageIndex` query param. Default: 1.
   */
  pageIndex?: number;

  /**
   * Number of results per page.
   * Passed as `perPage` query param. Default: 10.
   */
  perPage?: number;
}


// ============================================================================
// SECTION 10 — API ENDPOINT DEFINITIONS
// ============================================================================
// Each type fully describes one endpoint's contract:
//   params   → URL path parameters       e.g. { id: UUID }
//   query    → URL query string params
//   body     → JSON request body         (POST / PUT / PATCH only)
//   response → expected JSON response body shape
//
// BASE URL: /api/v1
// Auth: Authorization: Bearer <token>   (required on all non-public endpoints)
// ============================================================================


// ────────────────────────────────────────────────────────────────────────────
// 10.1  PUBLIC & NORMAL USER ENDPOINTS
// Main event feed, event detail page, and the "I'm Going" interest system.
// Scope filtering is applied automatically based on the viewer's memberships.
// ────────────────────────────────────────────────────────────────────────────

/**
 * GET /events/
 *
 * Main event feed for the authenticated viewer.
 * Automatically includes all events the viewer is eligible to see based on:
 *   • Global events        → always visible to all authenticated users
 *   • Campus membership    → campus-scoped events for the viewer's campus
 *   • IG memberships       → ig-scoped events for each IG the viewer belongs to
 *   • Campus IG membership → campus_ig events for each chapter the viewer is in
 *
 * Default (no filters): published + ongoing events, sorted by start_datetime ascending.
 * Use EventListQueryParams to narrow, sort, or paginate further.
 */
export type GET_events = {
  query: EventListQueryParams;
  response: SuccessResponse<PaginatedData<EventListItem>>;
};

// ---------------------------------------------------------------------------

/**
 * GET /events/featured/
 *
 * Returns events flagged as featured by platform admins.
 * Used to populate the homepage rotating carousel/slider.
 *
 * PUBLIC endpoint — no authentication required.
 * Returns only published events, sorted by start_datetime ascending.
 * Typically curated to 6–10 events at any one time.
 */
export type GET_events_featured = {
  query: { page?: number; page_size?: number };
  response: SuccessResponse<PaginatedData<EventListItem>>;
};

// ---------------------------------------------------------------------------

/**
 * GET /events/:id/
 *
 * Full event detail for the event detail page.
 * Returns EventDetail including, linked tasks,
 * collaborators, and viewer-context fields.
 *
 * ACCESS:
 *   Published events  → all users within the event's scope
 *   Draft events      → organiser and platform admins only
 *   Pending events    → organiser, relevant approver(s) (campus lead,
 *                       GIG lead, or mentor depending on stage), and admins
 *   Cancelled events  → organiser and admins only
 *
 * UNAUTHENTICATED:
 *   Global-scope published events are publicly accessible.
 *   viewer_* fields will be null for unauthenticated requests.
 */
export type GET_events_detail = {
  params: { id: UUID };
  response: SuccessResponse<EventDetail>;
};

// ---------------------------------------------------------------------------

/**
 * POST /events/:id/interest/
 *
 * Mark the authenticated viewer as "I'm Going" for this event.
 *
 * This is NOT a registration — it's a lightweight intent signal that:
 *   • Adds the event to the user's personal event calendar view
 *   • Subscribes the user to event reminder notifications
 *     (sent 1 day before and 1 hour before the event starts)
 *   • Increments event.interest_count
 *
 * The viewer must be within the event's scope to express interest.
 * If min_karma is set, the viewer must meet the threshold.
 *
 * Idempotent — safe to call multiple times; returns 200 if already interested.
 *
 * RESPONSES:
 *   201 → EventInterest record (first time expressing interest)
 *   200 → EventInterest record (already interested — no duplicate created)
 *   403 → Viewer is not within the event's scope, or min_karma not met
 *   404 → Event not found or not visible to viewer
 */
export type POST_event_interest = {
  params: { id: UUID };
  response: SuccessResponse<EventInterest>;
};

// ---------------------------------------------------------------------------

/**
 * DELETE /events/:id/interest/
 *
 * Remove the authenticated viewer's "I'm Going" interest for this event.
 * Unsubscribes them from event reminder notifications.
 * Decrements event.interest_count.
 *
 * RESPONSES:
 *   200 → { detail: "Interest removed." }
 *   404 → Viewer had not expressed interest in this event
 */
export type DELETE_event_interest = {
  params: { id: UUID };
  response: SuccessResponse<{ message: string }>;
};


// ────────────────────────────────────────────────────────────────────────────
// 10.2  MANAGE ENDPOINTS (Create / Edit / Publish / Delete)
// Powers the "Manage Events" screen shown for eligible roles
// (campus leads, company users, IG leads, and platform admins).
// All permissions are enforced based on the authenticated user's role,
// the organiser entity they claim authority over, OR co-owner status.
// Co-owners of an event have the SAME permissions as the event creator.
// ────────────────────────────────────────────────────────────────────────────

/**
 * GET /manage/events/
 *
 * Returns all events the authenticated user can manage.
 * "Can manage" means: user is the event creator, OR is a co-owner of the event,
 * OR is a lead with authority over the event's organiser entity (e.g. a GIG Lead
 * can manage all events created under their IG, even ones created by other leads
 * of the same IG).
 *
 * Includes ALL statuses (draft, pending, published, ongoing, completed, cancelled)
 * so organisers have a full portfolio view of their events.
 * Supports all EventListQueryParams for filtering and sorting within this managed set.
 *
 * SCREEN: Manage Events (sidebar item for campus/company/IG leads and admins)
 */
export type GET_manage_events = {
  query: EventListQueryParams;
  response: SuccessResponse<PaginatedData<EventListItem>>;
};

// ---------------------------------------------------------------------------

/**
 * POST /manage/events/
 *
 * Create a new event. Returns the full EventDetail of the created event.
 *
 * INITIAL STATUS LOGIC (what status the event starts with after creation):
 *   Admin creates any event              → "published" immediately
 *   Campus Lead/Enabler creates campus   → "published" immediately
 *   Company user creates event           → "published" immediately
 *
 *   GIG Lead creates a global/ig event   → "pending_mentor_approval"
 *     Requires a user with the "mentor" role to approve before going live.
 *     An approval request notification is automatically sent to all mentors.
 *
 *   CIG Lead creates campus_ig event     → "pending_campus_approval"
 *     TWO-LEVEL APPROVAL:
 *       1. Campus Lead of the chapter's campus must approve first.
 *          → status moves to "pending_approval"
 *       2. Global IG Lead of that IG must then approve.
 *          → status moves to "published"
 *     Notifications are sent at each stage to the next approver.
 *
 *   Campus Lead creates campus_ig event  → "pending_approval"
 *     Since the Campus Lead IS the first-level approver, the campus
 *     approval step is auto-skipped. Only GIG Lead approval is needed.
 *     → GIG Lead approves → status moves to "published"
 *
 *   Any role creating without publish    → "draft"
 *     Use POST /manage/events/:id/publish/ to submit when ready.
 *
 * PERMISSION MATRIX:
 * ┌─────────────────────┬──────────────────────────────────────────────────┐
 * │ Authenticated Role  │ Allowed organiser field + scopes                 │
 * ├─────────────────────┼──────────────────────────────────────────────────┤
 * │ Global IG Lead      │ organizer_ig_id (IGs they lead)                  │
 * │                     │ scope: global, ig                                │
 * │ Campus IG Lead      │ organizer_campus_ig_id (chapters they lead)      │
 * │                     │ scope: campus_ig, campus, global*                │
 * │ Campus Lead/Enabler │ organizer_campus_id (their campus)               │
 * │                     │ scope: campus, global                            │
 * │                     │ organizer_campus_ig_id (chapters in their campus)│
 * │                     │ scope: campus_ig**                               │
 * │ Company user        │ organizer_company_id (their company)             │
 * │                     │ scope: global                                    │
 * │ Admin               │ any organiser field, any scope                   │
 * └─────────────────────┴──────────────────────────────────────────────────┘
 * *  campus_ig → global escalation requires GIG Lead approval first
 * ** Campus Lead creating a campus_ig event skips campus-level approval;
 *    only GIG Lead approval is needed (campus lead IS the campus approver)
 *
 * RESPONSES:
 *   201 → EventDetail (the newly created event)
 *   400 → Validation error (missing fields, invalid scope/organiser combo, etc.)
 *   403 → User lacks the role to create events for the specified organiser entity
 */
export type POST_manage_events = {
  body: EventWriteBody;
  response: SuccessResponse<EventDetail>;
};

// ---------------------------------------------------------------------------

/**
 * GET /manage/events/:id/
 *
 * Full event detail enriched with management-only context:
 *   • edit_history: complete audit log (who changed what, when)
 *   • ALL collaborator invite statuses (pending / accepted / rejected)
 *   • event status even if draft or pending
 *
 * Used to render the event edit/management page with full context.
 *
 * PERMISSION: event creator, co-owner, authorised lead over the organiser entity, or admin.
 */
export type GET_manage_event_detail = {
  params: { id: UUID };
  response: SuccessResponse<EventDetail & {
    /**
     * Full chronological audit log of all edits to this event.
     * Useful for accountability, debugging, and recovering from accidental changes.
     * `changed_fields` lists the top-level EventWriteBody keys that were modified.
     */
    edit_history: Array<{
      edited_by: MinimalUser;
      edited_at: ISODateTime;
      /** e.g. ["title", "venue", "min_karma"] — top-level fields that changed */
      changed_fields: string[];
    }>;
  };
};

// ---------------------------------------------------------------------------

/**
 * PUT /manage/events/:id/
 *
 * Full replacement update — all EventWriteBody fields must be provided.
 * Prefer PATCH for targeted partial updates to avoid unintentional resets.
 *
 * PERMISSION:
 *   Only the original event creator, co-owners, OR a lead with authority over the
 *   organiser entity. Collaborators (even accepted ones) CANNOT edit the event.
 *   Platform admins can edit any event.
 *
 * RESTRICTIONS:
 *   Cannot edit a "cancelled" or "completed" event.
 *   Changing scope while the event is "ongoing" is blocked.
 *
 * All nested arrays use upsert semantics — send the complete desired state.
 *
 * RESPONSES:
 *   200 → EventDetail (fully updated event)
 *   400 → Validation error
 *   403 → Insufficient permissions
 */
export type PUT_manage_event = {
  params: { id: UUID };
  body: EventWriteBody;
  response: SuccessResponse<EventDetail>;
};

// ---------------------------------------------------------------------------

/**
 * PATCH /manage/events/:id/
 *
 * Partial update — only the fields included in the body are changed.
 * All unspecified fields remain exactly as they were. Safer than PUT.
 *
 * Same permission rules and restrictions as PUT.
 *
 * EXAMPLES:
 *   Update only the registration URL:      { registration_url: "https://unstop.com/..." }
 *   Update only the karma threshold:       { min_karma: 3000 }
 *   Add a new tag (send full array):       { tags: ["existing-tag", "new-tag"] }
 *   Update venue online link only:         { venue: { type: "online", online_link: "..." } }
 *
 * IMPORTANT: If you include a nested array field (, linked_tasks,
 * collaborators) in a PATCH body, the ENTIRE array is replaced with what you send.
 * Partial array merging is not supported — always send the complete desired array.
 */
export type PATCH_manage_event = {
  params: { id: UUID };
  body: Partial<EventWriteBody>;
  response: SuccessResponse<EventDetail>;
};

// ---------------------------------------------------------------------------

/**
 * DELETE /manage/events/:id/
 *
 * Cancels the event (soft delete — sets status to "cancelled").
 * The event record is retained in the database for analytics and audit purposes.
 * Hard deletion is not available via API; use Django admin only if truly needed.
 *
 * SIDE EFFECTS:
 *   • All users who clicked "I'm Going" receive a cancellation notification
 *   • Event disappears from all public feeds and search results immediately
 *   • Event remains visible to the organiser and admins in the manage view
 *     with status = "cancelled"
 *
 * PERMISSION: event creator, co-owner, authorised lead, or platform admin.
 *
 * RESPONSES:
 *   200 → { detail: "Event cancelled. N users have been notified." }
 *   403 → Insufficient permissions
 *   400 → Event is already cancelled or completed
 */
export type DELETE_manage_event = {
  params: { id: UUID };
  response: SuccessResponse<{ message: string }>;
};

// ---------------------------------------------------------------------------

/**
 * POST /manage/events/:id/publish/
 *
 * Transitions an event from "draft" into the appropriate approval pipeline
 * or directly to "published", depending on the creator's role.
 *
 * TRANSITION RULES:
 *
 *   ┌─────────────────────────────┬──────────────────────────────────────────┐
 *   │ Creator / Scenario          │ Status after publish                     │
 *   ├─────────────────────────────┼──────────────────────────────────────────┤
 *   │ Admin creates any event     │ → "published" immediately               │
 *   │ Campus Lead creates campus  │ → "published" immediately               │
 *   │ Company user creates event  │ → "published" immediately               │
 *   ├─────────────────────────────┼──────────────────────────────────────────┤
 *   │ GIG Lead creates ig/global  │ → "pending_mentor_approval"             │
 *   │                             │   Notification sent to mentors.         │
 *   │                             │   Mentor approves → "published"         │
 *   ├─────────────────────────────┼──────────────────────────────────────────┤
 *   │ CIG Lead creates campus_ig  │ → "pending_campus_approval"             │
 *   │                             │   1. Campus Lead approves               │
 *   │                             │      → "pending_approval"               │
 *   │                             │   2. GIG Lead approves                  │
 *   │                             │      → "published"                      │
 *   ├─────────────────────────────┼──────────────────────────────────────────┤
 *   │ Campus Lead creates         │ → "pending_approval"                    │
 *   │   campus_ig event           │   Campus approval auto-skipped (creator │
 *   │                             │   IS the campus approver).              │
 *   │                             │   GIG Lead approves → "published"       │
 *   └─────────────────────────────┴──────────────────────────────────────────┘
 *
 * VALIDATION (all must pass before status changes):
 *   • title and description are not empty
 *   • start_datetime is in the future
 *   • end_datetime is strictly after start_datetime
 *   • venue fields are valid for the chosen venue type
 *   • Scope-required targeting fields are provided
 *     (e.g. scope=campus requires target_campus_id)
 *
 * RESPONSES:
 *   200 → EventDetail with updated status
 *   400 → Validation failed (required fields missing, past start time, etc.)
 *   409 → Event is not currently in "draft" status
 */
export type POST_manage_event_publish = {
  params: { id: UUID };
  response: SuccessResponse<EventDetail>;
};


// ────────────────────────────────────────────────────────────────────────────
// 10.2.1  CO-OWNER MANAGEMENT ENDPOINTS
// Manage event co-owners — users with full owner-level authority.
// Only the event creator or existing co-owners can add/remove co-owners.
// ────────────────────────────────────────────────────────────────────────────

/**
 * GET /manage/events/:id/co-owners/
 *
 * List all co-owners of an event.
 *
 * PERMISSION: event creator, co-owner, or platform admin.
 */
export type GET_event_co_owners = {
  params: { id: UUID };
  response: SuccessResponse<EventCoOwner[]>;
};

// ---------------------------------------------------------------------------

/**
 * POST /manage/events/:id/co-owners/
 *
 * Add one or more users as co-owners of the event.
 * Co-owners receive a notification that they've been granted access.
 * The added users immediately gain full manage permissions on the event.
 *
 * Duplicate user_ids (user is already a co-owner) are silently skipped.
 * The event creator cannot be added as a co-owner (they are implicitly the owner).
 *
 * PERMISSION: event creator or existing co-owner.
 *
 * RESPONSES:
 *   201 → EventCoOwner[] (the newly created co-owner records)
 *   400 → Validation error (invalid user_id, user is already creator, etc.)
 *   403 → Insufficient permissions
 */
export type POST_event_co_owners = {
  params: { id: UUID };
  body: {
    co_owners: EventCoOwnerInput[];
  };
  response: SuccessResponse<EventCoOwner[]>;
};

// ---------------------------------------------------------------------------

/**
 * DELETE /manage/events/:id/co-owners/:co_owner_id/
 *
 * Remove a co-owner from the event.
 * The removed user loses all manage permissions on this event immediately.
 * The removed user receives a notification of their removal.
 *
 * The original event creator (created_by) CANNOT be removed — they are
 * the permanent primary owner.
 *
 * PERMISSION: event creator or another co-owner (co-owners can remove each other).
 *   Platform admins can also remove co-owners.
 *
 * RESPONSES:
 *   200 → { message: "Co-owner removed successfully." }
 *   403 → Cannot remove the event creator / insufficient permissions
 *   404 → Co-owner record not found
 */
export type DELETE_event_co_owner = {
  params: { id: UUID; co_owner_id: UUID };
  response: SuccessResponse<{ message: string }>;
};


// ────────────────────────────────────────────────────────────────────────────
// 10.3  SCOPED CONTEXT FEEDS
// Convenience list endpoints for specific dashboard sections.
// Avoid callers needing to manually construct the right filter combinations.
// All support the full EventListQueryParams for additional filtering/sorting.
// Cluster-based filtering via ?cluster=coder|maker|manager|creative is
// available on all these endpoints through EventListQueryParams.
// ────────────────────────────────────────────────────────────────────────────

/**
 * GET /ig/:ig_id/events/
 *
 * All published events for a specific Interest Group.
 * Includes:
 *   • Global IG events (scope=ig, created by the GIG Lead)
 *   • Campus IG events from all campus chapters of this IG (scope=campus_ig)
 * This gives a complete picture of all IG-related activity across all campuses.
 *
 * USED IN: IG Dashboard → Events tab, IG discovery/detail page
 * SCREEN: IG Detail page → Events section
 *
 * ACCESS:
 *   IG members         → full access including all campus chapter events
 *   Non-members        → only global-scope IG events (scope=ig)
 *   Unauthenticated    → only global-scope IG events
 */
export type GET_ig_events = {
  params: { ig_id: UUID };
  query: EventListQueryParams;
  response: SuccessResponse<PaginatedData<EventListItem>>;
};

// ---------------------------------------------------------------------------

/**
 * GET /ig/cluster/:cluster/events/
 *
 * All published events from IGs belonging to a specific cluster.
 * Returns events whose organiser IG or target IG has the matching cluster value.
 *
 * Clusters group IGs into broad categories:
 *   coder    → programming/development IGs
 *   maker    → hardware/IoT/robotics IGs
 *   manager  → product/business IGs
 *   creative → design/content IGs
 *
 * USED IN: Events tab → Cluster filter pills, Landing page → cluster sections
 * SCREEN: Events listing page (filtered by cluster)
 *
 * ACCESS: Public — all authenticated users. Unauthenticated users see only
 *         global-scope events from IGs in this cluster.
 */
export type GET_cluster_events = {
  params: { cluster: IGCluster };
  query: EventListQueryParams;
  response: SuccessResponse<PaginatedData<EventListItem>>;
};

// ---------------------------------------------------------------------------

/**
 * GET /campus/:campus_id/events/
 *
 * All published events for a specific campus.
 * Includes:
 *   • Campus events (scope=campus, created by Campus Lead/Enabler)
 *   • Campus IG events from all IG chapters within this campus (scope=campus_ig)
 * Provides the complete events calendar for a campus.
 *
 * USED IN: Campus Dashboard → Events, Student Dashboard → Campus Section,
 *          Campus public page → Events section
 * SCREEN: Campus Detail page → Events section (events listed on campus page)
 *
 * Supports cluster-based filtering via ?cluster=coder|maker|manager|creative
 * to narrow campus events to a specific IG cluster.
 *
 * ACCESS:
 *   Campus members (students, leads) → full access
 *   Non-members / unauthenticated   → only global-scope events targeting this campus
 *   Platform admins                 → full access regardless of campus membership
 */
export type GET_campus_events = {
  params: { campus_id: UUID };
  query: EventListQueryParams;
  response: SuccessResponse<PaginatedData<EventListItem>>;
};

// ---------------------------------------------------------------------------

/**
 * GET /campus-ig/:campus_ig_id/events/
 *
 * Events created by one specific campus IG chapter.
 * Narrower than GET /campus/:id/events/ — only this one IG chapter's events,
 * not all events happening at the campus.
 *
 * USED IN: Campus IG Lead Dashboard, per-chapter view within the Campus Dashboard
 *
 * ACCESS: campus members who are also members of this specific IG chapter.
 */
export type GET_campus_ig_events = {
  params: { campus_ig_id: UUID };
  query: EventListQueryParams;
  response: SuccessResponse<PaginatedData<EventListItem>>;
};

// ---------------------------------------------------------------------------

/**
 * GET /company/:company_id/events/
 *
 * All published events organised by a specific company/partner.
 * Companies post events (tech talks, hiring challenges, workshops) to engage
 * with the μLearn student community and discover talent.
 *
 * USED IN: Company public profile page, μVerse opportunities board
 *
 * PUBLIC — all authenticated users can browse company events.
 */
export type GET_company_events = {
  params: { company_id: UUID };
  query: EventListQueryParams;
  response: SuccessResponse<PaginatedData<EventListItem>>;
};


// ────────────────────────────────────────────────────────────────────────────
// 10.4  ADMIN ENDPOINTS
// Platform-wide oversight, moderation, approval, and curation.
// All require the authenticated user to have "admin" or "zonal_lead" role.
// ────────────────────────────────────────────────────────────────────────────

/**
 * GET /admin/events/
 *
 * Full platform event listing — ALL events, ALL statuses, ALL organiser types.
 * Used by platform admins for oversight, content moderation, support, and analytics.
 *
 * Extends EventListQueryParams with admin-only filter options:
 *   organizer_type → filter by the type of entity that created the event
 *   created_by     → filter by the specific user UUID who created the event
 */
export type GET_admin_events = {
  query: EventListQueryParams & {
    /** Filter by organiser entity type — e.g. show only company events */
    organizer_type?: OrganizerType;
    /** Filter by the UUID of the user who created the event */
    created_by?: UUID;
  };
  response: SuccessResponse<PaginatedData<EventListItem>>;
};

// ---------------------------------------------------------------------------

/**
 * POST /admin/events/:id/approve/
 *
 * Approve a pending event. The resulting status depends on the CURRENT status
 * and which approval level this satisfies:
 *
 * ┌───────────────────────────────┬─────────────────┬────────────────────────┐
 * │ Current Status                │ Who Approves    │ New Status             │
 * ├───────────────────────────────┼─────────────────┼────────────────────────┤
 * │ pending_campus_approval       │ Campus Lead     │ pending_approval       │
 * │   (campus IG event, step 1)   │                 │  → auto-notifies GIG  │
 * │                               │                 │    Lead for step 2     │
 * ├───────────────────────────────┼─────────────────┼────────────────────────┤
 * │ pending_approval              │ GIG Lead        │ published              │
 * │   (campus IG event, step 2)   │ or Admin        │  → event goes live     │
 * ├───────────────────────────────┼─────────────────┼────────────────────────┤
 * │ pending_mentor_approval       │ Mentor          │ published              │
 * │   (GIG Lead–created event)    │ or Admin        │  → event goes live     │
 * └───────────────────────────────┴─────────────────┴────────────────────────┘
 *
 * WHO CAN CALL THIS:
 *   Campus Lead   → can approve events in "pending_campus_approval" for their
 *                   campus only (step 1 of campus IG approval)
 *   Global IG Lead → can approve campus_ig events in "pending_approval" for
 *                    their own IG only (step 2 of campus IG approval)
 *   Mentor         → can approve events in "pending_mentor_approval"
 *                    (GIG Lead–created events awaiting mentor sign-off)
 *   Platform Admin → can approve ANY pending event at ANY stage
 *
 * SIDE EFFECTS:
 *   • Event status transitions as per the table above
 *   • If transitioning to "pending_approval" (from campus approval):
 *     → GIG Lead is notified that their approval is now needed
 *   • If transitioning to "published":
 *     → Event becomes immediately visible to its target audience
 *     → Organiser receives an approval notification
 *   • Optional `note` is included in the notification email to the organiser
 *
 * RESPONSES:
 *   200 → EventDetail with updated status
 *   400 → Event is not in a pending_* status
 *   403 → Authenticated user lacks approval authority for this event/stage
 */
export type POST_admin_event_approve = {
  params: { id: UUID };
  body: {
    /** Optional note included in the approval notification email to the organiser */
    note?: string;
  };
  response: SuccessResponse<EventDetail>;
};

// ---------------------------------------------------------------------------

/**
 * POST /admin/events/:id/reject/
 *
 * Reject a pending event → transitions ANY pending_* status back to "draft".
 * The organiser is notified with the rejection reason so they can fix and re-submit.
 *
 * Works for all pending statuses:
 *   pending_campus_approval  → draft (Campus Lead rejects at step 1)
 *   pending_approval         → draft (GIG Lead rejects at step 2)
 *   pending_mentor_approval  → draft (Mentor rejects GIG Lead's event)
 *
 * WHO CAN CALL THIS:
 *   Campus Lead    → can reject events in "pending_campus_approval" for their campus
 *   Global IG Lead → can reject events in "pending_approval" for their own IG
 *   Mentor         → can reject events in "pending_mentor_approval"
 *   Platform Admin → can reject any pending event
 *
 * SIDE EFFECTS:
 *   • Event status reverts to "draft" — invisible to all except organiser and admins
 *   • Organiser receives a rejection notification containing the reason
 *   • Organiser can edit the event and re-submit via POST /manage/events/:id/publish/
 *
 * RESPONSES:
 *   200 → EventDetail with status = "draft"
 *   400 → Event is not in a pending_* status; or reason is empty/missing
 *   403 → Authenticated user lacks rejection authority for this event/stage
 */
export type POST_admin_event_reject = {
  params: { id: UUID };
  body: {
    /** Required — sent to the organiser in the rejection notification email */
    reason: string;
  };
  response: SuccessResponse<EventDetail>;
};

// ---------------------------------------------------------------------------

/**
 * PATCH /admin/events/:id/feature/
 *
 * Toggle whether an event appears in the homepage featured slider.
 * is_featured = true  → event enters the curated carousel (GET /events/featured/)
 * is_featured = false → event is removed from the carousel
 *
 * Admins manually curate the featured set; typically 6–10 events at a time.
 * Only platform admins can call this — ignored/rejected for all other roles.
 *
 * RESPONSES:
 *   200 → EventDetail with updated is_featured value
 *   403 → Authenticated user is not a platform admin
 */
export type PATCH_admin_event_feature = {
  params: { id: UUID };
  body: { is_featured: boolean };
  response: SuccessResponse<EventDetail>;
};


// ────────────────────────────────────────────────────────────────────────────
// 10.5  COLLABORATION INVITE ENDPOINTS
// Manages the full invite lifecycle for multi-entity event co-hosting.
// Only the event creator or co-owners can add or remove collaborators.
// Collaborators can only accept or reject their own invite — they cannot
// edit the event, invite others, or remove co-hosts.
// ────────────────────────────────────────────────────────────────────────────

/**
 * GET /manage/events/:id/collaborators/
 *
 * Returns ALL collaborators for an event, including pending and rejected invites.
 * The public event detail endpoint only shows "accepted" collaborators.
 * This endpoint gives the event creator full visibility into invite progress.
 *
 * PERMISSION: event creator, co-owner, or platform admin.
 */
export type GET_event_collaborators = {
  params: { id: UUID };
  response: SuccessResponse<EventCollaborator[]>;
};

// ---------------------------------------------------------------------------

/**
 * POST /manage/events/:id/collaborators/
 *
 * Invite one or more entities to co-host the event.
 * Any combination of IGs, campuses, campus IGs, and companies can be invited together.
 *
 * Invitation notifications are sent to the lead of each invited entity:
 *   ig         → notification sent to the Global IG Lead of that IG
 *   campus     → notification sent to the Campus Lead
 *   campus_ig  → notification sent to the Campus IG Lead of that chapter
 *   company    → notification sent to the Company admin user
 *
 * Duplicate invites (same entity already invited) are silently skipped.
 * Invites can be sent while the event is still in "draft" status.
 * Returns the newly created EventCollaborator records with invite_status = "pending".
 *
 * PERMISSION: event creator or co-owner.
 */
export type POST_event_collaborators = {
  params: { id: UUID };
  body: {
    /**
     * One or more collaborators to invite. Mix types freely.
     * Uses the discriminated CollaboratorInput union — see Section 2.
     */
    collaborators: CollaboratorInput[];
  };
  response: SuccessResponse<EventCollaborator[]>;
};

// ---------------------------------------------------------------------------

/**
 * DELETE /manage/events/:id/collaborators/:collaborator_id/
 *
 * Remove a collaborator from the event, regardless of their current invite_status.
 * The removed entity receives a removal notification.
 * Their name and logo are immediately removed from the event page.
 * Can be re-invited later by the event creator if needed.
 *
 * PERMISSION: event creator, co-owner, or platform admin.
 *
 * RESPONSES:
 *   200 → { detail: "Collaborator removed successfully." }
 *   403 → Not the event creator or admin
 *   404 → Collaborator record not found on this event
 */
export type DELETE_event_collaborator = {
  params: { id: UUID; collaborator_id: UUID };
  response: SuccessResponse<{ message: string }>;
};

// ---------------------------------------------------------------------------

/**
 * POST /manage/events/:id/collaborators/:collaborator_id/accept/
 *
 * The lead of the invited entity formally accepts the collaboration invite.
 *
 * EFFECT:
 *   invite_status transitions from "pending" → "accepted"
 *   The entity's name, logo, and role_label become publicly visible on the event page
 *   The event creator receives an acceptance notification
 *
 * WHO CAN CALL THIS (only the lead of the invited entity):
 *   collaborator_type = "ig"        → Global IG Lead of that IG
 *   collaborator_type = "campus"    → Campus Lead of that campus
 *   collaborator_type = "campus_ig" → Campus IG Lead of that chapter
 *   collaborator_type = "company"   → Company admin user
 *   Backend verifies the authenticated user holds the correct lead role.
 *
 * RESPONSES:
 *   200 → EventCollaborator with invite_status = "accepted"
 *   403 → Authenticated user is not the lead of the invited entity
 *   409 → Invite has already been accepted or rejected
 */
export type POST_event_collaborator_accept = {
  params: { id: UUID; collaborator_id: UUID };
  response: SuccessResponse<EventCollaborator>;
};

// ---------------------------------------------------------------------------

/**
 * POST /manage/events/:id/collaborators/:collaborator_id/reject/
 *
 * The lead of the invited entity rejects the collaboration invite.
 *
 * EFFECT:
 *   invite_status transitions from "pending" → "rejected"
 *   The entity does NOT appear on the event page
 *   The event creator is notified with the rejection reason
 *   The creator can re-invite the same entity later if desired
 *
 * `reason` is optional but strongly encouraged — helps the event creator understand
 * why the collaboration was declined (scheduling conflict, capacity constraints, etc.)
 *
 * WHO CAN CALL THIS: same auth rules as the accept endpoint above.
 */
export type POST_event_collaborator_reject = {
  params: { id: UUID; collaborator_id: UUID };
  body: {
    /** Optional explanation sent to the event creator via notification */
    reason?: string;
  };
  response: SuccessResponse<EventCollaborator>;
};


// ────────────────────────────────────────────────────────────────────────────
// 10.6  META / HELPER ENDPOINTS
// Utility endpoints for populating form selectors in the event creation flow.
// Call these when the Create Event form first mounts to populate dropdowns.
// ────────────────────────────────────────────────────────────────────────────

/**
 * GET /events/meta/organizer-options/
 *
 * Returns all entities the authenticated user is authorised to create events for.
 * Used to populate the "Create as..." organiser selector at the top of the
 * event creation form.
 *
 * EXAMPLE RESPONSES BY ROLE:
 *   GIG Lead of "Web Dev IG":
 *     { can_create_as_ig: [{ id, name: "Web Dev IG" }], rest: empty }
 *
 *   CIG Lead of "AI IG @ CET Trivandrum":
 *     { can_create_as_campus_ig: [{ id, ig: {...}, campus: {...} }], rest: empty }
 *
 *   Campus Lead of "CET Trivandrum":
 *     { can_create_as_campus: [{ id, name: "CET Trivandrum" }], rest: empty }
 *
 *   Company admin at "TinkerHub":
 *     { can_create_as_company: [{ id, name: "TinkerHub" }], rest: empty }
 *
 *   Platform Admin:
 *     { can_create_as_admin: true, all arrays fully populated }
 *
 * A user can hold multiple roles simultaneously (e.g. both a GIG Lead and a CIG Lead).
 * In that case, multiple arrays will be non-empty — the form should present all options.
 */
export type GET_events_organizer_options = {
  response: {
    /** IGs the user leads — allows creating global IG events */
    can_create_as_ig: MinimalIG[];

    /** Campus IG chapters the user leads — allows creating campus IG events */
    can_create_as_campus_ig: MinimalCampusIG[];

    /** Campuses the user leads — allows creating campus events */
    can_create_as_campus: MinimalCampus[];

    /** Companies the user administers — allows creating company events */
    can_create_as_company: MinimalCompany[];

    /** True only for platform admins — unlocks all organiser options and all scopes */
    can_create_as_admin: boolean;
  }>;
};

// ---------------------------------------------------------------------------

/**
 * GET /events/meta/collaboration-targets/
 *
 * Searches for entities that can be added as event collaborators.
 * Powers the live-search input in the collaboration section of the event creation form.
 *
 * Omit `type` to search across ALL entity types simultaneously — ideal for a
 * unified search box where the user types a name and sees IGs, campuses, campus
 * IG chapters, and companies all in one result list.
 *
 * Specify `type` to restrict results to one entity category — ideal for
 * tab-separated selectors (separate tabs for IGs / Campuses / Companies).
 *
 * Each result is tagged with `collaborator_type` so the frontend can render
 * the correct icon and entity-specific display for each result row.
 *
 * EXAMPLE:
 *   User types "Kerala" →
 *   GET /events/meta/collaboration-targets/?search=Kerala
 *   Returns all matching IGs, campuses, campus IG chapters, and companies
 *   containing "Kerala" in their name, each with collaborator_type set.
 */
export type GET_events_collaboration_targets = {
  query: {
    /** Omit to search all entity types at once */
    type?: CollaboratorType;

    /** Substring search on entity name — case-insensitive */
    search?: string;

    page?: number;
    page_size?: number;
  };
  response: SuccessResponse<PaginatedData<
    | ({ collaborator_type: "ig" }        & MinimalIG)
    | ({ collaborator_type: "campus" }    & MinimalCampus)
    | ({ collaborator_type: "campus_ig" } & MinimalCampusIG)
    | ({ collaborator_type: "company" }   & MinimalCompany)
  >>;
};


// ============================================================================
// SECTION 11 — ERROR RESPONSES
// ============================================================================

/**
 * HTTP status codes used by this API with their meanings in context:
 *
 * 200 OK           → successful GET / PATCH / DELETE
 * 201 Created      → successful POST that created a new resource
 * 400 Bad Request  → validation error (hasError=true; check message fields)
 * 401 Unauthorized → missing or invalid/expired auth token
 * 403 Forbidden    → authenticated but lacking the required permission
 *                    (returned via get_unauthorized_response with statusCode=403)
 * 404 Not Found    → resource doesn't exist or is outside the viewer's scope
 * 409 Conflict     → state conflict (e.g. publishing a non-draft event)
 * 500 Server Error → unexpected backend error
 *
 * NOTE: The backend wraps ALL responses in the envelope shape:
 *   SuccessResponse<T> when hasError = false
 *   FailureResponse    when hasError = true
 * See those interfaces above for the full shape.
 *
 * ERROR EXAMPLES (inside the `message` field of FailureResponse):
 *   Non-field:  { general: ["You do not have permission to perform this action."] }
 *   Field-level:{ general: [], title: ["This field may not be blank."] }
 *   Mixed:      { general: ["Event creation failed."], min_karma: ["Must be non-negative."] }
 */
export type HTTPStatus = 200 | 201 | 400 | 401 | 403 | 404 | 409 | 500;


// ============================================================================
// SECTION 13 — SCREEN-BY-SCREEN API MAPPING
// ============================================================================
// Documents which API endpoints are consumed by each screen of the application.
// Enables frontend and backend teams to trace exactly which endpoints power
// each UI view.
// ============================================================================

/**
 * ┌─────────────────────────────────────────────────────────────────────────────┐
 * │ SCREEN-BY-SCREEN API MAPPING                                               │
 * ├────────────────────────────────┬────────────────────────────────────────────┤
 * │ Screen / Page                 │ APIs Used                                  │
 * ├────────────────────────────────┼────────────────────────────────────────────┤
 * │                                                                            │
 * │ ── HOME / LANDING PAGE ──────────────────────────────────────────────────  │
 * │                                                                            │
 * │ Home Screen                   │ GET  events/featured/                      │
 * │   Featured events carousel    │   → fetches featured events for slider     │
 * │                               │                                            │
 * │ Landing Page                  │ GET  events/                               │
 * │   All events listing          │   → main feed with filters                 │
 * │                               │ GET  events/featured/                      │
 * │                               │   → featured section at top                │
 * │                                                                            │
 * │ ── EVENTS TAB ───────────────────────────────────────────────────────────  │
 * │                                                                            │
 * │ Events Listing (All)          │ GET  events/                               │
 * │                               │   → paginated, filterable event feed       │
 * │                               │   ?cluster=coder|maker|manager|creative    │
 * │                               │   → cluster filter pills                   │
 * │                               │   ?event_type=hackathon|workshop|...       │
 * │                               │   → type filter dropdown                   │
 * │                               │   ?status=published|ongoing               │
 * │                               │   → status tabs (upcoming/live)            │
 * │                               │   ?search=<query>                          │
 * │                               │   → search bar                             │
 * │                                                                            │
 * │ Event Detail Page             │ GET  events/:id/                           │
 * │                               │   → full event info, venue, tasks, etc.    │
 * │                               │ POST events/:id/interest/                  │
 * │                               │   → "I'm Going" button                     │
 * │                               │ DEL  events/:id/interest/                  │
 * │                               │   → remove interest                        │
 * │                                                                            │
 * │ ── MANAGE EVENTS SCREEN ─────────────────────────────────────────────────  │
 * │ (Campus leads, Company users, IG leads, Admins — sidebar item)             │
 * │                                                                            │
 * │ Manage Events List            │ GET  manage/events/                        │
 * │                               │   → all events user can manage (all status)│
 * │                                                                            │
 * │ Create Event                  │ GET  events/meta/organizer-options/        │
 * │                               │   → populate "Create as..." dropdown       │
 * │                               │ GET  events/meta/collaboration-targets/    │
 * │                               │   → search for collaborator entities       │
 * │                               │ POST manage/events/                        │
 * │                               │   → submit the new event                   │
 * │                                                                            │
 * │ Edit Event                    │ GET  manage/events/:id/                    │
 * │                               │   → load event with edit history           │
 * │                               │ PUT  manage/events/:id/                    │
 * │                               │   → full update                            │
 * │                               │ PATCH manage/events/:id/                   │
 * │                               │   → partial update                         │
 * │                                                                            │
 * │ Publish Event                 │ POST manage/events/:id/publish/            │
 * │                               │   → transition draft → published/pending   │
 * │                                                                            │
 * │ Cancel Event                  │ DEL  manage/events/:id/                    │
 * │                               │   → soft delete (status → cancelled)       │
 * │                                                                            │
 * │ Manage Co-Owners              │ GET  manage/events/:id/co-owners/          │
 * │                               │   → list current co-owners                 │
 * │                               │ POST manage/events/:id/co-owners/          │
 * │                               │   → add co-owners (full authority grant)   │
 * │                               │ DEL  manage/events/:id/co-owners/:coid/    │
 * │                               │   → remove a co-owner                      │
 * │                                                                            │
 * │ Manage Collaborators          │ GET  manage/events/:id/collaborators/      │
 * │                               │   → all collaborator invites               │
 * │                               │ POST manage/events/:id/collaborators/      │
 * │                               │   → invite new collaborators               │
 * │                               │ DEL  manage/events/:id/collaborators/:cid/ │
 * │                               │   → remove collaborator                    │
 * │                                                                            │
 * │ Accept/Reject Collaboration   │ POST manage/events/:id/collaborators/      │
 * │                               │      :cid/accept/                          │
 * │                               │ POST manage/events/:id/collaborators/      │
 * │                               │      :cid/reject/                          │
 * │                                                                            │
 * │ ── CAMPUS PAGE ──────────────────────────────────────────────────────────  │
 * │                                                                            │
 * │ Campus Detail → Events        │ GET  campus/:campus_id/events/             │
 * │                               │   → events at this campus                  │
 * │                               │   ?cluster=coder|maker|manager|creative    │
 * │                               │   → filter by IG cluster within campus     │
 * │                                                                            │
 * │ ── IG PAGE ──────────────────────────────────────────────────────────────  │
 * │                                                                            │
 * │ IG Detail → Events            │ GET  ig/:ig_id/events/                     │
 * │                               │   → all events for this IG                 │
 * │                                                                            │
 * │ Cluster Events                │ GET  ig/cluster/:cluster/events/           │
 * │                               │   → all events from IGs in this cluster    │
 * │                                                                            │
 * │ ── CAMPUS IG PAGE ───────────────────────────────────────────────────────  │
 * │                                                                            │
 * │ Campus IG → Events            │ GET  campus-ig/:campus_ig_id/events/       │
 * │                               │   → events for this specific IG chapter    │
 * │                                                                            │
 * │ ── COMPANY PAGE ─────────────────────────────────────────────────────────  │
 * │                                                                            │
 * │ Company Profile → Events      │ GET  company/:company_id/events/           │
 * │                               │   → events by this company                 │
 * │                                                                            │
 * │ ── ADMIN DASHBOARD ──────────────────────────────────────────────────────  │
 * │                                                                            │
 * │ Admin Events Overview         │ GET  admin/events/                         │
 * │                               │   → all events, all statuses, all types    │
 * │                                                                            │
 * │ Approve Pending Event         │ POST admin/events/:id/approve/             │
 * │                               │   → pending_approval → published           │
 * │                                                                            │
 * │ Reject Pending Event          │ POST admin/events/:id/reject/              │
 * │                               │   → pending_approval → draft               │
 * │                                                                            │
 * │ Feature/Unfeature Event       │ PATCH admin/events/:id/feature/            │
 * │                               │   → toggle homepage featured status        │
 * └────────────────────────────────┴────────────────────────────────────────────┘
 */


// ============================================================================
// SECTION 12 — ROUTER SUMMARY & PERMISSION MATRIX
// ============================================================================

/**
 * ┌─────────────────────────────────────────────────────────────────────────┐
 * │ ROUTE SUMMARY — /api/v1/                                                │
 * ├──────────────────────────────────────────────┬──────────────────────────┤
 * │ Endpoint                                     │ Purpose                  │
 * ├──────────────────────────────────────────────┼──────────────────────────┤
 * │ GET  events/                                 │ Viewer-scoped event feed  │
 * │ GET  events/featured/                        │ Homepage slider (public)  │
 * │ GET  events/:id/                             │ Event detail page         │
 * │ POST events/:id/interest/                    │ Click "I'm Going"         │
 * │ DEL  events/:id/interest/                    │ Remove "I'm Going"        │
 * ├──────────────────────────────────────────────┼──────────────────────────┤
 * │ GET  manage/events/                          │ My managed events list    │
 * │ POST manage/events/                          │ Create a new event        │
 * │ GET  manage/events/:id/                      │ Manage view + audit log   │
 * │ PUT  manage/events/:id/                      │ Full event update         │
 * │ PAT  manage/events/:id/                      │ Partial event update      │
 * │ DEL  manage/events/:id/                      │ Cancel event (soft)       │
 * │ POST manage/events/:id/publish/              │ Publish from draft        │
 * ├──────────────────────────────────────────────┼──────────────────────────┤
 * │ GET  manage/events/:id/co-owners/            │ List co-owners            │
 * │ POST manage/events/:id/co-owners/            │ Add co-owners             │
 * │ DEL  manage/events/:id/co-owners/:coid       │ Remove a co-owner         │
 * ├──────────────────────────────────────────────┼──────────────────────────┤
 * │ GET  manage/events/:id/collaborators/        │ All invite statuses       │
 * │ POST manage/events/:id/collaborators/        │ Invite collaborators      │
 * │ DEL  manage/events/:id/collaborators/:cid    │ Remove a collaborator     │
 * │ POST manage/events/:id/collaborators/        │                           │
 * │      :cid/accept/                            │ Accept collaboration      │
 * │ POST manage/events/:id/collaborators/        │                           │
 * │      :cid/reject/                            │ Reject collaboration      │
 * ├──────────────────────────────────────────────┼──────────────────────────┤
 * │ GET  ig/:ig_id/events/                       │ IG dashboard event feed   │
 * │ GET  ig/cluster/:cluster/events/             │ Cluster event feed        │
 * │ GET  campus/:campus_id/events/               │ Campus page event list    │
 * │ GET  campus-ig/:campus_ig_id/events/         │ Campus IG chapter events  │
 * │ GET  company/:company_id/events/             │ Company event feed        │
 * ├──────────────────────────────────────────────┼──────────────────────────┤
 * │ GET  admin/events/                           │ All events (admin view)   │
 * │ POST admin/events/:id/approve/               │ Approve pending event     │
 * │ POST admin/events/:id/reject/                │ Reject pending event      │
 * │ PAT  admin/events/:id/feature/               │ Toggle homepage slider    │
 * ├──────────────────────────────────────────────┼──────────────────────────┤
 * │ GET  events/meta/organizer-options/          │ "Create as" selector      │
 * │ GET  events/meta/collaboration-targets/      │ Collaborator search       │
 * └──────────────────────────────────────────────┴──────────────────────────┘
 *
 * PERMISSION MATRIX:
 * ┌──────────────────────────────┬───────┬───────┬───────┬────────┬─────────┐
 * │ Action                       │ User  │ CIG   │ GIG   │ Campus │ Company │
 * │                              │       │ Lead  │ Lead  │ Lead   │         │
 * ├──────────────────────────────┼───────┼───────┼───────┼────────┼─────────┤
 * │ Browse eligible events       │  ✅   │  ✅   │  ✅   │  ✅   │  ✅     │
 * │ Click "I'm Going"            │  ✅   │  ✅   │  ✅   │  ✅   │  ✅     │
 * │ Create campus IG event       │  ❌   │  ✅   │  ❌   │  ✅²  │  ❌     │
 * │ Create campus event          │  ❌   │  ❌   │  ❌   │  ✅   │  ❌     │
 * │ Create global IG event       │  ❌   │  ❌   │  ✅   │  ❌   │  ❌     │
 * │ Create company event         │  ❌   │  ❌   │  ❌   │  ❌   │  ✅     │
 * │ Edit / delete own events     │  ❌   │  ✅   │  ✅   │  ✅   │  ✅     │
 * │ Edit / delete as co-owner   │  ✅*¹ │  ✅*¹ │  ✅*¹ │  ✅*¹ │  ✅*¹   │
 * │ Add / remove co-owners      │  ❌   │  ✅   │  ✅   │  ✅   │  ✅     │
 * │ Invite collaborators         │  ❌   │  ✅   │  ✅   │  ✅   │  ✅     │
 * │ Accept / reject invite       │  ❌   │  ✅*  │  ✅*  │  ✅*  │  ✅*    │
 * │ Approve campus IG (step 1)  │  ❌   │  ❌   │  ❌   │  ✅³  │  ❌     │
 * │ Approve campus IG (step 2)  │  ❌   │  ❌   │  ✅†  │  ❌   │  ❌     │
 * │ Approve GIG Lead events     │  ❌   │  ❌   │  ❌   │  ❌   │  ❌     │
 * │   (mentor approval)          │ Mentor role only                        │
 * │ Feature events (homepage)    │  ❌   │  ❌   │  ❌   │  ❌   │  ❌     │
 * │ All actions above            │  ❌   │  ❌   │  ❌   │  ❌   │  ❌     │
 * │   + admin-only actions       │ Admin only (platform admin role)         │
 * └──────────────────────────────┴───────┴───────┴───────┴────────┴─────────┘
 *  *  Only if the user is the lead of the invited entity
 *  *¹ Any user can edit/delete events they are a co-owner of,
 *     regardless of their organisational role.
 *  ²  Campus Lead can create campus_ig events for chapters within their
 *     campus. Campus approval is auto-skipped (they ARE the campus approver);
 *     only GIG Lead approval is required (goes straight to pending_approval).
 *  ³  Campus Lead approves campus IG events (step 1): transitions
 *     pending_campus_approval → pending_approval. Auto-notifies GIG Lead.
 *  †  GIG Lead approves campus_ig events (step 2) within their own IG:
 *     transitions pending_approval → published.
 *     Platform Admin can approve any pending event at any stage.
 *     Mentor approves GIG Lead–created events (pending_mentor_approval).
 *     Homepage featured toggle is platform admin only.
 *
 * ============================================================================
 * KEY DESIGN DECISIONS
 * ============================================================================
 *
 * 1. REGISTRATION IS FULLY EXTERNAL
 *    μLearn does not manage registration forms, ticket sales, capacity limits,
 *    waitlists, or attendance. Each event has a registration_url that points to
 *    an external platform (event website, Unstop, Devfolio, Townscript, etc.).
 *    "I'm Going" is a lightweight interest signal — not a registration record.
 *    This keeps the platform focused on learning and discovery, not ticketing.
 *
 * 2. KARMA ELIGIBILITY (min_karma)
 *    A visibility/access gate on the registration URL.
 *    User's TOTAL accumulated karma must be >= min_karma to access the link.
 *    Karma is NOT deducted — it is purely a threshold check.
 *    null min_karma = no requirement; anyone within scope can register.
 *    Blocked users see a clear message: "Requires X karma. You have Y."
 *
 * 3. EVENT CO-OWNERS
 *    Event owners can grant same-level authority to other users by adding
 *    them as co-owners. Co-owners can edit, publish, cancel, manage
 *    collaborators, and add/remove other co-owners. This is per-event
 *    and does not require any organisational role — any user can be a co-owner.
 *
 * 4. COLLABORATION MODEL
 *    Events can be co-hosted by any mix and any count of IGs, campuses,
 *    campus IGs, and companies simultaneously via the CollaboratorInput union.
 *    Each invited entity must ACCEPT the invite before appearing publicly.
 *    Only the event creator or co-owners can add/remove collaborators.
 *    Collaborators are display-only co-hosts — they cannot edit the event.
 *
 * 5. MULTI-LEVEL APPROVAL FLOW
 *    a) CAMPUS IG EVENTS — two-level approval:
 *       Step 1: Campus Lead of the chapter's campus approves
 *               (pending_campus_approval → pending_approval).
 *               If the Campus Lead created the event, step 1 is auto-skipped.
 *       Step 2: Global IG Lead of that IG approves
 *               (pending_approval → published).
 *       This ensures campus chapter events meet both campus standards and
 *       the global IG's quality bar.
 *    b) GIG LEAD EVENTS — mentor approval:
 *       Events created by Global IG Leads go to "pending_mentor_approval".
 *       A user with the "mentor" role must approve before the event goes live.
 *       This provides oversight for IG-level event creation.
 *    c) On rejection at any level, the organiser receives a reason and can
 *       edit the event and re-submit via POST /manage/events/:id/publish/.
 *
 * 6. TWO EVENT RESPONSE SHAPES
 *    EventDetail — rich full object for detail/manage pages
 *    EventListItem — lean card object for feeds and grids
 *    Keeps list endpoints fast even with hundreds of results.
 *
 * 7. SOFT DELETES ONLY
 *    Cancelling an event sets status="cancelled"; the record is never hard-deleted.
 *    This preserves data for analytics, audit trails, and user history.
 *
 * 8. IG CLUSTERS
 *    IGs are grouped into four clusters: coder, maker, manager, creative.
 *    The `cluster` column on interest_group enables:
 *      • Cluster-based event filtering (?cluster=coder on any list endpoint)
 *      • Cluster-scoped event feeds (GET /ig/cluster/:cluster/events/)
 *      • Dashboard segmentation for campus and IG views
 *    This provides a high-level categorisation for event discovery.
 */

/*
================================================================================
SQL MIGRATIONS — Events System
Target DB: MySQL 8.0+
Schema reference: existing μLearn production tables
================================================================================

Conventions used below:
  • id columns  → VARCHAR(36)  UUIDs, matching every existing table
  • audit cols  → created_by / updated_by / deleted_by → FK → user(id)
  • soft delete → deleted_at DATETIME NULL  (NULL = live row)
  • FK actions  → CASCADE on the owning side, SET NULL where a child
                  row should survive the parent being removed

Existing tables referenced (structural changes in M8.1 and M9):
  user, wallet, organization, interest_group,
  user_organization_link, user_ig_link,
  task_list, karma_activity_log

Run sections M1 → M11 in order. Each section is idempotent.

================================================================================
M1. CORE EVENT TABLE
================================================================================
One row per event. Venue details live in event_venue (M3) to avoid a
wide table with many NULLable columns depending on venue type.
Scope / targeting lives in event_scope (M4) for the same reason.
================================================================================
*/

CREATE TABLE IF NOT EXISTS event
(
    id                    VARCHAR(36)  PRIMARY KEY NOT NULL,

    -- Content
    title                 VARCHAR(200)             NOT NULL,
    -- slug is auto-generated from title on the backend (unique, URL-safe)
    slug                  VARCHAR(220)             NOT NULL,
    description           TEXT                     NOT NULL,
    cover_image           VARCHAR(500),
    banner_image          VARCHAR(500),

    -- Classification (mirrors EventType in TS schema)
    event_type            ENUM(
                              'workshop', 'webinar', 'hackathon',
                              'meetup', 'competition', 'social_gathering', 'other'
                          )                        NOT NULL DEFAULT 'other',

    -- Lifecycle (mirrors EventStatus in TS schema)
    status                ENUM(
                              'draft', 'pending_campus_approval',
                              'pending_approval', 'pending_mentor_approval',
                              'published', 'ongoing', 'completed', 'cancelled'
                          )                        NOT NULL DEFAULT 'draft',

    -- Dates
    start_datetime        DATETIME                 NOT NULL,
    end_datetime          DATETIME                 NOT NULL,

    -- External registration (registration is fully handled outside μLearn)
    registration_url      VARCHAR(500),
    registration_deadline DATETIME,

    -- Karma eligibility gate.
    -- Viewer's wallet.karma must be >= this value to see the registration_url.
    -- NULL = no requirement.  NOT deducted — purely a threshold check.
    min_karma             BIGINT       UNSIGNED    DEFAULT NULL,

    -- Collaboration & curation flags
    is_collaboration      BOOLEAN      DEFAULT FALSE NOT NULL,
    is_featured           BOOLEAN      DEFAULT FALSE NOT NULL,

    -- Denormalised counter kept in sync by triggers (see M7)
    interest_count        INT UNSIGNED DEFAULT 0    NOT NULL,

    -- Audit (matches pattern used across all existing μLearn tables)
    created_by            VARCHAR(36)              NOT NULL,
    created_at            DATETIME                 NOT NULL,
    updated_by            VARCHAR(36)              NOT NULL,
    updated_at            DATETIME                 NOT NULL,
    deleted_at            DATETIME,
    deleted_by            VARCHAR(36),

    CONSTRAINT uq_event_slug           UNIQUE (slug),
    CONSTRAINT chk_event_dates         CHECK  (end_datetime > start_datetime),
    CONSTRAINT chk_event_min_karma     CHECK  (min_karma IS NULL OR min_karma >= 0),

    CONSTRAINT fk_event_created_by     FOREIGN KEY (created_by) REFERENCES user (id) ON DELETE RESTRICT,
    CONSTRAINT fk_event_updated_by     FOREIGN KEY (updated_by) REFERENCES user (id) ON DELETE RESTRICT,
    CONSTRAINT fk_event_deleted_by     FOREIGN KEY (deleted_by) REFERENCES user (id) ON DELETE SET NULL
);

/*
================================================================================
M2. EVENT TAGS
================================================================================
Normalised M2M instead of a CSV column so tag-based filtering is indexable.
A plain VARCHAR("AI,beginners") would require LIKE '%AI%' — no index possible.
================================================================================
*/

CREATE TABLE IF NOT EXISTS event_tag
(
    id         VARCHAR(36)  PRIMARY KEY NOT NULL,
    name       VARCHAR(50)  UNIQUE      NOT NULL,   -- e.g. "AI", "free", "certificate"
    created_at DATETIME                 NOT NULL
);

CREATE TABLE IF NOT EXISTS event_tag_link
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    event_id   VARCHAR(36)             NOT NULL,
    tag_id     VARCHAR(36)             NOT NULL,
    created_at DATETIME                NOT NULL,

    CONSTRAINT uq_event_tag_link        UNIQUE      (event_id, tag_id),
    CONSTRAINT fk_etl_event             FOREIGN KEY (event_id) REFERENCES event     (id) ON DELETE CASCADE,
    CONSTRAINT fk_etl_tag               FOREIGN KEY (tag_id)   REFERENCES event_tag (id) ON DELETE CASCADE
);

/*
================================================================================
M3. EVENT VENUE
================================================================================
1-to-1 with event. Extracted to avoid 6+ nullable columns on the main table
and to allow clean CHECK constraints per venue_type.
================================================================================
*/

CREATE TABLE IF NOT EXISTS event_venue
(
    id           VARCHAR(36) PRIMARY KEY NOT NULL,
    event_id     VARCHAR(36) UNIQUE      NOT NULL,   -- enforces 1-to-1
    venue_type   ENUM('physical','online','hybrid') NOT NULL,

    -- Physical / hybrid
    address      VARCHAR(300),
    city         VARCHAR(100),
    maps_url     VARCHAR(500),

    -- Online / hybrid
    online_link  VARCHAR(500),
    platform     VARCHAR(100),                        -- "Zoom", "Google Meet", "Discord" …

    created_at   DATETIME NOT NULL,
    updated_at   DATETIME NOT NULL,

    CONSTRAINT fk_event_venue_event FOREIGN KEY (event_id) REFERENCES event (id) ON DELETE CASCADE
);

/*
================================================================================
M4. EVENT SCOPE & TARGETING
================================================================================
1-to-1 with event. Stores which specific campus / IG / campus-IG-chapter the
event is restricted to. All target columns are nullable — only the one that
matches `scope` is populated; the backend enforces this in the serializer.

Maps to existing tables:
  campus          → organization (org_type = 'College')
  ig              → interest_group
  campus_ig       → organization + interest_group pair
                    (no explicit campus_ig table exists; the pair identifies
                     the chapter, matching how user_organization_link +
                     user_ig_link already work together)
================================================================================
*/

CREATE TABLE IF NOT EXISTS event_scope
(
    id               VARCHAR(36) PRIMARY KEY NOT NULL,
    event_id         VARCHAR(36) UNIQUE      NOT NULL,   -- 1-to-1 with event
    scope            ENUM('global','campus','ig','campus_ig') NOT NULL DEFAULT 'global',

    -- Populated when scope = 'campus'
    target_org_id    VARCHAR(36),    -- → organization.id

    -- Populated when scope = 'ig'
    target_ig_id     VARCHAR(36),    -- → interest_group.id

    -- Both populated when scope = 'campus_ig' (identifies the chapter)
    target_ci_org_id VARCHAR(36),    -- → organization.id
    target_ci_ig_id  VARCHAR(36),    -- → interest_group.id

    created_at       DATETIME        NOT NULL,
    updated_at       DATETIME        NOT NULL,

    CONSTRAINT fk_es_event      FOREIGN KEY (event_id)        REFERENCES event          (id) ON DELETE CASCADE,
    CONSTRAINT fk_es_org        FOREIGN KEY (target_org_id)   REFERENCES organization   (id) ON DELETE SET NULL,
    CONSTRAINT fk_es_ig         FOREIGN KEY (target_ig_id)    REFERENCES interest_group (id) ON DELETE SET NULL,
    CONSTRAINT fk_es_ci_org     FOREIGN KEY (target_ci_org_id) REFERENCES organization  (id) ON DELETE SET NULL,
    CONSTRAINT fk_es_ci_ig      FOREIGN KEY (target_ci_ig_id)  REFERENCES interest_group(id) ON DELETE SET NULL
);

/*
================================================================================
M5. EVENT ORGANISER
================================================================================
1-to-1 with event. Tracks which entity type created the event and which
specific entity it is. Same nullable-FK pattern as event_scope.

organiser_type  → which column is non-null
  'global_ig'   → ig_id
  'campus'      → org_id  (organization.org_type = 'College')
  'company'     → org_id  (organization.org_type = 'Company')
  'campus_ig'   → ci_org_id + ci_ig_id
  'admin'       → all NULL (the creating user is sufficient context)
================================================================================
*/

CREATE TABLE IF NOT EXISTS event_organiser
(
    id             VARCHAR(36) PRIMARY KEY NOT NULL,
    event_id       VARCHAR(36) UNIQUE      NOT NULL,
    organiser_type ENUM('global_ig','campus_ig','campus','company','admin') NOT NULL,

    ig_id          VARCHAR(36),    -- → interest_group.id  (global_ig)
    org_id         VARCHAR(36),    -- → organization.id    (campus or company)
    ci_org_id      VARCHAR(36),    -- → organization.id    (campus_ig)
    ci_ig_id       VARCHAR(36),    -- → interest_group.id  (campus_ig)

    created_at     DATETIME        NOT NULL,
    updated_at     DATETIME        NOT NULL,

    CONSTRAINT fk_eo_event    FOREIGN KEY (event_id)  REFERENCES event          (id) ON DELETE CASCADE,
    CONSTRAINT fk_eo_ig       FOREIGN KEY (ig_id)     REFERENCES interest_group (id) ON DELETE SET NULL,
    CONSTRAINT fk_eo_org      FOREIGN KEY (org_id)    REFERENCES organization   (id) ON DELETE SET NULL,
    CONSTRAINT fk_eo_ci_org   FOREIGN KEY (ci_org_id) REFERENCES organization   (id) ON DELETE SET NULL,
    CONSTRAINT fk_eo_ci_ig    FOREIGN KEY (ci_ig_id)  REFERENCES interest_group (id) ON DELETE SET NULL
);

/*
================================================================================
M6. EVENT COLLABORATORS
================================================================================
Many rows per event. Each row = one invited co-host entity.
Same discriminated-nullable-FK pattern as organiser and scope.

collaborator_type  → which column is non-null
  'ig'             → ig_id
  'campus'         → org_id  (org_type = 'College')
  'company'        → org_id  (org_type = 'Company')
  'campus_ig'      → ci_org_id + ci_ig_id

UNIQUE constraints prevent duplicate invites for the same entity on the same event.
Only one constraint fires per row (the others have NULL values, which are
excluded from MySQL unique key checks — this is intentional and correct).
================================================================================
*/

CREATE TABLE IF NOT EXISTS event_collaborator
(
    id                VARCHAR(36) PRIMARY KEY NOT NULL,
    event_id          VARCHAR(36)             NOT NULL,
    collaborator_type ENUM('ig','campus','campus_ig','company') NOT NULL,

    ig_id             VARCHAR(36),    -- → interest_group.id
    org_id            VARCHAR(36),    -- → organization.id  (campus or company)
    ci_org_id         VARCHAR(36),    -- → organization.id  (campus_ig)
    ci_ig_id          VARCHAR(36),    -- → interest_group.id (campus_ig)

    role_label        VARCHAR(100),   -- "Venue Partner", "Sponsor", "Co-organizer" …

    invite_status     ENUM('pending','accepted','rejected') NOT NULL DEFAULT 'pending',
    rejection_reason  VARCHAR(500),
    invited_at        DATETIME        NOT NULL,
    responded_at      DATETIME,

    -- The event creator who sent the invite
    created_by        VARCHAR(36)     NOT NULL,
    created_at        DATETIME        NOT NULL,

    -- Prevent duplicate invites: unique per (event, entity)
    -- MySQL ignores NULLs in unique keys, so only the live column pair fires
    CONSTRAINT uq_ec_ig       UNIQUE (event_id, ig_id),
    CONSTRAINT uq_ec_org      UNIQUE (event_id, org_id),
    CONSTRAINT uq_ec_ci       UNIQUE (event_id, ci_org_id, ci_ig_id),

    CONSTRAINT fk_ec_event    FOREIGN KEY (event_id)  REFERENCES event          (id) ON DELETE CASCADE,
    CONSTRAINT fk_ec_ig       FOREIGN KEY (ig_id)     REFERENCES interest_group (id) ON DELETE CASCADE,
    CONSTRAINT fk_ec_org      FOREIGN KEY (org_id)    REFERENCES organization   (id) ON DELETE CASCADE,
    CONSTRAINT fk_ec_ci_org   FOREIGN KEY (ci_org_id) REFERENCES organization   (id) ON DELETE CASCADE,
    CONSTRAINT fk_ec_ci_ig    FOREIGN KEY (ci_ig_id)  REFERENCES interest_group (id) ON DELETE CASCADE,
    CONSTRAINT fk_ec_created  FOREIGN KEY (created_by) REFERENCES user          (id) ON DELETE RESTRICT
);

/*
================================================================================
M7. EVENT INTEREST ("I'M GOING")
================================================================================
One row per user per event. Lightweight intent signal — NOT a registration.
Drives: event reminder notifications, personal calendar, interest_count.
================================================================================
*/

CREATE TABLE IF NOT EXISTS event_interest
(
    id           VARCHAR(36) PRIMARY KEY NOT NULL,
    event_id     VARCHAR(36)             NOT NULL,
    user_id      VARCHAR(36)             NOT NULL,
    expressed_at DATETIME                NOT NULL,

    CONSTRAINT uq_event_interest         UNIQUE      (event_id, user_id),
    CONSTRAINT fk_ei_event               FOREIGN KEY (event_id) REFERENCES event (id) ON DELETE CASCADE,
    CONSTRAINT fk_ei_user                FOREIGN KEY (user_id)  REFERENCES user  (id) ON DELETE CASCADE
);

/*
================================================================================
M8. EVENT EDIT AUDIT LOG
================================================================================
Lightweight change log for the manage view's edit_history field.
Stores which top-level fields changed on each save — not full diffs.
Uses JSON for changed_fields to avoid a schema change every time a new
event field is added (MySQL 8.0 has native JSON with indexing support).
================================================================================
*/

CREATE TABLE IF NOT EXISTS event_edit_log
(
    id             VARCHAR(36) PRIMARY KEY NOT NULL,
    event_id       VARCHAR(36)             NOT NULL,
    edited_by      VARCHAR(36)             NOT NULL,
    -- e.g. '["title", "venue", "min_karma"]'
    changed_fields JSON                    NOT NULL,
    edited_at      DATETIME                NOT NULL,

    CONSTRAINT fk_eel_event  FOREIGN KEY (event_id)  REFERENCES event (id) ON DELETE CASCADE,
    CONSTRAINT fk_eel_editor FOREIGN KEY (edited_by) REFERENCES user  (id) ON DELETE RESTRICT
);

/*
================================================================================
M8.1. ADD CLUSTER COLUMN TO interest_group
================================================================================
Groups IGs into one of four high-level clusters for event filtering,
discovery, and dashboard segmentation.

Values: 'coder', 'maker', 'manager', 'creative'
Matches the IGCluster type in the TypeScript schema.
================================================================================
*/

ALTER TABLE interest_group
    ADD COLUMN cluster ENUM('coder', 'maker', 'manager', 'creative')
    DEFAULT NULL
    AFTER name;

-- Index for cluster-based event filtering
CREATE INDEX IF NOT EXISTS idx_ig_cluster
    ON interest_group (cluster);

/*
================================================================================
M8.2. EVENT CO-OWNERS TABLE
================================================================================
Many rows per event. Each row = one user granted co-owner authority.
Co-owners have the same edit/manage permissions as the event creator.

The event creator (event.created_by) is the implicit primary owner and
does NOT need a row in this table — they always have full access.
================================================================================
*/

CREATE TABLE IF NOT EXISTS event_co_owner
(
    id         VARCHAR(36) PRIMARY KEY NOT NULL,
    event_id   VARCHAR(36)             NOT NULL,
    user_id    VARCHAR(36)             NOT NULL,
    role       ENUM('co_owner', 'admin') NOT NULL DEFAULT 'co_owner',
    added_by   VARCHAR(36)             NOT NULL,
    added_at   DATETIME                NOT NULL,

    -- One co-owner entry per user per event
    CONSTRAINT uq_eco_event_user  UNIQUE      (event_id, user_id),

    CONSTRAINT fk_eco_event       FOREIGN KEY (event_id) REFERENCES event (id) ON DELETE CASCADE,
    CONSTRAINT fk_eco_user        FOREIGN KEY (user_id)  REFERENCES user  (id) ON DELETE CASCADE,
    CONSTRAINT fk_eco_added_by    FOREIGN KEY (added_by) REFERENCES user  (id) ON DELETE RESTRICT
);

/*
================================================================================
M9. MODIFY task_list — LINK TASKS TO EVENTS
================================================================================
task_list.event already exists as VARCHAR(50).
We rename it to event_id, widen to VARCHAR(36) to hold a UUID,
and add a proper FK to event.id so the relationship is enforced at the DB level.

ON DELETE SET NULL: if an event is cancelled/deleted, the task survives
(it may still be valuable outside the event context).

The old `event` column stored a free-text slug or short name.
After this migration the application must store event.id (UUID) instead.
A one-time data migration (not shown here) should translate any existing
slug values to the matching event.id once the event table is populated.
================================================================================
*/

-- Step 1: drop the existing FK on org_id so we can alter the column safely
--         (task_list has no FK on `event`, so no FK to drop there)
-- Step 2: rename + widen the column
ALTER TABLE task_list
    CHANGE COLUMN `event` `event_id` VARCHAR(36) DEFAULT NULL;

-- Step 3: add the FK — tasks can exist without an event (SET NULL on delete)
ALTER TABLE task_list
    ADD CONSTRAINT fk_task_list_event_id
    FOREIGN KEY (event_id) REFERENCES event (id) ON DELETE SET NULL;

/*
================================================================================
M10. PERFORMANCE INDEXES
================================================================================
Covers the most common query patterns:
  - Event feed (status + start_datetime)
  - Soft-delete filter (deleted_at IS NULL on nearly every query)
  - Featured carousel (is_featured + status)
  - Scope-based visibility lookups
  - Organiser lookups (manage/events/)
  - Collaborator lookups
  - Interest count / user calendar
  - Task-to-event join
  - Tag filtering
  - Audit log per event
================================================================================
*/

-- event: the most common feed filter — status + chronological order
CREATE INDEX IF NOT EXISTS idx_event_status_start
    ON event (status, start_datetime);

-- event: soft-delete filter applied on virtually every query
CREATE INDEX IF NOT EXISTS idx_event_deleted_at
    ON event (deleted_at);

-- event: homepage featured carousel
CREATE INDEX IF NOT EXISTS idx_event_featured
    ON event (is_featured, status);

-- event_scope: resolve which events a given campus can see
CREATE INDEX IF NOT EXISTS idx_es_campus
    ON event_scope (scope, target_org_id);

-- event_scope: resolve which events a given IG can see
CREATE INDEX IF NOT EXISTS idx_es_ig
    ON event_scope (scope, target_ig_id);

-- event_scope: resolve which events a given campus-IG chapter can see
CREATE INDEX IF NOT EXISTS idx_es_campus_ig
    ON event_scope (scope, target_ci_org_id, target_ci_ig_id);

-- event_organiser: all events created by a given IG
CREATE INDEX IF NOT EXISTS idx_eo_ig
    ON event_organiser (organiser_type, ig_id);

-- event_organiser: all events created by a given campus or company (org)
CREATE INDEX IF NOT EXISTS idx_eo_org
    ON event_organiser (organiser_type, org_id);

-- event_organiser: all events created by a given campus-IG chapter
CREATE INDEX IF NOT EXISTS idx_eo_campus_ig
    ON event_organiser (organiser_type, ci_org_id, ci_ig_id);

-- event_collaborator: which events is a given IG collaborating on
CREATE INDEX IF NOT EXISTS idx_ec_ig
    ON event_collaborator (ig_id, invite_status);

-- event_collaborator: which events is a given org collaborating on
CREATE INDEX IF NOT EXISTS idx_ec_org
    ON event_collaborator (org_id, invite_status);

-- event_collaborator: pending invites per event (organiser invite-management view)
CREATE INDEX IF NOT EXISTS idx_ec_event_status
    ON event_collaborator (event_id, invite_status);

-- event_interest: count / check interest per event (also used by trigger)
CREATE INDEX IF NOT EXISTS idx_ei_event
    ON event_interest (event_id);

-- event_interest: user's personal event calendar
CREATE INDEX IF NOT EXISTS idx_ei_user
    ON event_interest (user_id);

-- task_list: join tasks to their event
CREATE INDEX IF NOT EXISTS idx_task_event_id
    ON task_list (event_id);

-- event_tag_link: tag-based event filtering
CREATE INDEX IF NOT EXISTS idx_etl_tag
    ON event_tag_link (tag_id);

-- event_edit_log: audit history per event ordered by time
CREATE INDEX IF NOT EXISTS idx_eel_event_time
    ON event_edit_log (event_id, edited_at);

-- event_co_owner: which events is a given user co-owner of (manage/events/)
CREATE INDEX IF NOT EXISTS idx_eco_user
    ON event_co_owner (user_id);

-- event_co_owner: co-owners per event
CREATE INDEX IF NOT EXISTS idx_eco_event
    ON event_co_owner (event_id);

/*
================================================================================
M11. INTEREST COUNT TRIGGERS
================================================================================
interest_count on event is a denormalised counter. Counting event_interest
rows on every list query adds a correlated subquery or GROUP BY to every
feed request — expensive at scale. Triggers keep the counter exact at zero
extra read cost.

GREATEST(..., 0) guards against the counter going negative due to any
out-of-order deletes that could theoretically occur during bulk operations.
================================================================================
*/

DROP TRIGGER IF EXISTS trg_event_interest_insert;

CREATE TRIGGER trg_event_interest_insert
    AFTER INSERT ON event_interest
    FOR EACH ROW
    UPDATE event
    SET    interest_count = interest_count + 1
    WHERE  id = NEW.event_id;


DROP TRIGGER IF EXISTS trg_event_interest_delete;

CREATE TRIGGER trg_event_interest_delete
    AFTER DELETE ON event_interest
    FOR EACH ROW
    UPDATE event
    SET    interest_count = GREATEST(interest_count - 1, 0)
    WHERE  id = OLD.event_id;

/*
================================================================================
MIGRATION COMPLETE — Summary
================================================================================

New tables created:
  event              core event record
  event_tag          normalised tag dictionary
  event_tag_link     event ↔ tag  M2M
  event_venue        venue details  1-to-1 with event
  event_scope        scope / visibility targeting  1-to-1 with event
  event_organiser    who owns the event  1-to-1 with event
  event_collaborator co-host invites  many-per-event
  event_co_owner     users with full owner-level authority  many-per-event
  event_interest     "I'm Going" signals  many-per-event
  event_edit_log     manage-view audit trail  many-per-event

Modified existing tables:
  task_list.event    renamed → task_list.event_id  VARCHAR(36)
                     + FK → event(id)  ON DELETE SET NULL
                     + index on event_id
  interest_group     + cluster ENUM('coder','maker','manager','creative')
                     + index on cluster

New columns on existing tables:
  event.interest_count       INT UNSIGNED  kept in sync by INSERT/DELETE triggers
  interest_group.cluster     ENUM  groups IGs into coder/maker/manager/creative

Foreign key references used from existing schema:
  user(id)            created_by / updated_by / deleted_by / edited_by / co-owners
  organization(id)    campus and company targeting / organiser / collaborator
  interest_group(id)  IG targeting / organiser / collaborator / cluster filtering
  task_list(id)       (unchanged — karma_activity_log already FKs here)

No existing tables were structurally altered except task_list and interest_group.
================================================================================
*/