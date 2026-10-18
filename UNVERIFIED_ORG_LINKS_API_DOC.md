# Unverified Organization Link User Management API Documentation

This document describes the API endpoints for listing unverified user-organization links and updating their verification status.

---

## 1. List Unverified Organization Link Users

### **Endpoint**
`GET /api/v1/dashboard/user/unverified-org-links/`

### **Allowed Roles**
* `Admin`
* `Campus Lead`

### **Description**
Retrieves a paginated list of users whose `UserOrganizationLink` has `verified = false`.
* **Admins**: Can view all unverified user organization links platform-wide.
* **Campus Leads**: Can view unverified user organization links restricted **only** to their verified campus (`org_id`). Callers without a verified campus link receive a `400 Bad Request` failure response.

---

### **Request**

#### **Headers**
```http
Authorization: Bearer <JWT_TOKEN>
```

#### **Query Parameters (All Optional)**
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `search` | `string` | `null` | Search query matching user's `full_name`, `muid`, `email`, `mobile`, or organization `title`. |
| `sortBy` | `string` | `created_at` | Field to sort by: `full_name`, `muid`, `email`, `org_title`, `created_at`. |
| `sortOrder` | `string` | `desc` | Sort order: `asc` or `desc`. |
| `page` | `integer` | `1` | Page number for pagination. |
| `perPage` | `integer` | `10` | Number of items per page. |

#### **Request Body**
*None (GET request)*

---

### **Response**

#### **200 OK — Success Response (Paginated)**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Success"
    ]
  },
  "response": {
    "data": [
      {
        "id": "link-uuid-1",
        "user_id": "user-uuid-1",
        "full_name": "Jane Doe",
        "muid": "JANEDOE@mulearn",
        "email": "jane@example.com",
        "mobile": "9876543210",
        "org_id": "org-uuid-1",
        "org_title": "College of Engineering",
        "org_type": "College",
        "graduation_year": "2025",
        "is_alumni": false,
        "verified": false,
        "created_at": "2026-09-14T10:00:00Z"
      }
    ],
    "pagination": {
      "count": 1,
      "totalPages": 1,
      "isNext": false,
      "isPrev": false,
      "nextPage": null
    }
  }
}
```

#### **400 Bad Request — Unverified / Unlinked Campus Lead**
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": [
      "You do not have a verified campus organization."
    ]
  },
  "response": {}
}
```

---

## 2. Update Organization Link Verification Status

### **Endpoint**
`PATCH /api/v1/dashboard/user/unverified-org-links/<link_id>/`

### **Allowed Roles**
* `Admin`
* `Campus Lead`

### **Description**
Updates the `verified` status of a specific `UserOrganizationLink` record (`link_id`).
* **Admins**: Can update verification status for any organization link.
* **Campus Leads**: Can **only** update verification status for organization links belonging to their verified campus.
* **Idempotent Execution**: Accepts an explicit boolean payload (`true` or `false`), preventing unintended state flips on network retries or concurrent requests.

---

### **Request**

#### **Headers**
```http
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

#### **URL Parameters**
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `link_id` | `string` | The UUID/ID of the `UserOrganizationLink` record to update. |

#### **Request Body**
```json
{
  "verified": true
}
```

---

### **Response**

#### **200 OK — Success Response**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Verification status set to True."
    ]
  },
  "response": {
    "id": "link-uuid-1",
    "user_id": "user-uuid-1",
    "full_name": "Jane Doe",
    "muid": "JANEDOE@mulearn",
    "email": "jane@example.com",
    "mobile": "9876543210",
    "org_id": "org-uuid-1",
    "org_title": "College of Engineering",
    "org_type": "College",
    "graduation_year": "2025",
    "is_alumni": false,
    "verified": true,
    "created_at": "2026-09-14T10:00:00Z"
  }
}
```

#### **400 Bad Request — Cross-Campus Modification Attempt by Campus Lead**
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": [
      "You can only manage links for your own campus."
    ]
  },
  "response": {}
}
```

#### **400 Bad Request — Invalid Payload**
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": [
      "Please provide a valid boolean 'verified' value in the request body."
    ]
  },
  "response": {}
}
```

#### **400 Bad Request — Organization Link Not Found**
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": [
      "Organization link not found."
    ]
  },
  "response": {}
}
```
