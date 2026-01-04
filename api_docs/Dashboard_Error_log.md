# Dashboard / Error_Log


Base path: `/api/dashboard/error_log/`


## Endpoint: `graph/`
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


## Endpoint: `tab/`
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


## Endpoint: `patch/<str:error_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:error_id`
- Request body example (JSON):
```json
{
  "error_id": "<str:error_id>",
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


## Endpoint: `<str:log_name>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:log_name`
- Request body example (JSON):
```json
{
  "log_name": "<str:log_name>",
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


## Endpoint: `view/<str:log_name>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:log_name`
- Request body example (JSON):
```json
{
  "log_name": "<str:log_name>",
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


## Endpoint: `clear/<str:log_name>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:log_name`
- Request body example (JSON):
```json
{
  "log_name": "<str:log_name>",
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

