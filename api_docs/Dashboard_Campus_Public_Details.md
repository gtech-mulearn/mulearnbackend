# Public Campus Details API Documentation

---

## 1. Get Campus Details by ID

### [GET] /api/v1/dashboard/campus/{org_id}/

**Status:** IMPLEMENTED (Extended with Social Links)

**Purpose:**
Retrieves the public profile for a specific campus/college. This endpoint has been extended to include the campus's official social media links. It is publicly accessible to any authenticated user across the platform.

**Roles:**
- Authenticated user (any role)

**Constraints:**
- The requested `org_id` must validly exist as a College organization.

**Authentication:**
Bearer token (JWT) required.

### Request Parameters

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `org_id`  | string (UUID) | Yes | Identifier of the campus organization |

### Request Body
None

### Response Body

**Success Response (200 OK):**

Structure:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["string"]
  },
  "response": {
    "college_name": "string",
    "campus_code": "string",
    "campus_zone": "string",
    "campus_level": "integer",
    "total_karma": "integer",
    "total_members": "integer",
    "active_members": "integer",
    "rank": "integer",
    "social_links": [
      {
        "id": "string (UUID)",
        "platform": "string",
        "url": "string"
      }
    ]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `response.college_name` | string | Name of the college/campus |
| `response.campus_code` | string | The unique MULEARN campus code |
| `response.campus_zone` | string | Geographical zone of the campus |
| `response.campus_level` | integer | Active tier/level of the campus |
| `response.total_karma` | integer | Total karma amassed by members |
| `response.total_members` | integer | Total registered users at campus |
| `response.active_members` | integer | Actively engaged members in the last 6 months |
| `response.rank` | integer | Sub-platform leaderboard rank |
| `response.social_links` | array of objects | List of official social media links for the campus |
| `response.social_links[].id` | string (UUID) | Unique ID of the social link |
| `response.social_links[].platform` | string | The social media platform (e.g., `instagram`) |
| `response.social_links[].url` | string (URL) | The full link to the social profile |

Example:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Campus details fetched successfully"]
  },
  "response": {
    "college_name": "Example Engineering College",
    "campus_code": "EEC",
    "campus_zone": "Central",
    "campus_level": 2,
    "total_karma": 45000,
    "total_members": 350,
    "active_members": 120,
    "rank": 4,
    "social_links": [
      {
        "id": "e5f67890-abcd-ef12-3456-7890abcdef12",
        "platform": "instagram",
        "url": "https://instagram.com/eec_mulearn"
      },
      {
        "id": "f5f67890-abcd-ef12-3456-7890abcdef13",
        "platform": "linkedin",
        "url": "https://linkedin.com/company/eec-mulearn"
      }
    ]
  }
}
```

**Error Codes:**
- 200: Success
- 401: Unauthorized (invalid or missing token)
- 404: Not Found (organization ID does not exist)
