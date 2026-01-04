# Launchpad API Reference

## Authentication

### Company Login
**Endpoint:** `/api/v1/launchpad/company/login/`
**Method:** `POST`
**Brief:** Login for companies.

**Request Body:**
```json
{
  "username": "string (or email)",
  "password": "string"
}
```

### Recruiter Login
**Endpoint:** `/api/v1/launchpad/recruiter/login/`
**Method:** `POST`
**Brief:** Login for recruiters.

**Request Body:**
```json
{
  "email": "string (or phone)",
  "password": "string"
}
```

### Forgot Password
**Endpoint:** `/api/v1/launchpad/forgot-password/`
**Method:** `POST`

**Request Body:**
```json
{
  "email": "string",
  "user_type": "company/recruiter"
}
```

### Reset Password
**Endpoint:** `/api/v1/launchpad/reset-password/`
**Method:** `POST`

**Request Body:**
```json
{
  "token": "string",
  "new_password": "string",
  "confirm_password": "string",
  "user_type": "company/recruiter"
}
```

### Change Password
**Endpoint:** `/api/v1/launchpad/change-password/`
**Method:** `POST`
**Auth:** Launchpad JWT

**Request Body:**
```json
{
  "current_password": "string",
  "new_password": "string",
  "confirm_password": "string"
}
```

## Companies

### Register Company
**Endpoint:** `/api/v1/launchpad/company/register/`
**Method:** `POST`
**Brief:** Register a new company.

**Request Body:**
```json
{
  "name": "string",
  "username": "string",
  "password": "string",
  "poc_name": "string",
  "poc_role": "string",
  "poc_email": "string",
  "poc_phone": "string",
  "website": "string",
  "description": "string",
  "address": "string"
}
```

### List Companies (Admin)
**Endpoint:** `/api/v1/launchpad/company/list/`
**Method:** `GET`
**Auth:** Admin Role

### List Verified Companies
**Endpoint:** `/api/v1/launchpad/company/list/verified/`
**Method:** `GET`
**Brief:** Public list of verified companies.

### Get Company Info
**Endpoint:** `/api/v1/launchpad/company/info/`
**Method:** `POST`
**Auth:** Launchpad JWT

**Request Body:**
```json
{
  "company_id": "uuid"
}
```

## Recruiters

### Register Recruiter
**Endpoint:** `/api/v1/launchpad/recruiter/register/`
**Method:** `POST`
**Auth:** Company JWT

**Request Body:**
```json
{
  "name": "string",
  "email": "string",
  "phone": "string",
  "password": "string",
  "role": "string"
}
```

### Get Recruiter Info
**Endpoint:** `/api/v1/launchpad/recruiter/info/`
**Method:** `POST`
**Auth:** Launchpad JWT

**Request Body:**
```json
{
  "recruiter_id": "uuid"
}
```

## Jobs

### Add Job
**Endpoint:** `/api/v1/launchpad/job/add/`
**Method:** `POST`
**Auth:** Recruiter JWT

**Request Body:**
```json
{
  "title": "string",
  "skills": "string",
  "experience": "string",
  "minimum_karma": 0,
  "opening_type": "General/Task",
  "location": "string",
  "salary_range": "string",
  "job_type": "string",
  "domain": "string",
  "interest_groups": ["uuid"],
  "task_description": "string (required if opening_type=Task)"
}
```

### Update Job
**Endpoint:** `/api/v1/launchpad/job/update/<str:job_id>/`
**Method:** `PUT`
**Auth:** Recruiter/Company JWT

### Delete Job
**Endpoint:** `/api/v1/launchpad/job/delete/<str:job_id>/`
**Method:** `DELETE`
**Auth:** Recruiter/Company JWT

### Get Job
**Endpoint:** `/api/v1/launchpad/job/<str:job_id>/`
**Method:** `GET`
**Auth:** Launchpad JWT

### List Jobs
**Endpoint:** `/api/v1/launchpad/job/list/`
**Method:** `GET`
**Auth:** Launchpad JWT or Regular Auth (for students)

## Tasks

### Verify Task
**Endpoint:** `/api/v1/launchpad/task/verify/`
**Method:** `POST`
**Auth:** Admin Role

**Request Body:**
```json
{
  "task_id": "uuid",
  "hashtag": "string"
}
```
