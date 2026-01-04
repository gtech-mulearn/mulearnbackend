# Integrations API Reference

## KKEM Integration

### Bulk Karma
**Endpoint:** `/api/v1/integrations/kkem/`
**Method:** `GET`
**Brief:** Get bulk karma data for KKEM users.
**Auth:** Token required (KKEM)
**Query Params:** `from_datetime` (YYYY-MM-DDTHH:MM:SS)

### Individual Karma
**Endpoint:** `/api/v1/integrations/kkem/user/<str:muid>/`
**Method:** `GET`
**Brief:** Get karma data for a specific KKEM user.
**Auth:** Token required (KKEM)

### Authorization (Setup)
**Endpoint:** `/api/v1/integrations/kkem/authorization/`
**Method:** `POST`
**Brief:** Initiate KKEM authorization (sends email).

**Request Body:**
```json
{
  "emailOrMuid": "string",
  "param": "encrypted_string"
}
```

### Authorization (Verify)
**Endpoint:** `/api/v1/integrations/kkem/authorization/<str:token>/`
**Method:** `PATCH`
**Brief:** Verify and complete KKEM authorization.

### Login
**Endpoint:** `/api/v1/integrations/kkem/login/`
**Method:** `POST`
**Brief:** Login with KKEM integration (or link account during login).

**Request Body:**
```json
{
  "emailOrMuid": "string",
  "password": "string",
  "param": "encrypted_string (optional)"
}
```

### Fetch Details
**Endpoint:** `/api/v1/integrations/kkem/details/<str:encrypted_data>/`
**Method:** `GET`
**Brief:** Fetch job seeker details (proxy to KKEM).

### User Status
**Endpoint:** `/api/v1/integrations/kkem/user-status/<str:encrypted_data>/`
**Method:** `GET`
**Brief:** Decrypt data and get MUID.

### Hackathon Stats
**Endpoint:** `/api/v1/integrations/kkem/hackathon/`
**Method:** `GET`
**Brief:** Get hackathon statistics for KKEM.
**Auth:** Token required (KKEM)

## Wadhwani Integration

### Auth Token
**Endpoint:** `/api/v1/integrations/wadhwani/auth-token/`
**Method:** `POST`
**Brief:** Get Wadhwani client auth token.

**Response Body:**
```json
{
  "response": {
      "access_token": "string",
      "expires_in": 0,
       "token_type": "Bearer"
  }
}
```

### User Login
**Endpoint:** `/api/v1/integrations/wadhwani/user-login/`
**Method:** `POST`
**Brief:** Login user to Wadhwani.

**Request Body:**
```json
{
  "Client-Auth-Token": "string",
  "course_root_id": "string"
}
```

### Course Details
**Endpoint:** `/api/v1/integrations/wadhwani/course-details/`
**Method:** `POST`
**Brief:** Get Wadhwani course details.

**Request Body:**
```json
{
  "Client-Auth-Token": "string"
}
```

### Enroll Status
**Endpoint:** `/api/v1/integrations/wadhwani/enroll-status/`
**Method:** `POST`
**Brief:** Get user enrollment status.

**Request Body:**
```json
{
  "Client-Auth-Token": "string"
}
```

### Quiz Data
**Endpoint:** `/api/v1/integrations/wadhwani/quiz-data/`
**Method:** `POST`
**Brief:** Get user quiz data.

**Request Body:**
```json
{
  "Client-Auth-Token": "string",
  "course_id": "string"
}
```

## QSeverse Integration

### Issue Verifiable Credential
**Endpoint:** `/api/v1/integrations/qseverse/issue-vc/`
**Method:** `POST`
**Brief:** Issue a Verifiable Credential.

**Request Body:**
```json
{
  "subject_info": {
      "name": "string",
      "email": "string",
      "phone": "string (optional)"
  },
  "credential_info": {
      "name": "string",
      "description": "string"
  },
  "template_id": "string"
}
```

### Get All Connected Users
**Endpoint:** `/api/v1/integrations/qseverse/connected-users/`
**Method:** `GET`
**Brief:** Get all connected users from QSeverse.

### Get Connected User (Search)
**Endpoint:** `/api/v1/integrations/qseverse/connected-user/`
**Method:** `GET`
**Brief:** Search for connected users.
**Query Params:** `key`, `value`

### Get QS Credentials
**Endpoint:** `/api/v1/integrations/qseverse/qs-credentials/`
**Method:** `GET`
**Brief:** Get user credentials from QSeverse.
