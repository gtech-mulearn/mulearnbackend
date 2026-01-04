# Register API Reference

## Registration

### User Registration
**Endpoint:** `/api/v1/register/`
**Method:** `POST`
**Brief:** Register a new user.
**Request Body:**
```json
{
    "user": {
        "full_name": "John Doe",
        "email": "john@example.com",
        "mobile": "9876543210",
        "password": "password123",
        "confirm_password": "password123",
         "gender": "Male",
         "dob": "2000-01-01"
    },
    "organization": {
        "organizations": ["org_uuid"],
        "department": "dept_uuid",
        "graduation_year": "2025"
    },
    "referral": {
        "muid": "referrer_muid",
        "invite_code": "code"
    },
     "param": {
          "jsid": "jsid_string",
          "dwms_id": "dwms_id_string"
     },
     "integration": "KKEM"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "User Registered Successfully"
        ]
    },
    "response": {
        "accessToken": "access_token",
        "refreshToken": "refresh_token",
        "data": {
            "id": "uuid",
            "muid": "muid",
            "email": "john@example.com",
            "full_name": "John Doe",
            "role": "Student"
        }
    }
}
```

### Email Verification
**Endpoint:** `/api/v1/register/email-verification/`
**Method:** `POST`
**Brief:** Check if an email is already registered.
**Request Body:**
```json
{
    "email": "check@example.com"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "This email already exists"
        ]
    },
    "response": {
        "value": true
    }
}
```

## Data Lists (Metadata)

### List Roles
**Endpoint:** `/api/v1/register/role/list/`
**Method:** `GET`
**Brief:** List available roles.
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {},
    "response": {
        "roles": [
            {
                "id": "uuid",
                "title": "Student"
            }
        ]
    }
}
```

### List Departments
**Endpoint:** `/api/v1/register/department/list/`
**Method:** `GET`
**Brief:** List departments.
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {},
    "response": {
        "departments": [
            {"id": "uuid", "title": "Computer Science"}
        ]
    }
}
```

### List Countries
**Endpoint:** `/api/v1/register/country/list/`
**Method:** `GET`
**Brief:** List countries.
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {},
    "response": {
        "countries": [
            {"id": "uuid", "name": "India"}
        ]
    }
}
```

### List States
**Endpoint:** `/api/v1/register/state/list/`
**Method:** `POST`
**Brief:** List states for a country.
**Request Body:**
```json
{
    "country": "country_uuid"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {},
    "response": {
        "states": [
            {"id": "uuid", "name": "Kerala"}
        ]
    }
}
```

### List Districts
**Endpoint:** `/api/v1/register/district/list/`
**Method:** `POST`
**Brief:** List districts for a state.
**Request Body:**
```json
{
    "state": "state_uuid"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {},
    "response": {
        "districts": [
            {"id": "uuid", "name": "Ernakulam"}
        ]
    }
}
```

### List Colleges
**Endpoint:** `/api/v1/register/college/list/`
**Method:** `POST`
**Brief:** List colleges, optionally filtered by district.
**Request Body:**
```json
{
    "district": "district_uuid",
    "search": "College Name"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {},
    "response": {
        "colleges": [
            {"id": "uuid", "title": "Model Engineering College"}
        ],
        "departments": []
    }
}
```
