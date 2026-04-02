# Dashboard / Company

Base path: `/api/dashboard/company/`

## Endpoint: `create/`

### POST `create/`
- Brief: Public company onboarding signup with POC account creation.
- Auth: No authentication required.
- Required fields: `name`, `poc_name`, `poc_email`, `password`
- Optional fields: `poc_phone`, `website_link`, `description`, `industry_sector`, `location`, `district_id`, `legal_name`, `registration_number`, `tax_id`, `company_size`, `linkedin_url`, `verification_document_url`
- Notes:
  - `district_id` is required only when a matching company organization record does not already exist.
  - Duplicate `poc_email` and duplicate company `name` return `409` conflicts.
- Success response includes: `company_id`, `slug`, `muid`, `status`, and `auth` token payload.

## Endpoint: `onboarding/status/`

### GET `onboarding/status/`
- Brief: Get current company verification status for the authenticated company user.
- Auth: Bearer token required (Company role mapping required).
- Response includes: status, rejection reason, verification timestamps, and access hints.

## Endpoint: `verification/requests/`

### GET `verification/requests/`
- Brief: Admin list of company verification requests.
- Auth: Bearer token required (Admin role).
- Query params:
  - `status` (optional)
  - `search` (optional)
  - `dateFrom` / `dateTo` (optional, YYYY-MM-DD)

## Endpoint: `verification/requests/<company_id>/`

### PATCH `verification/requests/<company_id>/`
- Brief: Admin verification action for a company.
- Auth: Bearer token required (Admin role).
- Request body:
```json
{
  "action": "approve",
  "reason": ""
}
```
- Allowed actions: `approve`, `reject`
- `reason` is required when rejecting.

## Endpoint: `verification/resubmit/`

### POST `verification/resubmit/`
- Brief: Resubmit verification request for rejected companies.
- Auth: Bearer token required (Company role mapping required).

## Endpoint: `profile/`

### GET `profile/`
- Brief: Get authenticated company's own editable profile (`active`, `pending_verification`, `rejected`).
- Auth: Bearer token required.
- Success response example:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Company profile fetched successfully"
    ]
  },
  "response": {
    "id": "8bbfd80d-2f1b-4a6c-a1f1-275bf95ea264",
    "company_user_id": "a65f7d99-ff4a-44ca-a038-bfd05e8b8958",
    "name": "Acme Labs",
    "logo": "https://cdn.example.com/logo.png",
    "description": "Building tools for learners.",
    "industry_sector": "EdTech",
    "website_link": "https://acme.example",
    "email": "hello@acme.example",
    "slug": "acme-labs",
    "status": "active",
    "location": "Kochi",
    "created_at": "2026-04-02T12:00:00Z",
    "updated_at": "2026-04-02T12:00:00Z",
    "deleted_at": null
  }
}
```

### POST `profile/`
- Brief: Create company profile for authenticated user.
- Auth: Bearer token required.
- Request body:
```json
{
  "name": "Acme Labs",
  "logo": "https://cdn.example.com/logo.png",
  "description": "Building tools for learners.",
  "industry_sector": "EdTech",
  "website_link": "https://acme.example",
  "email": "hello@acme.example",
  "slug": "acme-labs",
  "location": "Kochi"
}
```
- Conflict response (`409`) when profile already exists:
```json
{
  "hasError": true,
  "statusCode": 409,
  "message": {
    "general": [
      "Company profile already exists for this user"
    ],
    "error_code": "COMPANY_ALREADY_EXISTS"
  },
  "response": {}
}
```

### PATCH `profile/`
- Brief: Partial update of authenticated company's editable profile.
- Auth: Bearer token required.
- Request body example:
```json
{
  "description": "Updated company description.",
  "location": "Thiruvananthapuram"
}
```
- Conflict response (`409`) for duplicate slug:
```json
{
  "hasError": true,
  "statusCode": 409,
  "message": {
    "general": [
      "Company slug already exists"
    ],
    "error_code": "DUPLICATE_SLUG"
  },
  "response": {}
}
```

### DELETE `profile/`
- Brief: Soft delete authenticated company's profile.
- Auth: Bearer token required.
- Success response example:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Company profile deleted successfully"
    ]
  },
  "response": {
    "company_id": "8bbfd80d-2f1b-4a6c-a1f1-275bf95ea264",
    "status": "inactive",
    "deleted_at": "2026-04-02T13:10:00.000000+00:00"
  }
}
```

## Endpoint: `profile/public/<slug>/`

### GET `profile/public/<slug>/`
- Brief: Public read-only company profile by slug.
- Auth: No authentication required.
- Success response example:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Public company profile fetched successfully"
    ]
  },
  "response": {
    "id": "8bbfd80d-2f1b-4a6c-a1f1-275bf95ea264",
    "name": "Acme Labs",
    "logo": "https://cdn.example.com/logo.png",
    "description": "Building tools for learners.",
    "industry_sector": "EdTech",
    "website_link": "https://acme.example",
    "slug": "acme-labs",
    "location": "Kochi"
  }
}
```
