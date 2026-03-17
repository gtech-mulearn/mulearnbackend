# IG Task Summary API - Testing Guide

## Endpoint Details

**Method:** GET
**Path:** `/api/v1/dashboard/ig/<ig_id>/task-summary/`
**Auth Required:** Yes (JWT Token)
**Allowed Roles:** ADMIN, FELLOW, ASSOCIATE

## Query Parameters

- `from_date` (optional): Start date in YYYY-MM-DD format
- `to_date` (optional): End date in YYYY-MM-DD format

## Test Cases

### 1. Success Case - Without Date Range

```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/ig/{ig_id}/task-summary/" \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json"
```

**Expected Response (200):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Task summary fetched successfully"]
  },
  "response": {
    "ig_id": "abc-123",
    "ig_name": "Web Development",
    "ig_code": "WEB",
    "total_tasks_completed": 124,
    "total_karma_awarded": 3720,
    "unique_contributors": 38,
    "top_contributors": [
      {
        "full_name": "Alice Johnson",
        "muid": "alicejohnson@mulearn",
        "karma_earned": 540
      },
      {
        "full_name": "Bob Smith",
        "muid": "bobsmith@mulearn",
        "karma_earned": 480
      }
    ],
    "date_range": {
      "from_date": null,
      "to_date": null
    }
  }
}
```

### 2. Success Case - With Date Range

```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/ig/{ig_id}/task-summary/?from_date=2025-01-01&to_date=2025-03-14" \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json"
```

**Expected Response (200):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Task summary fetched successfully"]
  },
  "response": {
    "ig_id": "abc-123",
    "ig_name": "Web Development",
    "ig_code": "WEB",
    "total_tasks_completed": 50,
    "total_karma_awarded": 1500,
    "unique_contributors": 20,
    "top_contributors": [...],
    "date_range": {
      "from_date": "2025-01-01",
      "to_date": "2025-03-14"
    }
  }
}
```

### 3. Error Case - IG Not Found

```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/ig/invalid-ig-id/task-summary/" \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json"
```

**Expected Response (404):**
```json
{
  "hasError": true,
  "statusCode": 404,
  "message": {
    "general": ["Interest Group not found"]
  },
  "response": {}
}
```

### 4. Error Case - Invalid Date Format

```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/ig/{ig_id}/task-summary/?from_date=01/01/2025" \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json"
```

**Expected Response (400):**
```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "general": ["Invalid date format. Use YYYY-MM-DD"]
  },
  "response": {}
}
```

### 5. Success Case - No Activity in Date Range

```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/ig/{ig_id}/task-summary/?from_date=2020-01-01&to_date=2020-12-31" \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json"
```

**Expected Response (200 - NOT a failure):**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Task summary fetched successfully"]
  },
  "response": {
    "ig_id": "abc-123",
    "ig_name": "Web Development",
    "ig_code": "WEB",
    "total_tasks_completed": 0,
    "total_karma_awarded": 0,
    "unique_contributors": 0,
    "top_contributors": [],
    "date_range": {
      "from_date": "2020-01-01",
      "to_date": "2020-12-31"
    }
  }
}
```

### 6. Error Case - Unauthenticated

```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/ig/{ig_id}/task-summary/"
```

**Expected Response (401):** Unauthorized

### 7. Error Case - Wrong Role

**User with STUDENT role** calling the endpoint

**Expected Response (403):** Forbidden

## Testing Checklist

- [x] New view `IGTaskSummaryAPI` added to `dash_ig_view.py`
- [x] URL registered in `urls.py` (proper ordering - before generic `<str:pk>/`)
- [x] Date range filtering works correctly (from_date and to_date)
- [x] Returns zeros (not failure) when no activity exists
- [x] Returns failure when ig_id is invalid
- [x] No N+1 queries - uses ORM aggregation (Count, Sum, annotate, values, distinct)
- [x] Follows existing code style and conventions
- [x] Proper error handling with appropriate HTTP status codes
- [x] Response format matches specification exactly

## Key Implementation Details

### ORM Query Strategy

The implementation uses efficient ORM queries to avoid N+1 issues:

1. **Task Count:** `karma_logs.count()` - Single count query
2. **Total Karma:** `karma_logs.aggregate(total=Sum("karma"))` - Single aggregation query
3. **Unique Contributors:** `karma_logs.filter(user_id__isnull=False).values("user_id").distinct().count()` - Single distinct count
4. **Top 5 Contributors:** Uses `values()`, `annotate()`, and `order_by()` for efficient grouping and sorting in a single query

### Date Filtering

- Uses Django Q objects for clean conditional filtering
- Validates date format before building queries
- Returns appropriate error responses for invalid formats
- Handles null dates gracefully (returns all data when dates not provided)

### Response Format

- Follows the CustomResponse pattern used throughout the codebase
- Returns hasError, statusCode, message with general array, and response object
- Includes date_range in response for auditability
- Top contributors limited to 5 items ordered by karma_earned descending
