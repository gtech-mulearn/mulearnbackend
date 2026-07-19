# Dashboard / Roles


Base path: `/api/dashboard/roles/`


## Endpoint: `user-role/<str:role_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:role_id`
- Request body example (JSON):
```json
{
  "role_id": "<str:role_id>",
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


## Endpoint: `base-template/`
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


## Endpoint: `bulk-assign/`
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


## Endpoint: `bulk-assign/<str:role_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:role_id`
- Request body example (JSON):
```json
{
  "role_id": "<str:role_id>",
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


## Endpoint: `bulk-assign-excel/`
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


## Endpoint: `user-role/`
- Brief: Assign a role to a single user and provision any required downstream resources.
- Headers required:
  - `Authorization: Bearer <token>`
- Request body examples:
  - General role assignment:
    ```json
    {
      "user_id": "<uuid>",
      "role_id": "<role-uuid>"
    }
    ```
  - Intern role assignment:
    ```json
    {
      "user_id": "<uuid>",
      "role_id": "<intern-role-uuid>",
      "guild": "Backend Guild"
    }
    ```
  - Mentor role assignment (General mentor):
    ```json
    {
      "user_id": "<uuid>",
      "role_id": "<mentor-role-uuid>",
      "mentor_tier": "MENTOR"
    }
    ```
  - Mentor role assignment (IG mentor):
    ```json
    {
      "user_id": "<uuid>",
      "role_id": "<mentor-role-uuid>",
      "mentor_tier": "IG_MENTOR",
      "ig_ids": ["<ig-uuid-1>", "<ig-uuid-2>"]
    }
    ```
  - Mentor role assignment (Campus/Company mentor):
    ```json
    {
      "user_id": "<uuid>",
      "role_id": "<mentor-role-uuid>",
      "mentor_tier": "CAMPUS_MENTOR",
      "org_id": "<college-or-company-uuid>"
    }
    ```
- Notes:
  - `guild` is required when `role_id` corresponds to the Intern role.
  - `mentor_tier` is required when `role_id` corresponds to the Mentor role.
  - `ig_ids` is required when `mentor_tier` is `IG_MENTOR`.
  - `org_id` is required when `mentor_tier` is `CAMPUS_MENTOR` or `COMPANY_MENTOR`.
- Response example (success):
```json
{
  "hasError": false,
  "statusCode": 200,
  "message": {
    "general": ["Role Added Successfully"]
  },
  "response": {
    "message": "Role Added Successfully"
  }
}
```
- Extended success response examples:
  - Intern role assignment:
    ```json
    {
      "hasError": false,
      "statusCode": 200,
      "message": {
        "general": ["Role Added Successfully"]
      },
      "response": {
        "message": "Role Added Successfully",
        "intern_guild_created": true
      }
    }
    ```
  - Mentor role assignment:
    ```json
    {
      "hasError": false,
      "statusCode": 200,
      "message": {
        "general": ["Role Added Successfully"]
      },
      "response": {
        "message": "Role Added Successfully",
        "mentor_profile_created": true
      }
    }
    ```
- Error examples:
  - Missing guild for Intern:
    ```json
    {
      "hasError": true,
      "statusCode": 400,
      "message": {
        "guild": ["guild is required when assigning the Intern role."]
      }
    }
    ```
  - Missing org_id for Campus/Company Mentor:
    ```json
    {
      "hasError": true,
      "statusCode": 400,
      "message": {
        "org_id": ["org_id is required for CAMPUS_MENTOR."]
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


## Endpoint: `<str:roles_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:roles_id`
- Request body example (JSON):
```json
{
  "roles_id": "<str:roles_id>",
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


## Endpoint: `<str:roles_id>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:roles_id`
- Request body example (JSON):
```json
{
  "roles_id": "<str:roles_id>",
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

