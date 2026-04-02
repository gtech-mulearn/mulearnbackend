# Company Dashboard API Reference

Base URL: `/api/v1/dashboard/company/`

All responses use this envelope:

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["..."]
  },
  "response": {}
}
```

---

## 1) Company Onboarding APIs

### 1.1 `POST /api/v1/dashboard/company/create/`
Description: Public company signup with POC user creation, company-role mapping, org-linking, and company record creation in `pending_verification`.
Auth: `AllowAny`

Request body:
```json
{
  "name": "TechNova Solutions Pvt Ltd",
  "poc_name": "Arjun Menon",
  "poc_email": "arjun.menon@technova.com",
  "password": "Password@123",
  "poc_phone": "+919876543210",
  "website_link": "https://technova.example",
  "description": "Product engineering company focused on developer tooling.",
  "industry_sector": "Software",
  "location": "Kochi, Kerala",
  "district_id": "1be42c62-f200-42fc-9158-692fecae9192",
  "legal_name": "TechNova Solutions Private Limited",
  "registration_number": "U72900KL2021PTC123456",
  "tax_id": "GSTIN32ABCDE1234F1Z9",
  "company_size": "51-200",
  "linkedin_url": "https://www.linkedin.com/company/technova",
  "verification_document_url": "https://cdn.example.com/docs/technova-certificate.pdf"
}
```

Success response:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Company registration submitted successfully"]
  },
  "response": {
    "company_id": "51cbdf98-62eb-45b8-8e8d-3db500609e23",
    "slug": "technova-solutions-pvt-ltd",
    "muid": "arjunmenon@mulearn",
    "status": "pending_verification",
    "auth": {
      "accessToken": "eyJ...",
      "refreshToken": "eyJ..."
    }
  }
}
```

Validation error response example:
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": ["Invalid company signup data"],
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

---

### 1.2 `GET /api/v1/dashboard/company/onboarding/status/`
Description: Fetch onboarding/verification status for logged-in company user.
Auth: JWT required.

Request body:
```json
{}
```

Success response:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Company onboarding status fetched successfully"]
  },
  "response": {
    "id": "51cbdf98-62eb-45b8-8e8d-3db500609e23",
    "name": "TechNova Solutions Pvt Ltd",
    "slug": "technova-solutions-pvt-ltd",
    "status": "pending_verification",
    "poc_name": "Arjun Menon",
    "poc_email": "arjun.menon@technova.com",
    "rejection_reason": null,
    "verification_requested_at": "2026-04-02T10:12:28Z",
    "verified_at": null,
    "created_at": "2026-04-02T10:12:28Z",
    "updated_at": "2026-04-02T10:12:28Z",
    "can_edit_profile": true,
    "can_access_advanced_features": false,
    "next_steps": ["Wait for admin verification approval"]
  }
}
```

---

### 1.3 `GET /api/v1/dashboard/company/verification/requests/`
Description: Admin list API for verification queue.
Auth: JWT + Admin role.

Query params:
- `status` (optional)
- `search` (optional)
- `dateFrom` (optional, `YYYY-MM-DD`)
- `dateTo` (optional, `YYYY-MM-DD`)
- `pageIndex`, `perPage`, `sortBy` (optional pagination/sort)

Request body:
```json
{}
```

Success response:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": []
  },
  "response": {
    "data": [
      {
        "id": "51cbdf98-62eb-45b8-8e8d-3db500609e23",
        "name": "TechNova Solutions Pvt Ltd",
        "slug": "technova-solutions-pvt-ltd",
        "status": "pending_verification",
        "poc_name": "Arjun Menon",
        "poc_email": "arjun.menon@technova.com",
        "poc_phone": "+919876543210",
        "website_link": "https://technova.example",
        "industry_sector": "Software",
        "location": "Kochi, Kerala",
        "verification_requested_at": "2026-04-02T10:12:28Z",
        "verified_at": null,
        "rejection_reason": null,
        "created_at": "2026-04-02T10:12:28Z",
        "updated_at": "2026-04-02T10:12:28Z"
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

---

### 1.4 `PATCH /api/v1/dashboard/company/verification/requests/<company_id>/`
Description: Admin action to approve/reject a company.
Auth: JWT + Admin role.

Request body:
```json
{
  "action": "approve",
  "reason": ""
}
```

Reject example request body:
```json
{
  "action": "reject",
  "reason": "Please upload valid registration document."
}
```

Success response:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Company verified successfully"]
  },
  "response": {
    "company_id": "51cbdf98-62eb-45b8-8e8d-3db500609e23",
    "status": "active",
    "verified_at": "2026-04-02T11:00:00Z",
    "rejection_reason": null
  }
}
```

---

### 1.5 `POST /api/v1/dashboard/company/verification/resubmit/`
Description: Resubmit verification for rejected companies.
Auth: JWT required.

Request body:
```json
{}
```

Success response:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Company verification request resubmitted successfully"]
  },
  "response": {
    "company_id": "51cbdf98-62eb-45b8-8e8d-3db500609e23",
    "status": "pending_verification",
    "verification_requested_at": "2026-04-02T11:10:00Z"
  }
}
```

---

## 2) Company Profile APIs

### 2.1 `GET /api/v1/dashboard/company/profile/`
Description: Get own company profile (`active`, `pending_verification`, `rejected`).
Auth: JWT required.

Request body:
```json
{}
```

Success response:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Company profile fetched successfully"]
  },
  "response": {
    "id": "51cbdf98-62eb-45b8-8e8d-3db500609e23",
    "company_user_id": "a4de2755-5578-4b8b-8af5-f067988edb05",
    "name": "TechNova Solutions Pvt Ltd",
    "logo": null,
    "description": "Product engineering company focused on developer tooling.",
    "industry_sector": "Software",
    "website_link": "https://technova.example",
    "email": "arjun.menon@technova.com",
    "slug": "technova-solutions-pvt-ltd",
    "status": "pending_verification",
    "location": "Kochi, Kerala",
    "legal_name": "TechNova Solutions Private Limited",
    "registration_number": "U72900KL2021PTC123456",
    "tax_id": "GSTIN32ABCDE1234F1Z9",
    "company_size": "51-200",
    "linkedin_url": "https://www.linkedin.com/company/technova",
    "verification_document_url": "https://cdn.example.com/docs/technova-certificate.pdf",
    "verification_requested_at": "2026-04-02T10:12:28Z",
    "verified_at": null,
    "verified_by": null,
    "rejection_reason": null,
    "created_at": "2026-04-02T10:12:28Z",
    "updated_at": "2026-04-02T10:12:28Z",
    "deleted_at": null
  }
}
```

---

### 2.2 `POST /api/v1/dashboard/company/profile/`
Description: Create profile for authenticated company user.
Auth: JWT required.

Request body:
```json
{
  "name": "TechNova Solutions Pvt Ltd",
  "logo": "https://cdn.example.com/logo.png",
  "description": "Product engineering company focused on developer tooling.",
  "industry_sector": "Software",
  "website_link": "https://technova.example",
  "email": "arjun.menon@technova.com",
  "slug": "technova-solutions-pvt-ltd",
  "location": "Kochi, Kerala",
  "legal_name": "TechNova Solutions Private Limited",
  "registration_number": "U72900KL2021PTC123456",
  "tax_id": "GSTIN32ABCDE1234F1Z9",
  "company_size": "51-200",
  "linkedin_url": "https://www.linkedin.com/company/technova",
  "verification_document_url": "https://cdn.example.com/docs/technova-certificate.pdf"
}
```

Success response: same shape as Profile GET (newly created record).

---

### 2.3 `PATCH /api/v1/dashboard/company/profile/`
Description: Partial update own company profile.
Auth: JWT required.

Request body:
```json
{
  "description": "Updated description.",
  "location": "Thiruvananthapuram, Kerala"
}
```

Success response: same shape as Profile GET (updated record).

---

### 2.4 `DELETE /api/v1/dashboard/company/profile/`
Description: Soft delete own profile.
Auth: JWT required.

Request body:
```json
{}
```

Success response:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Company profile deleted successfully"]
  },
  "response": {
    "company_id": "51cbdf98-62eb-45b8-8e8d-3db500609e23",
    "status": "inactive",
    "deleted_at": "2026-04-02T11:20:00+00:00"
  }
}
```

---

### 2.5 `GET /api/v1/dashboard/company/profile/public/<slug>/`
Description: Public profile read for active companies.
Auth: `AllowAny`

Request body:
```json
{}
```

Success response:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Public company profile fetched successfully"]
  },
  "response": {
    "id": "51cbdf98-62eb-45b8-8e8d-3db500609e23",
    "name": "TechNova Solutions Pvt Ltd",
    "logo": "https://cdn.example.com/logo.png",
    "description": "Product engineering company focused on developer tooling.",
    "industry_sector": "Software",
    "website_link": "https://technova.example",
    "slug": "technova-solutions-pvt-ltd",
    "location": "Kochi, Kerala"
  }
}
```

---

## 3) Company Jobs APIs

### 3.1 `GET /api/v1/dashboard/company/jobs/`
Description: List all non-deleted jobs for authenticated active company user (with pagination/search/sort).
Auth: JWT required.

Query params:
- `pageIndex` (optional, default `1`)
- `perPage` (optional, default `10`)
- `search` (optional; searches `title`, `location`, `job_type`)
- `sortBy` (optional; `title`, `createdAt`, `salary`, with optional `-` prefix)

Request body:
```json
{}
```

Success response:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Jobs retrieved successfully"]
  },
  "response": {
    "company_id": "51cbdf98-62eb-45b8-8e8d-3db500609e23",
    "company_name": "TechNova Solutions Pvt Ltd",
    "jobs": [
      {
        "id": "bcf4c2f2-c30e-4d78-977d-c8d01e76bba8",
        "title": "Backend Engineer",
        "job_type": "Full-Time",
        "location": "Remote",
        "salary_range": "12-18 LPA",
        "min_karma": 100,
        "min_level": 2,
        "status": "Active",
        "created_at": "2026-04-02T12:00:00Z",
        "updated_at": "2026-04-02T12:00:00Z",
        "rules": [
          {
            "id": "325e4487-cbc3-47bc-8f68-5033f97f86ec",
            "rule_type": "skill",
            "rule_type_id": "d8d0bd0d-cd5b-4ab1-8c6d-bf5054815a8e",
            "rule_name": "Django"
          }
        ]
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

---

### 3.2 `POST /api/v1/dashboard/company/jobs/create/`
Description: Create a new job.
Auth: JWT required (active company only).

Request body:
```json
{
  "title": "Backend Engineer",
  "experience": "2-4 years",
  "job_description": "Build APIs and background jobs.",
  "location": "Remote",
  "salary_range": "12-18 LPA",
  "job_type": "Full-Time",
  "min_karma": 100,
  "min_level": 2
}
```

Success response:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Job created successfully"]
  },
  "response": {
    "job": {
      "id": "bcf4c2f2-c30e-4d78-977d-c8d01e76bba8",
      "company_id": "51cbdf98-62eb-45b8-8e8d-3db500609e23",
      "title": "Backend Engineer",
      "job_type": "Full-Time",
      "created_at": "2026-04-02T12:00:00Z"
    }
  }
}
```

---

### 3.3 `GET /api/v1/dashboard/company/jobs/<job_id>/details/`
Description: Fetch one job (with rules).
Auth: JWT required.

Request body:
```json
{}
```

Success response:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Job details fetched successfully"]
  },
  "response": {
    "job": {
      "id": "bcf4c2f2-c30e-4d78-977d-c8d01e76bba8",
      "title": "Backend Engineer",
      "job_type": "Full-Time",
      "location": "Remote",
      "salary_range": "12-18 LPA",
      "min_karma": 100,
      "min_level": 2,
      "status": "Active",
      "created_at": "2026-04-02T12:00:00Z",
      "updated_at": "2026-04-02T12:00:00Z",
      "rules": [
        {
          "id": "325e4487-cbc3-47bc-8f68-5033f97f86ec",
          "rule_type": "skill",
          "rule_type_id": "d8d0bd0d-cd5b-4ab1-8c6d-bf5054815a8e",
          "rule_name": "Django"
        }
      ]
    }
  }
}
```

---

### 3.4 `PATCH /api/v1/dashboard/company/jobs/<job_id>/`
Description: Partial update job.
Auth: JWT required.

Request body:
```json
{
  "title": "Senior Backend Engineer",
  "salary_range": "18-24 LPA",
  "min_karma": 180
}
```

Success response:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Job updated successfully"]
  },
  "response": {
    "job_id": "bcf4c2f2-c30e-4d78-977d-c8d01e76bba8",
    "updated_fields": ["title", "salary_range", "min_karma"]
  }
}
```

---

### 3.5 `DELETE /api/v1/dashboard/company/jobs/<job_id>/`
Description: Soft delete job (`is_deleted = true`).
Auth: JWT required.

Request body:
```json
{}
```

Success response:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Job deleted successfully"]
  },
  "response": {
    "job_id": "bcf4c2f2-c30e-4d78-977d-c8d01e76bba8",
    "deleted_at": "2026-04-02T12:20:00Z"
  }
}
```

---

### 3.6 `POST /api/v1/dashboard/company/jobs/<job_id>/rules/create/`
Description: Add eligibility rule to a job.
Auth: JWT required.

Request body:
```json
{
  "rule_type": "skill",
  "rule_type_id": "d8d0bd0d-cd5b-4ab1-8c6d-bf5054815a8e"
}
```

`rule_type` allowed values: `skill`, `interest_group`, `achievement`

Success response:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Job rule added successfully"]
  },
  "response": {
    "job_rule": {
      "id": "325e4487-cbc3-47bc-8f68-5033f97f86ec",
      "job_id": "bcf4c2f2-c30e-4d78-977d-c8d01e76bba8",
      "rule_type": "skill",
      "rule_type_id": "d8d0bd0d-cd5b-4ab1-8c6d-bf5054815a8e",
      "created_at": "2026-04-02T12:05:00Z"
    }
  }
}
```

---

### 3.7 `PATCH /api/v1/dashboard/company/jobs/<job_id>/rules/<rule_id>/`
Description: Update an existing eligibility rule.
Auth: JWT required.

Request body:
```json
{
  "rule_type": "interest_group",
  "rule_type_id": "f6d4dd06-c5c8-4fb1-b608-8a0deca2f95f"
}
```

Success response:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Job rule updated successfully"]
  },
  "response": {
    "rule_id": "325e4487-cbc3-47bc-8f68-5033f97f86ec",
    "updated_value": "f6d4dd06-c5c8-4fb1-b608-8a0deca2f95f"
  }
}
```

---

### 3.8 `DELETE /api/v1/dashboard/company/jobs/<job_id>/rules/<rule_id>/delete/`
Description: Hard delete one eligibility rule.
Auth: JWT required.

Request body:
```json
{}
```

Success response:
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Job rule deleted successfully"]
  },
  "response": {
    "rule_id": "325e4487-cbc3-47bc-8f68-5033f97f86ec",
    "job_id": "bcf4c2f2-c30e-4d78-977d-c8d01e76bba8",
    "deleted_at": "2026-04-02T12:30:00Z"
  }
}
```

---

## Notes

- Company signup supports one profile per user (`company.company_user_id` unique).
- Most company feature endpoints expect the company profile to be `active` (job APIs are active-company gated).
- Admin verification workflow updates:
  - `Company.status`
  - `Company.verified_at`, `verified_by`, `rejection_reason`
  - `UserRoleLink.verified` and `UserOrganizationLink.verified`
