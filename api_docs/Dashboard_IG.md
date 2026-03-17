# Dashboard / Ig


Base path: `/api/dashboard/ig/`


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


## Endpoint: `csv/`
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


## Endpoint: `<str:pk>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:pk`
- Request body example (JSON):
```json
{
  "pk": "<str:pk>",
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


## Endpoint: `get/<str:pk>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:pk`
- Request body example (JSON):
```json
{
  "pk": "<str:pk>",
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


## Endpoint: `<str:ig_id>/task-summary/`
- Brief: Get task activity summary for a specific Interest Group.
- Path params:
  - `str:ig_id`
- Request body example (JSON):
```json
{
  "from_date": "YYYY-MM-DD",
  "to_date": "YYYY-MM-DD"
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


