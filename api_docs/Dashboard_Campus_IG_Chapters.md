# Campus IG Chapters API Documentation

---

## 1. List Campus IG Chapters

### [GET] /api/v1/dashboard/campus/ig-chapters/

**Status:** IMPLEMENTED

**Purpose:**
Retrieves a list of all active Interest Group (IG) chapters associated with the authenticated user's campus.

**Roles:**
- Campus Lead
- Lead Enabler

**Constraints:**
- User must have the required role
- Only returns chapters belonging to the user's organization (`status` active)

**Authentication:**
Bearer token (JWT) required.

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
  "response": [
    {
      "id": "string (UUID)",
      "ig_id": "string (UUID)",
      "ig_name": "string",
      "ig_code": "string",
      "ig_icon": "string | null",
      "lead_id": "string (UUID) | null",
      "lead_name": "string | null",
      "description": "string | null",
      "is_active": "boolean",
      "campus_ig_member_count": "integer"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `response[].id` | string (UUID) | Unique identifier for the chapter |
| `response[].ig_id` | string (UUID) | Unique identifier for the interest group |
| `response[].ig_name` | string | Name of the interest group |
| `response[].ig_code` | string | Code of the interest group |
| `response[].ig_icon` | string or null | URL to the interest group icon |
| `response[].lead_id` | string (UUID) or null | Unique identifier for the assigned chapter lead |
| `response[].lead_name` | string or null | Full name of the assigned chapter lead |
| `response[].description` | string or null | Description of the chapter |
| `response[].is_active` | boolean | Active status of the chapter |
| `response[].campus_ig_member_count` | integer | Number of members in this IG at the campus |

Example:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {},
  "response": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "ig_id": "b2c3d4e5-f678-90ab-cdef-1234567890ab",
      "ig_name": "Web Development",
      "ig_code": "WEB",
      "ig_icon": "https://mulearn.org/icon.png",
      "lead_id": "c3d4e5f6-7890-abcd-ef12-34567890abcd",
      "lead_name": "John Doe",
      "description": "Learn web development",
      "is_active": true,
      "campus_ig_member_count": 42
    }
  ]
}
```

**Error Response (401 / 403 / 404):**
Returns standard error formatted responses for missing organization or invalid permissions.

**Error Codes:**
- 200: Success
- 401: Unauthorized (invalid token)
- 403: Forbidden (insufficient role)
- 404: User have no organization

---

## 2. Create Campus IG Chapter

### [POST] /api/v1/dashboard/campus/ig-chapters/

**Status:** IMPLEMENTED

**Purpose:**
Creates a new Interest Group chapter at the authenticated user's campus. It can optionally assign a user as the chapter lead.

**Roles:**
- Campus Lead
- Lead Enabler

**Constraints:**
- Only one active chapter per IG per campus is permitted
- If a `lead` is provided, that user must be a member of the campus
- The newly created chapter lead will be automatically assigned the `{ig_code} CampusLead` role
- User must have the required role

**Authentication:**
Bearer token (JWT) required.

### Request Body

**Content-Type:** application/json

| Parameter | Type | Required | Max Length | Description |
|-----------|------|----------|------------|-------------|
| `ig` | string (UUID) | Yes | 36 | Interest Group ID |
| `lead` | string (UUID) | No | 36 | User ID of the chapter lead |
| `description` | string | No | - | Brief description of the chapter |

**Example Request:**
```json
{
  "ig": "b2c3d4e5-f678-90ab-cdef-1234567890ab",
  "lead": "c3d4e5f6-7890-abcd-ef12-34567890abcd",
  "description": "Official Web Dev chapter for our campus"
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
    "general": ["IG Chapter created successfully"]
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
    "ig": ["An active chapter for this IG already exists in your campus."]
  },
  "response": {}
}
```

**Error Codes:**
- 200: Success
- 400: Bad Request (validation failure, duplicate chapter, user not in campus)
- 401: Unauthorized (invalid token)
- 403: Forbidden (insufficient role)
- 404: User have no organization

---

## 3. Update Campus IG Chapter

### [PATCH] /api/v1/dashboard/campus/ig-chapters/{chapter_id}/

**Status:** IMPLEMENTED

**Purpose:**
Updates an existing IG chapter. Allows modification of description, active status, and the chapter lead.

**Roles:**
- Campus Lead
- Lead Enabler

**Constraints:**
- User must have the required role
- Target chapter must belong to the user's campus
- If the `lead` is changed, the new lead must be in the campus
- Role `{ig_code} CampusLead` is automatically revoked from the old lead and granted to the new lead

**Authentication:**
Bearer token (JWT) required.

### Request Parameters

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chapter_id` | string (UUID) | Yes | Identifier of the IG chapter |

### Request Body

**Content-Type:** application/json

| Parameter | Type | Required | Max Length | Description |
|-----------|------|----------|------------|-------------|
| `lead` | string (UUID) or null | No | 36 | New user ID for lead, or null to clear |
| `description` | string | No | - | Updated description |
| `is_active` | boolean | No | - | Enable or disable the chapter |

**Example Request:**
```json
{
  "lead": "d4e5f678-90ab-cdef-1234-567890abcdef",
  "description": "Updated Web Dev chapter description"
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
    "general": ["IG Chapter updated successfully"]
  },
  "response": {}
}
```

**Error Codes:**
- 200: Success
- 400: Bad Request (validation failure, user not in campus)
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found (chapter not found or user lacks organization)

---

## 4. Delete Campus IG Chapter

### [DELETE] /api/v1/dashboard/campus/ig-chapters/{chapter_id}/

**Status:** IMPLEMENTED

**Purpose:**
Soft-deletes a campus IG chapter. It deactivates the chapter by setting `is_active=False`, clears the lead, and revokes the associated `{ig_code} CampusLead` role.

**Roles:**
- Campus Lead
- Lead Enabler

**Constraints:**
- User must have the required role
- Chapter must belong to the user's campus

**Authentication:**
Bearer token (JWT) required.

### Request Parameters

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chapter_id` | string (UUID) | Yes | Identifier of the IG chapter to delete |

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
    "general": ["IG Chapter deleted successfully"]
  },
  "response": {}
}
```

**Error Codes:**
- 200: Success
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found (chapter not found or user lacks organization)
