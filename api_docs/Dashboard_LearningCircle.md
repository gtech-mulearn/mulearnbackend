# Dashboard / Learningcircle


Base path: `/api/dashboard/learningcircle/`


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


## Endpoint: `info/<str:circle_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:circle_id`
- Request body example (JSON):
```json
{
  "circle_id": "<str:circle_id>",
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


## Endpoint: `members/<str:circle_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:circle_id`
- Request body example (JSON):
```json
{
  "circle_id": "<str:circle_id>",
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


## Endpoint: `edit/<str:circle_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:circle_id`
- Request body example (JSON):
```json
{
  "circle_id": "<str:circle_id>",
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


## Endpoint: `delete/<str:circle_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:circle_id`
- Request body example (JSON):
```json
{
  "circle_id": "<str:circle_id>",
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


## Endpoint: `meeting/create/<str:circle_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:circle_id`
- Request body example (JSON):
```json
{
  "circle_id": "<str:circle_id>",
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


## Endpoint: `meeting/list-public/`
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


## Endpoint: `meeting/list/`
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


## Endpoint: `meeting/list/<str:circle_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:circle_id`
- Request body example (JSON):
```json
{
  "circle_id": "<str:circle_id>",
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


## Endpoint: `meeting/edit/<str:meet_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:meet_id`
- Request body example (JSON):
```json
{
  "meet_id": "<str:meet_id>",
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


## Endpoint: `meeting/info/<str:meet_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:meet_id`
- Request body example (JSON):
```json
{
  "meet_id": "<str:meet_id>",
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


## Endpoint: `meeting/delete/<str:meet_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:meet_id`
- Request body example (JSON):
```json
{
  "meet_id": "<str:meet_id>",
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


## Endpoint: `meeting/join/<str:meet_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:meet_id`
- Request body example (JSON):
```json
{
  "meet_id": "<str:meet_id>",
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


## Endpoint: `meeting/rsvp/<str:meet_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:meet_id`
- Request body example (JSON):
```json
{
  "meet_id": "<str:meet_id>",
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


## Endpoint: `meeting/leave/<str:meet_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:meet_id`
- Request body example (JSON):
```json
{
  "meet_id": "<str:meet_id>",
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


## Endpoint: `meeting/attendee-report/<str:meet_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:meet_id`
- Request body example (JSON):
```json
{
  "meet_id": "<str:meet_id>",
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


## Endpoint: `meeting/report/<str:meet_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:meet_id`
- Request body example (JSON):
```json
{
  "meet_id": "<str:meet_id>",
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

