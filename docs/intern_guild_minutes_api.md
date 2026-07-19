# Intern Guild Minutes — API Documentation

Base path: `/api/v1/dashboard/intern/minutes/`

All endpoints require a valid **Bearer token** in the `Authorization` header.

---

## Endpoints

### 1. List All Guild Minutes

```
GET /api/v1/dashboard/intern/minutes/
```

**Access:** Intern · Intern Lead · Admin

**Query Parameters**

| Parameter | Type   | Required | Description                                    |
|-----------|--------|----------|------------------------------------------------|
| `guild`   | string | No       | Filter by guild name (e.g. `Frontend Guild`)   |
| `date`    | string | No       | Filter by exact date (`YYYY-MM-DD`)             |
| `page`    | int    | No       | Page number (default: 1)                       |
| `perPage` | int    | No       | Results per page (default: 10)                 |
| `sortBy`  | string | No       | Sort field: `date` or `guild`                  |

**Success Response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Success",
  "response": {
    "data": [
      {
        "id": "uuid",
        "guild": "Frontend Guild",
        "date": "2026-06-17",
        "title": "Daily Standup — June 17",
        "minutes": "Discussed sprint goals...",
        "created_by_name": "John Doe",
        "created_at": "2026-06-17T08:00:00Z",
        "updated_at": "2026-06-17T08:00:00Z"
      }
    ],
    "pagination": {
      "currentPage": 1,
      "totalPages": 3,
      "totalItems": 25,
      "itemsPerPage": 10
    }
  }
}
```

---

### 2. Get a Specific Guild Minute

```
GET /api/v1/dashboard/intern/minutes/<minute_id>/
```

**Access:** Intern · Intern Lead · Admin

**Path Parameter**

| Parameter   | Type   | Description               |
|-------------|--------|---------------------------|
| `minute_id` | string | UUID of the minute record |

**Success Response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Success",
  "response": {
    "id": "uuid",
    "guild": "Backend Guild",
    "date": "2026-06-17",
    "title": "Backend Sync — June 17",
    "minutes": "API review completed...",
    "created_by_name": "Jane Smith",
    "created_at": "2026-06-17T09:30:00Z",
    "updated_at": "2026-06-17T09:30:00Z"
  }
}
```

**Error Response `400`** (not found)

```json
{
  "hasError": true,
  "message": "Guild minute not found."
}
```

---

### 3. Upload Guild Minutes

```
POST /api/v1/dashboard/intern/minutes/
```

**Access:** Intern Lead · Admin

**Request Body** (`application/json`)

| Field     | Type   | Required | Description                                                                       |
|-----------|--------|----------|-----------------------------------------------------------------------------------|
| `guild`   | string | Yes      | One of: `Frontend Guild`, `Backend Guild`, `Design Guild`, `Mobile Guild`         |
| `date`    | string | Yes      | Date of the meeting (`YYYY-MM-DD`)                                                |
| `title`   | string | Yes      | Short title / heading for the minutes (max 200 chars)                             |
| `minutes` | string | Yes      | Full minutes content (plain text or markdown)                                     |

**Example Request**

```json
{
  "guild": "Frontend Guild",
  "date": "2026-06-17",
  "title": "Daily Standup — June 17",
  "minutes": "Attendees: Alice, Bob, Carol\n\n- Completed navbar redesign\n- Working on mobile responsiveness\n- Blocker: API contract not finalized"
}
```

**Success Response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Guild minutes uploaded successfully.",
  "response": {
    "id": "generated-uuid"
  }
}
```

**Error Response `400`** (validation)

```json
{
  "hasError": true,
  "response": {
    "guild": ["\"Invalid Guild\" is not a valid choice."],
    "minutes": ["Minutes content cannot be blank."]
  }
}
```

---

### 4. Update Guild Minutes

```
PUT /api/v1/dashboard/intern/minutes/<minute_id>/
```

**Access:** Intern Lead · Admin

**Path Parameter**

| Parameter   | Type   | Description               |
|-------------|--------|---------------------------|
| `minute_id` | string | UUID of the minute record |

**Request Body** — same schema as POST (all fields required)

```json
{
  "guild": "Frontend Guild",
  "date": "2026-06-17",
  "title": "Daily Standup — June 17 (revised)",
  "minutes": "Updated minutes content..."
}
```

**Success Response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Guild minutes updated successfully."
}
```

**Error Response `400`** (not found)

```json
{
  "hasError": true,
  "message": "Guild minute not found."
}
```

---

### 5. Delete Guild Minutes

```
DELETE /api/v1/dashboard/intern/minutes/<minute_id>/
```

**Access:** Intern Lead · Admin

**Path Parameter**

| Parameter   | Type   | Description               |
|-------------|--------|---------------------------|
| `minute_id` | string | UUID of the minute record |

**Success Response `200`**

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": "Guild minutes deleted successfully."
}
```

**Error Response `400`** (not found)

```json
{
  "hasError": true,
  "message": "Guild minute not found."
}
```

---

## Role Summary

| Method   | Endpoint                                              | Intern | Intern Lead | Admin |
|----------|-------------------------------------------------------|:------:|:-----------:|:-----:|
| `GET`    | `/api/v1/dashboard/intern/minutes/`                   | ✅     | ✅          | ✅    |
| `GET`    | `/api/v1/dashboard/intern/minutes/<minute_id>/`       | ✅     | ✅          | ✅    |
| `POST`   | `/api/v1/dashboard/intern/minutes/`                   | ❌     | ✅          | ✅    |
| `PUT`    | `/api/v1/dashboard/intern/minutes/<minute_id>/`       | ❌     | ✅          | ✅    |
| `DELETE` | `/api/v1/dashboard/intern/minutes/<minute_id>/`       | ❌     | ✅          | ✅    |

---

## Valid Guild Values

| Value            |
|------------------|
| `Frontend Guild` |
| `Backend Guild`  |
| `Design Guild`   |
| `Mobile Guild`   |

---

## Related Change — Manage Interns: Leave API

**Endpoint:** `GET /api/v1/dashboard/manage-interns/leave/?page=1&perPage=10`

`user_muid` has been added to each leave record in the response:

```diff
 {
   "id": "uuid",
   "user": "user-uuid",
   "user_name": "John Doe",
+  "user_muid": "johndoe@mulearn",
   "leave_type": "SICK",
   "start_date": "2026-06-18",
   "end_date": "2026-06-19",
   "reason": "Fever",
   "status": "PENDING",
   "review_note": null,
   "created_at": "2026-06-17T10:00:00Z"
 }
```
