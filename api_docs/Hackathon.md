# Hackathon API Reference

## List Hackathons
**Endpoint:** `/api/v1/hackathon/list-hackathons/`
**Method:** `GET`
**Brief:** List all hackathons (published or owned by user).

**Response Body:**
```json
{
  "response": [
    {
       "id": "uuid",
       "title": "string",
       "tagline": "string",
       "description": "string",
       "status": "string (Draft/Published/Completed/Deleted)"
    }
  ]
}
```

## List Upcoming Hackathons
**Endpoint:** `/api/v1/hackathon/list-hackathons/upcoming/`
**Method:** `GET`
**Brief:** List upcoming hackathons.

## Create Hackathon
**Endpoint:** `/api/v1/hackathon/create-hackathon/`
**Method:** `POST`
**Brief:** Create a new hackathon.

**Request Body:**
```json
{
  "title": "string",
  "tagline": "string (optional)",
  "description": "string (optional)",
  "participant_count": 0,
  "org_id": "uuid (optional)",
  "district_id": "uuid (optional)",
  "place": "string (optional)",
  "is_open_to_all": false,
  "application_start": "datetime",
  "application_ends": "datetime",
  "event_start": "datetime",
  "event_end": "datetime",
  "status": "string (Draft)",
  "form_fields": { "field_name": "field_type" },
  "type": "offline/online",
  "website": "string",
  "event_logo": "file",
  "banner": "file"
}
```

## Edit Hackathon
**Endpoint:** `/api/v1/hackathon/edit-hackathon/<str:hackathon_id>/`
**Method:** `PUT`
**Brief:** Update hackathon details.
**Request Body:** Same as Create Hackathon.

## Delete Hackathon
**Endpoint:** `/api/v1/hackathon/delete-hackathon/<str:hackathon_id>/`
**Method:** `DELETE`
**Brief:** Delete a hackathon (soft delete usually).

## Publish Hackathon
**Endpoint:** `/api/v1/hackathon/publish-hackathon/<str:hackathon_id>/`
**Method:** `PUT`
**Brief:** Change hackathon status to Published.

**Request Body:**
```json
{
  "status": "Published"
}
```

## Hackathon Info
**Endpoint:** `/api/v1/hackathon/info/<str:hackathon_id>/`
**Method:** `GET`
**Brief:** Get detailed info about a hackathon.

## Submit Hackathon Application
**Endpoint:** `/api/v1/hackathon/submit-hackathon/`
**Method:** `POST`
**Brief:** User submission for a hackathon.

**Request Body:**
```json
{
  "hackathon_id": "uuid",
  "data": { "custom_field": "value" }
}
```

## List Applicants
**Endpoint:** `/api/v1/hackathon/list-applicants/<str:hackathon_id>/`
**Method:** `GET`
**Brief:** List all applicants for a hackathon.

## Add Organiser
**Endpoint:** `/api/v1/hackathon/add-organiser/<str:hackathon_id>/`
**Method:** `POST`
**Brief:** Add an organizer to a hackathon.

**Request Body:**
```json
{
  "muid": "string"
}
```

## Delete Organiser
**Endpoint:** `/api/v1/hackathon/delete-organiser/<str:organiser_link_id>/`
**Method:** `DELETE`
**Brief:** Remove an organizer from a hackathon.

## List Organisations
**Endpoint:** `/api/v1/hackathon/list-organisations/`
**Method:** `GET`
**Brief:** List simplified organizations for dropdowns.

## List Districts
**Endpoint:** `/api/v1/hackathon/list-districts/`
**Method:** `GET`
**Brief:** List simplified districts for dropdowns.

## List Form Fields
**Endpoint:** `/api/v1/hackathon/list-form/<str:hackathon_id>/`
**Method:** `GET`
**Brief:** Get form fields for a specific hackathon.
