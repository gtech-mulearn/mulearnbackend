# Dashboard / Channels


Base path: `/api/dashboard/channels/`


## Endpoint: `<str:channel_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:channel_id`
- Request body example (JSON):
```json
{
  "channel_id": "<str:channel_id>",
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

