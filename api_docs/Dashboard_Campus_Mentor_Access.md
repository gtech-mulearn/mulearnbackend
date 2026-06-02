# Dashboard — Campus Mentor Access

**Base path:** `/api/v1/dashboard/campus/`  
**Authorization:** `campus_access_required` in `api/dashboard/campus/dash_campus_helper.py`

Approved campus mentors are identified in the database, not by the global JWT `Mentor` role alone:

| Field | Value |
|-------|-------|
| `user_mentor.mentor_tier` | `CAMPUS_MENTOR` |
| `user_mentor.status` | `APPROVED` |
| `user_mentor.org_id` | Same college as `user_organization_link` |

IG mentors (`MENTOR` JWT + `IG_MENTOR` tier) do **not** receive campus staff APIs.

---

## Access matrix

| Endpoint | Campus Lead / Enabler | Campus mentor | Notes |
|----------|----------------------|---------------|--------|
| `campus-details/` | Yes | Yes (read) | |
| `home-summary/`, `member-funnel/`, `circle-health/`, `recent-activity/` | Yes | Yes (read) | |
| `student-details/`, `student-details/csv/` | Yes | Yes (read) | |
| `students/<muid>/activity/` | Yes | Yes (read) | |
| `weekly-karma/` (no `org_id`) | Yes | Yes (read) | |
| `igs/`, `igs/<id>/members/` | Yes | Yes (read) | |
| `learning-circles/`, `.../members/` | Yes | Yes (read) | |
| `analytics/karma-trend/`, `analytics/growth/` | Yes | Yes (read) | |
| `events/`, `events/distribution/` | Yes | Yes (read) | |
| `ig-chapters/` GET | Yes | Yes (read) | |
| `showcase/` GET | Yes | Yes (read) | |
| `sessions/list/` | All statuses | All statuses | Students: scheduled only |
| `sessions/create/` | No | Yes | `mentor_only` |
| `assign-mentor/` | Yes | No | Staff only |
| `transfer-*`, `change-student-type/` | Yes | No | Staff only |
| `ig-chapters/` POST/PATCH/DELETE | Yes | No | Staff only |
| `social-links/` PUT/DELETE | Yes | No | Staff only |
| `showcase/` PATCH | Yes | No | Staff only |
| `execom/*` | Yes (varies) | No | Campus Lead for mutations |

---

## Session list visibility

`can_view_all_campus_session_statuses()` returns true for:

- Admin (JWT)
- Campus Lead / Lead Enabler
- Approved campus mentor for the user’s college

Otherwise only `SCHEDULED` sessions are returned.

---

## Related

- [Dashboard_Campus_Mentor_Sessions.md](./Dashboard_Campus_Mentor_Sessions.md) — session API samples
- [Dashboard_Campus.md](./Dashboard_Campus.md) — full campus API index
