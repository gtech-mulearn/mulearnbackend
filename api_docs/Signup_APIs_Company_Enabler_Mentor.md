# Signup APIs: Company, Enabler, Mentor

Base URL: `/api/v1`

This document is based on the current code paths in:
- `api/dashboard/company/onboarding/*`
- `api/register/*`
- `api/dashboard/user/*`

## Important implementation note

There is a dedicated signup API for `company`.

There is currently **no separate public `mentor signup` API** or **`enabler signup` API** controller in the codebase. Both `mentor` and `enabler` signups are implemented through the generic user registration endpoint:

- `POST /api/v1/register/`

The requested role is attached during registration, and that role starts as:
- `verified = true` for `Student` and `Mulearner`
- `verified = false` for roles such as `Mentor` and `Enabler`

That behavior is implemented in `api/register/serializers.py`.

## Common response envelope

All endpoints documented here use the shared `CustomResponse` format:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Success"
    ]
  },
  "response": {}
}
```

Failure responses follow the same shape with `hasError: true`.

---

## 1. Company Signup

### POST `/api/v1/dashboard/company/create/`

Creates:
- a new `user` for the point of contact
- a `company` role link with `verified = false`
- a `company` organization link with `verified = false`
- a `company` onboarding record with `status = pending_verification`

### Authentication

No authentication required.

### Request body

#### Required fields

```json
{
  "name": "Acme Labs",
  "poc_name": "Jane Doe",
  "poc_email": "jane@acme.com",
  "password": "StrongPass123"
}
```

#### Optional fields

```json
{
  "poc_phone": "+919999999999",
  "website_link": "https://acme.com",
  "description": "Product engineering company",
  "industry_sector": "Technology",
  "location": "Kochi, Kerala",
  "district_id": "district-uuid",
  "legal_name": "Acme Labs Private Limited",
  "registration_number": "REG-12345",
  "tax_id": "GSTIN-12345",
  "company_size": "51-200",
  "linkedin_url": "https://linkedin.com/company/acme",
  "verification_document_url": "https://example.com/proof.pdf"
}
```

### Validation rules

- `name`: required, trimmed, max 75 chars, cannot be empty.
- `poc_name`: required, trimmed, max 150 chars, cannot be empty.
- `poc_email`: required, lowercased, must be unique across users.
- `password`: required, min length `8`.
- `poc_phone`: optional, must match `^\+?[0-9]{8,15}$` if provided, must be unique across users.
- `district_id`: optional only when a matching company organization already exists.
- If no existing `Organization` of type `Company` exists with the same title, `district_id` becomes required.
- If a `Company` record already exists with the same name, signup fails with conflict.

### Success response

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Company registration submitted successfully"
    ]
  },
  "response": {
    "company_id": "uuid",
    "slug": "acme-labs",
    "muid": "jane-doe@mulearn",
    "status": "pending_verification",
    "auth": {
      "access": "...",
      "refresh": "...",
      "data": {
        "id": "user-uuid",
        "muid": "jane-doe@mulearn",
        "email": "jane@acme.com",
        "role": null,
        "full_name": "Jane Doe"
      }
    }
  }
}
```

### Notes

- The nested `auth` object comes from `get_auth_token(...)`.
- `response.auth.data.role` is usually `null` here because `UserDetailSerializer` only surfaces `Mentor` or `Enabler`, not `Company`.
- If no matching company organization exists, the API creates one automatically using the provided `district_id`.

### Error cases

#### 400 Validation error

```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": [
      "Invalid company signup data"
    ],
    "error_code": "VALIDATION_ERROR",
    "errors": {
      "district_id": [
        "district_id is required when no matching company organization exists"
      ]
    }
  },
  "response": {}
}
```

#### 409 Duplicate email

```json
{
  "hasError": true,
  "statusCode": 409,
  "message": {
    "general": [
      "A user with this email already exists"
    ],
    "error_code": "DUPLICATE_POC_EMAIL",
    "errors": {
      "poc_email": [
        "A user with this email already exists"
      ]
    }
  },
  "response": {}
}
```

#### 409 Duplicate company name

```json
{
  "hasError": true,
  "statusCode": 409,
  "message": {
    "general": [
      "Company name already exists"
    ],
    "error_code": "DUPLICATE_COMPANY_NAME",
    "errors": {
      "name": [
        "Company name already exists"
      ]
    }
  },
  "response": {}
}
```

#### 409 Duplicate phone

```json
{
  "hasError": true,
  "statusCode": 409,
  "message": {
    "general": [
      "A user with this phone number already exists"
    ],
    "error_code": "DUPLICATE_POC_PHONE",
    "errors": {
      "poc_phone": [
        "A user with this phone number already exists"
      ]
    }
  },
  "response": {}
}
```

---

## 2. Company Signup Follow-up APIs

These are part of the company signup lifecycle.

### GET `/api/v1/dashboard/company/onboarding/status/`

Returns the current company onboarding state for the authenticated company user.

### Authentication

Bearer token required.

### Success response shape

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Company onboarding status fetched successfully"
    ]
  },
  "response": {
    "id": "company-uuid",
    "name": "Acme Labs",
    "slug": "acme-labs",
    "status": "pending_verification",
    "poc_name": "Jane Doe",
    "poc_email": "jane@acme.com",
    "rejection_reason": null,
    "verification_requested_at": "2026-04-05T10:00:00+05:30",
    "verified_at": null,
    "created_at": "2026-04-05T10:00:00+05:30",
    "updated_at": "2026-04-05T10:00:00+05:30",
    "can_edit_profile": true,
    "can_access_advanced_features": false,
    "next_steps": [
      "Wait for admin verification approval"
    ]
  }
}
```

### POST `/api/v1/dashboard/company/verification/resubmit/`

Allows an authenticated company user to resubmit a previously rejected company verification request.

### Authentication

Bearer token required.

### Success response

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Company verification request resubmitted successfully"
    ]
  },
  "response": {
    "company_id": "company-uuid",
    "status": "pending_verification",
    "verification_requested_at": "2026-04-05T10:00:00+05:30"
  }
}
```

---

## 3. Mentor Signup

## Actual implementation in this codebase

Mentor signup is handled through:

- `POST /api/v1/register/`

There is no separate public endpoint like `/mentor/signup/`.

### POST `/api/v1/register/`

Registers a new user and optionally assigns a role during signup.

### Authentication

No authentication required.

### Request body for mentor signup

```json
{
  "user": {
    "full_name": "Alex Mentor",
    "email": "alex@example.com",
    "password": "StrongPass123",
    "dob": "1998-08-17",
    "gender": "Male",
    "role": "mentor-role-id",
    "district": "district-uuid",
    "area_of_interest": [
      "ig-uuid-1",
      "ig-uuid-2"
    ]
  }
}
```

### Optional nested objects

```json
{
  "integration": {
    "title": "DWMS",
    "param": "encrypted-value"
  },
  "referral": {
    "muid": "referrer@mulearn"
  }
}
```

### What happens internally

- A new `user` is created.
- `Wallet`, `Socials`, `UserSettings`, and default level link records are created.
- A `UserRoleLink` is created for the requested role.
- Since mentor is not `Student` or `Mulearner`, the role is created with `verified = false`.

### Success response

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": []
  },
  "response": {
    "access": "...",
    "refresh": "...",
    "data": {
      "id": "user-uuid",
      "muid": "alex-mentor@mulearn",
      "email": "alex@example.com",
      "role": "Mentor",
      "full_name": "Alex Mentor"
    }
  }
}
```

### Important notes

- The role value must be the DB primary key of the `Mentor` role, not the string `"Mentor"`.
- Use `GET /api/v1/register/role/list/` to fetch role ids.
- The codebase includes a `MentorSerializer` for storing mentor-specific fields (`about`, `reason`, `hours`), but it is not wired into `POST /api/v1/register/` or exposed by a dedicated public signup view right now.
- Actual approval of mentor requests happens later through admin verification.

### Admin verification endpoint used after signup

#### PATCH `/api/v1/dashboard/user/verification/{link_id}/`

Marks a pending user-role link as verified or unverified.

Example body:

```json
{
  "verified": true
}
```

---

## 4. Enabler Signup

## Actual implementation in this codebase

Enabler signup is handled through:

- `POST /api/v1/register/`

There is no separate public endpoint like `/enabler/signup/`.

### POST `/api/v1/register/`

### Request body for enabler signup

```json
{
  "user": {
    "full_name": "Ena Builder",
    "email": "ena@example.com",
    "password": "StrongPass123",
    "dob": "1999-02-20",
    "gender": "Female",
    "role": "enabler-role-id",
    "district": "district-uuid",
    "area_of_interest": [
      "ig-uuid-1"
    ]
  }
}
```

### What happens internally

- A new `user` is created.
- The requested `Enabler` role is attached through `UserRoleLink`.
- Since `Enabler` is not one of the auto-verified roles, the new role link is created with `verified = false`.

### Success response

Response shape is the same as mentor signup, with `response.data.role` typically resolving to `"Enabler"`.

### Important notes

- The role value must be the DB role id for `Enabler`.
- Use `GET /api/v1/register/role/list/` to resolve role ids.
- Verification is completed later through admin review on the user verification API.

### Admin verification endpoint used after signup

#### PATCH `/api/v1/dashboard/user/verification/{link_id}/`

Example body:

```json
{
  "verified": true
}
```

---

## 5. Shared helper APIs used by frontend signup flows

### GET `/api/v1/register/role/list/`

Returns available roles with DB ids.

Example response:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": []
  },
  "response": {
    "roles": [
      {
        "id": "role-uuid",
        "title": "Mentor"
      },
      {
        "id": "role-uuid",
        "title": "Enabler"
      }
    ]
  }
}
```

### GET `/api/v1/register/company/list/`

Returns company organizations.

### GET `/api/v1/register/colleges/`

Returns college organizations.

### GET `/api/v1/register/department/list/`

Returns departments.

### GET `/api/v1/register/country/list/`

Returns countries.

### POST `/api/v1/register/state/list/`

Input:

```json
{
  "country": "country-uuid"
}
```

### POST `/api/v1/register/district/list/`

Input:

```json
{
  "state": "state-uuid"
}
```

### POST `/api/v1/register/college/list/`

Input:

```json
{
  "district": "district-uuid",
  "search": "engineering"
}
```

### POST `/api/v1/register/email-verification/`

Checks whether an email already exists.

Input:

```json
{
  "email": "user@example.com"
}
```

### GET `/api/v1/register/location/?q=kochi`

Searches districts/locations for signup forms.

---

## 6. Summary

- `Company` has a dedicated signup endpoint: `POST /api/v1/dashboard/company/create/`
- `Mentor` signup uses the generic user registration endpoint: `POST /api/v1/register/`
- `Enabler` signup uses the generic user registration endpoint: `POST /api/v1/register/`
- `Mentor` and `Enabler` are not auto-verified during signup
- `Company` is also not auto-verified and moves through a dedicated onboarding verification flow
