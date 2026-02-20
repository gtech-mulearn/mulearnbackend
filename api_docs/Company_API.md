# Company API Documentation

## Database Schema

### Company Table
```sql
CREATE TABLE `company` (
  `id` VARCHAR(36) NOT NULL,
  `company_user_id` VARCHAR(36) NOT NULL,
  `name` VARCHAR(75) NOT NULL,
  `logo` TEXT,
  `description` TEXT NOT NULL,
  `industry_sector` VARCHAR(75),
  `website_link` TEXT,
  `email` VARCHAR(100),
  `slug` VARCHAR(100) NOT NULL,
  `status` ENUM('pending', 'active', 'inactive') NOT NULL DEFAULT 'pending',
  `location` VARCHAR(150),
  `created_at` DATETIME NOT NULL,
  `updated_at` DATETIME NOT NULL,
  `deleted_at` DATETIME,
  `updated_by` VARCHAR(36),
  `deleted_by` VARCHAR(36),
  
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `slug` (`slug`),
  CONSTRAINT `fk_company_user_id`
    FOREIGN KEY (`company_user_id`)
    REFERENCES `user`(`id`)
    ON DELETE CASCADE
);
```

---

## 1. Create Company (Onboarding)

### [POST] /api/v1/register/company/create/

**Status:** IMPLEMENTED

**Purpose:**
Creates a new company profile during user onboarding. This endpoint is used when a user selects "Not a student" and chooses "Company" as their organization type. The endpoint automatically assigns the "Company" role to the user upon successful creation. The company is created with `status='pending'` and must be approved by an admin before it becomes publicly visible.

**Roles:**
- Authenticated user (any role)

**Constraints:**
- One company per user (enforced at database level)
- Company name must be unique across the platform
- User must provide valid JWT token
- Slug is auto-generated from company name with collision handling

**Authentication:**
Bearer token (JWT) required in Authorization header.

### Request Body

**Content-Type:** application/json

| Parameter | Type | Required | Max Length | Description |
|-----------|------|----------|------------|-------------|
| `name` | string | Yes | 75 | Company name. Must be unique. Used to generate slug. |
| `description` | string | Yes | 500 | Company description. Brief overview of the company. |
| `industry_sector` | string | No | 75 | Industry category. Examples: "Education", "Technology", "Healthcare". |
| `website_link` | string (URL) | No | 255 | Company website URL. Must be valid URL format. |
| `email` | string (email) | No | 255 | Company contact email. Must be valid email format. |
| `location` | string | No | 255 | Company location. Can be city, country, or "Remote". |

**Example Request:**
```json
{
  "name": "Acme Technologies",
  "description": "EdTech company focused on skill-based hiring",
  "industry_sector": "Education",
  "website_link": "https://acmetech.com",
  "email": "contact@acmetech.com",
  "location": "Remote"
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
  "response": {
    "company_id": "string (UUID)",
    "name": "string",
    "slug": "string"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `hasError` | boolean | Always false for success responses |
| `statusCode` | integer | HTTP status code (200) |
| `message.general` | array of strings | Success message |
| `response.company_id` | string (UUID) | Unique identifier for the created company |
| `response.name` | string | Company name as provided |
| `response.slug` | string | Auto-generated URL-friendly slug |

Example:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Company created successfully"]
  },
  "response": {
    "company_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "Acme Technologies",
    "slug": "acme-technologies"
  }
}
```

**Error Response (400 Bad Request - Duplicate Company):**

Structure:
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": ["string"]
  },
  "response": {}
}
```

Example:
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": ["Company already exists for this user"]
  },
  "response": {}
}
```

**Error Response (400 Bad Request - Validation Error):**

Structure:
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": ["string"],
    "field_name": ["string"]
  },
  "response": {}
}
```

Example:
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": ["Validation failed"],
    "name": ["This field is required."],
    "description": ["This field is required."]
  },
  "response": {}
}
```

**Error Response (401 Unauthorized):**

```json
{
  "hasError": true,
  "statusCode": 401,
  "message": {
    "general": ["Unauthorized access"]
  },
  "response": {}
}
```

**Error Codes:**
- 200: Success
- 400: Bad Request (validation error or duplicate company)
- 401: Unauthorized (invalid or missing token)
- 500: Internal Server Error

---

## 2. Get Company by Slug (Public)

### [GET] /api/v1/dashboard/company/<slug>/

**Status:** IMPLEMENTED

**Purpose:**
Retrieves public company profile information using the company slug. This endpoint is publicly accessible and does not require authentication. It allows anyone to view active company profiles on the platform.

**Roles:**
- Public (no authentication required)

**Constraints:**
- Only returns companies with `status='active'` AND `deleted_at IS NULL`
- Companies with `status='pending'` are NOT returned (awaiting admin approval)
- Companies with `status='inactive'` are NOT returned (deactivated)

**Authentication:**
None required.

### Request Parameters

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `slug` | string | Yes | Company slug (URL-friendly identifier). Example: "acme-technologies" |

**Example Request:**
```
GET /api/v1/dashboard/company/acme-technologies/
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
  "response": {
    "id": "string (UUID)",
    "company_user_id": "string (UUID)",
    "name": "string",
    "slug": "string",
    "logo": "string | null",
    "description": "string",
    "industry_sector": "string | null",
    "website_link": "string | null",
    "email": "string | null",
    "location": "string | null",
    "status": "string (enum)",
    "created_at": "string (ISO 8601 datetime)",
    "updated_at": "string (ISO 8601 datetime)"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `response.id` | string (UUID) | Unique company identifier |
| `response.company_user_id` | string (UUID) | User ID of company owner |
| `response.name` | string | Company name |
| `response.slug` | string | URL-friendly slug |
| `response.logo` | string or null | Logo URL or null if not set |
| `response.description` | string | Company description |
| `response.industry_sector` | string or null | Industry category |
| `response.website_link` | string or null | Company website URL |
| `response.email` | string or null | Contact email |
| `response.location` | string or null | Company location |
| `response.status` | string | Status enum: "pending", "active", "inactive" (only "active" returned by this endpoint) |
| `response.created_at` | string (ISO 8601) | Creation timestamp |
| `response.updated_at` | string (ISO 8601) | Last update timestamp |

Example:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Company profile retrieved successfully"]
  },
  "response": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "company_user_id": "user-uuid-here",
    "name": "Acme Technologies",
    "slug": "acme-technologies",
    "logo": null,
    "description": "EdTech company focused on skill-based hiring",
    "industry_sector": "Education",
    "website_link": "https://acmetech.com",
    "email": "contact@acmetech.com",
    "location": "Remote",
    "status": "active",
    "created_at": "2026-01-15T10:30:00Z",
    "updated_at": "2026-01-15T10:30:00Z"
  }
}
```

**Error Response (404 Not Found):**

```json
{
  "hasError": true,
  "statusCode": 404,
  "message": {
    "general": ["Company not found"]
  },
  "response": {}
}
```

**Error Codes:**
- 200: Success
- 404: Not Found (company does not exist, is pending, inactive, or soft-deleted)
- 500: Internal Server Error

---

## 3. Get Own Company Profile

### [GET] /api/v1/dashboard/company/profile/

**Status:** IMPLEMENTED

**Purpose:**
Retrieves the authenticated company user's own company profile. This endpoint is used by company users to view their complete profile information including all fields.

**Roles:**
- Company role required

**Constraints:**
- User must have "Company" role assigned
- Returns only the company associated with the authenticated user

**Authentication:**
Bearer token (JWT) required with "Company" role.

### Request Parameters

None required. User identification is extracted from JWT token.

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
    "id": "string (UUID)",
    "company_user_id": "string (UUID)",
    "name": "string",
    "slug": "string",
    "logo": "string | null",
    "description": "string",
    "industry_sector": "string | null",
    "website_link": "string | null",
    "email": "string | null",
    "location": "string | null",
    "status": "string (enum)",
    "created_at": "string (ISO 8601 datetime)",
    "updated_at": "string (ISO 8601 datetime)"
  }
}
```

Field descriptions are identical to endpoint #2 (Get Company by Slug).

Example:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Company profile retrieved successfully"]
  },
  "response": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "company_user_id": "user-uuid-here",
    "name": "Acme Technologies",
    "slug": "acme-technologies",
    "logo": null,
    "description": "EdTech company focused on skill-based hiring",
    "industry_sector": "Education",
    "website_link": "https://acmetech.com",
    "email": "contact@acmetech.com",
    "location": "Remote",
    "status": "active",
    "created_at": "2026-01-15T10:30:00Z",
    "updated_at": "2026-01-15T10:30:00Z"
  }
}
```

**Error Response (404 Not Found):**

```json
{
  "hasError": true,
  "statusCode": 404,
  "message": {
    "general": ["Company profile not found"]
  },
  "response": {}
}
```

**Error Response (403 Forbidden):**

```json
{
  "hasError": true,
  "statusCode": 403,
  "message": {
    "general": ["Access denied. Company role required."]
  },
  "response": {}
}
```

**Error Response (401 Unauthorized):**

```json
{
  "hasError": true,
  "statusCode": 401,
  "message": {
    "general": ["Unauthorized access"]
  },
  "response": {}
}
```

**Error Codes:**
- 200: Success
- 401: Unauthorized (invalid or missing token)
- 403: Forbidden (user does not have Company role)
- 404: Not Found (no company associated with user)
- 500: Internal Server Error

---

## 4. Update Company Profile

### [PUT] /api/v1/dashboard/company/profile/
### [PATCH] /api/v1/dashboard/company/profile/

**Status:** IMPLEMENTED

**Purpose:**
Updates the authenticated company user's company profile. Allows company users to modify their profile information. PUT replaces all editable fields, PATCH allows partial updates.

**Roles:**
- Company role required

**Constraints:**
- User must have "Company" role assigned
- Can only update own company profile
- Cannot modify: name, slug, status, company_user_id (these fields are immutable or admin-only)
- All editable fields are optional for PATCH requests

**Authentication:**
Bearer token (JWT) required with "Company" role.

### Request Body

**Content-Type:** application/json

| Parameter | Type | Required | Max Length | Description |
|-----------|------|----------|------------|-------------|
| `description` | string | No | 500 | Company description |
| `industry_sector` | string | No | 75 | Industry category |
| `website_link` | string (URL) | No | 255 | Company website URL |
| `email` | string (email) | No | 255 | Contact email |
| `location` | string | No | 255 | Company location |
| `logo` | string | No | - | Logo URL or file path |

**Non-Editable Fields:**
- `name` (requires admin intervention)
- `slug` (auto-generated, immutable)
- `status` (admin-only)
- `company_user_id` (immutable)

**Example Request:**
```json
{
  "description": "Updated company description",
  "industry_sector": "AI & Education",
  "website_link": "https://newdomain.com",
  "email": "newemail@acmetech.com",
  "location": "Hybrid",
  "logo": "https://cdn.acme.com/new-logo.png"
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
  "response": {
    "id": "string (UUID)",
    "name": "string",
    "description": "string",
    "industry_sector": "string | null",
    "website_link": "string | null",
    "email": "string | null",
    "location": "string | null",
    "logo": "string | null",
    "updated_at": "string (ISO 8601 datetime)"
  }
}
```

Example:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Company profile updated successfully"]
  },
  "response": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "Acme Technologies",
    "description": "Updated company description",
    "industry_sector": "AI & Education",
    "website_link": "https://newdomain.com",
    "email": "newemail@acmetech.com",
    "location": "Hybrid",
    "logo": "https://cdn.acme.com/new-logo.png",
    "updated_at": "2026-02-10T15:45:00Z"
  }
}
```

**Error Response (400 Bad Request - Validation Error):**

```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": ["Validation failed"],
    "email": ["Enter a valid email address."],
    "website_link": ["Enter a valid URL."]
  },
  "response": {}
}
```

**Error Response (404 Not Found):**

```json
{
  "hasError": true,
  "statusCode": 404,
  "message": {
    "general": ["Company profile not found"]
  },
  "response": {}
}
```

**Error Response (403 Forbidden):**

```json
{
  "hasError": true,
  "statusCode": 403,
  "message": {
    "general": ["Access denied. Company role required."]
  },
  "response": {}
}
```

**Error Response (401 Unauthorized):**

```json
{
  "hasError": true,
  "statusCode": 401,
  "message": {
    "general": ["Unauthorized access"]
  },
  "response": {}
}
```

**Error Codes:**
- 200: Success
- 400: Bad Request (validation error)
- 401: Unauthorized (invalid or missing token)
- 403: Forbidden (user does not have Company role)
- 404: Not Found (no company associated with user)
- 500: Internal Server Error

---

## 5. Admin Update Company by Slug (Admin Only)

### [PUT] /api/v1/dashboard/company/<slug>/
### [PATCH] /api/v1/dashboard/company/<slug>/

**Status:** IMPLEMENTED

**Purpose:**
Allows administrators to update any company's profile by slug. Unlike the self-service update endpoint (#4), admins can modify all fields including name, status, and other restricted fields. PUT replaces all editable fields, PATCH allows partial updates.

**Roles:**
- Admin role required

**Constraints:**
- Only users with "Admin" role can use this endpoint
- Admin can modify any company on the platform by slug
- Admin can change fields that company users cannot (name, status)
- If name is changed, slug is NOT auto-regenerated (must be handled separately or kept as-is)
- company_user_id remains immutable

**Authentication:**
Bearer token (JWT) required with "Admin" role.

### Request Parameters

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `slug` | string | Yes | Company slug to update. Example: "acme-technologies" |

### Request Body

**Content-Type:** application/json

| Parameter | Type | Required | Max Length | Description |
|-----------|------|----------|------------|-------------|
| `name` | string | No | 75 | Company name. Must be unique across platform. |
| `description` | string | No | 500 | Company description |
| `industry_sector` | string | No | 75 | Industry category |
| `website_link` | string (URL) | No | 255 | Company website URL |
| `email` | string (email) | No | 255 | Contact email |
| `location` | string | No | 255 | Company location |
| `logo` | string | No | - | Logo URL or file path |
| `status` | string (enum) | No | - | Company status. Possible values: "pending", "active", "inactive" |

**Non-Editable Fields:**
- `slug` (immutable, auto-generated)
- `company_user_id` (immutable)

**Example Request:**
```
PUT /api/v1/dashboard/company/acme-technologies/
```
```json
{
  "name": "Acme Tech Solutions",
  "status": "blocked",
  "description": "Updated by admin",
  "industry_sector": "Technology"
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
  "response": {
    "id": "string (UUID)",
    "name": "string",
    "slug": "string",
    "description": "string",
    "industry_sector": "string | null",
    "website_link": "string | null",
    "email": "string | null",
    "location": "string | null",
    "logo": "string | null",
    "status": "string (enum)",
    "updated_at": "string (ISO 8601 datetime)",
    "updated_by": "string (UUID)"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `response.id` | string (UUID) | Company identifier |
| `response.name` | string | Company name (may be changed by admin) |
| `response.slug` | string | Company slug (unchanged) |
| `response.status` | string | Current status: "pending", "active", "inactive" |
| `response.updated_at` | string (ISO 8601) | Timestamp of update |
| `response.updated_by` | string (UUID) | Admin user ID who made the change |

Example:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Company updated successfully"]
  },
  "response": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "Acme Tech Solutions",
    "slug": "acme-technologies",
    "description": "Updated by admin",
    "industry_sector": "Technology",
    "website_link": "https://acmetech.com",
    "email": "contact@acmetech.com",
    "location": "Remote",
    "logo": null,
    "status": "blocked",
    "updated_at": "2026-02-19T16:50:00Z",
    "updated_by": "admin-uuid-here"
  }
}
```

**Error Response (400 Bad Request - Validation Error):**

```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": ["Validation failed"],
    "name": ["Company with this name already exists."],
    "status": ["Invalid status. Must be one of: pending, active, inactive."]
  },
  "response": {}
}
```

**Error Response (404 Not Found):**

```json
{
  "hasError": true,
  "statusCode": 404,
  "message": {
    "general": ["Company not found"]
  },
  "response": {}
}
```

**Error Response (403 Forbidden):**

```json
{
  "hasError": true,
  "statusCode": 403,
  "message": {
    "general": ["Admin access required"]
  },
  "response": {}
}
```

**Error Response (401 Unauthorized):**

```json
{
  "hasError": true,
  "statusCode": 401,
  "message": {
    "general": ["Unauthorized access"]
  },
  "response": {}
}
```

**Error Codes:**
- 200: Success
- 400: Bad Request (validation error or duplicate name)
- 401: Unauthorized (invalid or missing token)
- 403: Forbidden (user does not have Admin role)
- 404: Not Found (company does not exist)
- 500: Internal Server Error

---

## 6. Deactivate Company (Admin Only)

### [DELETE] /api/v1/dashboard/company/<slug>/

**Status:** IMPLEMENTED

**Purpose:**
Soft-deletes (deactivates) a company profile. This is an admin-only operation used to deactivate companies that violate platform policies or are no longer active. The company data is preserved in the database but marked as inactive.

**Roles:**
- Admin role required

**Constraints:**
- Only users with "Admin" role can deactivate companies
- This is a soft delete operation (data is not removed from database)
- Sets status to 'inactive', deleted_at to current timestamp, and deleted_by to admin user ID
- Deactivated companies will not appear in public listings

**Authentication:**
Bearer token (JWT) required with "Admin" role.

### Request Parameters

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `slug` | string | Yes | Company slug to deactivate. Example: "acme-technologies" |

**Example Request:**
```
DELETE /api/v1/dashboard/company/acme-technologies/
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
  "response": {
    "slug": "string",
    "status": "string (enum)",
    "deleted_at": "string (ISO 8601 datetime)"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `response.slug` | string | Slug of the deactivated company |
| `response.status` | string | New status (always "inactive" after deletion) |
| `response.deleted_at` | string (ISO 8601) | Timestamp when company was deactivated |

Example:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Company deactivated successfully"]
  },
  "response": {
    "slug": "acme-technologies",
    "status": "inactive",
    "deleted_at": "2026-02-15T14:00:00Z"
  }
}
```

**Error Response (404 Not Found):**

```json
{
  "hasError": true,
  "statusCode": 404,
  "message": {
    "general": ["Company not found"]
  },
  "response": {}
}
```

**Error Response (403 Forbidden):**

```json
{
  "hasError": true,
  "statusCode": 403,
  "message": {
    "general": ["Admin access required"]
  },
  "response": {}
}
```

**Error Response (401 Unauthorized):**

```json
{
  "hasError": true,
  "statusCode": 401,
  "message": {
    "general": ["Unauthorized access"]
  },
  "response": {}
}
```

**Error Codes:**
- 200: Success
- 401: Unauthorized (invalid or missing token)
- 403: Forbidden (user does not have Admin role)
- 404: Not Found (company does not exist)
- 500: Internal Server Error

---

## 7. Approve Company (Admin Only)

### [PATCH] /api/v1/dashboard/company/<slug>/approve/

**Status:** IMPLEMENTED

**Purpose:**
Approves a pending company by transitioning its status from `'pending'` to `'active'`. This is an admin-only endpoint used as part of the company verification workflow. Once approved, the company becomes publicly visible via the public GET endpoint.

**Roles:**
- Admin role required

**Constraints:**
- Only companies with `status='pending'` can be approved
- Transition is strictly `'pending'` → `'active'` (no other transitions allowed via this endpoint)
- No request body required
- Admin user ID is recorded as `updated_by`

**Authentication:**
Bearer token (JWT) required with "Admin" role.

### Request Parameters

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `slug` | string | Yes | Company slug to approve. Example: "acme-technologies" |

**Request Body:** None required.

**Example Request:**
```
PATCH /api/v1/dashboard/company/acme-technologies/approve/
Authorization: Bearer <admin-jwt-token>
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
  "response": {
    "slug": "string",
    "status": "string (enum)",
    "updated_at": "string (ISO 8601 datetime)",
    "updated_by": "string (UUID)"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `response.slug` | string | Slug of the approved company |
| `response.status` | string | New status (always "active" after approval) |
| `response.updated_at` | string (ISO 8601) | Timestamp of approval |
| `response.updated_by` | string (UUID) | Admin user ID who approved the company |

Example:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Company approved successfully"]
  },
  "response": {
    "slug": "acme-technologies",
    "status": "active",
    "updated_at": "2026-02-20T12:00:00Z",
    "updated_by": "admin-uuid-here"
  }
}
```

**Error Response (404 Not Found):**

```json
{
  "hasError": true,
  "statusCode": 404,
  "message": {
    "general": ["Company not found or not in pending status"]
  },
  "response": {}
}
```

**Error Response (403 Forbidden):**

```json
{
  "hasError": true,
  "statusCode": 403,
  "message": {
    "general": ["Admin access required"]
  },
  "response": {}
}
```

**Error Response (401 Unauthorized):**

```json
{
  "hasError": true,
  "statusCode": 401,
  "message": {
    "general": ["Unauthorized access"]
  },
  "response": {}
}
```

**Error Codes:**
- 200: Success
- 401: Unauthorized (invalid or missing token)
- 403: Forbidden (user does not have Admin role)
- 404: Not Found (company does not exist or is not in pending status)
- 500: Internal Server Error

---

## Status Enum Documentation

### Company Status Values

| Status | Description | Publicly Visible | Can Transition To |
|--------|-------------|-------------------|-------------------|
| `pending` | Default status on creation. Awaiting admin approval. | No | `active` (via admin approval) |
| `active` | Company has been verified and approved by admin. | Yes | `inactive` (via admin deactivation) |
| `inactive` | Company has been deactivated or soft-deleted by admin. | No | `active` (via admin update) |

### Status Lifecycle Diagram

```
  [Creation]          [Admin Approval]        [Admin Deactivation]
      │                     │                         │
      ▼                     ▼                         ▼
  ┌─────────┐        ┌──────────┐             ┌──────────────┐
  │ pending │───────►│  active  │────────────►│   inactive   │
  └─────────┘        └──────────┘             └──────────────┘
                           ▲                         │
                           └─────────────────────────┘
                             (Admin reactivation)
```

---

## Business Rules

1. **One Company Per User:** Users can create only one company profile.
2. **Auto Role Assignment:** "Company" role is automatically assigned upon company creation.
3. **Unique Slugs:** Slugs are auto-generated from company name with collision handling (company-1, company-2, etc.).
4. **Unique Names:** Company names must be unique across the platform.
5. **Pending by Default:** New companies are created with `status='pending'` and are NOT publicly visible until approved.
6. **Admin Approval Required:** An admin must approve a company (transition `pending` → `active`) before it appears in public listings.
7. **Public Visibility:** Only companies with `status='active'` AND `deleted_at IS NULL` are returned by the public GET endpoint.
8. **Soft Deletes:** Companies are marked as inactive and `deleted_at` is set, rather than being removed from the database.
9. **Admin-Only Deactivation:** Only administrators can deactivate companies.
10. **Admin Update:** Administrators can modify any company's details including restricted fields (name, status).

---

## Implementation Status

All endpoints implemented:
- POST /api/v1/register/company/create/ (Company onboarding, creates with status='pending')
- GET /api/v1/dashboard/company/<slug>/ (Public company profile — active only)
- GET /api/v1/dashboard/company/profile/ (Authenticated company profile)
- PUT /api/v1/dashboard/company/profile/ (Self-service update)
- PATCH /api/v1/dashboard/company/profile/ (Self-service partial update)
- PUT /api/v1/dashboard/company/<slug>/ (Admin update company by slug)
- PATCH /api/v1/dashboard/company/<slug>/ (Admin partial update company by slug)
- PATCH /api/v1/dashboard/company/<slug>/approve/ (Approve company — Admin only)
- DELETE /api/v1/dashboard/company/<slug>/ (Deactivate company — Admin only)
- CompanyCreateSerializer (Input validation)
- CompanyReadSerializer, CompanySelfUpdateSerializer, CompanyAdminUpdateSerializer
- Auto role creation and assignment
- Unique slug generation
- Transaction safety

Pending:
- Logo upload functionality
