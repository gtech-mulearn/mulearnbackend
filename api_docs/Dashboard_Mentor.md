# Dashboard / Mentor

Base path: `/api/v1/dashboard/mentor/`

---

## Persona APIs

Base path: `/api/v1/dashboard/mentor/persona/`

---

### POST `persona/switch/`
- Brief: Switch authenticated user's active persona to **mentor** for a specific IG.
- Auth: Bearer token required.
- Permission: `CustomizePermission` (authenticated user).
- Required fields: `active_role_link_id`, `active_ig_id`
- Validation rules:
  - `active_role_link_id` MUST belong to the authenticated user
  - The role assignment MUST have `is_active = 1`
  - The `ig_id` on the role assignment MUST match `active_ig_id`
  - The role MUST be a Mentor role (`role.title == 'Mentor'`)
- Request body:
```json
{
  "active_role_link_id": "<user_role_link.id>",
  "active_ig_id": "<interest_group.id>"
}
```
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Persona switched to mentor successfully."
    ]
  },
  "response": {
    "active_persona": "mentor",
    "active_role_link_id": "abc12345-...",
    "active_ig_id": "ig67890-...",
    "ig_name": "Web Development",
    "is_verified": true,
    "mentor_tier": "VERIFIED",
    "last_persona_switched_at": "2026-05-05T00:00:00+05:30",
    "access": null
  }
}
```
- Error response (`403`) — role_link not owned, inactive, or not a Mentor role:
```json
{
  "hasError": true,
  "statusCode": 403,
  "message": {
    "general": [
      "Invalid persona switch request."
    ],
    "non_field_errors": [
      "No active mentor role found for this IG, or you do not own this role assignment."
    ]
  },
  "response": {}
}
```
- Error response (`400`) — missing required fields:
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": [
      "Invalid persona switch request."
    ],
    "active_role_link_id": [
      "This field is required."
    ],
    "active_ig_id": [
      "This field is required."
    ]
  },
  "response": {}
}
```
- Notes:
  - Writes to `user_settings` table — this is the DB source of truth for persona state.
  - `access` field is always present. Currently returns `null`; reserved for optional JWT reissue.
  - After switching, all subsequent mentor-protected API calls use the new IG context.

---

### POST `persona/reset/`
- Brief: Reset active persona back to **learner**. Clears IG and role_link context.
- Auth: Bearer token required.
- Permission: `CustomizePermission` (authenticated user).
- Request body: `{}` (empty object)
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Persona reset to learner."
    ]
  },
  "response": {
    "active_persona": "learner"
  }
}
```
- Error response (`404`) — user settings not found:
```json
{
  "hasError": true,
  "statusCode": 404,
  "message": {
    "general": [
      "User settings not found."
    ]
  },
  "response": {}
}
```
- Notes:
  - Sets `active_persona = 'learner'` and nullifies `active_role_link_id` and `active_ig_id` in `user_settings`.
  - After reset, all mentor-protected endpoints return `403`.

---

### GET `persona/ig-roles/`
- Brief: Get all active IG-scoped Mentor role assignments for the authenticated user. Used by the frontend persona switcher dropdown.
- Auth: Bearer token required.
- Permission: `CustomizePermission` (authenticated user).
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "IG roles fetched successfully."
    ]
  },
  "response": {
    "ig_roles": [
      {
        "role_link_id": "url-uuid-1",
        "ig_id": "ig-uuid-1",
        "ig_name": "Web Development",
        "role": "Mentor",
        "is_primary": true,
        "is_verified": true,
        "mentor_tier": "VERIFIED"
      },
      {
        "role_link_id": "url-uuid-2",
        "ig_id": "ig-uuid-2",
        "ig_name": "UI/UX Design",
        "role": "Mentor",
        "is_primary": false,
        "is_verified": false,
        "mentor_tier": "NORMAL"
      }
    ]
  }
}
```
- Notes:
  - Returns only roles where `role.title = 'Mentor'`, `ig_id IS NOT NULL`, and `is_active = 1`.
  - `is_verified` and `mentor_tier` come from `user_mentor` table, not the role assignment.
  - Field name is `role_link_id` (maps to `user_role_link.id`).
  - Returns empty `ig_roles: []` if user has no active mentor assignments.

---

## Mentor Profile APIs

Base path: `/api/v1/dashboard/mentor/profile/`

---

### GET `profile/`
- Brief: Get authenticated mentor's own profile.
- Auth: Bearer token required.
- Permission: `CustomizePermission` + `IsIGMentor` (active mentor persona required).
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Mentor profile fetched."
    ]
  },
  "response": {
    "about": "I help students build production-grade web apps.",
    "reason": "Giving back to the community.",
    "expertise": "Django, React, PostgreSQL",
    "volunteer_hours": 24,
    "mentor_tier": "VERIFIED",
    "is_verified": true,
    "verified_at": "2026-01-15T10:00:00+05:30",
    "verification_note": "Approved by muLearn team."
  }
}
```
- Error response (`403`) — no active mentor persona:
```json
{
  "hasError": true,
  "statusCode": 403,
  "message": {
    "general": [
      "Active mentor persona required for this IG."
    ]
  },
  "response": {}
}
```
- Error response (`404`) — mentor profile not found:
```json
{
  "hasError": true,
  "statusCode": 404,
  "message": {
    "general": [
      "Mentor profile not found."
    ]
  },
  "response": {}
}
```
- Notes:
  - Reads from `user_mentor` table.
  - Requires switching persona to mentor first via `persona/switch/`.
  - `verified_at` and `verification_note` are read-only (set by admins).

---

### PATCH `profile/`
- Brief: Partial update of mentor profile. Only `about`, `reason`, and `expertise` are editable.
- Auth: Bearer token required.
- Permission: `CustomizePermission` + `IsIGMentor` (active mentor persona required).
- Request body (all fields optional):
```json
{
  "about": "I specialize in backend systems and API design.",
  "reason": "Passionate about open-source and student growth.",
  "expertise": "Django, DRF, PostgreSQL, Redis"
}
```
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Mentor profile updated."
    ]
  },
  "response": {
    "about": "I specialize in backend systems and API design.",
    "reason": "Passionate about open-source and student growth.",
    "expertise": "Django, DRF, PostgreSQL, Redis",
    "volunteer_hours": 24,
    "mentor_tier": "VERIFIED",
    "is_verified": true
  }
}
```
- Error response (`400`) — no valid fields provided:
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": [
      "No valid fields provided for update."
    ]
  },
  "response": {}
}
```
- Notes:
  - Verification fields (`mentor_tier`, `is_verified`, `verified_by`, `verified_at`, `verification_note`) are **read-only** — they cannot be set via this endpoint.
  - Creates `user_mentor` row if one does not already exist.

---

## Mentor Dashboard APIs

Base path: `/api/v1/dashboard/mentor/overview/`

---

### GET `overview/`
- Brief: Full mentor dashboard snapshot — user details, mentor profile, active persona context, all authorized IGs, and stats scoped to the active IG.
- Auth: Bearer token required.
- Permission: `CustomizePermission` + `IsIGMentor` (active mentor persona required).
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Mentor overview fetched."
    ]
  },
  "response": {
    "user": {
      "full_name": "Jane Doe",
      "muid": "jane-doe@mulearn",
      "profile_pic": "https://example.com/user/profile/uuid.png"
    },
    "mentor_profile": {
      "about": "I help students build web apps.",
      "expertise": "Django, React",
      "reason": "Giving back to the community.",
      "volunteer_hours": 24,
      "mentor_tier": "VERIFIED",
      "is_verified": true
    },
    "active_persona": {
      "active_persona": "mentor",
      "active_role_link_id": "role-link-uuid",
      "active_ig_id": "ig-uuid",
      "ig_name": "Web Development",
      "is_verified": true
    },
    "authorized_igs": [
      {
        "role_link_id": "role-link-uuid-1",
        "ig_id": "ig-uuid-1",
        "ig_name": "Web Development",
        "is_primary": true,
        "is_verified": true
      },
      {
        "role_link_id": "role-link-uuid-2",
        "ig_id": "ig-uuid-2",
        "ig_name": "UI/UX Design",
        "is_primary": false,
        "is_verified": false
      }
    ],
    "stats": {
      "total_mentees": 12,
      "sessions_conducted": 8,
      "pending_task_approvals": 0,
      "volunteer_hours": 24
    }
  }
}
```
- Error response (`403`) — no active mentor persona:
```json
{
  "hasError": true,
  "statusCode": 403,
  "message": {
    "general": [
      "Active mentor persona required for this IG."
    ]
  },
  "response": {}
}
```
- Notes:
  - `user` block intentionally excludes `email`.
  - `stats` are scoped to the active IG (from persona context).
  - `pending_task_approvals` currently returns `0` — will be live once `karma_activity_log.mentor_review_status` column is added.
  - `authorized_igs` shows **all** IGs where the user holds an active Mentor role, not just the active one.

---

## Mentor Availability APIs

Base path: `/api/v1/dashboard/mentor/availability/`

---

### GET `availability/`
- Brief: Get mentor's availability slots for the active IG, plus any global (IG-null) slots.
- Auth: Bearer token required.
- Permission: `CustomizePermission` + `IsIGMentor` (active mentor persona required).
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Availability slots fetched."
    ]
  },
  "response": {
    "active_ig_id": "ig-uuid",
    "slots": [
      {
        "id": "slot-uuid-1",
        "ig_id": "ig-uuid",
        "ig_name": "Web Development",
        "weekday": 1,
        "start_time": "10:00",
        "end_time": "12:00",
        "timezone": "Asia/Kolkata",
        "is_active": true,
        "valid_from": "2026-05-01",
        "valid_to": null
      },
      {
        "id": "slot-uuid-2",
        "ig_id": null,
        "ig_name": null,
        "weekday": 3,
        "start_time": "15:00",
        "end_time": "17:00",
        "timezone": "Asia/Kolkata",
        "is_active": true,
        "valid_from": null,
        "valid_to": null
      }
    ]
  }
}
```
- Notes:
  - Returns slots where `mentor_user_id = authenticated user` AND (`ig_id = active_ig_id` OR `ig_id IS NULL`).
  - `ig_id = NULL` means the slot is global — applies across all IGs.
  - Slots are ordered by `weekday`, then `start_time`.
  - `weekday` values: `1` = Monday through `7` = Sunday.

---

### POST `availability/`
- Brief: Create one or more availability slots for the active IG.
- Auth: Bearer token required.
- Permission: `CustomizePermission` + `IsIGMentor` (active mentor persona required).
- Request body:
```json
{
  "slots": [
    {
      "weekday": 1,
      "start_time": "10:00",
      "end_time": "12:00",
      "timezone": "Asia/Kolkata",
      "valid_from": "2026-05-01",
      "valid_to": null
    },
    {
      "weekday": 3,
      "start_time": "15:00",
      "end_time": "17:00",
      "timezone": "Asia/Kolkata",
      "valid_from": null,
      "valid_to": null
    }
  ]
}
```
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "2 slot(s) created."
    ]
  },
  "response": {
    "created_ids": [
      "slot-uuid-1",
      "slot-uuid-2"
    ],
    "errors": []
  }
}
```
- Partial success response (`200`) — some slots had validation errors:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "1 slot(s) created."
    ]
  },
  "response": {
    "created_ids": [
      "slot-uuid-1"
    ],
    "errors": [
      {
        "index": 1,
        "error": "start_time must be before end_time."
      }
    ]
  }
}
```
- Error response (`400`) — missing or empty slots:
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": [
      "'slots' must be a non-empty list."
    ]
  },
  "response": {}
}
```
- Validation rules:
  - `slots` must be a non-empty list.
  - `end_time` must be strictly after `start_time`.
  - `weekday` must be between `1` (Monday) and `7` (Sunday).
  - `ig_id` is **never accepted from the request body** — it is always derived from `request.persona_context.active_ig_id`. This prevents cross-IG injection.
  - `valid_from` and `valid_to` are optional (nullable).

---

### DELETE `availability/<slot_id>/`
- Brief: Soft-delete an availability slot (sets `is_active = false`).
- Auth: Bearer token required.
- Permission: `CustomizePermission` + `IsIGMentor` (active mentor persona required).
- Path parameter: `slot_id` — UUID of the `mentor_availability_slot` to delete.
- Success response (`200`):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Availability slot removed."
    ]
  },
  "response": {
    "slot_id": "slot-uuid"
  }
}
```
- Error response (`404`) — slot not found, wrong IG, or not owned:
```json
{
  "hasError": true,
  "statusCode": 404,
  "message": {
    "general": [
      "Slot not found or access denied."
    ]
  },
  "response": {}
}
```
- Validation rules:
  - `slot.mentor_user_id` must match the authenticated user.
  - `slot.ig_id` must match `active_ig_id` from persona context, **OR** `slot.ig_id` must be `NULL` (global slot).
  - This is a **soft delete** — the row is not removed, `is_active` is set to `0`.

---

## Authentication & Permission Reference

### Headers (all endpoints)

| Header | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <jwt_token>` | Yes |
| `Content-Type` | `application/json` | Yes (for POST/PATCH) |

### Permission Classes

| Class | Description | DB Hits |
|---|---|---|
| `CustomizePermission` | JWT authentication — validates token, extracts `user_id` | 0 (JWT only) |
| `IsIGMentor` | Requires active mentor persona (reads `user_settings` + validates `user_role_link`) | 2 (first call, cached after) |
| `IsVerifiedIGMentor` | Requires verified mentor status (`user_mentor.is_verified = 1`) | 1 (on top of IsIGMentor) |
| `HasIGAccess` | Validates URL `ig_id` matches active persona IG | 0 (in-memory) |

### Mentor Tiers

| Tier | `is_verified` | `mentor_tier` | Access |
|---|---|---|---|
| Normal | `false` | `NORMAL` | Standard mentor actions (profile, availability, overview) |
| Verified | `true` | `VERIFIED` | All actions + session creation |

---

## Tables Referenced

| Table | Purpose |
|---|---|
| `user_role_link` | Stores role assignments; IG-scoped when `ig_id` is set |
| `user_settings` | Stores active persona state (source of truth) |
| `user_mentor` | Mentor profile, verification status, and tier |
| `mentor_availability_slot` | Recurring availability time slots |
| `interest_group` | Interest Groups that mentors are assigned to |
