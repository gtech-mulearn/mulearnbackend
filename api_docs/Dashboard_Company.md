# Company Dashboard API Reference

Base path: `/api/v1/dashboard/company/`

This document covers every endpoint available in the company dashboard module.  
Code lives under `api/dashboard/company/`.

---

## Common Response Envelope

All endpoints use the `CustomResponse` wrapper:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success message"] },
  "response": {}
}
```

Failure responses use `"hasError": true` with an `"error_code"` key inside `message`.

---

## Authentication

All company-dashboard endpoints (except public profile endpoints) require:

```
Authorization: Bearer <access_token>
```

The company user must have:
1. A `UserRoleLink` with `role.title = "Company"`
2. An associated `Company` record (usually `status = "active"`, except onboarding endpoints which also allow `pending_verification` and `rejected`)

---

## Modules

| Module | Base Path |
|--------|-----------|
| [Onboarding](#1-onboarding) | `company/` |
| [Profile](#2-profile) | `company/profile/` |
| [Jobs](#3-jobs) | `company/jobs/` |
| [Job Rules](#4-job-rules) | `company/jobs/<job_id>/rules/` |
| [Applications (Company View)](#5-applications-company-view) | `company/jobs/<job_id>/applicants/` |
| [Applications (Learner View)](#6-applications-learner-view) | `company/applications/` |
| [Tasks](#7-tasks) | `company/tasks/` |
| [Members](#8-members) | `company/members/` |
| [Learner Discovery](#9-learner-discovery) | `company/learners/` |
| [Analytics](#10-analytics) | `company/` |
| [Admin Task Approval](#11-admin-task-approval) | `dashboard/task/` |

---

## 1. Onboarding

### POST `company/create/`

Create a new company account. No authentication required.

**Request body:**

```json
{
  "name": "Acme Labs",
  "poc_name": "Jane Doe",
  "poc_email": "jane@acme.com",
  "password": "StrongPass123",
  "poc_phone": "+919999999999",
  "website_link": "https://acme.com",
  "description": "A product engineering company",
  "industry_sector": "Technology",
  "location": "Kochi, Kerala",
  "district_id": "district-uuid",
  "legal_name": "Acme Labs Private Limited",
  "registration_number": "REG-12345",
  "tax_id": "GSTIN-12345",
  "company_size": "51-200",
  "linkedin_url": "https://linkedin.com/company/acme",
  "verification_document_url": "https://example.com/proof.pdf"
}
```

Required: `name`, `poc_name`, `poc_email`, `password`

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Company registration submitted successfully"] },
  "response": {
    "company_id": "uuid",
    "slug": "acme-labs",
    "muid": "jane-doe@mulearn",
    "status": "pending_verification",
    "auth": {
      "access": "<jwt>",
      "refresh": "<jwt>",
      "data": {
        "id": "user-uuid",
        "muid": "jane-doe@mulearn",
        "email": "jane@acme.com",
        "role": null,
        "full_name": "Jane Doe"
      }
    }
  }
}
```

**Error codes:**

| Code | HTTP | Description |
|------|------|-------------|
| `VALIDATION_ERROR` | 400 | Missing/invalid required fields |
| `DUPLICATE_POC_EMAIL` | 409 | Email already registered |
| `DUPLICATE_POC_PHONE` | 409 | Phone already registered |
| `DUPLICATE_COMPANY_NAME` | 409 | Company name taken |

---

### GET `company/onboarding/status/`

Returns the current onboarding status for the authenticated company user.

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Company onboarding status fetched successfully"] },
  "response": {
    "id": "company-uuid",
    "name": "Acme Labs",
    "slug": "acme-labs",
    "status": "pending_verification",
    "poc_name": "Jane Doe",
    "poc_email": "jane@acme.com",
    "rejection_reason": null,
    "verification_requested_at": "2026-04-05T10:00:00+05:30",
    "verified_at": null,
    "created_at": "2026-04-05T10:00:00+05:30",
    "updated_at": "2026-04-05T10:00:00+05:30",
    "can_edit_profile": true,
    "can_access_advanced_features": false,
    "next_steps": ["Wait for admin verification approval"]
  }
}
```

---

### POST `company/verification/resubmit/`

Resubmit a rejected company verification request.

**Request body:** None required.

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Company verification request resubmitted successfully"] },
  "response": {
    "company_id": "company-uuid",
    "status": "pending_verification",
    "verification_requested_at": "2026-05-27T10:00:00+05:30"
  }
}
```

**Error codes:**

| Code | HTTP | Description |
|------|------|-------------|
| `COMPANY_NOT_REJECTED` | 400 | Company is not in `rejected` status |
| `NO_COMPANY_FOUND` | 404 | No company found for this user |

---

## 2. Profile

### GET `company/profile/`

Fetch the authenticated company's profile.

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Company profile fetched successfully"] },
  "response": {
    "id": "company-uuid",
    "name": "Acme Labs",
    "slug": "acme-labs",
    "logo": "https://cdn.example.com/logo.png",
    "description": "A product engineering company",
    "industry_sector": "Technology",
    "website_link": "https://acme.com",
    "email": "contact@acme.com",
    "location": "Kochi, Kerala",
    "status": "active",
    "legal_name": "Acme Labs Private Limited",
    "registration_number": "REG-12345",
    "tax_id": "GSTIN-12345",
    "company_size": "51-200",
    "linkedin_url": "https://linkedin.com/company/acme",
    "verification_document_url": "https://example.com/proof.pdf",
    "founded_year": 2018,
    "remote_policy": "Hybrid",
    "culture_text": "We move fast and care deeply.",
    "tech_stack": ["Python", "React", "PostgreSQL"],
    "perks": ["Health Insurance", "Remote Fridays"],
    "testimonials": [],
    "gallery": [],
    "rejection_reason": null,
    "verified_at": "2026-01-10T09:00:00+05:30",
    "created_at": "2026-01-01T10:00:00+05:30",
    "updated_at": "2026-05-01T10:00:00+05:30"
  }
}
```

---

### POST `company/profile/`

Create a company profile (used after initial onboarding if the profile was deleted/incomplete).

**Request body:** Same fields as the profile GET response (all optional except `name`).

**Error codes:**

| Code | HTTP | Description |
|------|------|-------------|
| `COMPANY_ALREADY_EXISTS` | 409 | A profile already exists for this user |
| `DUPLICATE_COMPANY_NAME` | 409 | Name taken |
| `DUPLICATE_SLUG` | 409 | Slug taken |

---

### PATCH `company/profile/`

Partially update the authenticated company's profile. Send only the fields to change.

**Example request:**

```json
{
  "description": "Updated description",
  "tech_stack": ["Python", "Django", "Next.js"],
  "perks": ["Health Insurance", "WFH"]
}
```

**Success response:** Same shape as GET, with updated values.

**Error codes:**

| Code | HTTP | Description |
|------|------|-------------|
| `NO_FIELDS_TO_UPDATE` | 400 | Empty body |
| `DUPLICATE_COMPANY_NAME` | 409 | Name collision |
| `DUPLICATE_SLUG` | 409 | Slug collision |

---

### DELETE `company/profile/`

Soft-deletes the company profile (`status → inactive`, `deleted_at` stamped).

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Company profile deleted successfully"] },
  "response": {
    "company_id": "uuid",
    "status": "inactive",
    "deleted_at": "2026-05-27T10:00:00+05:30"
  }
}
```

---

### GET `company/profile/public/<slug>/`

Public endpoint. No authentication required.

**Success response:** Same as company profile GET but limited to public-facing fields.

**Error codes:**

| Code | HTTP | Description |
|------|------|-------------|
| `COMPANY_NOT_FOUND` | 404 | Company not found or not active |

---

### GET `company/profile/public/<slug>/jobs/`

Public endpoint. Returns active jobs for a company. Paginated.

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `search` | string | Filter by title, location, job_type |
| `sortBy` | string | `title` or `createdAt` (default `createdAt`) |
| `page` | int | Page number |
| `perPage` | int | Page size |

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Public company jobs fetched successfully"] },
  "response": {
    "company": {
      "id": "company-uuid",
      "name": "Acme Labs",
      "slug": "acme-labs"
    },
    "jobs": [
      {
        "id": "job-uuid",
        "title": "Backend Engineer",
        "experience": "1-3 years",
        "job_description": "Build and maintain APIs...",
        "job_type": "Full-Time",
        "location": "Kochi",
        "salary_range": "6-10 LPA",
        "min_karma": 1000,
        "min_level": 3,
        "status": "Active",
        "karma_reward": 500,
        "requires_task_completion": false,
        "linked_task_info": null,
        "rules": [],
        "created_at": "2026-05-01T10:00:00+05:30",
        "updated_at": "2026-05-20T10:00:00+05:30"
      }
    ],
    "pagination": {
      "count": 1,
      "totalPages": 1,
      "isNext": false,
      "isPrev": false
    }
  }
}
```

---

## 3. Jobs

### GET `company/jobs/`

List all non-deleted jobs for the authenticated company.

**Query params:** `search`, `sortBy`, `page`, `perPage`

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Jobs fetched successfully"] },
  "response": {
    "jobs": [
      {
        "id": "job-uuid",
        "title": "Backend Engineer",
        "experience": "1-3 years",
        "job_description": "Build and maintain APIs...",
        "job_type": "Full-Time",
        "location": "Kochi",
        "salary_range": "6-10 LPA",
        "min_karma": 1000,
        "min_level": 3,
        "status": "Active",
        "karma_reward": 500,
        "duration_value": null,
        "duration_unit": null,
        "hourly_rate": null,
        "deliverables": null,
        "stipend": null,
        "certificate_provided": null,
        "requires_task_completion": true,
        "linked_task_info": {
          "id": "task-uuid",
          "hashtag": "#django-api",
          "title": "Build a REST API",
          "karma": 200
        },
        "rules": [
          {
            "id": "rule-uuid",
            "rule_type": "skill",
            "rule_type_id": "skill-uuid",
            "rule_name": "Python"
          }
        ],
        "created_at": "2026-05-01T10:00:00+05:30",
        "updated_at": "2026-05-20T10:00:00+05:30"
      }
    ],
    "pagination": {
      "count": 5,
      "totalPages": 1,
      "isNext": false,
      "isPrev": false
    }
  }
}
```

---

### POST `company/jobs/create/`

Create a new job listing.

**Request body:**

```json
{
  "company_id": "company-uuid",
  "title": "Backend Engineer",
  "experience": "1-3 years",
  "job_description": "Build and maintain REST APIs...",
  "location": "Kochi",
  "salary_range": "6-10 LPA",
  "job_type": "Full-Time",
  "min_karma": 1000,
  "min_level": 3,
  "karma_reward": 500,
  "requires_task_completion": true,
  "linked_task_id": "task-uuid"
}
```

`job_type` choices: `Hybrid`, `Full-Time`, `Remote`, `Part-Time`, `Internship`, `Gig`

For `Gig` type, also send: `duration_value`, `duration_unit` (days/weeks/months), `hourly_rate`, `deliverables` (array of strings)

For `Internship` type, also send: `duration_value`, `duration_unit`, `stipend`, `certificate_provided` (bool)

> If `requires_task_completion = true`, `linked_task_id` is required and must point to an approved, active task.

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Job created successfully"] },
  "response": {
    "job_id": "job-uuid",
    "title": "Backend Engineer",
    "status": "Active",
    "company_id": "company-uuid"
  }
}
```

**Error codes:**

| Code | HTTP | Description |
|------|------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid fields |
| `COMPANY_NOT_FOUND` | 404 | Company UUID does not exist or not active |
| `UNAUTHORIZED` | 403 | Authenticated user does not own this company |

---

### GET `company/jobs/<job_id>/details/`

Get full details for a single job.

**Success response:** Same shape as the job object in the list endpoint above.

---

### PATCH `company/jobs/<job_id>/update/`

Partially update a job. Send only the fields to change.

**Error codes:**

| Code | HTTP | Description |
|------|------|-------------|
| `JOB_NOT_FOUND` | 404 | Job not found or deleted |
| `UNAUTHORIZED` | 403 | Job does not belong to this company |

---

### DELETE `company/jobs/<job_id>/delete/`

Soft-delete a job (`is_deleted = True`).

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Job deleted successfully"] },
  "response": {
    "job_id": "uuid",
    "status": "Deleted"
  }
}
```

---

## 4. Job Rules

Rules define eligibility requirements (skill, interest group, or achievement).

### POST `company/jobs/<job_id>/rules/create/`

Add a rule to a job.

**Request body:**

```json
{
  "rule_type": "skill",
  "rule_type_id": "skill-uuid"
}
```

`rule_type` choices: `skill`, `interest_group`, `achievement`

---

### PATCH `company/jobs/<job_id>/rules/<rule_id>/update/`

Update an existing rule.

---

### DELETE `company/jobs/<job_id>/rules/<rule_id>/delete/`

Delete a rule from a job.

---

## 5. Applications (Company View)

### GET `company/jobs/<job_id>/applicants/`

List all applicants for a specific job.

**Query params:** `search`, `sortBy`, `page`, `perPage`

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Applicants fetched successfully"] },
  "response": {
    "job": {
      "id": "job-uuid",
      "title": "Backend Engineer"
    },
    "applicants": [
      {
        "id": "application-uuid",
        "status": "applied",
        "cover_note": "I'm excited about this opportunity...",
        "applicant_id": "user-uuid",
        "full_name": "Riya Sharma",
        "muid": "riya-sharma@mulearn",
        "district": "Thrissur",
        "karma": 3200,
        "level": {
          "id": "level-uuid",
          "name": "Explorer",
          "level_order": 4
        },
        "reviewed_by_id": null,
        "reviewed_at": null,
        "created_at": "2026-05-10T10:00:00+05:30",
        "updated_at": "2026-05-10T10:00:00+05:30"
      }
    ],
    "pagination": { "count": 1, "totalPages": 1, "isNext": false, "isPrev": false }
  }
}
```

---

### PATCH `company/jobs/<job_id>/applicants/<application_id>/status/`

Update the status of an application.

**FSM (allowed transitions):**

```
applied → shortlisted | rejected
shortlisted → accepted | rejected
accepted, rejected, withdrawn → (terminal, no further transitions)
```

**Request body:**

```json
{
  "status": "shortlisted"
}
```

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Application shortlisted successfully"] },
  "response": {
    "application_id": "uuid",
    "applicant_id": "user-uuid",
    "new_status": "shortlisted",
    "reviewed_by": "company-user-uuid",
    "reviewed_at": "2026-05-27T10:00:00+05:30"
  }
}
```

**Error codes:**

| Code | HTTP | Description |
|------|------|-------------|
| `INVALID_STATUS_TRANSITION` | 400 | FSM violation (e.g., accepted → shortlisted) |
| `APPLICATION_NOT_FOUND` | 404 | Application not found for this job |
| `TERMINAL_STATUS` | 400 | Attempting to move from a terminal state |

---

## 6. Applications (Learner View)

### GET `company/applications/`

Learner fetches their own applications across all companies.

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Applications fetched successfully"] },
  "response": {
    "applications": [
      {
        "id": "application-uuid",
        "status": "shortlisted",
        "cover_note": "I'm excited...",
        "job_id": "job-uuid",
        "job_title": "Backend Engineer",
        "job_type": "Full-Time",
        "company_name": "Acme Labs",
        "company_id": "company-uuid",
        "created_at": "2026-05-10T10:00:00+05:30",
        "updated_at": "2026-05-15T10:00:00+05:30"
      }
    ],
    "pagination": { "count": 1, "totalPages": 1, "isNext": false, "isPrev": false }
  }
}
```

---

### POST `company/jobs/<job_id>/apply/`

Learner applies to a job.

**Request body (optional):**

```json
{
  "cover_note": "I believe my skills are a great match..."
}
```

> **Task gate:** If the job has `requires_task_completion = true`, the learner must have a `KarmaActivityLog` entry with `appraiser_approved = true` for the linked task. Otherwise the request is rejected with `TASK_NOT_COMPLETED`.

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Application submitted successfully."] },
  "response": {
    "application_id": "uuid",
    "job_id": "job-uuid",
    "job_title": "Backend Engineer",
    "status": "applied",
    "applied_at": "2026-05-27T10:00:00+05:30"
  }
}
```

**Error codes:**

| Code | HTTP | Description |
|------|------|-------------|
| `JOB_NOT_FOUND` | 404 | Job does not exist or is deleted |
| `JOB_NOT_ACTIVE` | 400 | Job is not in `Active` status |
| `DUPLICATE_APPLICATION` | 409 | Learner already applied |
| `TASK_NOT_COMPLETED` | 400 | Learner has not completed the required task |
| `COMPANY_ROLE_NOT_ALLOWED` | 403 | Company users cannot apply |

---

### PATCH `company/applications/<app_id>/withdraw/`

Learner withdraws their own application.

Only possible from `applied` or `shortlisted` status.

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Application withdrawn successfully."] },
  "response": {
    "application_id": "uuid",
    "job_id": "job-uuid",
    "new_status": "withdrawn"
  }
}
```

**Error codes:**

| Code | HTTP | Description |
|------|------|-------------|
| `APPLICATION_NOT_FOUND` | 404 | Application not found |
| `INVALID_STATUS_TRANSITION` | 400 | Application is in a terminal state |
| `COMPANY_ROLE_NOT_ALLOWED` | 403 | Company users cannot withdraw |

---

## 7. Tasks

Companies can submit tasks tied to an Interest Group (IG). Tasks go live only after admin approval.

**Workflow:** `company submits → pending + active=False → admin approves → approved + active=True`

---

### GET `company/tasks/`

List all tasks submitted by the authenticated company.

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `approval_status` | string | Filter: `pending`, `approved`, `rejected` |
| `search` | string | Filter by title or hashtag |
| `page`, `perPage` | int | Pagination |

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Tasks fetched successfully."] },
  "response": {
    "tasks": [
      {
        "id": "task-uuid",
        "title": "Build a REST API",
        "hashtag": "#django-api",
        "description": "Create a fully documented REST API using Django REST Framework.",
        "karma": 200,
        "approval_status": "pending",
        "rejection_reason": null,
        "ig_name": "Web Development",
        "type_name": "Task",
        "active": false,
        "created_at": "2026-05-27T10:00:00+05:30",
        "updated_at": "2026-05-27T10:00:00+05:30"
      }
    ],
    "pagination": { "count": 1, "totalPages": 1, "isNext": false, "isPrev": false }
  }
}
```

---

### POST `company/tasks/submit/`

Submit a new task for admin review.

**Request body:**

```json
{
  "title": "Build a REST API",
  "hashtag": "#django-api",
  "description": "Create a fully documented REST API using DRF.",
  "karma": 200,
  "ig_id": "ig-uuid",
  "type_id": "task-type-uuid",
  "channel_id": "channel-uuid",
  "level_id": "level-uuid"
}
```

Required: `title`, `hashtag`, `karma`, `ig_id`, `type_id`

> `hashtag` must start with `#` and must be unique across all tasks.  
> `ig_id` must reference an existing Interest Group.  
> `karma` must be ≥ 1.

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Task submitted for admin review."] },
  "response": {
    "id": "task-uuid",
    "title": "Build a REST API",
    "hashtag": "#django-api",
    "karma": 200,
    "approval_status": "pending",
    "rejection_reason": null,
    "ig_name": "Web Development",
    "type_name": "Task",
    "active": false,
    "created_at": "2026-05-27T10:00:00+05:30",
    "updated_at": "2026-05-27T10:00:00+05:30"
  }
}
```

**Error codes:**

| Code | HTTP | Description |
|------|------|-------------|
| `VALIDATION_ERROR` | 400 | Missing required fields or invalid values |
| `NO_ACTIVE_COMPANY` | 403 | User has no active company |

---

### POST `company/tasks/<task_id>/resubmit/`

Reset a previously rejected task back to pending.

> Does **not** create a new row — resets the existing record.

**Request body:** None required.

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Task resubmitted for admin review."] },
  "response": {
    "id": "task-uuid",
    "title": "Build a REST API",
    "approval_status": "pending",
    "rejection_reason": null,
    "active": false,
    "updated_at": "2026-05-27T11:00:00+05:30"
  }
}
```

**Error codes:**

| Code | HTTP | Description |
|------|------|-------------|
| `TASK_NOT_FOUND` | 404 | Task not found or not owned by this company |
| `INVALID_STATUS_TRANSITION` | 400 | Task is not in `rejected` status |

---

## 8. Members

Companies can build a roster of muLearn users as employees or mentors.

---

### GET `company/members/`

List all active members of the authenticated company.

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `role` | string | Filter: `employee` or `mentor` |
| `search` | string | Filter by name or muid |
| `page`, `perPage` | int | Pagination |

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Members fetched successfully."] },
  "response": {
    "members": [
      {
        "id": "link-uuid",
        "user_id": "user-uuid",
        "full_name": "Arjun Dev",
        "muid": "arjun-dev@mulearn",
        "district": "Ernakulam",
        "karma": 4200,
        "level": {
          "id": "level-uuid",
          "name": "Navigator",
          "level_order": 5
        },
        "interest_groups": [
          { "id": "ig-uuid", "name": "Web Development" },
          { "id": "ig-uuid", "name": "Cloud Computing" }
        ],
        "role": "mentor",
        "status": "active",
        "created_at": "2026-05-10T10:00:00+05:30"
      }
    ],
    "pagination": { "count": 1, "totalPages": 1, "isNext": false, "isPrev": false }
  }
}
```

---

### POST `company/members/add/`

Add a muLearn user to the company roster.

> Users with the `Company` role cannot be added as members.  
> If a previously removed member is re-added, their link is reactivated instead of creating a duplicate.

**Request body:**

```json
{
  "user_id": "user-uuid",
  "role": "mentor"
}
```

`role` choices: `employee`, `mentor`

**Success response:** Member object (same as in the list response above).

**Error codes:**

| Code | HTTP | Description |
|------|------|-------------|
| `VALIDATION_ERROR` | 400 | Missing fields or invalid role |
| `USER_NOT_FOUND` | 404 | Target user does not exist |
| `COMPANY_ROLE_NOT_ALLOWED` | 400 | Cannot add a company admin as member |
| `DUPLICATE_MEMBER` | 409 | User is already an active member |

---

### DELETE `company/members/<link_id>/remove/`

Soft-remove a member from the company (`status → removed`).

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Member removed successfully."] },
  "response": {
    "link_id": "link-uuid",
    "status": "removed"
  }
}
```

**Error codes:**

| Code | HTTP | Description |
|------|------|-------------|
| `MEMBER_NOT_FOUND` | 404 | Link not found for this company |
| `ALREADY_REMOVED` | 400 | Member already removed |

---

## 9. Learner Discovery

### GET `company/learners/`

Search and filter muLearn learners for talent discovery.

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `search` | string | Filter by name, muid, email |
| `ig` | string | Filter by interest group name |
| `min_karma` | int | Minimum karma threshold |
| `sortBy` | string | Sort field |
| `page`, `perPage` | int | Pagination |

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Learners fetched successfully"] },
  "response": {
    "learners": [
      {
        "id": "user-uuid",
        "full_name": "Riya Sharma",
        "muid": "riya-sharma@mulearn",
        "email": "riya@example.com",
        "district": "Thrissur",
        "karma": 3200,
        "level": {
          "id": "level-uuid",
          "name": "Explorer",
          "level_order": 4
        },
        "interest_groups": [
          { "id": "ig-uuid", "name": "Machine Learning" }
        ]
      }
    ],
    "pagination": { "count": 50, "totalPages": 5, "isNext": true, "isPrev": false }
  }
}
```

---

## 10. Analytics

### GET `company/home-summary/`

Returns a summary dashboard for the authenticated company.

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Dashboard summary fetched successfully"] },
  "response": {
    "company": {
      "id": "company-uuid",
      "name": "Acme Labs",
      "status": "active"
    },
    "stats": {
      "total_jobs": 5,
      "active_jobs": 3,
      "total_applications": 42,
      "pending_applications": 18,
      "total_views": 0
    }
  }
}
```

---

### GET `company/talent-pool/analytics/`

Returns analytics on the talent pool (learner distribution).

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `period` | string | `7d`, `30d` (default), `90d`, `1y` |

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Talent pool analytics fetched successfully"] },
  "response": {
    "period_days": 30,
    "talent_pool": {
      "total_learners": 1240,
      "active_learners": 380,
      "avg_karma": 2150,
      "district_distribution": [
        { "district": "Ernakulam", "count": 210 },
        { "district": "Thrissur", "count": 185 }
      ],
      "level_distribution": [
        { "level": "Navigator", "count": 300 },
        { "level": "Explorer", "count": 280 }
      ],
      "ig_distribution": [
        { "ig": "Web Development", "count": 420 },
        { "ig": "Machine Learning", "count": 310 }
      ]
    }
  }
}
```

---

## 11. Admin Task Approval

> **Admin only.** Requires the `Admin` role.

---

### GET `dashboard/task/pending/`

List all tasks with `approval_status = pending` (company-submitted tasks awaiting review).

**Query params:** `search`, `sortBy`, `page`, `perPage`

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Pending tasks fetched successfully."] },
  "response": {
    "tasks": [
      {
        "id": "task-uuid",
        "title": "Build a REST API",
        "hashtag": "#django-api",
        "description": "Create a fully documented REST API...",
        "karma": 200,
        "approval_status": "pending",
        "ig": { "id": "ig-uuid", "name": "Web Development" },
        "type": { "id": "type-uuid", "title": "Task" },
        "submitted_by_company": {
          "id": "company-uuid",
          "name": "Acme Labs"
        },
        "created_at": "2026-05-27T10:00:00+05:30"
      }
    ],
    "pagination": { "count": 3, "totalPages": 1, "isNext": false, "isPrev": false }
  }
}
```

---

### PATCH `dashboard/task/<task_id>/review/`

Approve or reject a pending task.

**Request body — Approve:**

```json
{
  "action": "approve"
}
```

**Request body — Reject:**

```json
{
  "action": "reject",
  "reason": "Task description is too vague. Please add clear acceptance criteria."
}
```

**Success response:**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Task approved and is now live."] },
  "response": {
    "task_id": "task-uuid",
    "approval_status": "approved",
    "active": true,
    "rejection_reason": null,
    "reviewed_by": "admin-user-uuid",
    "reviewed_at": "2026-05-27T11:00:00+05:30"
  }
}
```

**Error codes:**

| Code | HTTP | Description |
|------|------|-------------|
| `INVALID_ACTION` | 400 | Action must be `approve` or `reject` |
| `TASK_NOT_FOUND` | 404 | Task does not exist |
| `INVALID_STATUS_TRANSITION` | 400 | Task is not in `pending` status |
| `REASON_REQUIRED` | 400 | `reason` missing on reject action |

---

