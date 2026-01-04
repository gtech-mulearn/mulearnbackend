# Dashboard / Lc


Base path: `/api/dashboard/lc/`


## Endpoint: `meets/list/`
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


## Endpoint: `meets/list/<str:is_user>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:is_user`
- Request body example (JSON):
```json
{
  "is_user": "<str:is_user>",
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


## Endpoint: `<str:circle_id>/meet/create/`
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


## Endpoint: `<str:circle_id>/meet/list/`
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


## Endpoint: `meets/report/<str:meet_id>/`
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


## Endpoint: `meets/attendee-report/<str:meet_id>/`
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


## Endpoint: `meets/attendee-report/<str:meet_id>/<str:task_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:meet_id`
  - `str:task_id`
- Request body example (JSON):
```json
{
  "meet_id": "<str:meet_id>",
  "task_id": "<str:task_id>",
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


## Endpoint: `meets/verify-list/`
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


## Endpoint: `meets/verify/<str:meet_id>/`
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


## Endpoint: `meets/attendees/<str:meet_id>/`
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


## Endpoint: `meets/interested/<str:meet_id>/`
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


## Endpoint: `meets/info/<str:meet_id>/`
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


## Endpoint: `meets/join/<str:meet_code_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:meet_code_id`
- Request body example (JSON):
```json
{
  "meet_code_id": "<str:meet_code_id>",
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


## Endpoint: `user-list/`
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


## Endpoint: `stats/`
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


## Endpoint: `<str:circle_id>/details/`
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


## Endpoint: `<str:circle_id>/schedule-meet/`
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


## Endpoint: `<str:circle_id>/add-member/`
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


## Endpoint: `join/<str:circle_id>/`
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


## Endpoint: `<str:circle_id>/ig-progress/`
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


## Endpoint: `<str:circle_id>/lead-transfer/<str:new_lead_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:circle_id`
  - `str:new_lead_id`
- Request body example (JSON):
```json
{
  "circle_id": "<str:circle_id>",
  "new_lead_id": "<str:new_lead_id>",
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


## Endpoint: `<str:circle_id>/note/edit/`
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


## Endpoint: `<str:circle_id>/user-accept-reject/<str:member_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:circle_id`
  - `str:member_id`
- Request body example (JSON):
```json
{
  "circle_id": "<str:circle_id>",
  "member_id": "<str:member_id>",
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


## Endpoint: `list-all/<str:circle_code>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:circle_code`
- Request body example (JSON):
```json
{
  "circle_code": "<str:circle_code>",
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


## Endpoint: `list-all/`
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


## Endpoint: `list-members/<str:circle_id>/`
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


## Endpoint: `invite/`
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


## Endpoint: `meet-record/list-all/<str:circle_id>/`
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


## Endpoint: `meet-record/edit/<str:circle_id>/`
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


## Endpoint: `member/invite/<str:circle_id>/<str:muid>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:circle_id`
  - `str:muid`
- Request body example (JSON):
```json
{
  "circle_id": "<str:circle_id>",
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


## Endpoint: `member/invite/status/<str:circle_id>/<str:muid>/<str:status>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:circle_id`
  - `str:muid`
  - `str:status`
- Request body example (JSON):
```json
{
  "circle_id": "<str:circle_id>",
  "muid": "<str:muid>",
  "status": "<str:status>",
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

