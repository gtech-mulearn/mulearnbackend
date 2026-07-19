# Company Mentor — API Reference

> **Base URL prefix** assumed throughout this document:
> - Company endpoints → `/api/v1/dashboard/company/`
> - Mentor endpoints → `/api/v1/dashboard/mentor/`
> - Calendar endpoints → `/api/v1/calendar/`
> - Leaderboard endpoints → `/api/v1/leaderboard/`
>
> All authenticated endpoints require `Authorization: Bearer <JWT>` header unless noted as public.

**Source:** `api/dashboard/company/`, `api/dashboard/mentor/`, `api/calendar/`, `api/leaderboard/`

**Related docs:** [Dashboard_Company.md](./Dashboard_Company.md), [Dashboard_Company_Tasks.md](./Dashboard_Company_Tasks.md), [Dashboard_Mentor.md](./Dashboard_Mentor.md)

---

## Response envelope

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

HTTP status codes follow `statusCode` in the body (typically `400`, `403`, or `404` on failure).

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
  "hasError": false,
  "statusCode": 200,
  "message": { "general": [] },
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

---

## Table of Contents

1. [Company Mentor — Nomination](#1-company-mentor--nomination)
2. [Admin — Mentor Approval](#2-admin--mentor-approval)
3. [Company Management (Extended)](#3-company-management-extended)
   - [Profile](#31-company-profile)
   - [Jobs](#32-company-jobs)
   - [Applications](#33-job-applications)
   - [MuLearner Directory](#34-mulearner-directory)
   - [Gig Analytics](#35-gig-analytics)
   - [Tasks](#36-task-management)
4. [Mentor Sessions (Extended)](#4-mentor-sessions-extended)
   - [Create Session](#41-create-session)
   - [Available Sessions](#42-available-sessions-for-learners)
5. [Calendar](#5-calendar)
   - [Company Session Calendar](#51-company-session-calendar)
   - [IG Mentor Session Calendar](#52-ig-mentor-session-calendar)
   - [Campus Mentor Session Calendar](#53-campus-mentor-session-calendar)
6. [Leaderboard](#6-leaderboard)
   - [IG Mentor Leaderboard](#61-ig-mentor-leaderboard)
   - [Campus Mentor Leaderboard](#62-campus-mentor-leaderboard)
7. [Event Management](#7-event-management)

---

## 1. Company Mentor — Nomination

> **Who can nominate?** Only the **verified company creator** (user with the `Company` role linked to a verified company).
>
> The nominated user must already be a member of the company's Organisation record (`UserOrganizationLink`) **before** nomination.
>
> After nomination the record enters `PENDING` state until an admin approves via `PATCH /dashboard/mentor/verify/<mentor_id>/`.
>
> **Approved Company Mentors cannot nominate** — nomination endpoints require the `Company` role, which is assigned to the company creator on verification, not to nominated mentors.

---

### `POST /api/v1/dashboard/company/mentor/nominate/`

Nominate a platform user (identified by their `muid`) as a Company Mentor for your company.

**Auth:** JWT · `Company` role · verified company profile

**Request body**

```json
{
  "muid": "john-doe@mulearn",
  "reason": "Senior developer, deeply involved in company projects."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `muid` | string | ✅ | MuID of the user to nominate (e.g. `john-doe@mulearn`) |
| `reason` | string | ❌ | Optional reason / recommendation note |

**Validation rules**

- `muid` must resolve to an existing platform user
- The resolved user must have a `UserOrganizationLink` entry for this company's org
- No active (non-`REJECTED`) `COMPANY_MENTOR` nomination must already exist for that user + company org

**Success response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["User nominated as Company Mentor. Pending admin approval."] },
  "response": {
    "id": "a1b2c3d4-...",
    "user_id": "u-uuid-here",
    "user_name": "John Doe",
    "user_email": "john@example.com",
    "org_name": "Acme Corp",
    "mentor_tier": "COMPANY_MENTOR",
    "status": "PENDING",
    "reason": "Senior developer, deeply involved in company projects.",
    "verification_note": null,
    "verified_at": null
  }
}
```

**Error responses**

| HTTP | Scenario |
|---|---|
| `403` | No verified company profile for caller (`You must have a verified company profile to nominate mentors.`) |
| `400` | `muid` not found on platform |
| `400` | User is not a member of this company's organisation |
| `400` | User already has an active nomination for this company |

---

### `GET /api/v1/dashboard/company/mentor/list/`

List all Company Mentor nominations for the authenticated company.

**Auth:** JWT · `Company` role · verified company profile (creator only)

**Success response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": [] },
  "response": [
    {
      "id": "a1b2c3d4-...",
      "user_id": "u-uuid-here",
      "user_name": "John Doe",
      "user_email": "john@example.com",
      "org_name": "Acme Corp",
      "mentor_tier": "COMPANY_MENTOR",
      "status": "PENDING",
      "reason": "Senior developer.",
      "verification_note": null,
      "verified_at": null
    },
    {
      "id": "e5f6g7h8-...",
      "user_id": "u-uuid-2",
      "user_name": "Jane Smith",
      "user_email": "jane@example.com",
      "org_name": "Acme Corp",
      "mentor_tier": "COMPANY_MENTOR",
      "status": "APPROVED",
      "reason": "Team lead.",
      "verification_note": "Verified after background check.",
      "verified_at": "2026-06-02T10:00:00Z"
    }
  ]
}
```

> **Note:** The list is returned as a bare array in `response`, not wrapped in `data` / `pagination`.

---

## 2. Admin — Mentor Approval

> **Existing endpoint extended.** `PATCH /api/v1/dashboard/mentor/verify/<mentor_id>/` handles all mentor tiers. When an admin approves a `COMPANY_MENTOR`:
>
> 1. `UserMentor.status` → `APPROVED`
> 2. `UserRoleLink` (Mentor role) is created/updated for the user
> 3. A `UserOrganizationLink` is auto-created (or marked `verified = true`) linking the mentor user to the company's Organisation

### `PATCH /api/v1/dashboard/mentor/verify/<mentor_id>/`

**Auth:** JWT · `Admin` role required

**Request body — Approve**

```json
{
  "status": "APPROVED"
}
```

**Request body — Reject**

```json
{
  "status": "REJECTED",
  "verification_note": "Insufficient detail in expertise section."
}
```

| Field | Type | Values |
|---|---|---|
| `status` | string | `APPROVED` or `REJECTED` |
| `verification_note` | string | Required when `status` is `REJECTED` |

**Success response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Mentor status updated to APPROVED successfully."] },
  "response": {}
}
```

**Side-effects on approval (`COMPANY_MENTOR`)**

| Side-effect | Table | Result |
|---|---|---|
| Mentor role granted | `user_role_link` | Role `Mentor` linked to user (`verified = true`) |
| Org link created/verified | `user_organization_link` | `user → company_org`, `verified = true` |

---

## 3. Company Management (Extended)

> Endpoints below resolve the company via `_get_company_for_user()` — accessible to:
> - the **verified company creator** (`company_user_id`), OR
> - an **approved `COMPANY_MENTOR`** for that company.
>
> No explicit `Company` role is required for these endpoints; JWT authentication plus company resolution is sufficient.
>
> **Exception:** mentor nomination/list (§1) still requires the `Company` role (creator only).

---

### 3.1 Company Profile

#### `GET /api/v1/dashboard/company/profile/`

Retrieve the company profile.

**Auth:** JWT · verified company creator or approved Company Mentor

**Success response `200`**

Returns the full `CompanyDetailSerializer` shape (all model fields). See [Dashboard_Company.md §3 profile GET](./Dashboard_Company.md#3-profile) for the complete field list.

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": [] },
  "response": {
    "id": "cmp-uuid",
    "company_user": "user-uuid",
    "company_user_name": "Jane Doe",
    "company_user_email": "jane@example.com",
    "name": "Acme Corp",
    "slug": "acme-corp",
    "status": "verified",
    "logo": "https://cdn.example.com/logo.png",
    "description": "We build products.",
    "short_pitch": "The best product company.",
    "industry_sector": "Technology",
    "website_link": "https://acme.com",
    "email": "hr@acme.com",
    "location": "Bangalore",
    "company_size": "51-200",
    "linkedin_url": "https://linkedin.com/company/acme",
    "founded_year": 2015,
    "remote_policy": "Hybrid",
    "culture_text": "We value innovation.",
    "tech_stack": ["Django", "React", "PostgreSQL"],
    "perks": ["Health insurance", "Remote-friendly"],
    "testimonials": [],
    "gallery": []
  }
}
```

#### `PATCH /api/v1/dashboard/company/profile/`

Update the company profile (partial update).

**Auth:** JWT · verified company creator or approved Company Mentor

**Request body** *(all fields optional — same writable fields as company registration)*

```json
{
  "description": "Updated description.",
  "short_pitch": "Redefining product development.",
  "remote_policy": "Remote-first",
  "tech_stack": ["Django", "React", "PostgreSQL", "Redis"]
}
```

**Success response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Company profile updated successfully."] },
  "response": { "...updated profile fields..." }
}
```

---

### 3.2 Company Jobs

#### `POST /api/v1/dashboard/company/jobs/`

Post a new job or gig.

**Auth:** JWT · verified company creator or approved Company Mentor

**Request body**

```json
{
  "title": "Backend Engineer",
  "experience": "1-3 years",
  "job_description": "Build and maintain REST APIs.",
  "location": "Bangalore",
  "salary_range": "6-10 LPA",
  "job_type": "Full-Time",
  "status": "Active",
  "duration_value": null,
  "duration_unit": null,
  "hourly_rate": null,
  "deliverables": null,
  "stipend": null,
  "certificate_provided": null,
  "rules": [
    { "rule_type": "min_karma", "rule_value": "1000" }
  ]
}
```

| Field | Notes |
|-------|-------|
| `job_type` | `Hybrid`, `Full-Time`, `Remote`, `Part-Time`, `Internship`, `Gig` |
| `status` | `Draft`, `Active`, `Closed`, `Expired` |
| `duration_unit` | `days`, `weeks`, `months` (for Gig / Internship) |
| `certificate_provided` | `Yes` or `No` |
| `rules` | Optional; `rule_type`: `min_karma`, `max_karma`, `min_level`, `max_level`, etc. |

**Success response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Job posted successfully."] },
  "response": {
    "id": "job-uuid",
    "title": "Backend Engineer",
    "experience": "1-3 years",
    "job_description": "Build and maintain REST APIs.",
    "location": "Bangalore",
    "salary_range": "6-10 LPA",
    "job_type": "Full-Time",
    "status": "Active",
    "duration_value": null,
    "duration_unit": null,
    "hourly_rate": null,
    "deliverables": null,
    "stipend": null,
    "certificate_provided": null,
    "rules": [
      { "id": "rule-uuid", "rule_type": "min_karma", "rule_value": "1000" }
    ]
  }
}
```

---

#### `GET /api/v1/dashboard/company/jobs/`

List all jobs for the authenticated company.

**Auth:** JWT · verified company creator or approved Company Mentor

**Query params**

| Param | Type | Description |
|---|---|---|
| `search` | string | Search by `title`, `location`, `job_type` |
| `sortBy` | string | `title` or `created_at` (prefix `-` for descending) |
| `pageIndex`, `perPage` | int | Pagination |

**Success response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": [] },
  "response": {
    "data": [
      {
        "id": "job-uuid",
        "company_name": "Acme Corp",
        "company_logo": "https://cdn.example.com/logo.png",
        "title": "Backend Engineer",
        "experience": "1-3 years",
        "job_description": "Build and maintain REST APIs.",
        "location": "Bangalore",
        "salary_range": "6-10 LPA",
        "job_type": "Full-Time",
        "status": "Active",
        "duration_value": null,
        "duration_unit": null,
        "hourly_rate": null,
        "deliverables": null,
        "stipend": null,
        "certificate_provided": null,
        "rules": [],
        "created_at": "2026-06-01T10:00:00Z"
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

#### `GET /api/v1/dashboard/company/jobs/<job_id>/`

Retrieve details of a specific job. Returns a single job object in `response` (same fields as list item).

**Auth:** JWT · verified company creator or approved Company Mentor

#### `PATCH /api/v1/dashboard/company/jobs/<job_id>/`

Update a specific job (partial). Replacing `rules` deletes existing rules and recreates them.

**Auth:** JWT · verified company creator or approved Company Mentor

#### `DELETE /api/v1/dashboard/company/jobs/<job_id>/`

Soft-delete a specific job (`is_deleted = true`).

**Auth:** JWT · verified company creator or approved Company Mentor

**Success response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Job deleted successfully."] },
  "response": {}
}
```

---

### 3.3 Job Applications

#### `GET /api/v1/dashboard/company/jobs/<job_id>/applications/`

List all applicants for a specific job.

**Auth:** JWT · verified company creator or approved Company Mentor

**Query params:** `pageIndex`, `perPage`, `search`, `sortBy` (`applied_at`, `status`)

**Success response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": [] },
  "response": {
    "data": [
      {
        "id": "app-uuid",
        "job": "job-uuid",
        "applicant_name": "Priya K",
        "applicant_email": "priya@example.com",
        "resume_link": "https://cdn.example.com/resume.pdf",
        "cover_letter": "I am excited to apply.",
        "status": "Pending",
        "rejection_reason": null,
        "applied_at": "2026-06-02T08:30:00Z"
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

**Application status values:** `Pending`, `In-Review`, `Shortlisted`, `Interview`, `Selected`, `Rejected`

#### `PATCH /api/v1/dashboard/company/applications/<app_id>/status/`

Update the status of a job application.

**Auth:** JWT · verified company creator or approved Company Mentor

**Request body**

```json
{
  "status": "Shortlisted",
  "rejection_reason": null
}
```

**Reject example:**

```json
{
  "status": "Rejected",
  "rejection_reason": "Profile does not match required experience."
}
```

**Success response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Application status updated successfully."] },
  "response": {
    "id": "app-uuid",
    "job": "job-uuid",
    "applicant_name": "Priya K",
    "applicant_email": "priya@example.com",
    "resume_link": "https://cdn.example.com/resume.pdf",
    "cover_letter": "I am excited to apply.",
    "status": "Shortlisted",
    "rejection_reason": null,
    "applied_at": "2026-06-02T08:30:00Z"
  }
}
```

---

### 3.4 MuLearner Directory

#### `GET /api/v1/dashboard/company/mulearners/`

Browse the directory of MuLearners. Only users with `is_public = true` in user settings are returned.

**Auth:** JWT · verified company creator or approved Company Mentor

**Query params**

| Param | Type | Description |
|---|---|---|
| `min_karma` | int | Minimum karma score |
| `max_karma` | int | Maximum karma score |
| `level` | int | Level order number |
| `college` | string | College name (partial match) |
| `department` | string | Department (partial match) |
| `graduation_year` | string | Graduation year |
| `ig` | string | Interest Group name (partial match) |
| `skill` | string | Skill UUID |
| `achievement` | string | Achievement UUID |
| `task` | string | Task UUID (users with karma log for task) |
| `pageIndex`, `perPage`, `search`, `sortBy` | — | Search `full_name`, `muid`, `email`; sort `full_name`, `created_at`, `karma` |

**Success response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": [] },
  "response": {
    "data": [
      {
        "id": "u-uuid",
        "full_name": "Arjun Nair",
        "muid": "arjun-nair@mulearn",
        "email": "arjun@example.com",
        "karma": 4200,
        "level": 4,
        "college": "CUSAT",
        "department": "Computer Science",
        "graduation_year": 2026
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

### 3.5 Gig Analytics

#### `GET /api/v1/dashboard/company/analytics/gigs/`

Retrieve analytics for **Gig**-type jobs posted by the company.

**Auth:** JWT · verified company creator or approved Company Mentor

**Success response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": [] },
  "response": {
    "total_gigs_posted": 12,
    "active_gigs": 5,
    "closed_gigs": 7,
    "average_hourly_rate": 850.0,
    "application_funnel": {
      "Total": 148,
      "Pending": 40,
      "In-Review": 30,
      "Shortlisted": 22,
      "Interview": 18,
      "Selected": 8,
      "Rejected": 30
    },
    "conversion_rate": "5.41%"
  }
}
```

---

### 3.6 Task Management

> Company creators and Company Mentors can submit tasks. Tasks start in `pending` state and go active only after admin approval.
>
> **Important:** Tasks are scoped to **`requested_by = current user`**, not to the company as a whole. Each mentor/creator only sees and manages tasks they personally submitted.
>
> Full task field reference: [Dashboard_Company_Tasks.md](./Dashboard_Company_Tasks.md)

#### `GET /api/v1/dashboard/company/tasks/`

List tasks submitted by the **authenticated user** (`requested_by_id = current user`).

**Auth:** JWT (any authenticated user; returns empty list if none submitted)

**Query params**

| Param | Description |
|---|---|
| `approval_status` | Filter: `pending` / `approved` / `rejected` |
| `pageIndex`, `perPage`, `search`, `sortBy` | Search `hashtag`, `title`, `description`, `karma`, `ig__name`, `type__title`, `approval_status` |

**Success response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": [] },
  "response": {
    "data": [
      {
        "id": "task-uuid",
        "hashtag": "#acme-onboarding-2026",
        "discord_link": null,
        "title": "Acme Onboarding Challenge",
        "description": "Complete the onboarding modules provided by Acme Corp.",
        "karma": 200,
        "channel": null,
        "type": "Learning",
        "active": false,
        "variable_karma": false,
        "usage_count": 1,
        "level": "Level 4",
        "org": null,
        "ig": null,
        "event": null,
        "bonus_karma": null,
        "bonus_time": null,
        "approval_status": "pending",
        "rejection_reason": null,
        "reviewed_at": null,
        "requested_by_name": "Jane Smith",
        "requested_at": "2026-06-01T00:00:00Z",
        "skills": [
          { "id": "skill-uuid-1", "name": "Python", "code": "python" }
        ],
        "created_at": "2026-06-01T00:00:00Z",
        "updated_at": "2026-06-01T00:00:00Z"
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

#### `POST /api/v1/dashboard/company/tasks/`

Submit a new task for admin approval. Requires a verified company profile (creator or approved Company Mentor).

**Auth:** JWT · verified company creator or approved Company Mentor

**Request body**

```json
{
  "hashtag": "#acme-onboarding-2026",
  "title": "Acme Onboarding Challenge",
  "description": "Complete the onboarding modules provided by Acme Corp.",
  "karma": 200,
  "usage_count": 1,
  "type": "type-uuid",
  "level": "level-uuid",
  "skill_ids": ["skill-uuid-1", "skill-uuid-2"]
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `hashtag` | Yes | Globally unique |
| `title` | Yes | Max 75 chars |
| `karma` | Yes | Integer |
| `type` | Yes | `TaskType` UUID |
| `description`, `usage_count`, `level`, `skill_ids` | No | `ig` / `channel` are **not** part of the company task create serializer |

**Success response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Task submitted for approval."] },
  "response": {}
}
```

#### `GET /api/v1/dashboard/company/tasks/<task_id>/`

Retrieve details of a task where `requested_by` is the current user. Requires verified company profile.

#### `PUT /api/v1/dashboard/company/tasks/<task_id>/`

Edit a task (resets `approval_status` to `pending` and `active` to `false` for re-approval).

**Success message:** `"Task updated and re-submitted for approval."`

#### `DELETE /api/v1/dashboard/company/tasks/<task_id>/`

Delete a task. Only `pending` tasks can be deleted.

**Success message:** `"Task deleted successfully."`

---

## 4. Mentor Sessions (Extended)

### 4.1 Create Session

#### `POST /api/v1/dashboard/mentor/session/create/`

Create a new mentorship session (starts in `PENDING_APPROVAL`). The endpoint **auto-detects** mentor type:

- **Company Mentor** (approved `COMPANY_MENTOR`) → `session_type = company_session`, `entity_id = company org UUID` (auto-resolved; do **not** pass `ig`)
- **IG Mentor** → `session_type = ig_session`, `entity_id = ig` (caller must pass `ig`; must be assigned as mentor for that IG)

> If the caller is an approved Company Mentor, the company path takes precedence even if `ig` is supplied.

**Auth:** JWT · `Mentor` role required

**Request body — IG Mentor**

```json
{
  "ig": "ig-uuid",
  "title": "Python Basics for Beginners",
  "description": "Covering core Python concepts.",
  "mode": "ONLINE",
  "starts_at": "2026-06-10T10:00:00Z",
  "ends_at": "2026-06-10T11:30:00Z",
  "meeting_link": "https://meet.google.com/abc-defg-hij",
  "venue": null,
  "max_participants": 30
}
```

**Request body — Company Mentor**

```json
{
  "title": "Acme Developer Mentoring — Sprint 1",
  "description": "Weekly sync for onboarding batch.",
  "mode": "ONLINE",
  "starts_at": "2026-06-11T15:00:00Z",
  "ends_at": "2026-06-11T16:00:00Z",
  "meeting_link": "https://meet.google.com/xyz-1234-abc",
  "venue": null,
  "max_participants": 20
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `ig` | IG mentors only | Interest Group UUID |
| `title` | Yes | Max 150 chars |
| `description` | No | |
| `mode` | Yes | `ONLINE`, `OFFLINE`, or `HYBRID` (uppercase) |
| `starts_at` | Yes | ISO 8601 datetime |
| `ends_at` | Yes | Must be after `starts_at` |
| `meeting_link` | No | For online/hybrid |
| `venue` | No | For offline/hybrid |
| `max_participants` | No | Cap on joins |

**Success response `200` — Company Mentor**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Session created successfully and is pending approval."] },
  "response": {
    "entity_id": "org-uuid-of-company",
    "session_type": "company_session",
    "title": "Acme Developer Mentoring — Sprint 1",
    "description": "Weekly sync for onboarding batch.",
    "mode": "ONLINE",
    "starts_at": "2026-06-11T15:00:00Z",
    "ends_at": "2026-06-11T16:00:00Z",
    "meeting_link": "https://meet.google.com/xyz-1234-abc",
    "venue": null,
    "max_participants": 20
  }
}
```

**Success response `200` — IG Mentor**

Same shape, but `entity_id` is the IG UUID and `session_type` is `ig_session`. The response does **not** include a separate `ig` field.

---

### 4.2 Available Sessions (for Learners)

#### `GET /api/v1/dashboard/mentor/session/available/`

List `SCHEDULED` sessions available to the authenticated user:

- IG sessions for Interest Groups the user belongs to
- Company sessions for company orgs the user is linked to via `UserOrganizationLink`

**Auth:** JWT (any authenticated user)

**Query params**

| Param | Description |
|---|---|
| `search` | Search by `title` or `description` |
| `sortBy` | `starts_at` or `created_at` |
| `pageIndex`, `perPage` | Pagination |

**Success response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": [] },
  "response": {
    "data": [
      {
        "id": "sess-uuid-1",
        "entity_id": "ig-uuid",
        "entity_name": "Python",
        "session_type": "ig_session",
        "title": "Python Basics for Beginners",
        "mode": "ONLINE",
        "starts_at": "2026-06-10T10:00:00Z",
        "ends_at": "2026-06-10T11:30:00Z",
        "status": "SCHEDULED",
        "created_by_id": "user-uuid",
        "created_by_name": "Mentor One",
        "created_at": "2026-06-01T10:00:00Z",
        "max_participants": 30
      },
      {
        "id": "sess-uuid-2",
        "entity_id": "org-uuid-of-acme",
        "entity_name": "Acme Corp",
        "session_type": "company_session",
        "title": "Acme Developer Mentoring — Sprint 1",
        "mode": "ONLINE",
        "starts_at": "2026-06-11T15:00:00Z",
        "ends_at": "2026-06-11T16:00:00Z",
        "status": "SCHEDULED",
        "created_by_id": "user-uuid-2",
        "created_by_name": "Jane Smith",
        "created_at": "2026-06-02T10:00:00Z",
        "max_participants": 20
      }
    ],
    "pagination": {
      "count": 2,
      "totalPages": 1,
      "isNext": false,
      "isPrev": false,
      "nextPage": null
    }
  }
}
```

---

## 5. Calendar

> All session calendar endpoints return sessions grouped into `upcoming`, `ongoing`, and `completed` buckets.
> Use the `month` query param (format `YYYY-MM`) to filter by month.
>
> Session items use `MentorshipSessionCalendarSerializer` — they include `mentor_name` and `mentee_count`, **not** a `participants` array.

---

### 5.1 Company Session Calendar

#### `GET /api/v1/calendar/company/<company_org_id>/sessions/`

Calendar view of all mentorship sessions for a specific company org.

**Auth:** None (public)

**Path param:** `company_org_id` — UUID of the company's `Organisation` record (`org_type = Company`)

**Query params**

| Param | Type | Description |
|---|---|---|
| `month` | string | `YYYY-MM` (e.g. `2026-06`) |
| `status` | string | `SCHEDULED`, `COMPLETED`, or `CANCELLED` |

**Success response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": [] },
  "response": {
    "upcoming": [
      {
        "id": "sess-uuid",
        "title": "Acme Developer Mentoring — Sprint 1",
        "description": "Weekly sync for onboarding batch.",
        "mode": "ONLINE",
        "starts_at": "2026-06-11T15:00:00Z",
        "ends_at": "2026-06-11T16:00:00Z",
        "status": "SCHEDULED",
        "meeting_link": "https://meet.google.com/xyz-1234-abc",
        "venue": null,
        "mentor_name": "Jane Smith",
        "mentee_count": 0
      }
    ],
    "ongoing": [],
    "completed": [
      {
        "id": "sess-uuid-old",
        "title": "Acme Kick-off Session",
        "description": "Company onboarding kick-off.",
        "mode": "OFFLINE",
        "starts_at": "2026-06-01T10:00:00Z",
        "ends_at": "2026-06-01T11:00:00Z",
        "status": "COMPLETED",
        "meeting_link": null,
        "venue": "Acme HQ, Bangalore",
        "mentor_name": "Jane Smith",
        "mentee_count": 12
      }
    ]
  }
}
```

---

### 5.2 IG Mentor Session Calendar

#### `GET /api/v1/calendar/ig-mentor/<ig_id>/sessions/`

Calendar view of mentorship sessions for a specific Interest Group.

**Auth:** None (public)

**Query params:** `month` (YYYY-MM), `status` (`SCHEDULED`, `COMPLETED`, `CANCELLED`)

**Success response `200`:** Same bucket shape as [§5.1](#51-company-session-calendar).

---

### 5.3 Campus Mentor Session Calendar

#### `GET /api/v1/calendar/campus-mentor/<campus_id>/sessions/`

Calendar view of mentorship sessions for a specific campus (college org).

**Auth:** None (public)

**Query params:** `month` (YYYY-MM), `status` (`SCHEDULED`, `COMPLETED`, `CANCELLED`)

**Success response `200`:** Same bucket shape as [§5.1](#51-company-session-calendar).

---

## 6. Leaderboard

### 6.1 IG Mentor Leaderboard

#### `GET /api/v1/leaderboard/ig-mentor/<ig_id>/`

Ranked list of IG Mentors for a specific Interest Group.

Ranked by:
1. Number of **completed sessions** in that IG (descending)
2. Total **karma** as tiebreaker (descending)

**Auth:** None (public)

**Success response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": [] },
  "response": [
    {
      "rank": 1,
      "mentor_id": "u-uuid",
      "mentor_name": "Rahul Menon",
      "profile_pic": "https://cdn.example.com/rahul.png",
      "total_karma": 8500,
      "completed_sessions": 14,
      "ig_name": "Python"
    },
    {
      "rank": 2,
      "mentor_id": "u-uuid-2",
      "mentor_name": "Sneha Das",
      "profile_pic": null,
      "total_karma": 7200,
      "completed_sessions": 10,
      "ig_name": "Python"
    }
  ]
}
```

> **Note:** `mentor_id` is the **user's UUID** (`user.id`), not the `UserMentor.id`. There is no `muid` or separate `user_id` field in the response.

---

### 6.2 Campus Mentor Leaderboard

#### `GET /api/v1/leaderboard/campus-mentor/<campus_id>/`

Ranked list of Campus Mentors for a specific campus (college org).

Ranked by:
1. Number of **completed campus sessions** (descending)
2. Total **karma** as tiebreaker (descending)

**Auth:** None (public)

**Success response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": [] },
  "response": [
    {
      "rank": 1,
      "mentor_id": "u-uuid",
      "mentor_name": "Divya Krishnan",
      "profile_pic": "https://cdn.example.com/divya.png",
      "total_karma": 6400,
      "completed_sessions": 9,
      "campus_name": "CUSAT"
    },
    {
      "rank": 2,
      "mentor_id": "u-uuid-2",
      "mentor_name": "Arun Pillai",
      "profile_pic": null,
      "total_karma": 5100,
      "completed_sessions": 6,
      "campus_name": "CUSAT"
    }
  ]
}
```

---

## 7. Event Management

Company Mentors can manage (CRUD) events for their company via the `/api/v1/dashboard/events/` endpoints. The `organiser_type` MUST be set to `Company` (`Event.OrganiserType.COMPANY`).

### 7.1 View Company Events

#### `GET /api/v1/dashboard/events/company/<company_id>/`
List all published/ongoing events for the company. (Public feed)

#### `GET /api/v1/dashboard/events/manage/`
List all events the Company Mentor has permission to manage (including drafts and pending).

#### `GET /api/v1/dashboard/events/manage/<event_id>/`
Get full details of a specific event, including its edit history.

### 7.2 Create Event

#### `POST /api/v1/dashboard/events/manage/`
Create a new company event. 

**Auth:** JWT · verified `COMPANY_MENTOR`

**Request body**
```json
{
  "title": "Company Tech Talk",
  "description": "Discussing the latest tech stack.",
  "start_datetime": "2026-07-01T10:00:00Z",
  "end_datetime": "2026-07-01T12:00:00Z",
  "venue_type": "ONLINE",
  "organiser_type": "Company"
}
```

**Success response `200`**
Returns the created event object.

### 7.3 Update Event

#### `PUT /api/v1/dashboard/events/manage/<event_id>/`
Full update of an event.

#### `PATCH /api/v1/dashboard/events/manage/<event_id>/`
Partial update of an event. *Note: You cannot change `organiser_type` to anything other than `Company`.*

### 7.4 Cancel Event

#### `DELETE /api/v1/dashboard/events/manage/<event_id>/`
Soft cancel an event (status becomes `CANCELLED`).

### 7.5 Publish Event

#### `POST /api/v1/dashboard/events/manage/<event_id>/publish/`
Transition a `DRAFT` event into the approval pipeline (`PENDING_APPROVAL`).

---

## DB Migration Requirement

> [!IMPORTANT]
> Before deploying, add `company_session` to the `session_type` ENUM column on `mentorship_session` (the model is `managed = False`, so Django migrations won't auto-generate this):

```sql
ALTER TABLE mentorship_session
  MODIFY COLUMN session_type
    ENUM('ig_session', 'campus_session', 'company_session')
    NOT NULL DEFAULT 'ig_session';
```

Apply this SQL manually on the target database before enabling company mentor sessions in production.

---

## Access Control Summary

| Role | Nominate | List nominations | Profile / Jobs / Analytics / MuLearners | Tasks | Sessions (create) | Calendar / Leaderboard |
|---|---|---|---|---|---|---|
| Company Creator (`Company` role) | ✅ | ✅ | ✅ | ✅ (own tasks) | ✅ (as `Mentor` if approved) | Public |
| Approved Company Mentor | ❌ | ❌ | ✅ | ✅ (own tasks only) | ✅ (`company_session`) | Public |
| IG Mentor | — | — | — | ✅ (own IG tasks) | ✅ (`ig_session`) | Public |
| Campus Mentor | — | — | — | — | ✅ (`campus_session`) | Public |
| Admin | — | — | — | ✅ (approve via `/dashboard/task/`) | ✅ (verify sessions) | Public |
| Any Authenticated User | — | — | apply to jobs | list own submitted tasks | join / view available | Public |
| Public (no auth) | — | — | browse public company profile & jobs | — | calendar | leaderboard |

---

## Corrections applied vs. earlier draft

| Area | Issue in draft | Actual behaviour |
|------|----------------|------------------|
| Response envelope | Flat `"message": "string"` | `hasError` + `message.general[]` array |
| Pagination | `page`, `per_page`, `next`, `previous` | `pageIndex`, `perPage`, `totalPages`, `isNext`, `isPrev`, `nextPage` |
| Nomination / list auth | "Company Creator or Mentor" | **`Company` role only** (verified creator) |
| Jobs POST body | `description`, `experience_min`, `skills_required`, `mode` | `job_description`, `experience`, `salary_range`, `job_type`, optional `rules` |
| Applications | `user_name`, `resume_url` | `applicant_name`, `applicant_email`, `resume_link`, `job` |
| MuLearners | `igs[]`, `level` as string | `level` as integer; `email`, `department`, `graduation_year`; no `igs` |
| Tasks | Company-wide list; `channel`, `ig` on create | Per-user (`requested_by`); create uses `type`/`level` UUIDs + `skill_ids` |
| Session `mode` | `"Online"` | `"ONLINE"`, `"OFFLINE"`, `"HYBRID"` |
| Session create response | Mixed `ig` field for company | `entity_id` + `session_type`; no `ig` key |
| Available sessions | Missing `created_at`, `created_by_id` | Full `SessionListSerializer` fields |
| Calendar items | `participants[]`, `session_type` | `mentor_name`, `mentee_count`, `description`, `meeting_link`, `venue` |
| Leaderboard | `mentor_id` = UserMentor id; `full_name`, `muid` | `mentor_id` = **user id**; `mentor_name`, `profile_pic` |
