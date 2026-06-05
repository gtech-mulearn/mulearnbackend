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
| 7 | [`admin/list/`](#7-adminlist) | `GET` | Admin |
| 8 | [`admin/<partner_id>/verify/`](#8-adminpartner_idverify) | `PATCH` | Admin |

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

HTTP status codes may not always match `statusCode` in the body. Clients should rely on `hasError` and `statusCode` in the response body for error handling, not the HTTP status code.

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
| `verified` | Approved; `Partner` role assigned; dashboard endpoints available |
| `rejected` | Rejected; can `PATCH register/` to resubmit |

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
  "short_pitch": "A short pitch under 150 words.",
  "email": "contact@techbridge.example.com",
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
| `name` | Yes | Unique partner name; slug auto-generated |
| `email` | Yes | Contact email |
| `description` | No | Partner description |
| `short_pitch` | No | Max 900 characters |
| `partner_type` | No | One of: `Industry`, `NGO`, `Academia`, `Government`, `Community`, `Media`, `Startup` |
| `district_id` | No | UUID of a district |
| `state_id` | No | UUID of a state |
| `country_id` | No | UUID of a country |
| `social_links` | No | JSON object of platform → URL |

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Partner registration submitted successfully."] },
  "response": {
    "id": "partner-uuid",
    "user_link_id": "user-uuid",
    "user_name": "Jane Doe",
    "user_email": "jane@example.com",
    "name": "TechBridge Kerala",
    "slug": "techbridge-kerala",
    "logo": "https://cdn.example.com/logo.png",
    "description": "We connect learners with industry opportunities.",
    "email": "contact@techbridge.example.com",
    "short_pitch": "A short pitch under 150 words.",
    "location": "Kochi, Kerala",
    "district_id": "district-uuid",
    "district_name": "Ernakulam",
    "state_id": "state-uuid",
    "state_name": "Kerala",
    "country_id": "country-uuid",
    "country_name": "India",
    "partner_type": "Industry",
    "website_link": "https://techbridge.example.com",
    "social_links": { "twitter": "https://twitter.com/techbridge" },
    "status": "pending",
    "rejection_reason": null,
    "submitted_at": "2026-06-01T10:00:00Z",
    "verified_at": null,
    "created_at": "2026-06-01T10:00:00Z"
  }
}
```

**Common errors:** Registration already exists for this account.

---

**`PATCH /api/v1/dashboard/partner/register/`**

Update a pending or rejected registration. If `status` is `rejected`, saving automatically resets it to `pending` and clears `rejection_reason`.

**Roles:** Authenticated user (owner of the registration)

**Request body:** Same fields as POST (partial update — only send fields to change).

**Success response:** Updated registration object (same shape as POST response).

**Common errors:**
- No registration found for this account → 404
- Partner already `verified` — use `profile/` instead

---

## 2. `status/`

**`GET /api/v1/dashboard/partner/status/`**

Check the onboarding status of the authenticated user's partner registration.

**Roles:** Authenticated user

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Partner status fetched successfully."] },
  "response": {
    "status": "pending",
    "rejection_reason": null,
    "submitted_at": "2026-06-01T10:00:00Z",
    "verified_at": null
  }
}
```

**Common errors:** No registration found for this account → 404

---

## 3. `summary/`

**`GET /api/v1/dashboard/partner/summary/`**

High-level dashboard summary — event counts and learner engagement totals.

**Roles:** `Partner` (verified only)

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Partner summary fetched successfully."] },
  "response": {
    "partner": {
      "id": "partner-uuid",
      "user_link_id": "user-uuid",
      "user_name": "Jane Doe",
      "user_email": "jane@example.com",
      "name": "TechBridge Kerala",
      "slug": "techbridge-kerala",
      "status": "verified",
      "logo": "https://cdn.example.com/logo.png",
      "partner_type": "Industry"
    },
    "total_events": 12,
    "active_events": 3,
    "total_learners_engaged": 480,
    "recent_events": [
      {
        "id": "event-uuid",
        "title": "Partner Tech Workshop",
        "start_datetime": "2026-07-01T10:00:00Z",
        "learner_count": 45
      }
    ]
  }
}
```

**Notes:**
- `total_events` — events where the partner is the organiser **or** an accepted collaborator.
- `active_events` — subset with `status = published` or `ongoing`.
- `total_learners_engaged` — total `user_ticket` event connections across all partner events.
- `recent_events` — up to 5 most recent events ordered by `start_datetime` descending.

---

## 4. `profile/`

**`GET /api/v1/dashboard/partner/profile/`**

Retrieve the full profile of the logged-in partner.

**Roles:** `Partner`

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Partner profile fetched successfully."] },
  "response": {
    "id": "partner-uuid",
    "user_link_id": "user-uuid",
    "user_name": "Jane Doe",
    "user_email": "jane@example.com",
    "name": "TechBridge Kerala",
    "slug": "techbridge-kerala",
    "logo": "https://cdn.example.com/logo.png",
    "description": "We connect learners with industry opportunities.",
    "email": "contact@techbridge.example.com",
    "short_pitch": "A short pitch under 150 words.",
    "location": "Kochi, Kerala",
    "district_id": "district-uuid",
    "district_name": "Ernakulam",
    "state_id": "state-uuid",
    "state_name": "Kerala",
    "country_id": "country-uuid",
    "country_name": "India",
    "partner_type": "Industry",
    "website_link": "https://techbridge.example.com",
    "social_links": { "twitter": "https://twitter.com/techbridge" },
    "status": "verified",
    "rejection_reason": null,
    "submitted_at": "2026-06-01T10:00:00Z",
    "verified_at": "2026-06-05T09:00:00Z",
    "created_at": "2026-06-01T10:00:00Z"
  }
}
```

---

**`PATCH /api/v1/dashboard/partner/profile/`**

Update the logged-in partner's profile (partial update).

**Roles:** `Partner`

**Notes:** `name`, `slug`, `status`, and `user_link_id` are **read-only** after verification — they are silently ignored even if sent.

**Request example:**

```json
{
  "description": "Updated description.",
  "short_pitch": "New short pitch.",
  "social_links": { "twitter": "https://twitter.com/techbridge" }
}
```

**Success response:** Updated profile object (same shape as GET).

---

## 5. `profile/public/<slug>/`

**`GET /api/v1/dashboard/partner/profile/public/<slug>/`**

Public-facing partner profile. Only partners with `status = verified` are accessible.

**Auth:** None (no JWT required)

**Path params:** `slug` — partner URL slug (e.g. `techbridge-kerala`)

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
    "short_pitch": "A short pitch under 150 words.",
    "website_link": "https://techbridge.example.com",
    "location": "Kochi, Kerala",
    "district": "Ernakulam",
    "state": "Kerala",
    "country": "India",
    "partner_type": "Industry",
    "social_links": { "twitter": "https://twitter.com/techbridge" }
  }
}
```

**Notes:** `district`, `state`, `country` are resolved **name strings**, not UUIDs. IDs and audit fields are not exposed.

**Common errors:** Partner not found or not yet verified → 404

---

## 6. `events/`

**`GET /api/v1/dashboard/partner/events/`**

List all events where this partner is the organiser or an accepted collaborator. Paginated.

**Roles:** `Partner`

**Query params:**

| Param | Description |
|-------|-------------|
| `status` | Filter by event status: `draft`, `pending_approval`, `published`, `ongoing`, `completed`, `cancelled` |
| `type` | `organiser` — only events created as partner organiser; `collaborator` — only events where partner was invited and accepted |
| `pageIndex`, `perPage` | Pagination |
| `search` | Search by `title` or `venue_city` |
| `sortBy` | `start_datetime` (ascending) or `created_at` (descending) |

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
        "title": "Partner Tech Workshop",
        "slug": "partner-tech-workshop-1",
        "status": "published",
        "start_datetime": "2026-07-01T10:00:00Z",
        "end_datetime": "2026-07-01T15:00:00Z",
        "venue_type": "online",
        "venue_city": null,
        "cover_image": null,
        "partner_role": "organiser",
        "learner_count": 45
      }
    ],
    "pagination": {
      "count": 1,
      "totalPages": 1,
      "isNext": false,
      "isPrev": false,
      "nextPage": null
    }
  }
}
```

| Field | Description |
|-------|-------------|
| `partner_role` | `"organiser"` — partner created this event; `"collaborator"` — partner was invited and accepted |
| `learner_count` | Number of registered users (`user_ticket` connections) for this event |

---

## 7. `admin/list/`

**`GET /api/v1/dashboard/partner/admin/list/`**

List all partner registrations. Admins use this to review pending, verified, or rejected partners.

**Roles:** `Admin`

**Query params:**

| Param | Description |
|-------|-------------|
| `status` | `pending`, `verified`, `rejected` |
| `pageIndex`, `perPage` | Pagination |
| `search` | Search by `name`, `email`, `partner_type`, `location` |
| `sortBy` | `name`, `status`, `submitted_at` |

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
        "user_name": "Jane Doe",
        "user_email": "jane@example.com",
        "submitted_at": "2026-06-01T10:00:00Z",
        "verified_at": null
      }
    ],
    "pagination": {
      "count": 1,
      "totalPages": 1,
      "isNext": false,
      "isPrev": false,
      "nextPage": null
    }
  }
}
```

---

## 8. `admin/<partner_id>/verify/`

**`PATCH /api/v1/dashboard/partner/admin/<partner_id>/verify/`**

Approve or reject a partner registration.

**Roles:** `Admin`

**Path params:** `partner_id` — UUID of the partner registration

**Request body — Approve:**

```json
{
  "status": "verified"
}
```

**Request body — Reject:**

```json
{
  "status": "rejected",
  "rejection_reason": "Insufficient organization registration documentation."
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `status` | Yes | `"verified"` or `"rejected"` |
| `rejection_reason` | Yes if `status = rejected` | Required when rejecting |

**On approval:** The `Partner` role is automatically assigned to the registering user via `UserRoleLink`.

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Partner status updated to verified successfully."] },
  "response": {
    "id": "partner-uuid",
    "name": "TechBridge Kerala",
    "status": "verified",
    "verified_at": "2026-06-05T09:00:00Z",
    "rejection_reason": null
  }
}
```

**Common errors:**
- Partner not found → 404
- Partner already verified → 400

---

## Creating Partner Events

Partners create and manage events through the shared **Events manage API** — not through the partner endpoints directly.

**Key steps:**

| Step | Endpoint | Notes |
|------|----------|-------|
| Create event | `POST /api/v1/dashboard/events/manage/` | Send `"organiser_type": "partner"` in the body |
| Edit / update | `PATCH /api/v1/dashboard/events/manage/<event_id>/` | Partial update |
| Publish (submit for approval) | `POST /api/v1/dashboard/events/manage/<event_id>/publish/` | Status moves to `pending_approval` |
| Admin approves | `POST /api/v1/dashboard/events/admin/<event_id>/approve/` | Status moves to `published` |

**Minimum event create payload:**

```json
{
  "title": "Partner Tech Workshop",
  "description": "A workshop hosted by our partner.",
  "start_datetime": "2026-07-01T10:00:00Z",
  "end_datetime": "2026-07-01T15:00:00Z",
  "venue_type": "online",
  "venue_online_link": "https://zoom.us/j/12345678",
  "organiser_type": "partner",
  "scope": "global"
}
```

> **DB prerequisite:** The `organiser_type` ENUM must include `'partner'`. Run this once if not already applied:
> ```sql
> ALTER TABLE events
>   MODIFY COLUMN organiser_type
>     ENUM('global_ig','campus_ig','campus','company','admin','partner')
>     NOT NULL DEFAULT 'admin';
> ```

See [Dashboard_Events.md](./Dashboard_Events.md) for full event API reference.
