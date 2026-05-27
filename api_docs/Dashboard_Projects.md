# Dashboard / Projects

Base path: `/api/v1/dashboard/projects/`

All write endpoints require a valid JWT (`Authorization: Bearer <token>`).  
Read endpoints (GET) accept optional auth — unauthenticated requests see only `published` projects.

---

## Endpoint: `` (collection)

### `GET /`
List projects. Results are paginated.

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `muid` | string | Filter to projects created by or featuring this mulearn ID |
| `created_by` | string (UUID) | Filter to projects created by this user ID |
| `status` | `draft` \| `published` \| `archived` | Filter by status. Omitting this returns all statuses for the owner; public visitors always see only `published` |
| `search` | string | Full-text search on `title` and `description` |
| `sort_by` | string | Sort field, e.g. `created_at` |
| `page` | integer | Page number |
| `per_page` | integer | Items per page |

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "Projects": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "My Project",
        "description": "A short description of the project.",
        "status": "published",
        "logo": "https://example.com/media/projects/logos/logo.png",
        "images": [{ "image": "https://example.com/media/projects/images/img.png" }],
        "links": [
          { "id": "...", "label": "GitHub", "url": "https://github.com/...", "position": 0 }
        ],
        "skills": [
          { "id": "...", "name": "Python", "code": "PY", "icon": null }
        ],
        "members": [
          {
            "id": "...", "is_linked": true, "user_id": "...",
            "muid": "MU-1234", "full_name": "Alice", "profile_pic": null,
            "external_name": null, "role": "Backend", "created_at": "2025-01-01T00:00:00Z"
          }
        ],
        "votes": [
          { "id": "...", "vote": "upvote", "project": "...", "user": "Alice", "user_id": "...", "created_at": "...", "updated_at": "..." }
        ],
        "comments": [
          { "id": "...", "comment": "Great work!", "project": "...", "user": "Bob", "user_id": "...", "created_at": "...", "updated_at": "..." }
        ],
        "created_by": "Alice",
        "created_by_id": "550e8400-e29b-41d4-a716-446655440001",
        "updated_by": "Alice",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-02T00:00:00Z"
      }
    ],
    "pagination": {
      "count": 42,
      "totalPages": 5,
      "isNext": true,
      "isPrev": false,
      "nextPage": 2
    }
  }
}
```

---

### `POST /`
Create a new project. **Auth required.**  
Request must be `multipart/form-data` (because of file fields).

**Form fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Project title (max 50 chars) |
| `description` | string | Yes | Project description |
| `status` | `draft` \| `published` \| `archived` | No | Defaults to `published` |
| `logo` | file | No | Project logo image |
| `images` | file[] | No | Additional project screenshots |
| `links_json` | string (JSON) | No | JSON array of `{ label, url, position? }` objects |
| `skill_ids_json` | string (JSON) | No | JSON array of skill ID strings |

**`links_json` example value:**
```json
[{"label":"GitHub","url":"https://github.com/myorg/myrepo"},{"label":"Live Demo","url":"https://myapp.com"}]
```

**`skill_ids_json` example value:**
```json
["skill-uuid-1","skill-uuid-2"]
```

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "Project": { "id": "...", "title": "My Project", "...": "..." }
  }
}
```

---

## Endpoint: `<uuid:pk>/`

### `GET <uuid:pk>/`
Retrieve a single project by ID.

**Path params:** `pk` — project UUID

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "Project": { "id": "...", "title": "My Project", "...": "..." }
  }
}
```

---

### `PUT <uuid:pk>/`
Update a project. **Auth required.** Partial updates are supported.  
Request must be `multipart/form-data`.

**Path params:** `pk` — project UUID

**Form fields:** same as `POST /`, all fields optional. Submitting `images` replaces all existing images. Submitting `links_json` replaces all links. Submitting `skill_ids_json` replaces all skill tags.

**Response (success):** same shape as `POST /`.

---

### `DELETE <uuid:pk>/`
Delete a project. **Auth required** (must be project owner).

**Path params:** `pk` — project UUID

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Project deleted successfully"] },
  "response": {}
}
```

---

## Endpoint: `<uuid:pk>/status/`

### `PATCH <uuid:pk>/status/`
Change a project's publication status. **Auth required** (must be project owner).

**Path params:** `pk` — project UUID

**Request body (JSON):**
```json
{
  "status": "archived"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `draft` \| `published` \| `archived` | New status |

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "Project": { "id": "...", "status": "archived", "...": "..." }
  }
}
```

---

## Endpoint: `<uuid:project_id>/members/`

### `GET <uuid:project_id>/members/`
List all team members of a project. **Auth required.**

**Path params:** `project_id` — project UUID

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "Members": [
      {
        "id": "...",
        "is_linked": true,
        "user_id": "...",
        "muid": "MU-1234",
        "full_name": "Alice",
        "profile_pic": null,
        "external_name": null,
        "role": "Backend",
        "created_at": "2025-01-01T00:00:00Z"
      },
      {
        "id": "...",
        "is_linked": false,
        "user_id": null,
        "muid": null,
        "full_name": "Bob External",
        "profile_pic": null,
        "external_name": "Bob External",
        "role": "Designer",
        "created_at": "2025-01-02T00:00:00Z"
      }
    ]
  }
}
```

---

### `POST <uuid:project_id>/members/`
Add a team member to a project. **Auth required** (must be project owner).

Provide exactly one of `muid`, `user_id`, or `external_name` to identify the member.

**Path params:** `project_id` — project UUID

**Request body (JSON):**
```json
{ "muid": "MU-5678", "role": "Frontend" }
```
or
```json
{ "user_id": "550e8400-...", "role": "Backend" }
```
or
```json
{ "external_name": "Jane Doe", "role": "Designer" }
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `muid` | string | One of three | Mulearn ID of an existing user |
| `user_id` | string (UUID) | One of three | Internal user ID |
| `external_name` | string | One of three | Free-text name for non-mulearn contributors (max 100 chars) |
| `role` | string | No | Member's role on the project (max 50 chars) |

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "Member": {
      "id": "...", "is_linked": true, "user_id": "...",
      "muid": "MU-5678", "full_name": "Alice", "profile_pic": null,
      "external_name": null, "role": "Frontend", "created_at": "..."
    }
  }
}
```

---

## Endpoint: `<uuid:project_id>/members/<uuid:pk>/`

### `DELETE <uuid:project_id>/members/<uuid:pk>/`
Remove a team member from a project. **Auth required** (must be project owner).

**Path params:**
- `project_id` — project UUID
- `pk` — member UUID

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Member removed"] },
  "response": {}
}
```

---

## Endpoint: `vote/`

### `POST vote/`
Cast or update a vote on a project (upsert — one vote per user per project). **Auth required.**

**Request body (JSON):**
```json
{
  "vote": "upvote",
  "project": "550e8400-e29b-41d4-a716-446655440000"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `vote` | `upvote` \| `downvote` | Vote type |
| `project` | string (UUID) | Project to vote on |

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "Vote": {
      "id": "...", "vote": "upvote", "project": "...",
      "user": "Alice", "user_id": "...",
      "created_at": "...", "updated_at": "..."
    }
  }
}
```

---

## Endpoint: `vote/<uuid:pk>/`

### `DELETE vote/<uuid:pk>/`
Remove a vote. **Auth required** (must be vote owner).

**Path params:** `pk` — vote UUID

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Vote deleted successfully"] },
  "response": {}
}
```

---

## Endpoint: `comment/`

### `POST comment/`
Post a comment on a project. **Auth required.**

**Request body (JSON):**
```json
{
  "comment": "This is a great project!",
  "project": "550e8400-e29b-41d4-a716-446655440000"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `comment` | string | Comment text |
| `project` | string (UUID) | Project to comment on |

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Success"] },
  "response": {
    "Comment": {
      "id": "...", "comment": "This is a great project!", "project": "...",
      "user": "Alice", "user_id": "...",
      "created_at": "...", "updated_at": "..."
    }
  }
}
```

---

## Endpoint: `comment/<uuid:pk>/`

### `PUT comment/<uuid:pk>/`
Edit a comment. **Auth required** (must be comment owner).

**Path params:** `pk` — comment UUID

**Request body (JSON):**
```json
{ "comment": "Updated comment text." }
```

**Response (success):** same shape as `POST comment/`.

---

### `DELETE comment/<uuid:pk>/`
Delete a comment. **Auth required** (must be comment owner).

**Path params:** `pk` — comment UUID

**Response (success):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["comment deleted successfully"] },
  "response": {}
}
```
