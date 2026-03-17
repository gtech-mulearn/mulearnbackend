# IG Task Summary API - Test Data Setup Guide

## How to Load Test Data

### Option 1: Using MySQL Command Line

```bash
# Connect to your database
mysql -u your_username -p your_database < IG_TASK_SUMMARY_TEST_DATA.sql
```

### Option 2: Using Django Shell

```bash
python manage.py shell
```

Then in the shell, execute the SQL directly:

```python
from django.db import connection
with connection.cursor() as cursor:
    with open('IG_TASK_SUMMARY_TEST_DATA.sql', 'r') as f:
        cursor.execute(f.read())
```

### Option 3: Copy-Paste into phpMyAdmin / MySQL Workbench

Simply copy the contents of `IG_TASK_SUMMARY_TEST_DATA.sql` and paste into your MySQL client.

## Test Data Summary

### Interest Group
- **ID:** `ig-test-001`
- **Name:** Web Development
- **Code:** WEB
- **Status:** Active

### Users (6 total)
1. **Alice Johnson** (alicejohnson@mulearn) - 540 karma
2. **Bob Smith** (bobsmith@mulearn) - 480 karma
3. **Carol White** (carolwhite@mulearn) - 420 karma
4. **David Brown** (davidbrown@mulearn) - 350 karma
5. **Eva Jones** (evajones@mulearn) - 280 karma
6. **Admin User** (admin@mulearn) - Used for created_by

### Tasks (5 total)
1. Learn HTML Basics - 100 karma
2. Master CSS Styling - 120 karma
3. JavaScript Fundamentals - 150 karma
4. Introduction to React - 200 karma
5. RESTful API Design - 180 karma

### KarmaActivityLog (15 total entries)
- **Total tasks completed:** 15
- **Total karma awarded:** 3,720
- **Unique contributors:** 5

## Test Scenarios

### Scenario 1: Get All Data (No Date Filter)

```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/ig/ig-test-001/task-summary/" \
  -H "Authorization: Bearer {your_jwt_token}" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Task summary fetched successfully"]
  },
  "response": {
    "ig_id": "ig-test-001",
    "ig_name": "Web Development",
    "ig_code": "WEB",
    "total_tasks_completed": 15,
    "total_karma_awarded": 3720,
    "unique_contributors": 5,
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
      },
      {
        "full_name": "Carol White",
        "muid": "carolwhite@mulearn",
        "karma_earned": 420
      },
      {
        "full_name": "David Brown",
        "muid": "davidbrown@mulearn",
        "karma_earned": 350
      },
      {
        "full_name": "Eva Jones",
        "muid": "evajones@mulearn",
        "karma_earned": 280
      }
    ],
    "date_range": {
      "from_date": null,
      "to_date": null
    }
  }
}
```

### Scenario 2: Filter by Date Range (January Only)

```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/ig/ig-test-001/task-summary/?from_date=2025-01-01&to_date=2025-01-31" \
  -H "Authorization: Bearer {your_jwt_token}" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "response": {
    "total_tasks_completed": 6,
    "total_karma_awarded": 990,
    "unique_contributors": 5,
    "top_contributors": [
      {"full_name": "Alice Johnson", "muid": "alicejohnson@mulearn", "karma_earned": 220},
      {"full_name": "Bob Smith", "muid": "bobsmith@mulearn", "karma_earned": 220},
      {"full_name": "Carol White", "muid": "carolwhite@mulearn", "karma_earned": 220},
      {"full_name": "Eva Jones", "muid": "evajones@mulearn", "karma_earned": 100}
    ],
    "date_range": {
      "from_date": "2025-01-01",
      "to_date": "2025-01-31"
    }
  }
}
```

### Scenario 3: Filter by Date Range (February Only)

```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/ig/ig-test-001/task-summary/?from_date=2025-02-01&to_date=2025-02-28" \
  -H "Authorization: Bearer {your_jwt_token}" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "response": {
    "total_tasks_completed": 9,
    "total_karma_awarded": 2730,
    "unique_contributors": 5,
    "top_contributors": [
      {"full_name": "Alice Johnson", "muid": "alicejohnson@mulearn", "karma_earned": 320},
      {"full_name": "Bob Smith", "muid": "bobsmith@mulearn", "karma_earned": 260},
      {"full_name": "Carol White", "muid": "carolwhite@mulearn", "karma_earned": 200},
      {"full_name": "David Brown", "muid": "davidbrown@mulearn", "karma_earned": 350},
      {"full_name": "Eva Jones", "muid": "evajones@mulearn", "karma_earned": 180}
    ],
    "date_range": {
      "from_date": "2025-02-01",
      "to_date": "2025-02-28"
    }
  }
}
```

### Scenario 4: No Results (Future Date)

```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/ig/ig-test-001/task-summary/?from_date=2026-01-01&to_date=2026-12-31" \
  -H "Authorization: Bearer {your_jwt_token}" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "response": {
    "total_tasks_completed": 0,
    "total_karma_awarded": 0,
    "unique_contributors": 0,
    "top_contributors": [],
    "date_range": {
      "from_date": "2026-01-01",
      "to_date": "2026-12-31"
    }
  }
}
```

### Scenario 5: Invalid IG ID

```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/ig/invalid-ig-id/task-summary/" \
  -H "Authorization: Bearer {your_jwt_token}" \
  -H "Content-Type: application/json"
```

**Expected Response:**
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

### Scenario 6: Invalid Date Format

```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/ig/ig-test-001/task-summary/?from_date=01/01/2025" \
  -H "Authorization: Bearer {your_jwt_token}" \
  -H "Content-Type: application/json"
```

**Expected Response:**
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

## Notes

- All timestamps use `NOW()` which will insert the current server time
- Adjust UUIDs if needed based on your system's UUID format
- Make sure `admin-001` user exists in your database (or adjust created_by/updated_by IDs)
- The test data assumes the `interest_group`, `task_list`, `user`, `task_type`, and `channel` tables exist
- KarmaActivityLog entries have peer_approved and appraiser_approved set to 1 (approved tasks)

## Clean Up

To remove test data, run:

```sql
DELETE FROM karma_activity_log WHERE id LIKE 'kal-%';
DELETE FROM task_list WHERE id LIKE 'task-%';
DELETE FROM task_type WHERE id LIKE 'task-type-%';
DELETE FROM channel WHERE id = 'channel-001';
DELETE FROM interest_group WHERE id = 'ig-test-001';
DELETE FROM user WHERE muid IN ('alicejohnson@mulearn', 'bobsmith@mulearn', 'carolwhite@mulearn', 'davidbrown@mulearn', 'evajones@mulearn');
```
