# Leaderboard API Reference

## Students Leaderboard
**Endpoint:** `/api/v1/leaderboard/students/`
**Method:** `GET`
**Brief:** Retrieve the top 20 students based on karma.

**Response Body:**
```json
{
  "response": [
    {
      "full_name": "string",
      "total_karma": 0,
       "college": "string"
    }
  ]
}
```

## Students Monthly Leaderboard
**Endpoint:** `/api/v1/leaderboard/students-monthly/`
**Method:** `GET`
**Brief:** Retrieve the top 20 students based on karma earned in the previous month.

**Response Body:**
```json
{
  "response": [
    {
      "full_name": "string",
      "total_karma": 0,
      "institution": "string"
    }
  ]
}
```

## College Leaderboard
**Endpoint:** `/api/v1/leaderboard/college/`
**Method:** `GET`
**Brief:** Retrieve the top 20 colleges based on total student karma.

**Response Body:**
```json
{
  "response": [
    {
      "code": "string",
      "title": "string",
      "total_students": 0,
      "total_karma": 0
    }
  ]
}
```

## College Monthly Leaderboard
**Endpoint:** `/api/v1/leaderboard/college-monthly/`
**Method:** `GET`
**Brief:** Retrieve the top 20 colleges based on karma earned in the previous month.

**Response Body:**
```json
{
  "response": [
    {
      "code": "string",
      "total_karma": 0,
      "students": 0
    }
  ]
}
```

## Wadhwani College Leaderboard
**Endpoint:** `/api/v1/leaderboard/wadhwani-college/`
**Method:** `GET`
**Brief:** Retrieve the top 12 colleges based on karma from Wadhwani-specific tasks.

**Response Body:**
```json
{
  "response": [
      {
          "code": "string",
          "title": "string",
          "total_karma": 0,
          "students": 0
      }
  ]
}
```

## Wadhwani Zonal Leaderboard
**Endpoint:** `/api/v1/leaderboard/wadhwani-zonal/`
**Method:** `GET`
**Brief:** Retrieve zonal leaderboard based on Wadhwani task karma.

**Response Body:**
```json
{
  "response": [
      {
          "zone_name": "string",
          "total_karma": 0,
          "students": 0
      }
  ]
}
```
