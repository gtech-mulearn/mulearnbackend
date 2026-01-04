# Dashboard Location & Organization API Reference

## Location Management

### List Countries
**Endpoint:** `/api/v1/dashboard/location/country/`
**Method:** `GET`
**Brief:** List all countries.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "Country Fetched Successfully"
        ]
    },
    "response": {
        "data": [
            {
                "label": "India",
                "value": "uuid",
                "created_by": "User",
                "updated_by": "User",
                "created_at": "date",
                "updated_at": "date"
            }
        ],
        "pagination": {}
    }
}
```

### Create Country
**Endpoint:** `/api/v1/dashboard/location/country/`
**Method:** `POST`
**Brief:** Create a new country.
**Permissions:** Admin
**Request Body:**
```json
{
    "label": "Country Name"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Country Created Successfully"
        ]
    },
    "response": {
         "label": "Country Name",
         "created_by": "User",
         "updated_by": "User"
    }
}
```

### List States
**Endpoint:** `/api/v1/dashboard/location/state/`
**Method:** `GET`
**Brief:** List all states.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "State Fetched Successfully"
        ]
    },
    "response": {
        "data": [
            {
                "label": "Kerala",
                "value": "uuid",
                "country": "India",
                "created_by": "User",
                "updated_by": "User"
            }
        ],
        "pagination": {}
    }
}
```

### Create State
**Endpoint:** `/api/v1/dashboard/location/state/`
**Method:** `POST`
**Brief:** Create a new state.
**Permissions:** Admin
**Request Body:**
```json
{
    "label": "State Name",
    "country": "country_uuid"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "State Created Successfully"
        ]
    },
    "response": {}
}
```

### List Zones
**Endpoint:** `/api/v1/dashboard/location/zone/`
**Method:** `GET`
**Brief:** List all zones.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Zone Fetched Successfully"
        ]
    },
     "response": {
        "data": [
             {
                 "label": "South",
                 "value": "uuid",
                 "state": "Kerala",
                 "country": "India"
             }
        ]
     }
}
```

### Create Zone
**Endpoint:** `/api/v1/dashboard/location/zone/`
**Method:** `POST`
**Brief:** Create a new zone.
**Permissions:** Admin
**Request Body:**
```json
{
    "label": "Zone Name",
    "state": "state_uuid"
}
```

### List Districts
**Endpoint:** `/api/v1/dashboard/location/district/`
**Method:** `GET`
**Brief:** List all districts.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "District Fetched Successfully"
        ]
    },
     "response": {
        "data": [
             {
                 "label": "Ernakulam",
                 "value": "uuid",
                 "zone": "South",
                 "state": "Kerala",
                 "country": "India"
             }
        ]
     }
}
```

### Create District
**Endpoint:** `/api/v1/dashboard/location/district/`
**Method:** `POST`
**Brief:** Create a new district.
**Permissions:** Admin
**Request Body:**
```json
{
    "label": "District Name",
    "zone": "zone_uuid"
}
```

## Organization Management

### List Institutions
**Endpoint:** `/api/v1/dashboard/organisation/institutes/`
**Method:** `GET`
**Brief:** List all organizations.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Institutions Fetched Successfully"
        ]
    },
    "response": {
        "data": [
            {
                "id": "uuid",
                "title": "College Name",
                "code": "CODE",
                "affiliation": "University Name",
                "district": "District Name",
                "zone": "Zone Name",
                "state": "State Name",
                "country": "Country Name",
                "user_count": 100
            }
        ]
    }
}
```

### Create Institution
**Endpoint:** `/api/v1/dashboard/organisation/institutes/`
**Method:** `POST`
**Brief:** Create a new organization.
**Permissions:** Admin
**Request Body:**
```json
{
    "title": "Organization Title",
    "code": "ORG_CODE",
    "org_type": "College",
    "affiliation": "affiliation_uuid",
    "district": "district_uuid"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Institution Created Successfully"
        ]
    },
    "response": {
        "id": "uuid",
        "title": "Organization Title",
        "code": "ORG_CODE"
    }
}
```

### Edit Institution
**Endpoint:** `/api/v1/dashboard/organisation/institutes/<str:org_code>/`
**Method:** `PUT`
**Brief:** Edit an existing organization.
**Permissions:** Admin
**Request Body:**
```json
{
    "title": "Updated Title",
    "code": "UPDATED_CODE"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Institution Updated Successfully"
        ]
    },
    "response": {}
}
```

### Delete Institution
**Endpoint:** `/api/v1/dashboard/organisation/institutes/<str:org_code>/`
**Method:** `DELETE`
**Brief:** Delete an organization.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Institution Deleted Successfully"
        ]
    },
    "response": {}
}
```

### Verify Organization
**Endpoint:** `/api/v1/dashboard/organisation/institutes/verify/`
**Method:** `PATCH`
**Brief:** Verify an organization.
**Permissions:** Admin
**Request Body:**
```json
{
    "org_id": "org_uuid",
    "verified": true
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Organization Verified Successfully"
        ]
    },
    "response": {}
}
```

### User Affiliation
**Endpoint:** `/api/v1/dashboard/affiliation/`
**Method:** `GET`
**Brief:** List affiliations.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Affiliation Fetched Successfully"
        ]
    },
    "response": [
        {
            "value": "uuid",
            "label": "Affiliation Name"
        }
    ]
}
```

### Create Affiliation
**Endpoint:** `/api/v1/dashboard/affiliation/`
**Method:** `POST`
**Brief:** Create a new affiliation.
**Permissions:** Admin
**Request Body:**
```json
{
    "title": "New Affiliation"
}
```

### Edit Affiliation
**Endpoint:** `/api/v1/dashboard/affiliation/<str:affiliation_id>/`
**Method:** `PUT`
**Brief:** Edit an existing affiliation.
**Permissions:** Admin
**Request Body:**
```json
{
    "title": "Updated Affiliation"
}
```

## Zonal, District, Campus, College Management (Read Only)
These endpoints are primarily read-only data aggregators for dashboard visualization.

### Zonal Details
**Endpoint:** `/api/v1/dashboard/zonal/`
**Method:** `GET`
**Brief:** Get aggregated details for zones.
**Permissions:** Admin

### District Details
**Endpoint:** `/api/v1/dashboard/district/`
**Method:** `GET`
**Brief:** Get aggregated details for districts.
**Permissions:** Admin

### Campus Details
**Endpoint:** `/api/v1/dashboard/campus/`
**Method:** `GET`
**Brief:** Get aggregated details for campuses.
**Permissions:** Admin

### College List
**Endpoint:** `/api/v1/dashboard/college/`
**Method:** `GET`
**Brief:** List colleges.
**Permissions:** Admin
