# Dashboard / Profile


Base path: `/api/dashboard/profile/`


## Endpoint: `badges/<str:muid>`
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


## Endpoint: `user-profile/`
- Brief: GET - Fetch authenticated user's full profile. PATCH - Update authenticated user's profile fields.

### GET Request
- Response example (success - returns full profile including bio, projects, experience):
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
      "id": "user-uuid",
      "full_name": "John Doe",
      "muid": "john-doe@mulearn",
      "karma": 1500,
      "profile_pic": "https://...",
      "bio": "Passionate developer and open source contributor",
      "projects": [
        {
          "title": "μLearn Tracker",
          "link": "https://github.com/user/repo",
          "description": "Track tasks and progress",
          "tags": ["React", "Firebase"]
        }
      ],
      "experience": [
        "Intern at Tech Company (2023-2024)",
        "Developer at Startup (2024-Present)"
      ]
    }
  }
}
```

### PATCH Request
- Requires: Authentication token
- Request body example (all fields optional):
```json
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "bio": "I love building amazing products",
  "projects": [
    {
      "title": "μLearn Tracker",
      "link": "https://github.com/user/repo",
      "description": "Track tasks and progress",
      "tags": ["React", "Firebase"]
    },
    {
      "title": "Portfolio Site",
      "link": "https://johndoe.dev",
      "description": "Personal portfolio",
      "tags": ["Next.js", "Tailwind"]
    }
  ],
  "experience": [
    "Intern at Tech Company (2023-2024)",
    "Developer at Startup (2024-Present)"
  ],
  "gender": "Male",
  "dob": "1999-05-15",
  "mobile": "+91987654321"
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
      "full_name": "John Doe",
      "email": "john@example.com",
      "bio": "I love building amazing products",
      "projects": [
        {
          "title": "μLearn Tracker",
          "link": "https://github.com/user/repo",
          "description": "Track tasks and progress",
          "tags": ["React", "Firebase"]
        }
      ],
      "experience": [
        "Intern at Tech Company (2023-2024)"
      ]
    }
  }
}
```


## Endpoint: `ig-edit/`
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


## Endpoint: `user-profile/<str:muid>/`
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


## Endpoint: `edit-user-profile/`
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


## Endpoint: `user-log/`
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


## Endpoint: `user-log/<str:muid>/`
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


## Endpoint: `share-user-profile/`
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


## Endpoint: `share-user-profile/<str:uuid>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:uuid`
- Request body example (JSON):
```json
{
  "uuid": "<str:uuid>",
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


## Endpoint: `rank/<str:muid>/`
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


## Endpoint: `get-user-levels/`
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


## Endpoint: `get-user-levels/<str:muid>/`
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


## Endpoint: `socials/edit/`
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


## Endpoint: `socials/`
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


## Endpoint: `socials/<str:muid>/`
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


## Endpoint: `qrcode-get/<str:uuid>/`
- Brief: Resource-specific endpoint (path param).
- Path params:
  - `str:uuid`
- Request body example (JSON):
```json
{
  "uuid": "<str:uuid>",
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


## Endpoint: `change-password/`
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


## Endpoint: `userterm-approved/<str:muid>/`
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


## Endpoint: `karma-feed/`
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


## Endpoint: `user-level-feed/`
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


## Endpoint: `user-preferences/`
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


## Endpoint: `permute/<str:muid>/`
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

