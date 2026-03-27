# Dashboard — Zonal API

**Base path:** `/api/dashboard/zonal/`  
**Authentication:** JWT Bearer Token required on all endpoints.

---

## Table of Contents

| # | Endpoint | Method | Auth / Role |
|---|----------|--------|-------------|
| 1 | [`zonal-details/`](#1-zonal-details) | `GET` | Zonal Campus Lead |
| 2 | [`top-districts/`](#2-top-districts) | `GET` | Zonal Campus Lead |
| 3 | [`student-level/`](#3-student-level) | `GET` | Zonal Campus Lead |
| 4 | [`student-details/`](#4-student-details) | `GET` | Zonal Campus Lead |
| 5 | [`student-details/csv/`](#5-student-detailscsv) | `GET` | Zonal Campus Lead |
| 6 | [`college-details/`](#6-college-details) | `GET` | Zonal Campus Lead |
| 7 | [`college-details/csv/`](#7-college-detailscsv) | `GET` | Zonal Campus Lead |

---

## 1. Zonal Details

**`GET /api/dashboard/zonal/zonal-details/`**

Returns detailed information about the authenticated Zonal Campus Lead's zone, including rank, lead name, karma stats, and membership counts.

**Roles:** `Zonal Campus Lead`

**Request Body:** None

**Query Params:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "zone": "Central Zone",
    "rank": 1,
    "zonal_lead": "Priya Nair",
    "karma": 385000,
    "total_members": 4200,
    "active_members": 1850
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `zone` | string | Name of the zone |
| `rank` | integer | Zone rank across all zones (by total karma) |
| `zonal_lead` | string | Full name of the authenticated Zonal Campus Lead |
| `karma` | integer | Total karma earned by all college members in the zone |
| `total_members` | integer | Total number of college org links in the zone |
| `active_members` | integer | Members with karma activity in the current month |

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["No college organization linked to this user."] } }
```

---

## 2. Top Districts

**`GET /api/dashboard/zonal/top-districts/`**

Returns the top 3 districts in the zone by total karma.

**Roles:** `Zonal Campus Lead`

**Request Body:** None

**Query Params:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": [
    {
      "district": "Ernakulam",
      "rank": 1,
      "karma": 128500
    },
    {
      "district": "Thrissur",
      "rank": 2,
      "karma": 105200
    },
    {
      "district": "Kottayam",
      "rank": 3,
      "karma": 87300
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `district` | string | Name of the district |
| `rank` | integer | Rank of the district within the zone |
| `karma` | integer | Total karma of all verified college members in the district |

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["No college organization linked to this user."] } }
```

---

## 3. Student Level

**`GET /api/dashboard/zonal/student-level/`**

Returns the count of students at each karma level across all colleges in the zone.

**Roles:** `Zonal Campus Lead`

**Request Body:** None

**Query Params:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": [
    { "level_order": 1, "students_count": 1800 },
    { "level_order": 2, "students_count": 980 },
    { "level_order": 3, "students_count": 520 },
    { "level_order": 4, "students_count": 190 },
    { "level_order": 5, "students_count": 35 }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `level_order` | integer | The level number |
| `students_count` | integer | Number of distinct students at this level in the zone |

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["No college organization linked to this user."] } }
```

---

## 4. Student Details

**`GET /api/dashboard/zonal/student-details/`**

Returns a paginated list of all students across colleges in the zone with their karma, level, and rank.

**Roles:** `Zonal Campus Lead`

**Query Params:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `pageIndex` | integer | No | Page number (default: 1) |
| `perPage` | integer | No | Items per page (default: 20) |
| `sortBy` | string | No | Field to sort by (`full_name`, `muid`, `karma`, `level`) |
| `search` | string | No | Search by full name or level |

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
        "level": "Pathfinder"
      }
    ],
    "pagination": {
      "count": 4200,
      "totalPages": 210,
      "isFirst": true,
      "isLast": false,
      "nextPage": "/student-details/?pageIndex=2"
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | string (UUID) | Unique user ID |
| `full_name` | string | Student's full name |
| `muid` | string | muID of the student |
| `karma` | integer | Total karma points |
| `rank` | integer | Rank within the zone |
| `level` | string | Current karma level name |

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["No college organization linked to this user."] } }
```

---

## 5. Student Details CSV

**`GET /api/dashboard/zonal/student-details/csv/`**

Downloads the same student data as endpoint 4 as a CSV file (no pagination — exports all records).

**Roles:** `Zonal Campus Lead`

**Request Body:** None

**Response:** `text/csv` file download — `Zonal Student Details.csv`

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["No college organization linked to this user."] } }
```

---

## 6. College Details

**`GET /api/dashboard/zonal/college-details/`**

Returns a paginated list of all colleges in the zone, including their campus code, level, and campus lead information.

**Roles:** `Zonal Campus Lead`

**Query Params:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `pageIndex` | integer | No | Page number (default: 1) |
| `perPage` | integer | No | Items per page (default: 20) |
| `sortBy` | string | No | Field to sort by (`title`, `code`) |
| `search` | string | No | Search by college title or code |

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
        "code": "ECE001",
        "level": 3,
        "lead": "Arjun Menon",
        "lead_number": "9876543210"
      }
    ],
    "pagination": {
      "count": 120,
      "totalPages": 6,
      "isFirst": true,
      "isLast": false,
      "nextPage": "/college-details/?pageIndex=2"
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Unique organization ID of the college |
| `title` | string | Name of the college |
| `code` | string | Campus code |
| `level` | integer \| null | College's campus level |
| `lead` | string \| null | Full name of the college's Campus Lead |
| `lead_number` | string \| null | Mobile number of the Campus Lead |

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["No college organization linked to this user."] } }
```

---

## 7. College Details CSV

**`GET /api/dashboard/zonal/college-details/csv/`**

Downloads the same college data as endpoint 6 as a CSV file (no pagination — exports all records).

**Roles:** `Zonal Campus Lead`

**Request Body:** None

**Response:** `text/csv` file download — `Zonal College Details.csv`

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["No college organization linked to this user."] } }
```
