# Dashboard / Events


Base path: `/api/dashboard/events/`


## Endpoint: `<str:event_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:event_id`
- Request body example (JSON):
```json
{
  "event_id": "<str:event_id>",
  "field1": "value1",
  "field2": "value2"
}
```
- Response example (success):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Success"
    ]
  },
  "response": {
    "data": "..."
  }
}
```

