# Dashboard / Manage Interns

Base path: `/api/v1/dashboard/manage-interns/`

> **Access**: All endpoints require `ADMIN` role via `@role_required([RoleType.ADMIN.value])`.
> Future role expansion: add to the decorator list. No architectural changes needed.

---

## Overview Stats APIs

---

### GET `status/`
- Brief: Overview statistics — stat cards for total/active/at_risk/on_leave/inactive interns + task stats.
- Auth: Bearer token required.
- Permission: `CustomizePermission` + `@role_required([RoleType.ADMIN.value])`.
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Intern overview stats fetched successfully."]
  },
  "response": {
    "total_interns": 142,
    "active": 118,
    "at_risk": 15,
    "on_leave": 5,
    "inactive": 4,
    "engagement_rate": 83.1,
    "total_points_awarded": 125400,
    "average_karma": 883,
    "tasks_by_status": {
      "NOT_STARTED": 45,
      "IN_PROGRESS": 32,
      "COMPLETED": 120,
      "WAITING_FOR_REVIEW": 8
    },
    "interns_per_team": {
      "Frontend Guild": 40,
      "Backend Guild": 45,
      "Design Guild": 30,
      "Mobile Guild": 27
    }
  }
}
```
- Notes:
  - Intern counts from `InternEnrollment.objects.filter(status=...)`.
  - `engagement_rate` = `(active / total) * 100`.
  - `total_points_awarded` = `Sum(KarmaActivityLog.karma)` for intern hashtag tasks.
  - `average_karma` = `total_points_awarded / total_interns`.
  - `tasks_by_status` from `InternTask.objects.values('status').annotate(count=Count('id'))`.

---

## Intern CRUD APIs

---

### GET `interns/`
- Brief: Paginated intern directory table with filters.
- Auth: Bearer token required.
- Permission: `CustomizePermission` + `@role_required([RoleType.ADMIN.value])`.
- Query params:
  - `search` (optional) — name or email.
  - `team` (optional) — filter by team.
  - `status` (optional) — filter by enrollment status.
  - `per_page` (optional, default `10`).
  - `page` (optional, default `1`).
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Intern directory fetched successfully."]
  },
  "response": {
    "interns": [
      {
        "id": "enrollment-uuid",
        "user_id": "user-uuid",
        "name": "Alex Doe",
        "email": "alex.doe@example.com",
        "muid": "dev-1234",
        "team": "Frontend Guild",
        "status": "ACTIVE",
        "daily_streak": 14,
        "weekly_streak": 8,
        "total_points": 1240,
        "completed_tasks": 12,
        "leaderboard_rank": 3,
        "enrolled_at": "2026-01-15T00:00:00Z",
        "last_timesheet": "2026-05-14",
        "last_review": "W20 2026"
      }
    ],
    "pagination": {
      "current_page": 1,
      "total_pages": 15,
      "per_page": 10,
      "total_entries": 142
    }
  }
}
```

---

### POST `interns/`
- Brief: Add an existing user as an intern.
- Auth: Bearer token required.
- Permission: `CustomizePermission` + `@role_required([RoleType.ADMIN.value])`.
- Required fields: `user_id`, `team`
- Request body:
```json
{
  "user_id": "existing-user-uuid",
  "team": "Backend Guild"
}
```
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Intern added successfully."]
  },
  "response": {
    "enrollment_id": "enrollment-uuid",
    "user_id": "existing-user-uuid",
    "team": "Backend Guild",
    "status": "ACTIVE",
    "enrolled_at": "2026-05-22T08:00:00Z"
  }
}
```
- Validation:
  - `user_id` must exist in `User` table.
  - `team` must be a valid `InternTeam` value.
  - User must not already have an `InternEnrollment` record → 409.
- Side effects:
  - Create `InternEnrollment` row.
  - Create `UserRoleLink` with Intern role if not exists.

---

### GET `interns/{id}/`
- Brief: Full intern detail view.
- Auth: Bearer token required.
- Permission: `CustomizePermission` + `@role_required([RoleType.ADMIN.value])`.
- Path parameter: `id` = enrollment UUID.
- Success response includes: full profile, karma, both streaks, last timesheet date, last review date, assigned tasks list.

---

### PATCH `interns/{id}/`
- Brief: Update intern team or toggle active status.
- Auth: Bearer token required.
- Permission: `CustomizePermission` + `@role_required([RoleType.ADMIN.value])`.
- Request body (all optional):
```json
{
  "team": "Design Guild",
  "status": "ACTIVE"
}
```
- Validation: `team` must be valid `InternTeam`. `status` must be valid `InternEnrollmentStatus`.

---

### DELETE `interns/{id}/`
- Brief: Soft-deactivate intern. Sets `InternEnrollment.status = INACTIVE`.
- Auth: Bearer token required.
- Permission: `CustomizePermission` + `@role_required([RoleType.ADMIN.value])`.
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Intern deactivated successfully."]
  },
  "response": {
    "enrollment_id": "enrollment-uuid",
    "status": "INACTIVE"
  }
}
```
- Notes: Soft deactivate only. Does NOT delete records. Hard delete deferred.

---

### GET `interns/export/`
- Brief: CSV export of intern directory.
- Auth: Bearer token required.
- Permission: `CustomizePermission` + `@role_required([RoleType.ADMIN.value])`.
- Query params: Same filters as `GET interns/`.
- Response: `Content-Type: text/csv` download.
- CSV columns: `Rank,Name,Email,MUID,Team,Status,Daily Streak,Weekly Streak,Total Points,Completed Tasks`

---

## Task CRUD APIs

Base path: `/api/v1/dashboard/manage-interns/tasks/`

---

### GET `tasks/`
- Brief: List tasks with filters.
- Query params: `assigned_to`, `team`, `status`, `complexity`, `week`, `page`, `per_page`
- Success response includes paginated list of tasks with all fields.

### POST `tasks/`
- Brief: Create a task assigned to an intern.
- Required fields: `title`, `description`, `assigned_to`, `team`, `category`, `complexity`, `deadline`
- Request body:
```json
{
  "title": "Build User Profile Page",
  "description": "Implement the profile page with edit functionality.",
  "assigned_to": "user-uuid",
  "team": "Frontend Guild",
  "category": "UI Components",
  "complexity": "MEDIUM",
  "deadline": "2026-05-25"
}
```
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Task created successfully."]
  },
  "response": {
    "id": "task-uuid-1",
    "title": "Build User Profile Page",
    "assigned_to": "user-uuid",
    "status": "NOT_STARTED",
    "complexity": "MEDIUM",
    "deadline": "2026-05-25",
    "iso_week": 21
  }
}
```
- Validation:
  - `assigned_to` must be an enrolled intern.
  - `team` must match assigned intern's team.
  - `category` must be valid for the team (see `InternTaskCategory` enum).
  - `complexity` must be: LOW, MEDIUM, HIGH, or CRITICAL.
  - `iso_week` auto-computed from `deadline`.

### PATCH `tasks/{id}/`
- Brief: Update task. Admin can update all fields. Status transitions: `NOT_STARTED → IN_PROGRESS → COMPLETED / WAITING_FOR_REVIEW`.
- Side effect: `SystemActionLog` with `action_type='INTERN_TASK_UPDATE'`.

### DELETE `tasks/{id}/`
- Brief: Soft archive task. Sets `is_archived = True`.

---

## Leave Management APIs (Admin)

Base path: `/api/v1/dashboard/manage-interns/leave/`

---

### GET `leave/`
- Brief: All leave requests across teams.
- Query params: `status`, `team`, `leave_type`, `date_from`, `date_to`, `page`, `per_page`
- Success response includes paginated list with intern name, leave type, dates, status, reviewer.

### PATCH `leave/{id}/review/`
- Brief: Approve or reject a leave request.
- Required fields: `action`
- Optional fields: `review_note`
- Request body:
```json
{
  "action": "approve",
  "review_note": "Approved. Get well soon."
}
```
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Leave request approved."]
  },
  "response": {
    "id": "leave-uuid-1",
    "status": "APPROVED",
    "reviewed_by": "admin-uuid",
    "reviewed_at": "2026-05-22T10:00:00Z",
    "review_note": "Approved. Get well soon."
  }
}
```
- Validation:
  - `action` must be `approve` or `reject`.
  - Leave must be in `PENDING` status.
  - `review_note` optional for approve, recommended for reject.
- Side effects:
  - Update `intern_leave_request.status`, `reviewed_by`, `reviewed_at`.
  - Log to `SystemActionLog` with `action_type='INTERN_LEAVE_REVIEW'`.

---

## Authentication & Permission Reference

### Headers

| Header | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <jwt_token>` | Yes |
| `Content-Type` | `application/json` | Yes (POST/PATCH) |

### Permission

All manage-interns endpoints: `@role_required([RoleType.ADMIN.value])`

### Status Badge Colors

| Status | Badge | Color |
|---|---|---|
| `ACTIVE` | ● Active | Green |
| `AT_RISK` | ▲ At Risk | Orange |
| `ON_LEAVE` | ● On Leave | Blue |
| `INACTIVE` | ○ Inactive | Gray |

### Task Status Values

| Status | Label |
|---|---|
| `NOT_STARTED` | Not Yet Started |
| `IN_PROGRESS` | In Progress |
| `COMPLETED` | Completed |
| `WAITING_FOR_REVIEW` | Waiting for Review |

### Task Complexity Weights

| Complexity | Weight |
|---|---|
| LOW | 1 |
| MEDIUM | 2 |
| HIGH | 3 |
| CRITICAL | 5 |

### Leave Status Values

| Status | Description |
|---|---|
| `PENDING` | Awaiting admin review |
| `APPROVED` | Approved by admin |
| `REJECTED` | Rejected by admin |
| `CANCELLED` | Cancelled by intern |

---

## Tables Referenced

| Table | Purpose |
|---|---|
| `intern_enrollment` | Enrollment CRUD, status, team |
| `intern_daily_timesheet` | Timesheet data for stats |
| `intern_weekly_review` | Review data for reports |
| `intern_task` | Task CRUD |
| `intern_leave_request` | Leave management |
| `karma_activity_log` | Points aggregation |
| `system_action_log` | Audit trail for task/leave actions |
| `task_list` | Intern hashtag definitions |
| `wallet` | Karma balance |
| `user_streak` | Streak data |
| `user` | Identity |
| `user_role_link` | Role check |
