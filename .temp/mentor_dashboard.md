# Mentor Dashboard API Documentation

> **Base prefix**: `/api/v1/dashboard/mentor/`
> **Auth**: All endpoints require a valid JWT (`Authorization: Bearer <token>`), unless marked **[Public — no auth]**.
> **Roles**: `ADMIN` = platform admin · `MENTOR` = verified mentor

---

## Table of Contents

1. [Onboarding](#1-onboarding)
2. [Admin Mentor Roster](#2-admin-mentor-roster)
3. [Overview & Stats](#3-overview--stats)
4. [Leaderboard](#4-leaderboard)
5. [Sessions](#5-sessions)
6. [Global Session Approval Queue](#6-global-session-approval-queue)
7. [Task Review Queue](#7-task-review-queue)
8. [Availability Slots](#8-availability-slots)
9. [Task Requests](#9-task-requests)
10. [Opportunities](#10-opportunities)
11. [Mentees & Activity Log](#11-mentees--activity-log)
12. [Karma Award](#12-karma-award)
13. [Session Reminder](#13-session-reminder)
14. [My IGs](#14-my-igs)
15. [IG Mentor Link Requests](#15-ig-mentor-link-requests)
16. [Admin Mentor Tier Update](#16-admin-mentor-tier-update)
17. [Bulk Attendance Update](#17-bulk-attendance-update)
18. [Session Clone](#18-session-clone)
19. [Availability Calendar](#19-availability-calendar)
20. [Public Endpoints](#20-public-endpoints)
21. [Company Mentor](#21-company-mentor)
22. [Campus Mentor](#22-campus-mentor)

---

## Mentor Tier Reference

| `mentor_tier` value | Description | `org_id` |
|---|---|---|
| `IG_MENTOR` | Linked to specific Interest Group(s) | `null` |
| `MENTOR` | Platform-wide global mentor | `null` |
| `COMPANY_MENTOR` | Scoped to a specific Company org | Company UUID |
| `CAMPUS_MENTOR` | Scoped to a specific College org | College UUID |

> A user may hold **multiple** `UserMentor` rows — one per (tier, org) combination.
> System role (`"Mentor"`) is the same for all tiers; tier-specific access is enforced by `mentor_tier + org_id` inside each endpoint.

---

## 1. Onboarding

### `GET /mentor/onboarding/`

Fetch the authenticated user's mentor application.

| | |
|---|---|
| **Roles** | Any authenticated user |
| **Auth** | JWT required |

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Success",
  "response": {
    "mentor": {
      "id": "um-uuid-001",
      "full_name": "Arjun Nair",
      "email": "arjun@example.com",
      "muid": "arjun@mulearn",
      "about": "Passionate about open-source and teaching.",
      "expertise": ["Python", "Django", "REST APIs"],
      "reason": "I want to help junior devs grow.",
      "preferred_ig_ids": ["ig-uuid-001", "ig-uuid-002"],
      "mentor_tier": "IG_MENTOR",
      "is_verified": true,
      "verified_at": "2025-01-15T10:30:00Z",
      "verification_note": "Strong background verified.",
      "hours": 12,
      "created_at": "2025-01-01T08:00:00Z"
    }
  }
}
```

---

### `POST /mentor/onboarding/`

Submit a mentor application.

**Request Body**
```json
{
  "about": "Senior software engineer with 5 years in web development.",
  "expertise": ["JavaScript", "React", "Node.js"],
  "reason": "I want to mentor students on modern web development.",
  "preferred_ig_ids": ["ig-uuid-001", "ig-uuid-003"]
}
```

---

### `PATCH /mentor/onboarding/`

Update own mentor profile fields.

**Request Body** *(all fields optional)*
```json
{
  "about": "Updated bio.",
  "expertise": ["Python", "FastAPI", "Kubernetes"],
  "preferred_ig_ids": ["ig-uuid-005"]
}
```

---

## 2. Admin Mentor Roster

### `GET /mentor/list/`

Paginated list of all mentor applications.

| | |
|---|---|
| **Roles** | ADMIN |

**Query Parameters**

| Param | Type | Description |
|---|---|---|
| `is_verified` | boolean string | `true` / `false` |
| `search` | string | Name, email, or muid |
| `sort_by` | string | `full_name`, `created_at`, `mentor_tier` |

---

### `PATCH /mentor/<mentor_id>/verify/`

Approve or reject a pending mentor application.

**Request Body**
```json
{
  "action": "approve",
  "note": "Background verified. Welcome aboard!",
  "mentor_tier": "IG_MENTOR"
}
```

> `action`: `"approve"` | `"reject"`
> `mentor_tier` (approve only): `"IG_MENTOR"` | `"MENTOR"`

---

## 3. Overview & Stats

### `GET /mentor/overview/`
### `GET /mentor/stats/` *(alias)*

Single-call dashboard snapshot. Admins see platform-wide data; mentors see their own scoped data.

| | |
|---|---|
| **Roles** | ADMIN, MENTOR |

---

## 4. Leaderboard

### `GET /mentor/leaderboard/`

Ranked list of verified mentors.
**Score** = `(sessions_completed × 3) + (mentees_attended × 2) + (hours × 1)`

| | |
|---|---|
| **Roles** | ADMIN, MENTOR |

---

## 5. Sessions

### `GET /mentor/sessions/`
### `POST /mentor/sessions/`
### `GET /mentor/sessions/<session_id>/`
### `PATCH /mentor/sessions/<session_id>/`
### `DELETE /mentor/sessions/<session_id>/`
### `PATCH /mentor/sessions/<session_id>/status/`
### `GET /mentor/sessions/<session_id>/participants/`
### `POST /mentor/sessions/<session_id>/participants/`
### `DELETE /mentor/sessions/<session_id>/participants/<user_id>/`

---

## 6. Global Session Approval Queue

### `GET /mentor/sessions/pending/`
### `PATCH /mentor/sessions/<session_id>/approve/`

---

## 7. Task Review Queue

### `GET /mentor/review-queue/`
### `GET /mentor/review-queue/<kal_id>/`
### `PATCH /mentor/review-queue/<kal_id>/`

---

## 8. Availability Slots

### `GET /mentor/availability/`
### `POST /mentor/availability/`
### `PUT /mentor/availability/<slot_id>/`
### `DELETE /mentor/availability/<slot_id>/`

---

## 9. Task Requests

### `GET /mentor/task-requests/`
### `POST /mentor/task-requests/`
### `GET /mentor/task-requests/<task_request_id>/`
### `PATCH /mentor/task-requests/<task_request_id>/`
### `DELETE /mentor/task-requests/<task_request_id>/`

---

## 10. Opportunities

### `GET /mentor/opportunities/`
### `POST /mentor/opportunities/`
### `GET /mentor/opportunities/<opportunity_id>/`
### `PATCH /mentor/opportunities/<opportunity_id>/`
### `DELETE /mentor/opportunities/<opportunity_id>/`

---

## 11. Mentees & Activity Log

### `GET /mentor/mentees/`
### `GET /mentor/mentees/<user_id>/`
### `GET /mentor/activity-log/`

---

## 12. Karma Award

### `GET /mentor/sessions/<session_id>/karma-award/`
### `POST /mentor/sessions/<session_id>/karma-award/`

---

## 13. Session Reminder

### `POST /mentor/sessions/<session_id>/remind/`

---

## 14. My IGs

### `GET /mentor/my-igs/`

---

## 15. IG Mentor Link Requests

### `GET /mentor/ig-requests/`
### `PATCH /mentor/ig-requests/<request_id>/`

---

## 16. Admin Mentor Tier Update

### `PATCH /mentor/list/<mentor_id>/tier/`

| | |
|---|---|
| **Roles** | ADMIN only |

**Request Body**
```json
{ "mentor_tier": "MENTOR" }
```

> `mentor_tier`: `"IG_MENTOR"` | `"MENTOR"` — note: `"COMPANY_MENTOR"` and `"CAMPUS_MENTOR"` tiers are managed through their own onboarding flows and cannot be set via this endpoint.

---

## 17. Bulk Attendance Update

### `PATCH /mentor/sessions/<session_id>/attendance/`

---

## 18. Session Clone

### `POST /mentor/sessions/<session_id>/clone/`

---

## 19. Availability Calendar

### `GET /mentor/availability/calendar/`

---

## 20. Public Endpoints

### `GET /mentor/<muid>/public/`
### `GET /mentor/<muid>/public/sessions/`
### `GET /mentor/availability/public/?mentor_muid=<muid>`

---

---

# 21. Company Mentor

> **Prefix**: `/api/v1/dashboard/mentor/company/`
>
> Company mentors are users with a verified `UserMentor` row where `mentor_tier = "COMPANY_MENTOR"` and `org_id` points to a **Company-type** organisation.
>
> **Tier enforcement**: Every write endpoint verifies that the requesting user has `is_verified=True` for the exact `(COMPANY_MENTOR, org_id)` combination. A company mentor cannot act on a different company's data, cannot use campus-mentor endpoints, and cannot act beyond their approved org scope.

---

### `GET /mentor/company/onboarding/`

List the authenticated user's own Company Mentor application rows.

| | |
|---|---|
| **Roles** | Any authenticated user |
| **Auth** | JWT required |

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "response": {
    "mentors": [
      {
        "id": "um-uuid-c01",
        "full_name": "Rahul Dev",
        "email": "rahul@acmecorp.com",
        "muid": "rahul@mulearn",
        "mentor_tier": "COMPANY_MENTOR",
        "org_id": "org-uuid-acme",
        "org_name": "Acme Corp",
        "org_type": "Company",
        "about": "10 years in backend engineering.",
        "expertise": ["Go", "Kubernetes", "gRPC"],
        "reason": "Want to hire and mentor the next generation.",
        "is_verified": true,
        "verified_at": "2026-05-20T11:00:00Z",
        "verification_note": "Verified by admin.",
        "hours": 5,
        "created_at": "2026-05-10T09:00:00Z"
      }
    ]
  }
}
```

---

### `POST /mentor/company/onboarding/`

Apply to become a Company Mentor for a specific organisation.

| | |
|---|---|
| **Roles** | Any authenticated user |
| **Auth** | JWT required |

**Rules**
- `org` must point to an existing organisation with `org_type = "Company"` — returns `400` otherwise
- Only one application per `(user, COMPANY_MENTOR, org)` triple — duplicate returns `400`
- Application starts as `is_verified = False`; an admin must approve it

**Request Body**
```json
{
  "org": "org-uuid-acme",
  "about": "10 years in backend engineering at Acme Corp.",
  "expertise": ["Go", "Kubernetes", "gRPC"],
  "reason": "Want to hire and mentor the next generation of engineers."
}
```

**Response — 201 Created**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Company mentor application submitted. Awaiting admin approval.",
  "response": {
    "mentor": {
      "id": "um-uuid-c02",
      "mentor_tier": "COMPANY_MENTOR",
      "org_id": "org-uuid-acme",
      "org_name": "Acme Corp",
      "is_verified": false,
      "created_at": "2026-05-27T10:00:00Z"
    }
  }
}
```

**Error — Wrong org type (400)**
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": "A valid Company organisation id is required."
}
```

**Error — Duplicate (400)**
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": "You have already applied as a company mentor for this organisation."
}
```

---

### `PATCH /mentor/company/onboarding/<mentor_id>/`

Update own Company Mentor profile (about / expertise / reason only).

| | |
|---|---|
| **Roles** | MENTOR |
| **Auth** | JWT required |

**Tier enforcement**: Can only edit rows where `mentor_tier = "COMPANY_MENTOR"` and `user_id` matches the requester.

**Request Body** *(all fields optional)*
```json
{
  "about": "Updated: now leading the platform engineering team.",
  "expertise": ["Go", "Kubernetes", "gRPC", "Terraform"]
}
```

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Profile updated."
}
```

---

### `GET /mentor/company/list/`

Admin: paginated list of all Company Mentor applications.

| | |
|---|---|
| **Roles** | ADMIN |
| **Auth** | JWT required |

**Query Parameters**

| Param | Type | Description |
|---|---|---|
| `org_id` | UUID | Filter by organisation |
| `is_verified` | boolean string | `true` / `false` |
| `search` | string | Name, email, or org name |
| `sort_by` | string | `created_at`, `full_name` |

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "response": [
    {
      "id": "um-uuid-c01",
      "full_name": "Rahul Dev",
      "email": "rahul@acmecorp.com",
      "muid": "rahul@mulearn",
      "mentor_tier": "COMPANY_MENTOR",
      "org_id": "org-uuid-acme",
      "org_name": "Acme Corp",
      "org_type": "Company",
      "is_verified": false,
      "created_at": "2026-05-10T09:00:00Z"
    }
  ],
  "pagination": { "count": 8, "totalPages": 1, "isNext": false, "isPrev": false }
}
```

---

### `PATCH /mentor/company/<mentor_id>/verify/`

Admin approves or rejects a Company Mentor application.

| | |
|---|---|
| **Roles** | ADMIN |
| **Auth** | JWT required |

**On approve**: sets `is_verified = True`, assigns existing `"Mentor"` system role (idempotent), logs action.
**On reject**: sets `is_verified = False`, logs action.

**Request Body — Approve**
```json
{
  "action": "approve",
  "verification_note": "Identity and company affiliation verified."
}
```

**Request Body — Reject**
```json
{
  "action": "reject",
  "verification_note": "Could not verify company affiliation."
}
```

**Response — Approve (200 OK)**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Company mentor approved.",
  "response": {
    "mentor": {
      "id": "um-uuid-c01",
      "mentor_tier": "COMPANY_MENTOR",
      "org_id": "org-uuid-acme",
      "org_name": "Acme Corp",
      "is_verified": true,
      "verified_at": "2026-05-27T12:00:00Z"
    }
  }
}
```

**Response — Reject (200 OK)**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Company mentor application rejected."
}
```

**Error — Invalid action (400)**
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": "action must be 'approve' or 'reject'."
}
```

---

### `GET /mentor/company/sessions/`

List sessions scoped to the requesting mentor's verified company orgs. Admins see all company-org sessions.

| | |
|---|---|
| **Roles** | ADMIN, MENTOR |
| **Auth** | JWT required |

**Tier enforcement**: Non-admin mentors only see sessions whose `org_id` matches one of their `is_verified=True` + `COMPANY_MENTOR` rows.

**Query Parameters**

| Param | Type | Description |
|---|---|---|
| `search` | string | Filter by title or org name |
| `sort_by` | string | `starts_at`, `title` |

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "response": [
    {
      "id": "sess-uuid-c01",
      "title": "System Design for Freshers",
      "org_id": "org-uuid-acme",
      "org_name": "Acme Corp",
      "status": "SCHEDULED",
      "mode": "ONLINE",
      "starts_at": "2026-06-01T10:00:00Z",
      "ends_at": "2026-06-01T12:00:00Z",
      "meeting_link": "https://meet.google.com/acme-sysdesign",
      "created_by_name": "Rahul Dev",
      "created_at": "2026-05-27T10:00:00Z",
      "participant_count": 12
    }
  ],
  "pagination": { "count": 4, "totalPages": 1, "isNext": false, "isPrev": false }
}
```

---

### `POST /mentor/company/sessions/`

Create a session scoped to a specific company org.

| | |
|---|---|
| **Roles** | MENTOR |
| **Auth** | JWT required |

**Tier enforcement**: Requester must have `is_verified=True` for `(COMPANY_MENTOR, org)`.
**Auto-status**: Org-scoped sessions are always `SCHEDULED` — no admin approval queue.

**Request Body**
```json
{
  "org": "org-uuid-acme",
  "title": "System Design for Freshers",
  "description": "Covers scalability, databases, and microservices.",
  "mode": "ONLINE",
  "starts_at": "2026-06-01T10:00:00Z",
  "ends_at": "2026-06-01T12:00:00Z",
  "meeting_link": "https://meet.google.com/acme-sysdesign",
  "max_participants": 20
}
```

> `ig` is optional — set it only if the session is also linked to a specific Interest Group.

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Company session created.",
  "response": {
    "session": {
      "id": "sess-uuid-c01",
      "title": "System Design for Freshers",
      "org_id": "org-uuid-acme",
      "org_name": "Acme Corp",
      "status": "SCHEDULED",
      "is_global": false,
      "starts_at": "2026-06-01T10:00:00Z",
      "ends_at": "2026-06-01T12:00:00Z"
    }
  }
}
```

**Error — Not a verified company mentor for this org (403)**
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": "You are not a verified company mentor for this organisation."
}
```

---

### `GET /mentor/company/sessions/<session_id>/`

Retrieve full details of a single company-scoped session.

| | |
|---|---|
| **Roles** | ADMIN, MENTOR |

**Tier enforcement**: MENTOR must have a verified `COMPANY_MENTOR` row for the session's `org_id`.

---

### `PATCH /mentor/company/sessions/<session_id>/`

Update a company session. Only the session creator can update it.

| | |
|---|---|
| **Roles** | MENTOR |

**Request Body** *(all fields optional)*
```json
{
  "title": "System Design — Advanced Track",
  "starts_at": "2026-06-02T10:00:00Z",
  "ends_at": "2026-06-02T12:00:00Z"
}
```

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Session updated."
}
```

---

### `DELETE /mentor/company/sessions/<session_id>/`

Cancel (soft-delete) a company session.

| | |
|---|---|
| **Roles** | ADMIN, MENTOR (creator only) |

Sets `status = "CANCELLED"`.

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Session cancelled."
}
```

---

### `GET /mentor/company/opportunities/`

List opportunities scoped to the mentor's company org(s).

| | |
|---|---|
| **Roles** | ADMIN, MENTOR |

**Tier enforcement**: MENTOR only sees opportunities for their verified company orgs.

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "response": [
    {
      "id": "opp-uuid-c01",
      "org_id": "org-uuid-acme",
      "org_name": "Acme Corp",
      "ig_id": null,
      "ig_name": null,
      "type": "INTERNSHIP",
      "title": "Backend Engineer Intern — Summer 2026",
      "description": "3-month paid internship at Acme Corp.",
      "eligibility": "Final year CS students only.",
      "application_url": "https://acmecorp.com/intern/apply",
      "starts_at": "2026-07-01T00:00:00Z",
      "ends_at": "2026-09-30T00:00:00Z",
      "status": "PUBLISHED",
      "created_by_name": "Rahul Dev",
      "created_at": "2026-05-20T10:00:00Z",
      "updated_at": "2026-05-20T10:00:00Z"
    }
  ],
  "pagination": { "count": 3, "totalPages": 1, "isNext": false, "isPrev": false }
}
```

---

### `POST /mentor/company/opportunities/`

Create a new company-scoped opportunity.

| | |
|---|---|
| **Roles** | MENTOR |

**Tier enforcement**: Requester must have `is_verified=True` for `(COMPANY_MENTOR, org)`.

**Request Body**
```json
{
  "org": "org-uuid-acme",
  "type": "INTERNSHIP",
  "title": "Backend Engineer Intern — Summer 2026",
  "description": "3-month paid internship at Acme Corp.",
  "eligibility": "Final year CS students only.",
  "application_url": "https://acmecorp.com/intern/apply",
  "starts_at": "2026-07-01T00:00:00Z",
  "ends_at": "2026-09-30T00:00:00Z",
  "status": "PUBLISHED"
}
```

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Company opportunity created.",
  "response": { "opportunity": { "...": "full opportunity object" } }
}
```

---

### `GET /mentor/company/opportunities/<opportunity_id>/`
### `PATCH /mentor/company/opportunities/<opportunity_id>/`
### `DELETE /mentor/company/opportunities/<opportunity_id>/`

CRUD on a single company opportunity. `DELETE` sets `status = "ARCHIVED"`.

| | |
|---|---|
| **Roles** | GET: ADMIN, MENTOR · PATCH: MENTOR (creator only) · DELETE: ADMIN, MENTOR (creator only) |
| **Tier enforcement** | MENTOR must have verified `COMPANY_MENTOR` row for the opportunity's `org_id` |

---

### `GET /mentor/company/mentees/`

Distinct list of users who attended sessions in the mentor's company org(s).

| | |
|---|---|
| **Roles** | MENTOR |

**Tier enforcement**: Only sessions belonging to the mentor's verified company orgs are considered.

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "response": [
    {
      "user_id": "user-uuid-050",
      "user__full_name": "Riya Sharma",
      "user__muid": "riya@mulearn",
      "user__email": "riya@acmecorp.com",
      "total_sessions": 3
    }
  ],
  "pagination": { "count": 12, "totalPages": 2, "isNext": true, "isPrev": false }
}
```

**Error — No verified company orgs (400)**
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": "You have no verified company mentor scopes."
}
```

---

### `GET /mentor/company/review-queue/`

KarmaActivityLog entries **pending mentor review** for users in the mentor's company org(s).

| | |
|---|---|
| **Roles** | MENTOR |

**Tier enforcement**: Only KAL entries submitted by users whose `UserOrganizationLink.org_id` is in the mentor's verified company org list.

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "response": [
    {
      "id": "kal-uuid-c01",
      "user_name": "Riya Sharma",
      "user_muid": "riya@mulearn",
      "task_title": "Build a CI/CD Pipeline",
      "task_hashtag": "#cicd",
      "ig_name": null,
      "karma": 600,
      "mentor_review_status": "PENDING",
      "created_at": "2026-05-26T08:00:00Z"
    }
  ],
  "pagination": { "count": 5, "totalPages": 1, "isNext": false, "isPrev": false }
}
```

---

### `GET /mentor/company/review-queue/<kal_id>/`

Retrieve a single task submission entry.

| | |
|---|---|
| **Roles** | MENTOR |

**Tier enforcement**: The submitting user must belong to one of the mentor's verified company orgs.

---

### `PATCH /mentor/company/review-queue/<kal_id>/`

Approve or reject a task submission.

| | |
|---|---|
| **Roles** | MENTOR |

**Tier enforcement**: Only entries from company org users can be reviewed; cross-org or campus reviews are blocked.

**Request Body**
```json
{
  "status": "APPROVED",
  "feedback": "Clean implementation with proper error handling."
}
```

> `status`: `"APPROVED"` | `"REJECTED"`

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Review submitted."
}
```

**Error — Already reviewed (400)**
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": "Entry is already 'APPROVED'."
}
```

---

### `GET /mentor/company/my-orgs/`

List all Company Mentor rows for the authenticated user (one per verified company org).

| | |
|---|---|
| **Roles** | MENTOR |

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "response": {
    "orgs": [
      {
        "id": "um-uuid-c01",
        "mentor_tier": "COMPANY_MENTOR",
        "org_id": "org-uuid-acme",
        "org_name": "Acme Corp",
        "org_type": "Company",
        "is_verified": true,
        "verified_at": "2026-05-20T11:00:00Z"
      },
      {
        "id": "um-uuid-c03",
        "mentor_tier": "COMPANY_MENTOR",
        "org_id": "org-uuid-techco",
        "org_name": "TechCo Pvt Ltd",
        "org_type": "Company",
        "is_verified": false,
        "verified_at": null
      }
    ]
  }
}
```

---

### `GET /mentor/company/availability/`

List availability slots for the authenticated company mentor.

| | |
|---|---|
| **Roles** | MENTOR |

**Tier enforcement**: Returns `400` if the user has no verified `COMPANY_MENTOR` rows.

---

### `POST /mentor/company/availability/`

Create an availability slot.

| | |
|---|---|
| **Roles** | MENTOR |

**Tier enforcement**: User must have at least one verified `COMPANY_MENTOR` row.

**Request Body**
```json
{
  "weekday": 2,
  "start_time": "09:00:00",
  "end_time": "11:00:00",
  "timezone": "Asia/Kolkata"
}
```

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Availability slot created.",
  "response": {
    "slot": {
      "id": "slot-uuid-c01",
      "mentor_user_id": "user-uuid-001",
      "weekday": 2,
      "start_time": "09:00:00",
      "end_time": "11:00:00",
      "timezone": "Asia/Kolkata",
      "is_active": true
    }
  }
}
```

---

---

# 22. Campus Mentor

> **Prefix**: `/api/v1/dashboard/mentor/campus-mentor/`
>
> Campus mentors are users with a verified `UserMentor` row where `mentor_tier = "CAMPUS_MENTOR"` and `org_id` points to a **College-type** organisation.
>
> **Tier enforcement**: Every write endpoint verifies that the requesting user has `is_verified=True` for the exact `(CAMPUS_MENTOR, org_id)` combination. Campus mentors cannot use company-mentor endpoints, cannot manage events or sessions of other campuses, and cannot review tasks from non-campus users.
>
> **Campus-only feature**: Campus mentors can additionally create and manage **campus events** — an exclusive capability not available to company or IG mentors.

---

### `GET /mentor/campus-mentor/onboarding/`

List the authenticated user's own Campus Mentor application rows.

| | |
|---|---|
| **Roles** | Any authenticated user |
| **Auth** | JWT required |

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "response": {
    "mentors": [
      {
        "id": "um-uuid-cam01",
        "full_name": "Asha Krishnan",
        "email": "asha@geckerala.ac.in",
        "muid": "asha@mulearn",
        "mentor_tier": "CAMPUS_MENTOR",
        "org_id": "org-uuid-gec",
        "org_name": "GEC Kerala",
        "org_type": "College",
        "about": "CS faculty with focus on competitive programming.",
        "expertise": ["Data Structures", "Algorithms", "C++"],
        "reason": "Want to bridge the gap between academics and industry.",
        "is_verified": true,
        "verified_at": "2026-05-15T09:00:00Z",
        "verification_note": "Faculty credentials confirmed.",
        "hours": 8,
        "created_at": "2026-05-05T10:00:00Z"
      }
    ]
  }
}
```

---

### `POST /mentor/campus-mentor/onboarding/`

Apply to become a Campus Mentor for a specific college organisation.

| | |
|---|---|
| **Roles** | Any authenticated user |
| **Auth** | JWT required |

**Rules**
- `org` must point to an existing organisation with `org_type = "College"` — returns `400` otherwise
- Only one application per `(user, CAMPUS_MENTOR, org)` — duplicate returns `400`
- Application starts `is_verified = False`

**Request Body**
```json
{
  "org": "org-uuid-gec",
  "about": "CS faculty with 5 years of teaching experience at GEC Kerala.",
  "expertise": ["Data Structures", "Algorithms", "C++"],
  "reason": "Want to bridge the gap between academics and industry."
}
```

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Campus mentor application submitted. Awaiting admin approval.",
  "response": {
    "mentor": {
      "id": "um-uuid-cam02",
      "mentor_tier": "CAMPUS_MENTOR",
      "org_id": "org-uuid-gec",
      "org_name": "GEC Kerala",
      "is_verified": false,
      "created_at": "2026-05-27T10:00:00Z"
    }
  }
}
```

**Error — Wrong org type (400)**
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": "A valid College organisation id is required."
}
```

**Error — Duplicate (400)**
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": "You have already applied as a campus mentor for this organisation."
}
```

---

### `PATCH /mentor/campus-mentor/onboarding/<mentor_id>/`

Update own Campus Mentor profile.

| | |
|---|---|
| **Roles** | MENTOR |

**Request Body** *(all fields optional)*
```json
{
  "about": "Now also mentoring in competitive programming.",
  "expertise": ["Data Structures", "Algorithms", "C++", "Competitive Programming"]
}
```

---

### `GET /mentor/campus-mentor/list/`

Admin: paginated list of all Campus Mentor applications.

| | |
|---|---|
| **Roles** | ADMIN |

**Query Parameters**

| Param | Type | Description |
|---|---|---|
| `org_id` | UUID | Filter by college org |
| `is_verified` | boolean string | `true` / `false` |
| `search` | string | Name, email, or org name |

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "response": [
    {
      "id": "um-uuid-cam01",
      "full_name": "Asha Krishnan",
      "email": "asha@geckerala.ac.in",
      "muid": "asha@mulearn",
      "mentor_tier": "CAMPUS_MENTOR",
      "org_id": "org-uuid-gec",
      "org_name": "GEC Kerala",
      "org_type": "College",
      "is_verified": true,
      "created_at": "2026-05-05T10:00:00Z"
    }
  ],
  "pagination": { "count": 15, "totalPages": 2, "isNext": true, "isPrev": false }
}
```

---

### `PATCH /mentor/campus-mentor/<mentor_id>/verify/`

Admin approves or rejects a Campus Mentor application.

| | |
|---|---|
| **Roles** | ADMIN |

**On approve**: `is_verified = True`, assigns existing `"Mentor"` system role (idempotent), logs action.

**Request Body — Approve**
```json
{
  "action": "approve",
  "verification_note": "Faculty credentials verified with institution."
}
```

**Response — Approve (200 OK)**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Campus mentor approved.",
  "response": {
    "mentor": {
      "id": "um-uuid-cam01",
      "mentor_tier": "CAMPUS_MENTOR",
      "org_id": "org-uuid-gec",
      "org_name": "GEC Kerala",
      "is_verified": true,
      "verified_at": "2026-05-27T12:00:00Z"
    }
  }
}
```

---

### `GET /mentor/campus-mentor/sessions/`

List sessions scoped to the requesting mentor's verified college org(s).

| | |
|---|---|
| **Roles** | ADMIN, MENTOR |

**Tier enforcement**: MENTOR only sees sessions whose `org_id` matches one of their verified `CAMPUS_MENTOR` rows.

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "response": [
    {
      "id": "sess-uuid-cam01",
      "title": "DSA Workshop — Arrays & Sorting",
      "org_id": "org-uuid-gec",
      "org_name": "GEC Kerala",
      "ig_id": null,
      "ig_name": null,
      "status": "SCHEDULED",
      "mode": "OFFLINE",
      "venue": "CS Lab 2, GEC Kerala",
      "starts_at": "2026-06-05T09:00:00Z",
      "ends_at": "2026-06-05T12:00:00Z",
      "created_by_name": "Asha Krishnan",
      "participant_count": 35
    }
  ],
  "pagination": { "count": 6, "totalPages": 1, "isNext": false, "isPrev": false }
}
```

---

### `POST /mentor/campus-mentor/sessions/`

Create a session scoped to a campus org.

| | |
|---|---|
| **Roles** | MENTOR |

**Tier enforcement**: Requester must have `is_verified=True` for `(CAMPUS_MENTOR, org)`.
**Auto-status**: `SCHEDULED` — no admin approval needed.
**Optional `ig`**: Include to link the session to a specific Interest Group chapter at this campus.

**Request Body**
```json
{
  "org": "org-uuid-gec",
  "title": "DSA Workshop — Arrays & Sorting",
  "description": "Hands-on session on array manipulation and sorting algorithms.",
  "mode": "OFFLINE",
  "venue": "CS Lab 2, GEC Kerala",
  "starts_at": "2026-06-05T09:00:00Z",
  "ends_at": "2026-06-05T12:00:00Z",
  "max_participants": 40,
  "ig": "ig-uuid-dsa"
}
```

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Campus session created.",
  "response": {
    "session": {
      "id": "sess-uuid-cam01",
      "title": "DSA Workshop — Arrays & Sorting",
      "org_id": "org-uuid-gec",
      "org_name": "GEC Kerala",
      "status": "SCHEDULED",
      "is_global": false,
      "mode": "OFFLINE",
      "venue": "CS Lab 2, GEC Kerala"
    }
  }
}
```

---

### `GET /mentor/campus-mentor/sessions/<session_id>/`
### `PATCH /mentor/campus-mentor/sessions/<session_id>/`
### `DELETE /mentor/campus-mentor/sessions/<session_id>/`

CRUD on a single campus session. `DELETE` sets `status = "CANCELLED"`.

| | |
|---|---|
| **Roles** | GET/DELETE: ADMIN, MENTOR · PATCH: MENTOR (creator only) |
| **Tier enforcement** | MENTOR must have verified `CAMPUS_MENTOR` row for the session's `org_id` |

---

### `GET /mentor/campus-mentor/opportunities/`

List opportunities scoped to the mentor's campus org(s).

| | |
|---|---|
| **Roles** | ADMIN, MENTOR |

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "response": [
    {
      "id": "opp-uuid-cam01",
      "org_id": "org-uuid-gec",
      "org_name": "GEC Kerala",
      "ig_id": null,
      "ig_name": null,
      "type": "HACKATHON",
      "title": "GEC Internal Hackathon 2026",
      "description": "48-hour hackathon for all GEC students.",
      "eligibility": "Currently enrolled GEC students only.",
      "application_url": "https://gec.ac.in/hackathon/register",
      "starts_at": "2026-07-15T09:00:00Z",
      "ends_at": "2026-07-17T09:00:00Z",
      "status": "PUBLISHED",
      "created_by_name": "Asha Krishnan",
      "created_at": "2026-05-25T11:00:00Z"
    }
  ],
  "pagination": { "count": 2, "totalPages": 1, "isNext": false, "isPrev": false }
}
```

---

### `POST /mentor/campus-mentor/opportunities/`

Create a campus-scoped opportunity.

| | |
|---|---|
| **Roles** | MENTOR |

**Tier enforcement**: `is_verified=True` for `(CAMPUS_MENTOR, org)` required.

**Request Body**
```json
{
  "org": "org-uuid-gec",
  "type": "HACKATHON",
  "title": "GEC Internal Hackathon 2026",
  "description": "48-hour hackathon for all GEC students.",
  "eligibility": "Currently enrolled GEC students only.",
  "application_url": "https://gec.ac.in/hackathon/register",
  "starts_at": "2026-07-15T09:00:00Z",
  "ends_at": "2026-07-17T09:00:00Z",
  "status": "PUBLISHED"
}
```

---

### `GET /mentor/campus-mentor/opportunities/<opportunity_id>/`
### `PATCH /mentor/campus-mentor/opportunities/<opportunity_id>/`
### `DELETE /mentor/campus-mentor/opportunities/<opportunity_id>/`

CRUD on a single campus opportunity. `DELETE` sets `status = "ARCHIVED"`.

| | |
|---|---|
| **Roles** | GET/DELETE: ADMIN, MENTOR · PATCH: MENTOR (creator only) |

---

### `GET /mentor/campus-mentor/mentees/`

Distinct list of campus students who attended sessions in the mentor's college org(s).

| | |
|---|---|
| **Roles** | MENTOR |

**Tier enforcement**: Only sessions belonging to verified `CAMPUS_MENTOR` orgs are considered.

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "response": [
    {
      "user_id": "user-uuid-101",
      "user__full_name": "Arun S",
      "user__muid": "arun@mulearn",
      "user__email": "arun@geckerala.ac.in",
      "total_sessions": 5
    }
  ],
  "pagination": { "count": 35, "totalPages": 4, "isNext": true, "isPrev": false }
}
```

---

### `GET /mentor/campus-mentor/review-queue/`

KarmaActivityLog entries pending review for students in the mentor's campus org(s).

| | |
|---|---|
| **Roles** | MENTOR |

**Tier enforcement**: Only KAL entries from users whose `UserOrganizationLink.org_id` is in the mentor's verified college org list are returned.

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "response": [
    {
      "id": "kal-uuid-cam01",
      "user_name": "Arun S",
      "user_muid": "arun@mulearn",
      "task_title": "Implement Binary Search Tree",
      "task_hashtag": "#bst",
      "ig_name": "Data Structures",
      "karma": 400,
      "mentor_review_status": "PENDING",
      "created_at": "2026-05-26T07:30:00Z"
    }
  ],
  "pagination": { "count": 8, "totalPages": 1, "isNext": false, "isPrev": false }
}
```

---

### `GET /mentor/campus-mentor/review-queue/<kal_id>/`
### `PATCH /mentor/campus-mentor/review-queue/<kal_id>/`

GET retrieves a single entry. PATCH approves or rejects it.

| | |
|---|---|
| **Roles** | MENTOR |
| **Tier enforcement** | Submitting user must be in one of the mentor's verified campus orgs |

**PATCH Request Body**
```json
{
  "status": "APPROVED",
  "feedback": "Correct implementation with proper edge case handling."
}
```

---

### `GET /mentor/campus-mentor/events/`

List campus events scoped to the mentor's verified college org(s).

> **Campus-exclusive feature** — only `CAMPUS_MENTOR` tier has access to event management.

| | |
|---|---|
| **Roles** | MENTOR |

**Tier enforcement**: Events aggregated across all verified `CAMPUS_MENTOR` orgs.

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "response": {
    "data": [
      {
        "id": "event-uuid-cam01",
        "title": "CS Department Tech Fest 2026",
        "org_id": "org-uuid-gec",
        "org_name": "GEC Kerala",
        "start_datetime": "2026-06-20T09:00:00Z",
        "end_datetime": "2026-06-20T18:00:00Z",
        "venue": "GEC Main Auditorium",
        "created_by": "Asha Krishnan"
      }
    ],
    "pagination": { "count": 2, "totalPages": 1, "isNext": false, "isPrev": false }
  }
}
```

---

### `POST /mentor/campus-mentor/events/`

Create a new campus event.

| | |
|---|---|
| **Roles** | MENTOR |

**Tier enforcement**: Requester must have `is_verified=True` for `(CAMPUS_MENTOR, org)`.

**Request Body**
```json
{
  "org": "org-uuid-gec",
  "title": "CS Department Tech Fest 2026",
  "start_datetime": "2026-06-20T09:00:00Z",
  "end_datetime": "2026-06-20T18:00:00Z",
  "venue": "GEC Main Auditorium",
  "description": "Annual department-level tech fest with workshops and competitions."
}
```

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Campus event created.",
  "response": {
    "event_id": "event-uuid-cam01"
  }
}
```

**Error — Not a verified campus mentor for this org (400)**
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": "You are not a verified campus mentor for this organisation."
}
```

---

### `GET /mentor/campus-mentor/events/<event_id>/`

Retrieve a single campus event.

| | |
|---|---|
| **Roles** | MENTOR |
| **Tier enforcement** | Event must belong to one of the mentor's verified campus orgs |

---

### `PATCH /mentor/campus-mentor/events/<event_id>/`

Update a campus event.

| | |
|---|---|
| **Roles** | MENTOR (creator only) |

**Request Body** *(all fields optional)*
```json
{
  "title": "CS Department Tech Fest 2026 — Revised Schedule",
  "start_datetime": "2026-06-21T09:00:00Z"
}
```

---

### `DELETE /mentor/campus-mentor/events/<event_id>/`

Delete a campus event.

| | |
|---|---|
| **Roles** | MENTOR (creator only) |

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Event deleted."
}
```

**Error — Not creator (400)**
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": "You can only delete events you created."
}
```

---

### `GET /mentor/campus-mentor/my-orgs/`

List all Campus Mentor rows for the authenticated user.

| | |
|---|---|
| **Roles** | MENTOR |

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "response": {
    "orgs": [
      {
        "id": "um-uuid-cam01",
        "mentor_tier": "CAMPUS_MENTOR",
        "org_id": "org-uuid-gec",
        "org_name": "GEC Kerala",
        "org_type": "College",
        "is_verified": true,
        "verified_at": "2026-05-15T09:00:00Z"
      },
      {
        "id": "um-uuid-cam04",
        "mentor_tier": "CAMPUS_MENTOR",
        "org_id": "org-uuid-nitc",
        "org_name": "NIT Calicut",
        "org_type": "College",
        "is_verified": false,
        "verified_at": null
      }
    ]
  }
}
```

---

### `GET /mentor/campus-mentor/availability/`

List availability slots for the campus mentor.

| | |
|---|---|
| **Roles** | MENTOR |
| **Tier enforcement** | Returns `400` if user has no verified `CAMPUS_MENTOR` rows |

---

### `POST /mentor/campus-mentor/availability/`

Create an availability slot.

| | |
|---|---|
| **Roles** | MENTOR |

**Request Body**
```json
{
  "weekday": 1,
  "start_time": "14:00:00",
  "end_time": "16:00:00",
  "timezone": "Asia/Kolkata",
  "ig": "ig-uuid-dsa"
}
```

**Response — 200 OK**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Availability slot created.",
  "response": {
    "slot": {
      "id": "slot-uuid-cam01",
      "mentor_user_id": "user-uuid-asha",
      "weekday": 1,
      "start_time": "14:00:00",
      "end_time": "16:00:00",
      "timezone": "Asia/Kolkata",
      "is_active": true
    }
  }
}
```

---

## Tier Enforcement Summary

| Endpoint group | `mentor_tier` required | `org_id` check | System role |
|---|---|---|---|
| `/mentor/onboarding/` | `IG_MENTOR` or `MENTOR` | N/A | `Mentor` |
| `/mentor/sessions/` | `IG_MENTOR` or `MENTOR` | N/A | `Mentor` |
| `/mentor/company/*` | `COMPANY_MENTOR` | exact Company org match | `Mentor` |
| `/mentor/campus-mentor/*` | `CAMPUS_MENTOR` | exact College org match | `Mentor` |
| `/mentor/campus-mentor/events/*` | `CAMPUS_MENTOR` only | exact College org match | `Mentor` |

> A user holding all four tiers simultaneously (one IG mentor row, one global row, one company row, one campus row) can freely use **all** endpoint groups — but each group only sees and acts on its own tier's data.
