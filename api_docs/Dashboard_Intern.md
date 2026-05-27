# Dashboard / Intern

Base path: `/api/v1/dashboard/intern/`

---

## Intern Overview APIs

Base path: `/api/v1/dashboard/intern/overview/`

---

### GET `overview/status/`
- Brief: Dashboard snapshot — profile, points, dual streaks, rank, quest progress, status.
- Auth: Bearer token required.
- Permission: `CustomizePermission` (authenticated user with `Intern` role).
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Intern status fetched successfully."]
  },
  "response": {
    "name": "Alex Doe",
    "muid": "dev-1234",
    "email": "alex@example.com",
    "profile_pic": "https://example.com/avatar.png",
    "status": "ACTIVE",
    "total_points": 1240,
    "this_week_points": 120,
    "daily_streak": 14,
    "weekly_streak": 8,
    "longest_daily_streak": 14,
    "rank": 3,
    "weekly_quests": {
      "completed": 4,
      "total": 5
    },
    "team": "Frontend Guild",
    "enrolled_at": "2026-01-15T00:00:00Z"
  }
}
```
- Notes:
  - `total_points` = `Sum(KarmaActivityLog.karma)` filtered by intern hashtag tasks.
  - `this_week_points` = same sum, filtered to current ISO week date range (computed via `date.fromisocalendar()`).
  - `daily_streak` from `UserStreak` where `streak_type='intern_timesheet'`.
  - `weekly_streak` from `UserStreak` where `streak_type='intern_weekly_review'`.
  - `weekly_quests.completed` = daily timesheets this week + (1 if weekly review submitted).
  - `weekly_quests.total` = always 5.

---

### GET `overview/activity/`
- Brief: Recent activity feed combining karma events and system actions.
- Auth: Bearer token required.
- Permission: `CustomizePermission` (Intern role).
- Query params:
  - `limit` (optional, default `20`, max `50`)
  - `page` (optional, default `1`)
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Activity log fetched successfully."]
  },
  "response": [
    {
      "type": "TIMESHEET_SUBMITTED",
      "description": "Submitted daily timesheet for 14 May 2026",
      "points": 15,
      "date": "2026-05-14T10:00:00Z"
    },
    {
      "type": "LEAVE_APPROVED",
      "description": "Sick leave approved for 16-17 May 2026",
      "points": null,
      "date": "2026-05-14T11:30:00Z"
    },
    {
      "type": "TASK_STATUS_UPDATED",
      "description": "Task 'Build Profile Page' marked as COMPLETED",
      "points": null,
      "date": "2026-05-13T16:00:00Z"
    }
  ]
}
```
- Notes:
  - Merges two sources: `KarmaActivityLog` (karma events with `#intern-*` hashtags) + `SystemActionLog` (non-karma events with `INTERN_*` action types).
  - Sorted by `created_at` descending across both sources.
  - `points` = karma value for karma events, `null` for system actions.
  - Paginated beyond `limit`.

---

### GET `overview/leaderboard/top/`
- Brief: Top 3 interns for the elite leaders card.
- Auth: Bearer token required.
- Permission: `CustomizePermission` (Intern role).
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Top leaders fetched successfully."]
  },
  "response": [
    {
      "rank": 1,
      "name": "Michael Chen",
      "muid": "m-chen@mulearn",
      "total_score": 2100,
      "is_current_user": false
    },
    {
      "rank": 2,
      "name": "Jessica Wong",
      "muid": "j-wong@mulearn",
      "total_score": 1950,
      "is_current_user": false
    },
    {
      "rank": 3,
      "name": "Alex Doe",
      "muid": "dev-1234",
      "total_score": 1240,
      "is_current_user": true
    }
  ]
}
```
- Notes:
  - `total_score` = weighted composite (40% karma + 20% daily streak + 20% weekly streak + 10% tasks + 10% complexity).
  - Top 3 only.

---

## Timesheet APIs

Base path: `/api/v1/dashboard/intern/timesheets/`

---

### POST `timesheets/`
- Brief: Submit daily timesheet. One per user per day. 24h window (today or yesterday with reason).
- Auth: Bearer token required.
- Permission: `CustomizePermission` (Intern role).
- Required fields: `category`, `description`, `hours`
- Optional fields: `blockers`, `task_id`, `task_status`, `remark`, `edit_reason` (required if backdating)
- Request body:
```json
{
  "category": "frontend",
  "description": "Built dashboard UI components and integrated API endpoints.",
  "hours": 8,
  "blockers": "",
  "task_id": "task-uuid-1",
  "task_status": "IN_PROGRESS",
  "remark": "Good progress today"
}
```
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Daily timesheet submitted successfully."]
  },
  "response": {
    "id": "ts-uuid-1",
    "entry_date": "2026-05-14",
    "category": "frontend",
    "description": "Built dashboard UI components and integrated API endpoints.",
    "hours": 8.00,
    "blockers": "",
    "task_id": "task-uuid-1",
    "task_status": "IN_PROGRESS",
    "remark": "Good progress today",
    "status": "submitted",
    "karma_awarded": 15,
    "streak": {
      "current_streak": 15,
      "multiplier": 1.5
    }
  }
}
```
- Conflict response (`409`):
```json
{
  "hasError": true,
  "statusCode": 409,
  "message": {
    "general": ["Timesheet already submitted for today."]
  },
  "response": {}
}
```
- Validation rules:
  - `entry_date` = today or yesterday (24h window). Future dates rejected.
  - If `entry_date < today`: `edit_reason` is mandatory.
  - `hours` > 0, max 99.99.
  - `task_id` nullable — freeform timesheets allowed.
  - `UNIQUE(user_id, entry_date)` → `IntegrityError` → 409.
  - User's `InternEnrollment.status` must NOT be `INACTIVE`.
- Side effects (inside `transaction.atomic()`):
  1. Create `InternDailyTimesheet` row.
  2. Compute XP multiplier from daily streak tier.
  3. `add_karma()` with `#intern-daily-log`, karma = `int(base * multiplier)`.
  4. Update `UserStreak` (`streak_type='intern_timesheet'`).
  5. Streak milestone bonuses if applicable.
  6. If `AT_RISK` → transition to `ACTIVE`.
  7. If `task_id` provided → update `intern_task.status`.

---

### GET `timesheets/today/`
- Brief: Get today's timesheet if exists. Used to determine form lock state.
- Auth: Bearer token required.
- Permission: `CustomizePermission` (Intern role).
- Success response (`200`) — submitted:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Today's timesheet fetched successfully."]
  },
  "response": {
    "id": "ts-uuid-1",
    "entry_date": "2026-05-14",
    "category": "frontend",
    "description": "Built dashboard UI components.",
    "hours": 8.00,
    "task_status": "IN_PROGRESS",
    "remark": "Good progress",
    "end_of_day_note": null,
    "status": "submitted"
  }
}
```
- Response when not submitted:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["No timesheet submitted for today."]
  },
  "response": null
}
```

---

### PATCH `timesheets/{id}/`
- Brief: Edit remark or end-of-day note after submission. Requires edit_reason.
- Auth: Bearer token required.
- Permission: `CustomizePermission` (Intern role, must own timesheet).
- Required fields: `edit_reason`
- Optional fields: `remark`, `end_of_day_note`
- Request body:
```json
{
  "end_of_day_note": "Finished all planned tasks. PR submitted for review.",
  "edit_reason": "Adding EOD summary"
}
```
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Timesheet updated successfully."]
  },
  "response": {
    "id": "ts-uuid-1",
    "remark": "Good progress",
    "end_of_day_note": "Finished all planned tasks. PR submitted for review.",
    "edit_reason": "Adding EOD summary"
  }
}
```
- Error (`400`) — missing edit_reason:
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "edit_reason": ["This field is required when editing a submitted timesheet."]
  },
  "response": {}
}
```
- Notes:
  - Only `remark` and `end_of_day_note` are editable. All other fields are read-only after submit.
  - Logs to `SystemActionLog` with `action_type='INTERN_TIMESHEET_EDIT'`.

---

### GET `timesheets/history/`
- Brief: Paginated timesheet history for calendar display.
- Auth: Bearer token required.
- Permission: `CustomizePermission` (Intern role).
- Query params:
  - `days` (optional, default `14`)
  - `page`, `per_page` (optional)
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Timesheet history fetched successfully."]
  },
  "response": [
    {"entry_date": "2026-05-14", "status": "submitted", "hours": 8.00, "category": "frontend"},
    {"entry_date": "2026-05-13", "status": "submitted", "hours": 7.50, "category": "backend"},
    {"entry_date": "2026-05-12", "status": "missing"}
  ]
}
```

---

### GET `timesheets/summary/`
- Brief: Streak info for the streak bonus card.
- Auth: Bearer token required.
- Permission: `CustomizePermission` (Intern role).
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Streak summary fetched successfully."]
  },
  "response": {
    "current_streak": 14,
    "longest_streak": 14,
    "multiplier": 1.5,
    "next_milestone": {"days": 30, "bonus_karma": 100},
    "today_submitted": true
  }
}
```

---

## Weekly Review APIs

Base path: `/api/v1/dashboard/intern/reviews/`

---

### POST `reviews/`
- Brief: Submit weekly review. One per ISO week. Late submissions accepted but flagged.
- Auth: Bearer token required.
- Permission: `CustomizePermission` (Intern role).
- Required fields: `team`, `tasks_assigned`, `tasks_completed`, `weekly_review`, `hours_committed`
- Optional fields: `is_on_leave`, `blockers`, `leave_days`, `suggestions`, `task_remarks`
- Request body:
```json
{
  "team": "Frontend Guild",
  "is_on_leave": false,
  "tasks_assigned": "Build user profile page, Integrate API",
  "tasks_completed": "Profile page completed",
  "weekly_review": "Productive week. Completed the profile module and started API integration.",
  "hours_committed": "40",
  "blockers": "API rate limiting",
  "suggestions": "Better API documentation would help",
  "task_remarks": {"task-uuid-1": "Blocked by backend dependency"}
}
```
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Weekly review submitted successfully."]
  },
  "response": {
    "id": "wr-uuid-1",
    "iso_year": 2026,
    "iso_week": 20,
    "week_start_date": "2026-05-11",
    "week_end_date": "2026-05-17",
    "team": "Frontend Guild",
    "is_late": false,
    "status": "submitted",
    "karma_awarded": 50
  }
}
```
- Conflict response (`409`):
```json
{
  "hasError": true,
  "statusCode": 409,
  "message": {
    "general": ["Weekly review already submitted for this week."]
  },
  "response": {}
}
```
- Validation:
  - `iso_year`, `iso_week`, `week_start_date`, `week_end_date` computed server-side.
  - Deadline: Sunday 23:59 UTC. Late submissions: `is_late=True`, weekly streak broken.
  - `task_remarks` required for incomplete tasks past deadline.
  - `UNIQUE(user_id, iso_year, iso_week)` → 409.

---

### GET `reviews/current/`
- Brief: Current week's review status.
- Auth: Bearer token required.
- Permission: `CustomizePermission` (Intern role).
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Week status fetched successfully."]
  },
  "response": {
    "iso_year": 2026,
    "iso_week": 20,
    "is_submitted": true,
    "is_current_week": true,
    "deadline": "2026-05-17T23:59:00Z",
    "review": {
      "id": "wr-uuid-1",
      "team": "Frontend Guild",
      "weekly_review": "Productive week...",
      "hours_committed": "40",
      "is_late": false,
      "status": "submitted",
      "created_at": "2026-05-16T14:00:00Z"
    }
  }
}
```

---

### PATCH `reviews/{id}/`
- Brief: Update weekly review before deadline.
- Auth: Bearer token required.
- Permission: `CustomizePermission` (Intern role, must own review).
- Editable fields: `weekly_review`, `suggestions`, `task_remarks`, `blockers`
- Request body:
```json
{
  "weekly_review": "Updated review with more details.",
  "suggestions": "More pair programming sessions"
}
```
- Validation: Only allowed before Sunday 23:59 UTC of the review's week.

---

### GET `reviews/history/`
- Brief: Paginated past weekly reviews.
- Auth: Bearer token required.
- Permission: `CustomizePermission` (Intern role).
- Query params: `page`, `per_page`
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Review history fetched successfully."]
  },
  "response": {
    "reviews": [
      {
        "id": "wr-uuid-1",
        "week": "W20 2026",
        "team": "Frontend Guild",
        "is_late": false,
        "karma_awarded": 50,
        "created_at": "2026-05-16T14:00:00Z"
      }
    ],
    "pagination": {"current_page": 1, "total_pages": 5, "per_page": 10, "total_entries": 48}
  }
}
```

---

## Teams API

Base path: `/api/v1/dashboard/intern/teams/`

### GET `teams/`
- Brief: Static team list for dropdowns.
- Auth: Bearer token required.
- Success response: `["Frontend Guild", "Backend Guild", "Design Guild", "Mobile Guild"]`
- Source: `InternTeam` enum. No DB query.

---

## Leaderboard APIs

Base path: `/api/v1/dashboard/intern/leaderboard/`

---

### GET `leaderboard/`
- Brief: Full intern leaderboard with weighted composite scoring.
- Auth: Bearer token required.
- Permission: `CustomizePermission` (Intern role).
- Query params: `period` (week/month/all_time), `search`, `team`, `per_page`, `page`
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Leaderboard fetched successfully."]
  },
  "response": {
    "leaderboard": [
      {
        "rank": 1,
        "name": "Emma Wilson",
        "muid": "ew",
        "profile_pic": "https://example.com/ew.png",
        "total_score": 920,
        "karma_points": 500,
        "daily_streak": 12,
        "weekly_streak": 8,
        "completed_tasks": 15,
        "team": "Frontend Guild"
      }
    ],
    "pagination": {"current_page": 1, "total_pages": 1, "per_page": 10, "total_entries": 4},
    "current_user": {"rank": 3, "total_score": 810, "today_earned": 50, "total_interns": 142}
  }
}
```
- Scoring: 40% karma + 20% daily streak + 20% weekly streak + 10% completed tasks + 10% complexity score.
- Tie-breaking: earlier `User.created_at`.

---

### GET `leaderboard/me/`
- Brief: Own rank and score breakdown.
- Auth: Bearer token required.
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Your rank fetched successfully."]
  },
  "response": {
    "rank": 3,
    "total_score": 810,
    "breakdown": {
      "karma_component": 324,
      "daily_streak_component": 162,
      "weekly_streak_component": 162,
      "tasks_component": 81,
      "complexity_component": 81
    }
  }
}
```

---

## Leave APIs

Base path: `/api/v1/dashboard/intern/leave/`

---

### POST `leave/`
- Brief: Apply for leave.
- Auth: Bearer token required.
- Permission: `CustomizePermission` (Intern role).
- Required: `leave_type`, `start_date`, `end_date`, `reason`
- Request body:
```json
{
  "leave_type": "SICK",
  "start_date": "2026-05-20",
  "end_date": "2026-05-21",
  "reason": "Not feeling well"
}
```
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Leave request submitted successfully."]
  },
  "response": {
    "id": "leave-uuid-1",
    "leave_type": "SICK",
    "start_date": "2026-05-20",
    "end_date": "2026-05-21",
    "duration_days": 2,
    "status": "PENDING"
  }
}
```
- Validation:
  - `end_date >= start_date`
  - No overlapping approved/pending leave
  - Quota check: SICK ≤2/mo, CASUAL ≤1/mo, WFH ≤2/week
  - Non-emergency: `start_date > today`
- Side effect: `SystemActionLog` with `action_type='INTERN_LEAVE_REQUEST'`

---

### GET `leave/`
- Brief: Intern's leave history.
- Query params: `status`, `page`, `per_page`

### PATCH `leave/{id}/cancel/`
- Brief: Cancel pending leave (intern-only, before review).
- Validation: Only `PENDING` status can be cancelled.

### GET `leave/balance/`
- Brief: Remaining leave quota per type.
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Leave balance fetched successfully."]
  },
  "response": {
    "sick": {"used": 1, "limit": 2, "remaining": 1, "period": "monthly"},
    "casual": {"used": 0, "limit": 1, "remaining": 1, "period": "monthly"},
    "emergency": {"used": 0, "limit": null, "remaining": null, "period": null},
    "wfh": {"used": 1, "limit": 2, "remaining": 1, "period": "weekly"}
  }
}
```
- Computed dynamically: `COUNT(approved, type=X, period=current)`. No stored quota.

---

## Tasks API (Intern-facing)

Base path: `/api/v1/dashboard/intern/tasks/`

### GET `tasks/mine/`
- Brief: Intern's assigned tasks.
- Query params: `status`, `page`, `per_page`
- Success response includes: id, title, category, status, complexity, deadline, team.

---

## Authentication & Permission Reference

### Headers

| Header | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <jwt_token>` | Yes |
| `Content-Type` | `application/json` | Yes (POST/PATCH) |

### Intern Status Values

| Status | Badge | Color |
|---|---|---|
| `ACTIVE` | ● Active | Green |
| `AT_RISK` | ▲ At Risk | Orange |
| `ON_LEAVE` | ● On Leave | Blue |
| `INACTIVE` | ○ Inactive | Gray |

### XP Multiplier Tiers

| Streak | Multiplier |
|---|---|
| 0–6 days | 1.0x |
| 7–13 | 1.2x |
| 14–29 | 1.5x |
| 30+ | 2.0x |

### Streak Bonus Milestones

| Milestone | Bonus | Hashtag |
|---|---|---|
| 7 days | +20 | `#intern-streak-7` |
| 14 days | +50 | `#intern-streak-14` |
| 30 days | +100 | `#intern-streak-30` |
| 60 days | +200 | `#intern-streak-60` |
| 90 days | +500 | `#intern-streak-90` |

---

## Tables Referenced

| Table | Purpose |
|---|---|
| `intern_enrollment` | Enrollment status, team |
| `intern_daily_timesheet` | Daily timesheet submissions |
| `intern_weekly_review` | Weekly review submissions |
| `intern_task` | Admin-assigned tasks |
| `intern_leave_request` | Leave requests |
| `karma_activity_log` | Points/XP via `add_karma()` |
| `system_action_log` | Non-karma activity events |
| `task_list` | Intern hashtag definitions |
| `wallet` | Karma balance |
| `user_streak` | Dual streak tracking |
| `user` | Identity |
| `user_role_link` | Intern role check |
