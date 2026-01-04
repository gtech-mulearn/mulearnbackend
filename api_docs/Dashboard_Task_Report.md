# Dashboard / Task_Report


Base path: `/api/dashboard/task_report/`


## Endpoint: `<str:report_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:report_id`
- Request body example (JSON):
```json
{
  "report_id": "<str:report_id>",
  "status": "PENDING",
  "updated_by": "Moderator Name (optional)"
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
    "data": {
      "id": "<str:report_id>",
      "status": "RESOLVED"
    }
  }
}
```

### Update (PUT)
- Method: PUT
- Path: `/api/dashboard/task_report/<report_id>/`
- Brief: Update a task report's `status`. Requires role Admin or Fellow.
- Full request body (all params accepted):

```json
{
  "status": "RESOLVED",
  "updated_by": "Moderator Name (optional)"
}
```

- Success (200):

```json
{
  "hasError": false,
  "statusCode": 200,
  "message": { "general": ["Report status updated successfully"] },
  "response": {}
}
```

- Failure (not found) example (400):

```json
{
  "hasError": true,
  "statusCode": 400,
  "message": { "general": ["Report not found"] },
  "response": {}
}
```

- Failure (validation) example (400):

```json
{
  "hasError": true,
  "statusCode": 400,
  "message": {
    "status": ["This field is required."]
  },
  "response": {}
}
```


## Endpoint: `group-by-reporter/`
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

