# Impact Project API — Manual Test Guide

Base path: `/api/v1/dashboard/ig/<ig_id>/impact-projects/`

Auth: `Authorization: Bearer <accessToken>` header on every request.
- List (`GET`) works for any authenticated user.
- Create/Update/Delete/Image-upload require the caller to be an `Admins`, `IG Lead`, or that specific IG's `<CODE> IGLead` role (checked via `_can_manage_ig`).

---

## 1. List impact projects for an IG

`GET /api/v1/dashboard/ig/{ig_id}/impact-projects/`

No body. Supports the standard pagination query params: `pageIndex` (default 1), `perPage` (default 10), `search` (matches `title`/`description`), `sortBy` (`title`, `created_on`, `updated_on`, prefix with `-` to reverse).

**Response 200**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": [] },
  "response": {
    "data": [
      {
        "id": "b1f2c3d4-...",
        "ig_id": "ig-uuid-here",
        "title": "Community LMS",
        "image": "https://<BE_DOMAIN_NAME>/muback-media/impact_project/image/b1f2c3d4-....png",
        "description": "An online learning platform built for students and mentors.",
        "team": [
          { "muid": "alvin-dennis@mulearn", "name": "Alvin Dennis", "is_lead": true },
          { "muid": "akhil-raj@mulearn", "name": "Akhil Raj", "is_lead": false }
        ],
        "links": [
          { "label": "github", "url": "https://github.com/example/community-lms" },
          { "label": "live", "url": "https://lms.example.com" }
        ],
        "created_by": "Full Name",
        "updated_by": "Full Name",
        "created_at": "2026-07-24T08:25:30Z",
        "updated_at": "2026-07-24T08:25:30Z"
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

**Response 400 — IG not found**
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": { "general": ["Interest Group Does Not Exist"] },
  "response": {}
}
```

---

## 2. Create an impact project

`POST /api/v1/dashboard/ig/{ig_id}/impact-projects/`
`Content-Type: application/json`

`team[].muid` is required for every team member and must match an existing user's `muid`. `is_lead` may be `true` for zero, one, or multiple members — there is no restriction on lead count. `links` is optional and open-ended — any `label` is allowed, not just github/live/figma.

**Request body**
```json
{
  "title": "Community LMS",
  "description": "An online learning platform built for students and mentors.",
  "team": [
    { "muid": "alvin-dennis@mulearn", "is_lead": true },
    { "muid": "akhil-raj@mulearn", "is_lead": false }
  ],
  "links": [
    { "label": "github", "url": "https://github.com/example/community-lms" },
    { "label": "live", "url": "https://lms.example.com" },
    { "label": "figma", "url": "https://figma.com/file/example" }
  ]
}
```

**Response 200**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": [] },
  "response": {
    "impactProject": {
      "id": "b1f2c3d4-...",
      "ig_id": "ig-uuid-here",
      "title": "Community LMS",
      "image": null,
      "description": "An online learning platform built for students and mentors.",
      "team": [
        { "muid": "alvin-dennis@mulearn", "name": "Alvin Dennis", "is_lead": true },
        { "muid": "akhil-raj@mulearn", "name": "Akhil Raj", "is_lead": false }
      ],
      "links": [
        { "label": "github", "url": "https://github.com/example/community-lms" },
        { "label": "live", "url": "https://lms.example.com" },
        { "label": "figma", "url": "https://figma.com/file/example" }
      ],
      "created_by": "Your Full Name",
      "updated_by": "Your Full Name",
      "created_at": "2026-07-24T08:25:30Z",
      "updated_at": "2026-07-24T08:25:30Z"
    }
  }
}
```

**Error cases to try:**

a) Not a lead/admin of this IG → `400`
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["You do not have permission to manage this Interest Group"] }, "response": {} }
```

b) A team entry missing `muid` → `400`
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["Each team member requires a 'muid'."] }, "response": {} }
```

c) `team[].muid` doesn't exist → `400`
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["No user found with muid 'no-such-muid'"] }, "response": {} }
```

d) Bad URL in `links` → `400`
```json
{ "hasError": true, "statusCode": 400, "message": { "general": ["'not-a-url' is not a valid URL."] }, "response": {} }
```

---

## 3. Update an impact project

`PATCH /api/v1/dashboard/ig/{ig_id}/impact-projects/{project_id}/`
`Content-Type: application/json`

Partial update — send only the fields you want to change. Omitting `team`/`links` leaves them untouched; including either one **replaces the entire list** (not a merge). `ig` and `created_by` are silently ignored if sent — a project can't be reassigned to another IG or have its creator forged through this endpoint.

**Request body (rename + replace team)**
```json
{
  "title": "Community LMS v2",
  "team": [
    { "muid": "alvin-dennis@mulearn", "is_lead": true }
  ]
}
```

**Response 200** — same shape as create's response, under `"impactProject"`.

---

## 4. Delete an impact project

`DELETE /api/v1/dashboard/ig/{ig_id}/impact-projects/{project_id}/`

No body.

**Response 200**
```json
{ "hasError": false, "statusCode": 200, "message": { "general": ["Impact Project deleted successfully"] }, "response": {} }
```

---

## 5. Upload / replace the project image

`POST /api/v1/dashboard/ig/{ig_id}/impact-projects/{project_id}/image/`
`Content-Type: multipart/form-data`

**Form fields**
| key | value |
|---|---|
| `image` | (file) a `.png`/`.jpg` under 5 MB |

**Response 200**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": [] },
  "response": { "image": "https://<BE_DOMAIN_NAME>/muback-media/impact_project/image/b1f2c3d4-....png" }
}
```

**Error cases:**
- No file attached → `400` `"No image provided"`
- Non-image file → `400` `"Expected an image file"`
- File over 5 MB → `400` `"Image must be under 5 MB"`

---

## Quick curl examples

```bash
# List
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/dashboard/ig/<ig_id>/impact-projects/

# Create
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"Community LMS","description":"desc","team":[{"muid":"<some-existing-muid>","is_lead":true}],"links":[{"label":"github","url":"https://github.com/example/lms"}]}' \
  http://localhost:8000/api/v1/dashboard/ig/<ig_id>/impact-projects/

# Update
curl -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"Renamed"}' \
  http://localhost:8000/api/v1/dashboard/ig/<ig_id>/impact-projects/<project_id>/

# Delete
curl -X DELETE -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/dashboard/ig/<ig_id>/impact-projects/<project_id>/

# Image upload
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -F "image=@/path/to/photo.png" \
  http://localhost:8000/api/v1/dashboard/ig/<ig_id>/impact-projects/<project_id>/image/
```
