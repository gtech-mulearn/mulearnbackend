# Dashboard — Partner API

**Base path:** `/api/v1/dashboard/partner/`  
**Source:** `api/dashboard/partner/`  
**OpenAPI tag:** `Dashboard - Partner`, `Dashboard - Partner Admin`, `Public - Partner`

---

## Table of Contents

| # | Endpoint | Method(s) | Auth / Role |
|---|----------|-----------|-------------|
| 1 | [`register/`](#1-register) | `POST`, `PATCH` | Authenticated user |
| 2 | [`status/`](#2-status) | `GET` | Authenticated user |
| 3 | [`summary/`](#3-summary) | `GET` | Partner |
| 4 | [`profile/`](#4-profile) | `GET`, `PATCH` | Partner |
| 5 | [`profile/public/<slug>/`](#5-profilepublicslug) | `GET` | None (public) |
| 6 | [`events/`](#6-events) | `GET` | Partner |
| 7 | [`admin/list/`](#7-adminlist) | `GET` | Admins |
| 8 | [`admin/<partner_id>/verify/`](#8-adminpartner_idverify) | `PATCH` | Admins |

---

## Overview

### Response envelope

All endpoints return a `CustomResponse` wrapper:

**Success:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Human-readable success message"] },
  "response": {}
}
```

**Failure:**

```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": ["Error summary"],
    "field_name": ["Validation detail"]
  },
  "response": {}
}
```

HTTP status codes follow `statusCode` in the body (typically `400` or `404` on failure).

### Authentication

Most endpoints require a JWT:

```http
Authorization: Bearer <access_token>
```

Exceptions are noted per endpoint (`permission_classes = []`).

### Pagination & search

List endpoints use `CommonUtils.get_paginated_queryset`:

| Query param | Default | Description |
|-------------|---------|-------------|
| `pageIndex` | `1` | Page number |
| `perPage` | `10` | Items per page |
| `search` | — | Case-insensitive search (fields vary per endpoint) |
| `sortBy` | — | Sort key; prefix with `-` for descending |

**Paginated response shape:**

```json
{
  "response": {
    "data": [],
    "pagination": {
      "count": 42,
      "totalPages": 5,
      "isNext": true,
      "isPrev": false,
      "nextPage": 2
    }
  }
}
```

### Partner lifecycle

| `status` value | Meaning |
|----------------|---------|
| `pending` | Awaiting admin verification |
| `verified` | Approved; `Partner` role assigned; profile & events endpoints available |
| `rejected` | Rejected; can `PATCH register/` to resubmit; `rejection_reason` provided |

---

## 1. `register/`

**`POST /api/v1/dashboard/partner/register/`**

Submit a new partner registration for the authenticated user. One registration per user.

**Roles:** Any authenticated user (no `Partner` role required yet)

**Request body:**

```json
{
  "name": "TechBridge Kerala",
  "logo": "https://cdn.example.com/logo.png",
  "description": "We connect learners with industry opportunities.",
  "email": "contact@techbridge.example.com",
  "short_pitch": "We connect learners with industry opportunities in 150 words or less.",
  "location": "Kochi, Kerala",
  "district_id": "district-uuid",
  "state_id": "state-uuid",
  "country_id": "country-uuid",
  "partner_type": "Industry",
  "website_link": "https://techbridge.example.com",
  "social_links": {
    "twitter": "https://twitter.com/techbridge",
    "instagram": "https://instagram.com/techbridge"
  }
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `name` | Yes | Unique partner name; slug auto-generated from name |
| `description` | Yes | Full description of the partner organisation |
| `email` | Yes | Primary contact email |
| `logo` | No | URL to the partner's logo image |
| `short_pitch` | No | Max 900 chars; brief promotional summary |
| `location` | No | Human-readable location string |
| `district_id` | No | UUID FK → `district` table |
| `state_id` | No | UUID FK → `state` table |
| `country_id` | No | UUID FK → `country` table |
| `partner_type` | No | One of: `Industry`, `NGO`, `Academia`, `Government`, `Community`, `Media`, `Startup` |
| `website_link` | No | Partner website URL |
| `social_links` | No | JSON object of platform → URL |

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Partner registration submitted successfully."] },
  "response": {
    "id": "partner-uuid",
    "name": "TechBridge Kerala",
    "slug": "techbridge-kerala",
    "logo": "https://cdn.example.com/logo.png",
    "description": "We connect learners with industry opportunities.",
    "email": "contact@techbridge.example.com",
    "short_pitch": "We connect learners with industry opportunities in 150 words or less.",
    "location": "Kochi, Kerala",
    "district_id": "district-uuid",
    "state_id": "state-uuid",
    "country_id": "country-uuid",
    "partner_type": "Industry",
    "website_link": "https://techbridge.example.com",
    "social_links": {
      "twitter": "https://twitter.com/techbridge",
      "instagram": "https://instagram.com/techbridge"
    },
    "status": "pending",
    "submitted_at": "2024-06-01T10:30:00Z"
  }
}
```

**Common errors:**

| Condition | `statusCode` | Message |
|-----------|-------------|---------|
| Registration already exists for this account | `400` | `"A partner registration already exists for your account."` |
| `name` already taken | `400` | `"A partner with this name already exists."` |

---

**`PATCH /api/v1/dashboard/partner/register/`**

Update a `pending` or `rejected` registration. If status was `rejected`, saving resets `status` to `pending` and clears `rejection_reason`.

**Roles:** Authenticated user (must have an existing registration)

**Request body:** Same fields as POST (partial update supported — send only fields to change).

**Success response:** Updated registration fields (same shape as POST success response).

**Common errors:**

| Condition | `statusCode` | Message |
|-----------|-------------|---------|
| No registration found | `404` | `"No partner registration found for your account."` |
| Partner already `verified` | `400` | `"Your partner is already verified. Use the profile/ endpoint to update."` |

---

## 2. `status/`

**`GET /api/v1/dashboard/partner/status/`**

Check the onboarding status of the authenticated user's partner registration.

**Roles:** Authenticated user

**Request body:** None

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Partner status fetched successfully."] },
  "response": {
    "status": "pending",
    "rejection_reason": null,
    "submitted_at": "2024-06-01T10:30:00Z",
    "verified_at": null
  }
}
```

| `status` value | `rejection_reason` | `verified_at` | Notes |
|----------------|--------------------|---------------|-------|
| `pending` | `null` | `null` | Under admin review |
| `verified` | `null` | ISO timestamp | Full access granted; `Partner` role assigned |
| `rejected` | Reason string | `null` | Resubmit via `PATCH register/` |

**Common errors:**

| Condition | `statusCode` | Message |
|-----------|-------------|---------|
| No registration found | `404` | `"No partner registration found for your account."` |

---

## 3. `summary/`

**`GET /api/v1/dashboard/partner/summary/`**

High-level dashboard summary — event counts, learner engagement totals, and recent activity for the logged-in partner.

**Roles:** Partner (`status = verified`)

**Request body:** None

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Partner summary fetched successfully."] },
  "response": {
    "total_events": 12,
    "active_events": 3,
    "total_learners_engaged": 340,
    "recent_events": [
      {
        "id": "event-uuid",
        "title": "AI Workshop 2024",
        "start_datetime": "2024-07-15T09:00:00Z",
        "learner_count": 80
      }
    ]
  }
}
```

| Field | Source |
|-------|--------|
| `total_events` | Count of events where partner is organiser OR `collab_partner` collaborator |
| `active_events` | Subset of the above with `status IN (published, ongoing)` |
| `total_learners_engaged` | Sum of `user_ticket` connections across all partner events |
| `recent_events` | Last 5 events by `start_datetime DESC` |

**Common errors:**

| Condition | `statusCode` | Message |
|-----------|-------------|---------|
| User is not a verified partner | `403` | `"You do not have permission to access this resource."` |

---

## 4. `profile/`

**`GET /api/v1/dashboard/partner/profile/`**

Retrieve the full profile of the logged-in partner.

**Roles:** Partner (`status = verified`)

**Request body:** None

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Partner profile fetched successfully."] },
  "response": {
    "id": "partner-uuid",
    "name": "TechBridge Kerala",
    "slug": "techbridge-kerala",
    "logo": "https://cdn.example.com/logo.png",
    "description": "We connect learners with industry opportunities.",
    "email": "contact@techbridge.example.com",
    "short_pitch": "We connect learners with industry opportunities in 150 words or less.",
    "location": "Kochi, Kerala",
    "district_id": "district-uuid",
    "state_id": "state-uuid",
    "country_id": "country-uuid",
    "partner_type": "Industry",
    "website_link": "https://techbridge.example.com",
    "social_links": {
      "twitter": "https://twitter.com/techbridge",
      "instagram": "https://instagram.com/techbridge"
    },
    "status": "verified",
    "submitted_at": "2024-06-01T10:30:00Z",
    "verified_at": "2024-06-05T08:00:00Z",
    "created_at": "2024-06-01T10:30:00Z"
  }
}
```

---

**`PATCH /api/v1/dashboard/partner/profile/`**

Update the logged-in partner's profile. Only `verified` partners can use this endpoint.

**Roles:** Partner (`status = verified`)

**Request body:** Any subset of profile fields (partial update supported).

> The following fields are **read-only** after verification and will be ignored if sent:
> `name`, `slug`, `status`, `user_link_id`

**Success response:** Updated profile (same shape as GET response).

**Common errors:**

| Condition | `statusCode` | Message |
|-----------|-------------|---------|
| Partner not found or not verified | `403` | `"Partner profile not found or access denied."` |

---

## 5. `profile/public/<slug>/`

**`GET /api/v1/dashboard/partner/profile/public/<slug>/`**

Public-facing partner profile. Only partners with `status = verified` are accessible.

**Roles:** None (public — no authentication required)

**Path param:** `slug` — the auto-generated unique slug for the partner (e.g. `techbridge-kerala`)

**Request body:** None

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Public partner profile fetched successfully."] },
  "response": {
    "name": "TechBridge Kerala",
    "slug": "techbridge-kerala",
    "logo": "https://cdn.example.com/logo.png",
    "description": "We connect learners with industry opportunities.",
    "short_pitch": "We connect learners with industry opportunities in 150 words or less.",
    "website_link": "https://techbridge.example.com",
    "location": "Kochi, Kerala",
    "district": "Ernakulam",
    "state": "Kerala",
    "country": "India",
    "partner_type": "Industry",
    "social_links": {
      "twitter": "https://twitter.com/techbridge",
      "instagram": "https://instagram.com/techbridge"
    }
  }
}
```

> Note: `email`, `id`, `user_link_id`, audit fields and `status` are **not** exposed on the public profile.

**Common errors:**

| Condition | `statusCode` | Message |
|-----------|-------------|---------|
| Slug not found or partner not `verified` | `404` | `"Partner not found."` |

---

## 6. `events/`

**`GET /api/v1/dashboard/partner/events/`**

List all events where this partner is the **organiser** (`organiser_type = partner`) or an accepted `collab_partner` **collaborator**. Partners can create events via the standard `POST /api/v1/dashboard/events/manage/` endpoint once they hold the `Partner` role.

**Roles:** Partner (`status = verified`)

**Query params (in addition to standard pagination):**

| Param | Description |
|-------|-------------|
| `status` | Filter by event status: `draft`, `published`, `ongoing`, `completed`, `cancelled` |
| `type` | Filter by organiser role: `organiser` or `collaborator` |

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Events fetched successfully."] },
  "response": {
    "data": [
      {
        "id": "event-uuid",
        "title": "AI Workshop 2024",
        "slug": "ai-workshop-2024",
        "status": "completed",
        "start_datetime": "2024-07-15T09:00:00Z",
        "end_datetime": "2024-07-15T17:00:00Z",
        "venue_type": "physical",
        "venue_city": "Kochi",
        "partner_role": "organiser",
        "learner_count": 80,
        "cover_image": "https://cdn.example.com/event-banner.png"
      }
    ],
    "pagination": {
      "count": 12,
      "totalPages": 2,
      "isNext": true,
      "isPrev": false,
      "nextPage": 2
    }
  }
}
```

| `partner_role` value | Meaning |
|----------------------|---------|
| `organiser` | Partner created the event (`organiser_type = partner`) |
| `collaborator` | Partner was invited and accepted as `collab_partner` |

**Search fields:** `title`, `venue_city`

**Common errors:**

| Condition | `statusCode` | Message |
|-----------|-------------|---------|
| User is not a verified partner | `403` | `"You do not have permission to access this resource."` |

---

---

## 7. `admin/list/`

**`GET /api/v1/dashboard/partner/admin/list/`**

List all partner registrations on the platform. Admins use this to review pending registrations.

**Roles:** Admins

**Query params (in addition to standard pagination):**

| Param | Description |
|-------|-------------|
| `status` | Filter by registration status: `pending`, `verified`, `rejected` |

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Partner list fetched successfully."] },
  "response": {
    "data": [
      {
        "id": "partner-uuid",
        "name": "TechBridge Kerala",
        "slug": "techbridge-kerala",
        "email": "contact@techbridge.example.com",
        "partner_type": "Industry",
        "location": "Kochi, Kerala",
        "status": "pending",
        "user_link_id": "user-uuid",
        "user_name": "John Doe",
        "user_email": "john@example.com",
        "submitted_at": "2024-06-01T10:30:00Z",
        "verified_at": null
      }
    ],
    "pagination": {
      "count": 5,
      "totalPages": 1,
      "isNext": false,
      "isPrev": false,
      "nextPage": null
    }
  }
}
```

**Search fields:** `name`, `email`, `partner_type`, `location`

**Sort fields:** `name`, `status`, `submitted_at`

---

## 8. `admin/<partner_id>/verify/`

**`PATCH /api/v1/dashboard/partner/admin/<partner_id>/verify/`**

Approve or reject a partner registration. On approval, the `Partner` role is assigned to the registering user.

**Roles:** Admins

**Path param:** `partner_id` — UUID of the `user_partner` record

**Request body:**

```json
{
  "status": "verified",
  "rejection_reason": null
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `status` | Yes | Must be `"verified"` or `"rejected"` |
| `rejection_reason` | Conditional | **Required** when `status = "rejected"`; ignored on verification |

**On `status = "verified"`:**
1. Sets `status = verified`, `verified_by = <admin_id>`, `verified_at = now()`
2. Fetches the `Partner` role from the `role` table
3. Creates a `UserRoleLink` row linking the registering user to the `Partner` role (`verified = True`)

**On `status = "rejected"`:**
1. Sets `status = rejected`, `rejection_reason = <provided reason>`

**Success response (verify):**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Partner status updated to verified successfully."] },
  "response": {
    "id": "partner-uuid",
    "status": "verified",
    "verified_at": "2024-06-05T08:00:00Z"
  }
}
```

**Success response (reject):**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Partner status updated to rejected successfully."] },
  "response": {
    "id": "partner-uuid",
    "status": "rejected",
    "rejection_reason": "Insufficient documentation provided."
  }
}
```

**Common errors:**

| Condition | `statusCode` | Message |
|-----------|-------------|---------|
| Partner not found | `404` | `"Partner not found."` |
| Already verified | `400` | `"Partner is already verified."` |
| `rejection_reason` missing when rejecting | `400` | `"Rejection reason is required when rejecting."` |
| `Partner` role not found in `role` table | `400` | `"Partner role not found. Ensure the role has been seeded."` |

---

## Database — `user_partner` Table

Schema for the partner onboarding model, linking an authenticated user to their partner entity.

```sql
CREATE TABLE IF NOT EXISTS user_partner (
    id               VARCHAR(36)  PRIMARY KEY NOT NULL DEFAULT (UUID()),
    user_link_id     VARCHAR(36)  NOT NULL,
    name             VARCHAR(255) NOT NULL,
    slug             VARCHAR(255) NOT NULL,
    status           VARCHAR(20)  NOT NULL DEFAULT 'pending',
    rejection_reason TEXT         NULL,
    description      TEXT         NULL,
    email            VARCHAR(100) NOT NULL,
    logo             TEXT         NULL,
    short_pitch      VARCHAR(900) NULL,
    location         VARCHAR(150) NULL,
    district_id      VARCHAR(36)  NULL,
    state_id         VARCHAR(36)  NULL,
    country_id       VARCHAR(36)  NULL,
    partner_type     VARCHAR(75)  NULL,
    website_link     TEXT         NULL,
    social_links     JSON         NULL,
    submitted_at     DATETIME     NULL,
    verified_at      DATETIME     NULL,
    created_at       DATETIME     NOT NULL DEFAULT NOW(),
    updated_at       DATETIME     NOT NULL DEFAULT NOW(),
    created_by       VARCHAR(36)  NULL,
    updated_by       VARCHAR(36)  NULL,
    verified_by      VARCHAR(36)  NULL,
    UNIQUE KEY uk_user_partner_user_link  (user_link_id),
    UNIQUE KEY uk_user_partner_name       (name),
    UNIQUE KEY uk_user_partner_slug       (slug),
    CONSTRAINT fk_user_partner_user_link  FOREIGN KEY (user_link_id) REFERENCES user (id) ON DELETE CASCADE,
    CONSTRAINT fk_user_partner_district   FOREIGN KEY (district_id)  REFERENCES district (id) ON DELETE SET NULL,
    CONSTRAINT fk_user_partner_state      FOREIGN KEY (state_id)     REFERENCES state (id) ON DELETE SET NULL,
    CONSTRAINT fk_user_partner_country    FOREIGN KEY (country_id)   REFERENCES country (id) ON DELETE SET NULL,
    CONSTRAINT fk_user_partner_created_by FOREIGN KEY (created_by)   REFERENCES user (id) ON DELETE SET NULL,
    CONSTRAINT fk_user_partner_updated_by FOREIGN KEY (updated_by)   REFERENCES user (id) ON DELETE SET NULL,
    CONSTRAINT fk_user_partner_verified_by FOREIGN KEY (verified_by) REFERENCES user (id) ON DELETE SET NULL
);
```

### Column reference

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | `VARCHAR(36)` | No | Primary key, auto-generated UUID |
| `user_link_id` | `VARCHAR(36)` (FK → `user`) | No | The authenticated user who owns this registration; unique (one partner per user) |
| `name` | `VARCHAR(255)` | No | Display name of the partner organisation; unique across all partners |
| `slug` | `VARCHAR(255)` | No | URL-friendly slug auto-generated from `name`; unique |
| `status` | `VARCHAR(20)` | No | Lifecycle status: `pending`, `verified`, or `rejected` (default `pending`) |
| `rejection_reason` | `TEXT` | Yes | Admin-provided reason when `status = rejected`; cleared on resubmission |
| `description` | `TEXT` | Yes | Full description of the partner organisation |
| `email` | `VARCHAR(100)` | No | Primary contact email (matches `Company.email` size) |
| `logo` | `TEXT` | Yes | URL to the partner's logo image |
| `short_pitch` | `VARCHAR(900)` | Yes | Brief promotional summary (matches `Company.short_pitch` size) |
| `location` | `VARCHAR(150)` | Yes | Human-readable location string (matches `Company.location` size) |
| `district_id` | `VARCHAR(36)` (FK → `district`) | Yes | District FK; `SET NULL` on district delete |
| `state_id` | `VARCHAR(36)` (FK → `state`) | Yes | State FK; `SET NULL` on state delete |
| `country_id` | `VARCHAR(36)` (FK → `country`) | Yes | Country FK; `SET NULL` on country delete |
| `partner_type` | `VARCHAR(75)` | Yes | Enum-enforced category; see `PartnerType` below |
| `website_link` | `TEXT` | Yes | Partner website URL |
| `social_links` | `JSON` | Yes | Key-value map of social platform → URL (e.g. `{"twitter": "..."}`) |
| `submitted_at` | `DATETIME` | Yes | Timestamp when the registration was first submitted (set on POST `register/`) |
| `verified_at` | `DATETIME` | Yes | Timestamp when admin approved the registration |
| `created_at` | `DATETIME` | No | Record creation timestamp |
| `updated_at` | `DATETIME` | No | Last update timestamp |
| `created_by` | `VARCHAR(36)` (FK → `user`) | Yes | User who created the record |
| `updated_by` | `VARCHAR(36)` (FK → `user`) | Yes | User who last modified the record |
| `verified_by` | `VARCHAR(36)` (FK → `user`) | Yes | Admin user who approved or rejected the registration |

---

### `PartnerType` enum

The `partner_type` column is constrained at the **application layer** by a `PartnerType` Python enum in `utils/types.py`. The DB column is `VARCHAR(75)` with no SQL `CHECK` constraint (consistent with how `Company.industry_sector` and `Event.organiser_type` are handled).

```python
class PartnerType(Enum):
    INDUSTRY   = "Industry"
    NGO        = "NGO"
    ACADEMIA   = "Academia"
    GOVERNMENT = "Government"
    COMMUNITY  = "Community"
    MEDIA      = "Media"
    STARTUP    = "Startup"

    @classmethod
    def get_all_values(cls):
        return [member.value for member in cls]
```

| Value | Meaning |
|-------|---------|
| `Industry` | Private sector / corporate partner |
| `NGO` | Non-governmental / non-profit organisation |
| `Academia` | University, college, or research institution |
| `Government` | Government body or public sector agency |
| `Community` | Community group or open network |
| `Media` | Media house, publication, or content platform |
| `Startup` | Early-stage startup or incubated company |

---

## Database — Existing Table Changes

### 1. `role` table — Insert `Partner` role

**Why:** The platform assigns roles to users via the `user_role_link` table. The `Partner` role does not yet exist and must be seeded before the admin verification endpoint can assign it.

**Query:**

```sql
INSERT IGNORE INTO role (id, title, description, updated_by, updated_at, created_by, created_at)
VALUES (
    UUID(),
    'Partner',
    'Verified partner organisation representative',
    (SELECT id FROM user WHERE admin = 1 LIMIT 1),
    NOW(),
    (SELECT id FROM user WHERE admin = 1 LIMIT 1),
    NOW()
);
```

**Effect:** Adds a single `Partner` row to the `role` table. `INSERT IGNORE` prevents duplicate insertion if the script is re-run.

---

### 2. `events_connection` table — Support `collab_partner` entity type

**Why:** The `events_connection.entity_type` column uses a `VARCHAR(25)` with no database-level `CHECK` constraint (constraint is enforced at the model/application layer). Adding `collab_partner` as a valid type allows partners to be invited as event collaborators via the existing collaborator invite system.

**Query:**

```sql
-- No ALTER needed: entity_type is VARCHAR(25) with no CHECK constraint.
-- The new value 'collab_partner' is valid at the DB level as-is.
-- The application layer (EventConnection.EntityType) is updated to recognise it.
-- For documentation, the permitted entity_type values are now:
--
--   user_ticket       → user registered / expressed ticket interest
--   co_owner          → user with full manage access
--   collab_ig         → IG as co-host
--   collab_campus     → campus as co-host
--   collab_campus_ig  → campus IG chapter as co-host
--   collab_company    → company as co-host
--   collab_partner    → partner organisation as co-host  ← NEW
```

**Effect:** No DDL change required. The `events_connection` table already supports arbitrary VARCHAR values for `entity_type`. The change is enforced in the application model and serializer layer (see Events System Extension below).

---

## Events System Extension

The following changes integrate partners into the existing events system. Partners can **create their own events**, be **invited as collaborators**, and **accept or reject** collaboration invites — all using the existing event endpoints without any new endpoints.

---

### 1. `db/events.py` — Add `COLLAB_PARTNER` to `EventConnection`

**File:** `db/events.py`  
**Model:** `EventConnection`

**Change 1 — Add to `EntityType` choices:**

```python
# Before
class EntityType(models.TextChoices):
    USER_TICKET      = 'user_ticket',      'User Ticket'
    CO_OWNER         = 'co_owner',         'Co-owner'
    COLLAB_IG        = 'collab_ig',        'Collaborating IG'
    COLLAB_CAMPUS    = 'collab_campus',    'Collaborating Campus'
    COLLAB_CAMPUS_IG = 'collab_campus_ig', 'Collaborating Campus IG'
    COLLAB_COMPANY   = 'collab_company',   'Collaborating Company'

# After — add one line
class EntityType(models.TextChoices):
    USER_TICKET      = 'user_ticket',      'User Ticket'
    CO_OWNER         = 'co_owner',         'Co-owner'
    COLLAB_IG        = 'collab_ig',        'Collaborating IG'
    COLLAB_CAMPUS    = 'collab_campus',    'Collaborating Campus'
    COLLAB_CAMPUS_IG = 'collab_campus_ig', 'Collaborating Campus IG'
    COLLAB_COMPANY   = 'collab_company',   'Collaborating Company'
    COLLAB_PARTNER   = 'collab_partner',   'Collaborating Partner'   # ← NEW
```

**Change 2 — Add to `COLLABORATOR_TYPES`:**

```python
# Before
COLLABORATOR_TYPES = [
    EntityType.COLLAB_IG,
    EntityType.COLLAB_CAMPUS,
    EntityType.COLLAB_CAMPUS_IG,
    EntityType.COLLAB_COMPANY,
]

# After — add one entry
COLLABORATOR_TYPES = [
    EntityType.COLLAB_IG,
    EntityType.COLLAB_CAMPUS,
    EntityType.COLLAB_CAMPUS_IG,
    EntityType.COLLAB_COMPANY,
    EntityType.COLLAB_PARTNER,   # ← NEW
]
```

**Why:** `COLLABORATOR_TYPES` is used throughout `manage_views.py` and `serializers.py` to filter collaborator connections. Adding `COLLAB_PARTNER` here automatically includes partners in all existing collaborator list queries, the public detail serializer, and the manage detail view — without needing changes to every individual queryset.

**Change 3 — Add `PARTNER` to `Event.OrganiserType`:**

```python
# Before
class OrganiserType(models.TextChoices):
    GLOBAL_IG = 'global_ig', 'Global IG'
    CAMPUS_IG = 'campus_ig', 'Campus IG'
    CAMPUS    = 'campus',    'Campus'
    COMPANY   = 'company',   'Company'
    ADMIN     = 'admin',     'Admin'

# After — add one line
class OrganiserType(models.TextChoices):
    GLOBAL_IG = 'global_ig', 'Global IG'
    CAMPUS_IG = 'campus_ig', 'Campus IG'
    CAMPUS    = 'campus',    'Campus'
    COMPANY   = 'company',   'Company'
    ADMIN     = 'admin',     'Admin'
    PARTNER   = 'partner',   'Partner'   # ← NEW
```

**Why:** Without this, the `EventWriteSerializer` would reject `organiser_type = "partner"` as an invalid choice when a partner creates an event. No database ALTER is needed — `organiser_type` is a plain `VARCHAR(20)` with no `CHECK` constraint.

---

### 2. `api/dashboard/events/manage_views.py` — Add `COLLAB_PARTNER` to manage views

**File:** `api/dashboard/events/manage_views.py`

**Change 1 — Add `COLLAB_PARTNER` to local `COLLAB_TYPES` list:**

The file maintains its own `COLLAB_TYPES` constant (separate from the model-level `COLLABORATOR_TYPES`) used for POST invite validation. Add `COLLAB_PARTNER` to it:

```python
# Before
COLLAB_TYPES = [
    EventConnection.EntityType.COLLAB_IG,
    EventConnection.EntityType.COLLAB_CAMPUS,
    EventConnection.EntityType.COLLAB_CAMPUS_IG,
    EventConnection.EntityType.COLLAB_COMPANY,
]

# After
COLLAB_TYPES = [
    EventConnection.EntityType.COLLAB_IG,
    EventConnection.EntityType.COLLAB_CAMPUS,
    EventConnection.EntityType.COLLAB_CAMPUS_IG,
    EventConnection.EntityType.COLLAB_COMPANY,
    EventConnection.EntityType.COLLAB_PARTNER,   # ← NEW
]
```

**Change 2 — Update `_resolve_entity_name()` to handle partners:**

```python
# Add a new elif branch inside _resolve_entity_name()
elif entity_type == EventConnection.EntityType.COLLAB_PARTNER:
    from db.partner import UserPartner
    partner = UserPartner.objects.filter(id=entity_id).first()
    return partner.name if partner else entity_id
```

**Change 3 — Update `_caller_can_respond()` to authorise the partner's registered user:**

```python
# Add a new elif branch inside _caller_can_respond()
elif conn.entity_type == EventConnection.EntityType.COLLAB_PARTNER:
    from db.partner import UserPartner
    partner = UserPartner.objects.filter(
        id=conn.entity_id, status='verified'
    ).first()
    if partner:
        return str(partner.user_link_id) == str(user_id)
    return False
```

**Why:** `_caller_can_respond()` determines who is authorised to accept or reject a collaboration invite. For `COLLAB_PARTNER`, the authorised user is the partner's registered owner (`user_link_id`). Without this change, no one would be able to accept/reject partner invites.

**Change 4 — Add `PARTNER` to `MANAGEABLE_ROLES`:**

```python
# Before
MANAGEABLE_ROLES = {
    RoleType.ADMIN.value,
    RoleType.CAMPUS_LEAD.value,
    RoleType.IG_LEAD.value,
    RoleType.ZONAL_CAMPUS_LEAD.value,
    RoleType.DISTRICT_CAMPUS_LEAD.value,
    RoleType.COMPANY.value,
    RoleType.ENABLER.value,
    RoleType.LEAD_ENABLER.value,
}

# After — add one entry
MANAGEABLE_ROLES = {
    RoleType.ADMIN.value,
    RoleType.CAMPUS_LEAD.value,
    RoleType.IG_LEAD.value,
    RoleType.ZONAL_CAMPUS_LEAD.value,
    RoleType.DISTRICT_CAMPUS_LEAD.value,
    RoleType.COMPANY.value,
    RoleType.ENABLER.value,
    RoleType.LEAD_ENABLER.value,
    RoleType.PARTNER.value,   # ← NEW
}
```

**Why:** `MANAGEABLE_ROLES` is checked by `_can_create_event()` before allowing `POST /events/manage/`. Without adding `PARTNER` here, a verified partner user would receive `"You do not have permission to create events."` even after their role is assigned.

**Change 5 — Add partner branch to `MyEventInvitesAPI`:**

`GET /events/my-invites/` builds a per-role `Q()` query so each user sees only invites relevant to them. Without a `Partner` branch, a verified partner sees zero pending invites even though an `EventConnection` row exists for them.

```python
# Add this block inside MyEventInvitesAPI.get(), alongside the existing ig/campus/company blocks
if RoleType.PARTNER.value in roles:
    from db.partner import UserPartner
    partner = UserPartner.objects.filter(
        user_link_id=user_id, status='verified'
    ).first()
    if partner:
        query |= Q(
            entity_type=EventConnection.EntityType.COLLAB_PARTNER,
            entity_id=partner.id
        )
```

**Why:** Without this, the partner's pending collab invites are invisible to them via the invites endpoint — they could only be accepted by an admin.

---

### 3. `api/dashboard/events/serializers.py` — Handle `COLLAB_PARTNER` in collaborator detail

**File:** `api/dashboard/events/serializers.py`  
**Serializer:** `EventCollaboratorSerializer.get_entity_detail()`

Add a new `elif` branch to resolve partner details when `entity_type = collab_partner`:

```python
# Add inside get_entity_detail(), after the COLLAB_COMPANY branch
elif obj.entity_type == EventConnection.EntityType.COLLAB_PARTNER:
    from db.partner import UserPartner
    partner = UserPartner.objects.filter(id=obj.entity_id).first()
    if partner:
        return {
            'id': partner.id,
            'name': partner.name,
            'slug': partner.slug,
            'logo': partner.logo,
        }
    return None
```

**Why:** `get_entity_detail()` returns a resolved object (name, icon, etc.) for any collaborator. Without this, `entity_detail` would return `null` for partner collaborators even though a record exists, making it impossible to display which partner was invited.

---

### 4. `api/dashboard/events/meta_views.py` — Add partners to collaboration targets

**File:** `api/dashboard/events/meta_views.py`  
**View:** `CollaborationTargetsAPI` (`GET /events/meta/collaboration-targets/`)

Add a `partner` key to the results and query `UserPartner` for verified partners:

```python
# Before — results dict
results = {
    'ig': [],
    'campus': [],
    'company': [],
    'campus_ig': [],
}

# After — add partner key
results = {
    'ig': [],
    'campus': [],
    'company': [],
    'campus_ig': [],
    'partner': [],   # ← NEW
}
```

Add query block for partners (alongside existing ig/campus/company blocks):

```python
if not filter_type or filter_type == 'partner':
    from db.partner import UserPartner
    qs = UserPartner.objects.filter(status='verified')
    if search:
        qs = qs.filter(name__icontains=search)
    results['partner'] = list(
        qs.values('id', 'name', 'slug', 'logo', 'partner_type')[:20]
    )
```

**Updated response shape for `/events/meta/collaboration-targets/`:**

```json
{
  "response": {
    "ig": [ { "id": "...", "name": "WebDev", "icon": "...", "code": "WEBDEV" } ],
    "campus": [ { "id": "...", "title": "CUSAT", "org_type": "College" } ],
    "company": [ { "id": "...", "title": "Acme Corp", "org_type": "Company" } ],
    "campus_ig": [ { "id": "...", "name": "WebDev", "icon": "...", "code": "WEBDEV" } ],
    "partner": [
      {
        "id": "partner-uuid",
        "name": "TechBridge Kerala",
        "slug": "techbridge-kerala",
        "logo": "https://cdn.example.com/logo.png",
        "partner_type": "Industry"
      }
    ]
  }
}
```

**Why:** This endpoint powers the collaborator search dropdown in the event creation/edit form. Without adding `partner` here, event organisers would have no way to discover and invite verified partners as collaborators.

---

### 5. `api/dashboard/events/meta_views.py` — Add `can_create_as_partner` to `OrganizerOptionsAPI`

**File:** `api/dashboard/events/meta_views.py`  
**View:** `OrganizerOptionsAPI` (`GET /events/meta/organizer-options/`)

This endpoint powers the "Create as…" dropdown when a user opens the event creation form. Without this change, a verified partner opening the event creation form would not see themselves as an available organiser context.

**Change — add `can_create_as_partner` to the options dict and query:**

```python
# Before — options dict
options = {
    'can_create_as_ig': [],
    'can_create_as_campus_ig': [],
    'can_create_as_campus': [],
    'can_create_as_company': [],
    'can_create_as_admin': False,
}

# After — add partner key
options = {
    'can_create_as_ig': [],
    'can_create_as_campus_ig': [],
    'can_create_as_campus': [],
    'can_create_as_company': [],
    'can_create_as_admin': False,
    'can_create_as_partner': [],   # ← NEW
}
```

Add query block (alongside existing ig/campus/company blocks):

```python
# Add after the Company block
if RoleType.PARTNER.value in roles:
    from db.partner import UserPartner
    partner = UserPartner.objects.filter(
        user_link_id=user_id, status='verified'
    ).first()
    if partner:
        options['can_create_as_partner'] = [{
            'id': partner.id,
            'name': partner.name,
            'slug': partner.slug,
        }]
```

**Updated response shape for `/events/meta/organizer-options/`:**

```json
{
  "response": {
    "can_create_as_ig": [],
    "can_create_as_campus_ig": [],
    "can_create_as_campus": [],
    "can_create_as_company": [],
    "can_create_as_admin": false,
    "can_create_as_partner": [
      {
        "id": "partner-uuid",
        "name": "TechBridge Kerala",
        "slug": "techbridge-kerala"
      }
    ]
  }
}
```

**Why:** When a partner user opens the event creation form, the frontend calls this endpoint to populate the "Create as…" dropdown. Without `can_create_as_partner`, the partner user would have no organiser context to select and the form would be unusable for them.

---

## Affected Files Summary

| File | Type | Change |
|------|------|--------|
| `db/partner.py` | **NEW** | `UserPartner` model |
| `new_schema.sql` | **MODIFY** | `INSERT` Partner role + `CREATE TABLE user_partner` |
| `db/events.py` | **MODIFY** | Add `COLLAB_PARTNER` to `EntityType` + `COLLABORATOR_TYPES`; add `PARTNER` to `OrganiserType` |
| `api/dashboard/events/manage_views.py` | **MODIFY** | `COLLAB_PARTNER` in `COLLAB_TYPES` + `_resolve_entity_name` + `_caller_can_respond`; `PARTNER` in `MANAGEABLE_ROLES`; partner branch in `MyEventInvitesAPI` |
| `api/dashboard/events/serializers.py` | **MODIFY** | Handle `COLLAB_PARTNER` in `get_entity_detail` |
| `api/dashboard/events/meta_views.py` | **MODIFY** | `partner` in `CollaborationTargetsAPI`; `can_create_as_partner` in `OrganizerOptionsAPI` |
| `api/dashboard/partner/__init__.py` | **NEW** | Package init |
| `api/dashboard/partner/urls.py` | **NEW** | URL routing for all 8 endpoints |
| `api/dashboard/partner/serializers.py` | **NEW** | All partner serializers |
| `api/dashboard/partner/views.py` | **NEW** | Partner-facing views (endpoints 1–6) |
| `api/dashboard/partner/admin_views.py` | **NEW** | Admin views (endpoints 7–8) |
| `api/dashboard/urls.py` | **MODIFY** | Register `partner/` route |
| `utils/types.py` | **MODIFY** | Add `PARTNER = "Partner"` to `RoleType`; add `PartnerType` enum |
