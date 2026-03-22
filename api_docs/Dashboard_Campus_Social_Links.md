# Campus Social Links API Documentation

---

## 1. Upsert Campus Social Link

### [PUT] /api/v1/dashboard/campus/social-links/

**Status:** IMPLEMENTED

**Purpose:**
Creates or updates a social media link for the authenticated user's campus. If a link for the specified platform already exists for the campus, it will be updated with the new URL. Otherwise, a new link will be created.

**Roles:**
- Campus Lead
- Lead Enabler

**Constraints:**
- User must have the required role
- Only one link per platform per campus is permitted
- The `platform` must be one of the supported social platforms

**Authentication:**
Bearer token (JWT) required.

### Request Body

**Content-Type:** application/json

| Parameter | Type | Required | Max Length | Description |
|-----------|------|----------|------------|-------------|
| `platform` | string (enum) | Yes | 20 | The social media platform (e.g., `instagram`, `linkedin`, `twitter`, `facebook`, `youtube`, `github`, `website`) |
| `url` | string | Yes | 500 | The full URL to the campus social media page |

**Example Request:**
```json
{
  "platform": "instagram",
  "url": "https://instagram.com/mulearn_campus"
}
```

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
  "response": {}
}
```

Example:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Social link saved successfully"]
  },
  "response": {}
}
```

**Error Response (400 Bad Request):**

Example:
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "platform": ["Invalid platform."]
  },
  "response": {}
}
```

**Error Codes:**
- 200: Success
- 400: Bad Request (validation failure, invalid platform)
- 401: Unauthorized (invalid token)
- 403: Forbidden (insufficient role)
- 404: User have no organization

---

## 2. Delete Campus Social Link

### [DELETE] /api/v1/dashboard/campus/social-links/{link_id}/

**Status:** IMPLEMENTED

**Purpose:**
Hard-deletes a specific campus social link. The social link record is permanently removed from the database.

**Roles:**
- Campus Lead
- Lead Enabler

**Constraints:**
- User must have the required role
- Target social link must belong to the user's campus

**Authentication:**
Bearer token (JWT) required.

### Request Parameters

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `link_id` | string (UUID) | Yes | Identifier of the social link to delete |

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
  "response": {}
}
```

Example:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Social link deleted successfully"]
  },
  "response": {}
}
```

**Error Response (404 Not Found):**

Example:
```json
{
  "hasError": true,
  "statusCode": 404,
  "message": {
    "general": ["Social link not found"]
  },
  "response": {}
}
```

**Error Codes:**
- 200: Success
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found (social link not found or user lacks organization)
