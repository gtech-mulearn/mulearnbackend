# Dashboard Task & Activities API Reference

## Task Management

### List Tasks
**Endpoint:** `/api/v1/dashboard/task/`
**Method:** `GET`
**Brief:** List all tasks.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "Tasks Fetched Successfully"
        ]
    },
    "response": {
        "data": [
            {
                "id": "uuid",
                "hashtag": "#hashtag",
                "title": "Task Title",
                "description": "Description",
                "karma": 100,
                "total_karma_gainers": 10,
                "channel": "channel_name",
                "type": "Task Type",
                "active": true,
                "variable_karma": false,
                "usage_count": 1,
                "level": "Level",
                "org": "Org Name",
                "ig": "IG Name",
                "event": "event_uuid",
                "updated_at": "date",
                "updated_by": "User",
                "created_by": "User",
                "created_at": "date",
                "bonus_time": "date",
                "bonus_karma": 0
            }
        ],
        "pagination": {
             "count": 10,
             "totalPages": 1,
             "isNext": false,
             "isPrev": false,
             "nextPage": 1
        }
    }
}
```

### Create Task
**Endpoint:** `/api/v1/dashboard/task/`
**Method:** `POST`
**Brief:** Create a new task.
**Permissions:** Admin
**Request Body:**
```json
{
  "hashtag": "#newtask",
  "title": "New Task",
  "description": "Description of the task",
  "karma": 100,
  "channel_id": "channel_uuid",
  "type_id": "type_uuid",
  "org_id": "org_uuid",
  "level_id": "level_uuid",
  "ig_id": "ig_uuid",
  "variable_karma": false,
  "usage_count": 1
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "Task Created Successfully"
        ]
    },
    "response": {
         "id": "uuid",
         "hashtag": "#newtask",
         "title": "New Task",
         "description": "Description of the task",
         "karma": 100,
         "channel_id": "channel_name",
         "type_id": "Task Type",
         "org_id": "org_code",
         "level_id": "Level Name",
         "ig_id": "IG Name"
    }
}
```

### Edit Task
**Endpoint:** `/api/v1/dashboard/task/<str:task_id>/`
**Method:** `PUT`
**Brief:** Edit an existing task.
**Permissions:** Admin
**Request Body:**
```json
{
    "title": "Updated Title",
    "description": "Updated Description"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Task Updated Successfully"
        ]
    },
    "response": {
        "hashtag": "#hashtag",
        "title": "Updated Title",
        "description": "Updated Description",
        "karma": 100
    }
}
```

### Delete Task
**Endpoint:** `/api/v1/dashboard/task/<str:task_id>/`
**Method:** `DELETE`
**Brief:** Delete a task.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Task Deleted Successfully"
        ]
    },
    "response": {}
}
```

### Task Import
**Endpoint:** `/api/v1/dashboard/task/import/`
**Method:** `POST`
**Brief:** Import tasks from CSV.
**Permissions:** Admin
**Form Data:** `task_data`: file
**Sample Response:**
```json
{
     "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "Tasks Imported Successfully"
        ]
    },
    "response": {}
}
```

### Get Template
**Endpoint:** `/api/v1/dashboard/task/get-template/`
**Method:** `GET`
**Brief:** Download task import template.
**Sample Response:** (File Download)

## Interest Group (IG) Management

### List IGs
**Endpoint:** `/api/v1/dashboard/ig/`
**Method:** `GET`
**Brief:** List all interest groups.
**Permissions:** Admin
**Sample Response:**
```json
{
     "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "IGs Fetched Successfully"
        ]
    },
    "response": {
        "data": [
            {
                "id": "uuid",
                "name": "Web Development",
                "code": "WD",
                "icon": "url",
                "members": 100,
                "updated_by": "User",
                "updated_at": "date",
                "created_by": "User",
                "created_at": "date"
            }
        ],
        "pagination": {}
    }
}
```

### Create IG
**Endpoint:** `/api/v1/dashboard/ig/`
**Method:** `POST`
**Brief:** Create a new interest group.
**Permissions:** Admin
**Request Body:**
```json
{
    "name": "New IG",
    "code": "NIG",
    "icon": "string",
    "category": "coder"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "IG Created Successfully"
        ]
    },
    "response": {
        "name": "New IG",
        "code": "NIG",
        "category": "coder"
    }
}
```

### Edit IG
**Endpoint:** `/api/v1/dashboard/ig/<str:pk>/`
**Method:** `PUT`
**Brief:** Edit an existing IG.
**Permissions:** Admin
**Request Body:**
```json
{
    "name": "Updated IG Name"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "IG Updated Successfully"
        ]
    },
    "response": {
         "name": "Updated IG Name"
    }
}
```

### Delete IG
**Endpoint:** `/api/v1/dashboard/ig/<str:pk>/`
**Method:** `DELETE`
**Brief:** Delete an IG.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
         "general": [
             "IG Deleted Successfully"
         ]
    },
    "response": {}
}
```

## Learning Circle Management
**Base URL:** `/api/v1/dashboard/learningcircle/`

### Learning Circles
**Endpoints:**
- `GET /` - List all learning circles.
- `POST /` - Create a learning circle.

**Sample Response (List):**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "Learning Circles Fetched Successfully"
        ]
    },
    "response": [
        {
            "id": "uuid",
            "ig": "IG Name",
            "title": "Circle Title",
            "org": "Org Name",
            "total_members": 5
        }
    ]
}
```

**Request Body (Create):**
```json
{
    "ig": "ig_uuid",
    "org": "org_uuid",
    "title": "Circle Title",
    "description": "Description"
}
```

### Learning Circle Details
**Endpoints:**
- `GET /<str:circle_id>/` - Get details.
- `PUT /<str:circle_id>/` - Update details.
- `DELETE /<str:circle_id>/` - Delete circle.

**Sample Response (Get):**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Learning Circle Details Fetched Successfully"
        ]
    },
     "response": {
        "id": "uuid",
        "ig": "IG Name",
        "title": "Circle Title",
        "description": "Description",
        "org": "Org Name",
        "created_by": {
             "id": "user_uuid",
             "full_name": "User Name",
             "profile_pic": "url",
             "muid": "muid"
        },
        "rank": 1,
        "total_karma": 1000,
        "total_members": 5
     }
}
```

### Circle Meeting Log
**Endpoints:**
- `POST /meet/<str:circle_id>/` - Schedule/Create a meeting.
- `GET /meet/<str:circle_id>/` - List meetings.

**Request Body (Create Meet):**
```json
{
    "title": "Meeting Title",
    "meet_place": "Zoom",
    "meet_time": "2023-10-27T10:00:00Z",
    "duration": 1,
    "mode": "online",
    "meet_link": "http://zoom.us/..."
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Meeting Scheduled Successfully"
        ]
    },
    "response": {
        "circle_id": "uuid",
        "title": "Meeting Title",
        "meet_place": "Zoom",
        "meet_time": "2023-10-27T10:00:00Z",
        "duration": 1,
        "mode": "online",
        "meet_link": "http://zoom.us/..."
    }
}
```
