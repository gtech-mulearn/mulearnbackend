# Dashboard — District API

**Base path:** `/api/dashboard/district/`  
**Authentication:** JWT Bearer Token required on all endpoints.

---

## Table of Contents

| # | Endpoint | Method | Auth / Role |
|---|----------|--------|-------------|
| 1 | [`district-details/`](#1-district-details) | `GET` | District Campus Lead |
| 2 | [`top-campus/`](#2-top-campus) | `GET` | District Campus Lead |
| 3 | [`student-level/`](#3-student-level) | `GET` | District Campus Lead |
| 4 | [`student-details/`](#4-student-details) | `GET` | District Campus Lead |
| 5 | [`student-details/csv/`](#5-student-detailscsv) | `GET` | District Campus Lead |
| 6 | [`college-details/`](#6-college-details) | `GET` | District Campus Lead |
| 7 | [`college-details/csv/`](#7-college-detailscsv) | `GET` | District Campus Lead |

---

## 1. District Details

**`GET /api/dashboard/district/district-details/`**

Returns detailed information about the authenticated District Campus Lead's district, including the zone, lead name, karma stats, and membership counts.

**Roles:** `District Campus Lead`

**Request Body:** None

**Query Params:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "district": "Ernakulam",
    "zone": "Central Zone",
    "rank": 2,
    "district_lead": "Arjun Menon",
    "karma": 128500,
    "total_members": 1450,
    "active_members": 620
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `district` | string | Name of the district |
| `zone` | string | Name of the zone the district belongs to |
| `rank` | integer | District rank across all districts (by total karma) |
| `district_lead` | string \| null | Full name of the District Campus Lead |
| `karma` | integer | Total karma earned by all college members in the district |
| `total_members` | integer | Total number of college org links in the district |
| `active_members` | integer | Members with karma activity in the current month |

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["No college organization linked to this user."] } }
```

---

## 2. Top Campus

**`GET /api/dashboard/district/top-campus/`**

Returns the top 3 campuses (colleges) in the district by total karma.

**Roles:** `District Campus Lead`

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
      "rank": 1,
      "campus_code": "ECE001",
      "karma": 45200
    },
    {
      "rank": 2,
      "campus_code": "SCT002",
      "karma": 38100
    },
    {
      "rank": 3,
      "campus_code": "MES003",
      "karma": 29800
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `rank` | integer | Rank of the campus within the district |
| `campus_code` | string | Unique code of the college/campus |
| `karma` | integer | Total karma of all verified members in the campus |

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["No college organization linked to this user."] } }
```

---

## 3. Student Level

**`GET /api/dashboard/district/student-level/`**

Returns the count of students at each karma level across all colleges in the district.

**Roles:** `District Campus Lead`

**Request Body:** None

**Query Params:** None

**Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": [
    { "level_order": 1, "students_count": 520 },
    { "level_order": 2, "students_count": 340 },
    { "level_order": 3, "students_count": 180 },
    { "level_order": 4, "students_count": 65 },
    { "level_order": 5, "students_count": 12 }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `level_order` | integer | The level number |
| `students_count` | integer | Number of distinct students at this level in the district |

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["No college organization linked to this user."] } }
```

---

## 4. Student Details

**`GET /api/dashboard/district/student-details/`**

Returns a paginated list of all students across colleges in the district with their karma, level, and rank.

**Roles:** `District Campus Lead`

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
      "count": 1450,
      "totalPages": 73,
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
| `rank` | integer | Rank within the district |
| `level` | string | Current karma level name |

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["No college organization linked to this user."] } }
```

---

## 5. Student Details CSV

**`GET /api/dashboard/district/student-details/csv/`**

Downloads the same student data as endpoint 4 as a CSV file (no pagination — exports all records).

**Roles:** `District Campus Lead`

**Request Body:** None

**Response:** `text/csv` file download — `District Student Details.csv`

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["No college organization linked to this user."] } }
```

---

## 6. College Details

**`GET /api/dashboard/district/college-details/`**

Returns a paginated list of all colleges in the district, including their campus code, level, and campus lead information.

**Roles:** `District Campus Lead`

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
      "count": 42,
      "totalPages": 3,
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

**`GET /api/dashboard/district/college-details/csv/`**

Downloads the same college data as endpoint 6 as a CSV file (no pagination — exports all records).

**Roles:** `District Campus Lead`

**Request Body:** None

**Response:** `text/csv` file download — `District College Details.csv`

**Error Responses:**
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["No college organization linked to this user."] } }
```
