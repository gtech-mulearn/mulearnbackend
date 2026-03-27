# Dashboard — Campus API

**Base path:** `/api/dashboard/campus/`  
**Authentication:** JWT Bearer Token required on all endpoints.

---

## Table of Contents

| # | Endpoint | Method(s) | Auth / Role |
|---|----------|-----------|-------------|
| 1 | [`campus-details/`](#1-campus-details) | `GET` | Campus Lead, Lead Enabler |
| 2 | [`<org_id>/`](#2-org_id--public-campus-details) | `GET` | Any authenticated user |
| 3 | [`student-level/`](#3-student-level) | `GET` | Any authenticated user |
| 4 | [`student-level/<org_id>/`](#4-student-levelorg_id) | `GET` | Any authenticated user |
| 5 | [`student-details/`](#5-student-details) | `GET` | Campus Lead, Lead Enabler |
| 6 | [`student-details/csv/`](#6-student-detailscsv) | `GET` | Campus Lead, Lead Enabler |
| 7 | [`weekly-karma/`](#7-weekly-karma) | `GET` | Any authenticated user |
| 8 | [`weekly-karma/<org_id>/`](#8-weekly-karmaorg_id) | `GET` | Any authenticated user |
| 9 | [`change-student-type/<member_id>/`](#9-change-student-typemember_id) | `PATCH` | Campus Lead, Lead Enabler |
| 10 | [`transfer-lead-role/`](#10-transfer-lead-role) | `POST` | Campus Lead |
| 11 | [`transfer-enabler-role/`](#11-transfer-enabler-role) | `POST` | Campus Lead |
| 12 | [`transfer-ig-role/`](#12-transfer-ig-role) | `GET`, `POST` | Campus Lead, Lead Enabler |
| 13 | [`events/`](#13-events) | `GET` | Campus Lead, Lead Enabler |
| 14 | [`events/distribution/`](#14-eventsdistribution) | `GET` | Campus Lead, Lead Enabler |
| 15 | [`execom/`](#15-execom) | `GET`, `POST` | Campus Lead (POST), Campus Lead / Lead Enabler (GET) |
| 16 | [`execom/<member_id>/`](#16-execommember_id) | `DELETE` | Campus Lead |
| 17 | [`ig-chapters/`](#17-ig-chapters) | `GET`, `POST` | Campus Lead, Lead Enabler |
| 18 | [`ig-chapters/<chapter_id>/`](#18-ig-chapterschapter_id) | `PATCH`, `DELETE` | Campus Lead, Lead Enabler |
| 19 | [`social-links/`](#19-social-links) | `PUT` | Campus Lead, Lead Enabler |
| 20 | [`social-links/<link_id>/`](#20-social-linkslink_id) | `DELETE` | Campus Lead, Lead Enabler |
| 21 | [`<org_id>/leaderboard/`](#21-org_idleaderboard) | `GET` | Any authenticated user |
| 22 | [`<org_id>/karma-by-cluster/`](#22-org_idkarma-by-cluster) | `GET` | Any authenticated user |
| 23 | [`campus-list/`](#23-campus-list) | `GET` | Any authenticated user |

---

## 1. Campus Details

**`GET /api/dashboard/campus/campus-details/`**

Returns detailed information about the authenticated Campus Lead's own campus, including lead names, karma stats, and active IG count.

**Roles:** `Campus Lead`, `Lead Enabler`

**Request Body:** None

**Query Params:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "org_id": "82e6f245-59ea-4be4-a33d-35189a395000",
    "college_name": "Example College of Engineering",
    "campus_code": "ECE001",
    "campus_zone": "South Zone",
    "campus_level": 3,
    "total_karma": 45200,
    "total_members": 312,
    "active_members": 180,
    "rank": 5,
    "lead": {
      "campus_lead": "Arjun Menon",
      "enabler": "Priya Nair"
    },
    "karma_last_7_days": 1200,
    "karma_last_30_days": 4800,
    "active_ig_count": 7,
    "social_links": [
      {
        "id": "e5f67890-abcd-ef12-3456-7890abcdef12",
        "platform": "instagram",
        "url": "https://instagram.com/eec_mulearn"
      }
    ]
  }
}
```

---

## 2. `<org_id>/` — Public Campus Details

**`GET /api/dashboard/campus/<org_id>/`**

Returns public details of any campus by its organisation ID. Does not require a specific role.

**Path Params:**
- `org_id` *(string)* — UUID of the college organisation

**Request Body:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "org_id": "82e6f245-59ea-4be4-a33d-35189a395000",
    "college_name": "Example College of Engineering",
    "campus_code": "ECE001",
    "campus_zone": "South Zone",
    "campus_level": 3,
    "total_karma": 45200,
    "total_members": 312,
    "active_members": 180,
    "rank": 5,
    "social_links": [
      {
        "id": "e5f67890-abcd-ef12-3456-7890abcdef12",
        "platform": "instagram",
        "url": "https://instagram.com/eec_mulearn"
      }
    ]
  }
}
```

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["College not found"] } }
```

---

## 3. Student Level

**`GET /api/dashboard/campus/student-level/`**

Returns the number of students at each karma level for the authenticated user's campus.

**Roles:** Any authenticated user (no role restriction)

**Request Body:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": [
    { "level": 1, "students": 120 },
    { "level": 2, "students": 80 },
    { "level": 3, "students": 45 },
    { "level": 4, "students": 20 },
    { "level": 5, "students": 5 }
  ]
}
```

---

## 4. `student-level/<org_id>/`

**`GET /api/dashboard/campus/student-level/<org_id>/`**

Same as above but for any specific college by `org_id`.

**Path Params:**
- `org_id` *(string)* — UUID of the college organisation

**Request Body:** None

**Response:** Same structure as [Student Level](#3-student-level).

---

## 5. Student Details

**`GET /api/dashboard/campus/student-details/`**

Returns a paginated list of students in the campus lead's college with their karma, level, rank, department, and alumni status.

**Roles:** `Campus Lead`, `Lead Enabler`

**Query Params:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `is_alumni` | `"true"` / `"false"` | No | Filter by alumni status |
| `pageIndex` | integer | No | Page number (default: 1) |
| `perPage` | integer | No | Items per page (default: 20) |
| `sortBy` | string | No | Field to sort by (`full_name`, `karma`, `level`, `join_date`, `muid`, `email`, `mobile`, `is_alumni`) |
| `search` | string | No | Search by name or level |

**Request Body:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "data": [
      {
        "user_id": "a1b2c3d4-...",
        "full_name": "Rahul Krishna",
        "muid": "rahul-krishna@mulearn",
        "email": "rahul@example.com",
        "mobile": "9876543210",
        "karma": 3400,
        "rank": 1,
        "level": "Pathfinder",
        "join_date": "2023-08-01T10:00:00Z",
        "last_karma_gained": "2024-03-10T14:30:00Z",
        "department": "Computer Science",
        "graduation_year": "2025",
        "is_alumni": false
      }
    ],
    "pagination": {
      "count": 312,
      "totalPages": 16,
      "isFirst": true,
      "isLast": false,
      "nextPage": "/student-details/?pageIndex=2"
    }
  }
}
```

---

## 6. Student Details CSV

**`GET /api/dashboard/campus/student-details/csv/`**

Downloads the same student data as endpoint 5 as a CSV file.

**Roles:** `Campus Lead`, `Lead Enabler`

**Query Params:** Same as [Student Details](#5-student-details)

**Request Body:** None

**Response:** `text/csv` file download — `Campus Student Details.csv`

---

## 7. Weekly Karma

**`GET /api/dashboard/campus/weekly-karma/`**

Returns the total karma earned by students in the campus lead's college for each of the last 7 days.

**Roles:** Any authenticated user

**Request Body:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "college_name": "Example College of Engineering",
    "2024-03-15": 520,
    "2024-03-14": 340,
    "2024-03-13": 410,
    "2024-03-12": 290,
    "2024-03-11": 600,
    "2024-03-10": 480,
    "2024-03-09": 310
  }
}
```

---

## 8. `weekly-karma/<org_id>/`

**`GET /api/dashboard/campus/weekly-karma/<org_id>/`**

Same as above but for any specific college by `org_id`.

**Path Params:**
- `org_id` *(string)* — UUID of the college organisation

**Response:** Same structure as [Weekly Karma](#7-weekly-karma).

---

## 9. Change Student Type

**`PATCH /api/dashboard/campus/change-student-type/<member_id>/`**

Toggles a student's alumni status within the campus lead's college.

**Roles:** `Campus Lead`, `Lead Enabler`

**Path Params:**
- `member_id` *(string)* — UUID of the target user

**Request Body:**
```json
{
  "is_alumni": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `is_alumni` | boolean | Yes | `true` = mark as alumni, `false` = mark as student |

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Student Type updated successfully"] },
  "response": {}
}
```

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["User have no organization"] } }
```

---

## 10. Transfer Lead Role

**`POST /api/dashboard/campus/transfer-lead-role/`**

Transfers the `Campus Lead` role from the current lead to another student in the same college. The current lead **loses** the role.

**Roles:** `Campus Lead` only

**Request Body:**
```json
{
  "new_lead_muid": "rahul-krishna@mulearn"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `new_lead_muid` | string | Yes | muID of the new campus lead (must be a non-alumni member of the same college) |

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Assigned new Campus Lead successfully"] },
  "response": {}
}
```

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["Required data is missing"] } }
{ "hasError": true, "statusCode": 400, "message": { "general": ["Can't find the user"] } }
{ "hasError": true, "statusCode": 400, "message": { "general": ["Can't find the user in your college"] } }
```

---

## 11. Transfer Enabler Role

**`POST /api/dashboard/campus/transfer-enabler-role/`**

Assigns the `Lead Enabler` role to a student, replacing the current enabler if one exists.

**Roles:** `Campus Lead` only

**Request Body:**
```json
{
  "new_enabler_muid": "priya-nair@mulearn"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `new_enabler_muid` | string | Yes | muID of the new enabler (must be a non-alumni member of the same college) |

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Assigned new Enabler Lead successfully"] },
  "response": {}
}
```

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["Can't find the user in your college"] } }
```

---

## 12. Transfer IG Role

### `GET /api/dashboard/campus/transfer-ig-role/`

Returns a list of IG codes that have active members in the campus.

**Roles:** `Campus Lead`, `Lead Enabler`

**Request Body:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "ig_list": ["python", "webdev", "aiml", null]
  }
}
```

---

### `POST /api/dashboard/campus/transfer-ig-role/`

Assigns the campus IG lead role for a specific Interest Group to a student, replacing the current IG lead.

**Roles:** `Campus Lead`, `Lead Enabler`

**Request Body:**
```json
{
  "new_ig_muid": "arun-dev@mulearn",
  "ig_code": "python"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `new_ig_muid` | string | Yes | muID of the new IG campus lead |
| `ig_code` | string | Yes | Code of the Interest Group (e.g. `"python"`, `"webdev"`) |

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Assigned new Ig lead successfully"] },
  "response": {}
}
```

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["Can't find the role"] } }
{ "hasError": true, "statusCode": 400, "message": { "general": ["Can't find the user in your college"] } }
```

---

## 13. Events

**`GET /api/dashboard/campus/events/`**

Returns a paginated list of all campus-scoped and campus-IG-scoped live events for the authenticated lead's campus.

**Roles:** `Campus Lead`, `Lead Enabler`

**Query Params:**

| Param | Type | Description |
|-------|------|-------------|
| `status` | string | Filter by event status (e.g. `"live"`, `"completed"`) |
| `scope` | string | Filter by scope (`"campus"`, `"campus_ig"`) |
| `event_type` | string | Filter by organiser type |
| `date_from` | date | Events starting on or after this date (`YYYY-MM-DD`) |
| `date_to` | date | Events starting on or before this date (`YYYY-MM-DD`) |
| `pageIndex` | integer | Page number |
| `perPage` | integer | Items per page |
| `sortBy` | string | `start_datetime` or `interest_count` |

**Request Body:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "data": [
      {
        "id": "evt-uuid",
        "title": "Python Bootcamp",
        "status": "live",
        "scope": "campus",
        "organiser_type": "internal",
        "start_datetime": "2024-04-01T09:00:00Z",
        "end_datetime": "2024-04-01T17:00:00Z",
        "venue_type": "offline",
        "venue_city": "Kochi",
        "interest_count": 45,
        "cover_image": "https://...",
        "tags": ["python", "bootcamp"]
      }
    ],
    "pagination": {
      "count": 12,
      "totalPages": 1,
      "isFirst": true,
      "isLast": true
    }
  }
}
```

---

## 14. Events Distribution

**`GET /api/dashboard/campus/events/distribution/`**

Returns ranked tag distribution across all campus events (how many events have each tag).

**Roles:** `Campus Lead`, `Lead Enabler`

**Request Body:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "data": [
      { "tag": "python", "event_count": 8 },
      { "tag": "hackathon", "event_count": 5 },
      { "tag": "webdev", "event_count": 3 }
    ]
  }
}
```

---

## 15. Execom

### `GET /api/dashboard/campus/execom/`

Lists all execom role holders (Campus Lead, Lead Enabler, and IG Campus Leads) in the current campus.

**Roles:** `Campus Lead`, `Lead Enabler`

**Request Body:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "data": [
      {
        "user_id": "a1b2c3d4-...",
        "full_name": "Arjun Menon",
        "muid": "arjun-menon@mulearn",
        "profile_pic": "https://be.mulearn.org/media/user/profile/a1b2c3d4.png",
        "role_title": "Campus Lead",
        "ig_name": null
      },
      {
        "user_id": "b2c3d4e5-...",
        "full_name": "Arun Dev",
        "muid": "arun-dev@mulearn",
        "profile_pic": null,
        "role_title": "python CampusLead",
        "ig_name": "python"
      }
    ]
  }
}
```

---

### `POST /api/dashboard/campus/execom/`

Appoints a campus member to an execom role (replaces any existing holder of that role in the campus).

**Roles:** `Campus Lead` only

**Request Body:**
```json
{
  "muid": "arun-dev@mulearn",
  "role_title": "Campus Lead"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `muid` | string | Yes | muID of the member to appoint |
| `role_title` | string | Yes | Role to assign. Allowed: `"Campus Lead"`, `"Lead Enabler"`, or any `"<ig_code> CampusLead"` |

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Role assigned successfully"] },
  "response": {}
}
```

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["Invalid role"] } }
{ "hasError": true, "statusCode": 400, "message": { "general": ["muid and role_title are required"] } }
{ "hasError": true, "statusCode": 400, "message": { "general": ["User is not a member of your campus"] } }
```

---

## 16. `execom/<member_id>/`

**`DELETE /api/dashboard/campus/execom/<member_id>/`**

Removes an execom role link by the `UserRoleLink` ID. A Campus Lead cannot remove their own lead role this way.

**Roles:** `Campus Lead` only

**Path Params:**
- `member_id` *(string)* — UUID of the `UserRoleLink` record (not the user ID)

**Request Body:** None

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Role removed successfully"] },
  "response": {}
}
```

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["Role link not found or not part of this campus"] } }
{ "hasError": true, "statusCode": 400, "message": { "general": ["Cannot remove your own Campus Lead role. Use transfer-lead-role instead."] } }
```

---

## 17. IG Chapters

### `GET /api/dashboard/campus/ig-chapters/`

Returns all active IG chapters registered for the authenticated user's campus, including member count and lead info.

**Roles:** `Campus Lead`, `Lead Enabler`

**Request Body:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": [
    {
      "id": "chapter-uuid",
      "ig_id": "ig-uuid",
      "ig_name": "Python",
      "ig_code": "python",
      "ig_icon": "🐍",
      "lead_id": "user-uuid",
      "lead_name": "Arun Dev",
      "description": "Our campus Python chapter",
      "is_active": true,
      "campus_ig_member_count": 24
    }
  ]
}
```

---

### `POST /api/dashboard/campus/ig-chapters/`

Creates a new IG chapter for the campus. Only one active chapter per IG is allowed per campus.

**Roles:** `Campus Lead`, `Lead Enabler`

**Request Body:**
```json
{
  "ig": "ig-uuid",
  "description": "Our campus Python chapter",
  "lead": "user-uuid"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ig` | string (UUID) | Yes | UUID of the Interest Group |
| `description` | string | No | Short description of the chapter |
| `lead` | string (UUID) | No | UUID of the user to appoint as IG chapter lead (must be a non-alumni campus member) |

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["IG Chapter created successfully"] },
  "response": {}
}
```

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "ig": ["An active IG chapter already exists for this campus and IG."] } }
{ "hasError": true, "statusCode": 400, "message": { "lead": ["The lead must be a member of this campus."] } }
```

---

## 18. `ig-chapters/<chapter_id>/`

### `PATCH /api/dashboard/campus/ig-chapters/<chapter_id>/`

Partially updates an existing IG chapter (description, lead, or active status).

**Roles:** `Campus Lead`, `Lead Enabler`

**Path Params:**
- `chapter_id` *(string)* — UUID of the IG chapter

**Request Body** *(all fields optional):*
```json
{
  "description": "Updated description",
  "lead": "new-user-uuid",
  "is_active": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string | No | Updated chapter description |
| `lead` | string (UUID) | No | UUID of the new lead (must be a campus member) |
| `is_active` | boolean | No | Activate or deactivate the chapter |

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["IG Chapter updated successfully"] },
  "response": {}
}
```

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["IG Chapter not found"] } }
```

---

### `DELETE /api/dashboard/campus/ig-chapters/<chapter_id>/`

Soft-deletes an IG chapter (sets `is_active = false`). Also removes the IG campus lead role from the chapter lead.

**Roles:** `Campus Lead`, `Lead Enabler`

**Path Params:**
- `chapter_id` *(string)* — UUID of the IG chapter

**Request Body:** None

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["IG Chapter deleted successfully"] },
  "response": {}
}
```

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["IG Chapter not found"] } }
```

---

## 19. Social Links

### `PUT /api/dashboard/campus/social-links/`

Creates or updates (upsert) a social media link for the campus. Only one link per platform is stored — sending `PUT` for an existing platform updates its URL.

**Roles:** `Campus Lead`, `Lead Enabler`

**Request Body:**
```json
{
  "platform": "instagram",
  "url": "https://instagram.com/example_campus"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `platform` | string | Yes | One of: `instagram`, `linkedin`, `twitter`, `facebook`, `youtube`, `discord`, `github`, `website`, `other` |
| `url` | string (URL) | Yes | Full URL of the social profile/page |

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Social link saved successfully"] },
  "response": {}
}
```

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "platform": ["Invalid platform. Must be one of: instagram, linkedin, twitter, ..."] } }
```

---

## 20. `social-links/<link_id>/`

### `DELETE /api/dashboard/campus/social-links/<link_id>/`

Permanently deletes a social media link belonging to the campus.

**Roles:** `Campus Lead`, `Lead Enabler`

**Path Params:**
- `link_id` *(string)* — UUID of the `CampusSocialLink` record

**Request Body:** None

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Social link deleted successfully"] },
  "response": {}
}
```

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["Social link not found"] } }
```

---

## 21. `<org_id>/leaderboard/`

**`GET /api/dashboard/campus/<org_id>/leaderboard/`**

Returns a paginated, ranked leaderboard of all students in the specified campus, with optional filters.

**Path Params:**
- `org_id` *(string)* — UUID of the college organisation

**Query Params:**

| Param | Type | Description |
|-------|------|-------------|
| `pass_out_year` | string | Filter by graduation year (e.g. `"2025"`) |
| `ig_id` | string | Filter by IG UUID |
| `category` | string | Filter by IG category |
| `is_alumni` | `"true"` / `"false"` | Filter by alumni status |
| `search` | string | Search by full name or muID |
| `pageIndex` | integer | Page number |
| `perPage` | integer | Items per page |
| `sortBy` | string | `full_name`, `muid`, `karma`, `level`, `join_date`, `graduation_year`, `is_alumni` |

**Request Body:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "data": [
      {
        "user_id": "a1b2c3d4-...",
        "full_name": "Rahul Krishna",
        "muid": "rahul-krishna@mulearn",
        "karma": 3400,
        "rank": 1,
        "level": "Pathfinder",
        "join_date": "2023-08-01T10:00:00Z",
        "last_karma_gained": "2024-03-10T14:30:00Z",
        "department": "Computer Science",
        "graduation_year": "2025",
        "is_alumni": false,
        "ig_count": 3
      }
    ],
    "pagination": {
      "count": 312,
      "totalPages": 16,
      "isFirst": true,
      "isLast": false
    }
  }
}
```

> ⚠️ **Note:** This endpoint currently has a bug — `CampusLeaderboardSerializer` is not yet defined and will raise an error.

---

## 22. `<org_id>/karma-by-cluster/`

**`GET /api/dashboard/campus/<org_id>/karma-by-cluster/`**

Returns total karma and member count grouped by Interest Group category for the specified campus.

**Path Params:**
- `org_id` *(string)* — UUID of the college organisation

**Request Body:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "technology": {
      "total_karma": 28400,
      "member_count": 145
    },
    "design": {
      "total_karma": 9200,
      "member_count": 62
    },
    "unclustered": {
      "total_karma": 7600,
      "member_count": 105
    }
  }
}
```

> Members with no IG are grouped under `"unclustered"`.

---

## 23. Campus List

**`GET /api/dashboard/campus/campus-list/`**

Returns a simplified, paginated list of all active campuses, intended for dropdown menus or global selectors.

**Roles:** Any authenticated user.

**Request Body:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "data": [
      {
        "id": "82e6f245-59ea-4be4-a33d-35189a395000",
        "title": "Example College of Engineering",
        "code": "ECE001"
      }
    ],
    "pagination": {
      "count": 450,
      "totalPages": 23,
      "isFirst": true,
      "isLast": false
    }
  }
}
```
