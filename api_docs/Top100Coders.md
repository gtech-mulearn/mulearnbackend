# Top 100 Coders API Reference

## Leaderboard
**Endpoint:** `/api/v1/top-100/leaderboard/`
**Method:** `GET`
**Brief:** Get the Top 100 Coders leaderboard.

**Response Body:**
```json
{
  "response": [
    {
      "id": "uuid",
      "full_name": "string",
      "profile_pic": "url",
      "total_karma": 0,
      "org": "string",
      "dis": "string",
      "state": "string",
      "time_": "datetime"
    }
  ]
}
```
