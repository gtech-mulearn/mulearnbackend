# Protected / Organisation


Base path: `/api/protected/organisation/`


## Endpoint: `institutes/<str:organisation_type>/<str:district_name>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:organisation_type`
  - `str:district_name`
- Request body example (JSON):
```json
{
  "organisation_type": "<str:organisation_type>",
  "district_name": "<str:district_name>",
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


## Endpoint: `get-institutes/<str:district_name>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:district_name`
- Request body example (JSON):
```json
{
  "district_name": "<str:district_name>",
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

