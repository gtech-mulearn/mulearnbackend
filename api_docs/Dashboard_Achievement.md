# Dashboard / Achievement


Base path: `/api/dashboard/achievement/`


## Endpoint: `list/`
- Brief: Retrieval/list endpoint.
- Request body example (JSON):
```json
{
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


## Endpoint: `create/`
- Brief: Collection endpoint.
- Request body example (JSON):
```json
{
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


## Endpoint: `update/<str:achievement_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:achievement_id`
- Request body example (JSON):
```json
{
  "achievement_id": "<str:achievement_id>",
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


## Endpoint: `delete/<str:achievement_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:achievement_id`
- Request body example (JSON):
```json
{
  "achievement_id": "<str:achievement_id>",
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


## Endpoint: `list/user/<str:muid>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:muid`
- Request body example (JSON):
```json
{
  "muid": "<str:muid>",
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


## Endpoint: `issue-vc/`
- Brief: Collection endpoint.
- Request body example (JSON):
```json
{
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

```


## Endpoint: `bulk-claim/`
- Brief: Bulk sync endpoint to check and issue all eligible achievements for users active within a date range. Requires API Key authentication.
- Method: `POST`
- Headers:
  - `Api-Key: <BACKEND_API_KEY>`
  - `Content-Type: application/json`
- Request body example (JSON):
```json
{
  "date_from": "2026-01-14",
  "date_to": "2026-01-15"
}
```
- Response example (success):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": [
      "Bulk sync job scheduled successfully."
    ]
  },
  "response": {}
}
```
- Notes:
  - Both `date_from` and `date_to` are optional and default to yesterday's date.
  - The task runs asynchronously via Celery.
  - Logs are written to `logs/root.log`.

