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

