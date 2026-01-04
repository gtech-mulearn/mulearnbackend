# Dashboard / Affiliation


Base path: `/api/dashboard/affiliation/`


## Endpoint: `<str:affiliation_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:affiliation_id`
- Request body example (JSON):
```json
{
  "affiliation_id": "<str:affiliation_id>",
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

