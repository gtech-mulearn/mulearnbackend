# Dashboard Utilities & Extras API Reference

## Channels Management

### List Channels
**Endpoint:** `/api/v1/dashboard/channels/`
**Method:** `GET`
**Brief:** List all channels.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "Channels Fetched Successfully"
        ]
    },
    "response": {
        "data": [
            {
                "id": "uuid",
                "name": "Channel Name",
                "discord_id": "123456",
                "created_by": "User",
                "updated_by": "User",
                "created_at": "date",
                "updated_at": "date"
            }
        ],
        "pagination": {}
    }
}
```

### Create Channel
**Endpoint:** `/api/v1/dashboard/channels/`
**Method:** `POST`
**Brief:** Create a new channel.
**Permissions:** Admin
**Request Body:**
```json
{
    "name": "New Channel",
    "discord_id": "123456"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Channel Created Successfully"
        ]
    },
    "response": {
         "id": "uuid",
         "name": "New Channel",
         "discord_id": "123456"
    }
}
```

### Edit Channel
**Endpoint:** `/api/v1/dashboard/channels/<str:channel_id>/`
**Method:** `PUT`
**Brief:** Edit an existing channel.
**Permissions:** Admin
**Request Body:**
```json
{
    "name": "Updated Name",
    "discord_id": "654321"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Channel Updated Successfully"
        ]
    },
    "response": {}
}
```

### Delete Channel
**Endpoint:** `/api/v1/dashboard/channels/<str:channel_id>/`
**Method:** `DELETE`
**Brief:** Delete a channel.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Channel Deleted Successfully"
        ]
    },
    "response": {}
}
```

## Discord Moderator

### Moderator Leaderboard
**Endpoint:** `/api/v1/dashboard/discord-moderator/leaderboard/`
**Method:** `GET`
**Brief:** Get discord moderator leaderboard.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "Leaderboard Fetched Successfully"
        ]
    },
    "response": [
        {
            "muid": "user@mulearn",
            "full_name": "Full Name",
            "task_count": 10
        }
    ]
}
```

### Pending Tasks
**Endpoint:** `/api/v1/dashboard/discord-moderator/pending-tasks/`
**Method:** `GET`
**Brief:** Get count of pending tasks for moderator.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
         "general": [
             "Pending Tasks Fetched Successfully"
         ]
    },
     "response": {
         "count": 5
     }
}
```

### Task List
**Endpoint:** `/api/v1/dashboard/discord-moderator/tasks/`
**Method:** `GET`
**Brief:** List tasks for moderation.
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
                "user_id": "user_id",
                "fullname": "Full Name",
                "task_name": "Task Title",
                "discord_link": "link",
                "status": "pending",
                "level": "level",
                "karma": 100,
                "created_at": "date"
            }
        ],
        "pagination": {}
    }
}
```

## Events Management

### List Events
**Endpoint:** `/api/v1/dashboard/events/`
**Method:** `GET`
**Brief:** List all events.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "Events Fetched Successfully"
        ]
    },
    "response": {
        "data": [
            {
                "id": "uuid",
                "name": "Event Name",
                "description": "Description",
                "created_by": "User",
                "updated_by": "User",
                "created_at": "date",
                "updated_at": "date"
            }
        ],
        "pagination": {}
    }
}
```

### Create Event
**Endpoint:** `/api/v1/dashboard/events/`
**Method:** `POST`
**Brief:** Create a new event.
**Permissions:** Admin
**Request Body:**
```json
{
    "name": "New Event",
    "description": "Event Description"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Event Created Successfully"
        ]
    },
    "response": {
        "id": "uuid",
        "name": "New Event",
        "description": "Event Description"
    }
}
```

### Edit Event
**Endpoint:** `/api/v1/dashboard/events/<str:event_id>/`
**Method:** `PUT`
**Brief:** Edit an existing event.
**Permissions:** Admin
**Request Body:**
```json
{
    "name": "Updated Event Name",
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
             "Event Updated Successfully"
        ]
    },
    "response": {}
}
```

### Delete Event
**Endpoint:** `/api/v1/dashboard/events/<str:event_id>/`
**Method:** `DELETE`
**Brief:** Delete an event.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Event Deleted Successfully"
        ]
    },
    "response": {}
}
```

## Coupon Management

### Verify Coupon
**Endpoint:** `/api/v1/dashboard/coupon/verify/`
**Method:** `POST`
**Brief:** Verify a coupon code.
**Permissions:** Admin
**Request Body:**
```json
{
    "code": "COUPON123"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Coupon Verified"
        ]
    },
    "response": {
        "id": "uuid",
        "code": "COUPON123",
        "discount": 10
    }
}
```

## Projects Management

### List Projects
**Endpoint:** `/api/v1/dashboard/projects/`
**Method:** `GET`
**Brief:** List all projects.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Projects Fetched Successfully"
        ]
    },
    "response": [
        {
            "id": "uuid",
            "title": "Project Title",
            "description": "Description",
             "link": "url"
        }
    ]
}
```

## Achievement Management

### List Achievements
**Endpoint:** `/api/v1/dashboard/achievement/`
**Method:** `GET`
**Brief:** List achievements.
**Permissions:** Admin
**Sample Response:**
```json
{
     "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Achievements Fetched Successfully"
        ]
    },
    "response": [
        {
            "id": "uuid",
            "title": "Achievement Title",
            "description": "desc"
        }
    ]
}
```

### Create Achievement
**Endpoint:** `/api/v1/dashboard/achievement/`
**Method:** `POST`
**Brief:** Create achievement.
**Permissions:** Admin
**Request Body:**
```json
{
    "title": "Title",
    "description": "Description"
}
```

## Task Report

### List Reports
**Endpoint:** `/api/v1/dashboard/task-report/`
**Method:** `GET`
**Brief:** List task reports.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Task Reports Fetched Successfully"
        ]
    },
    "response": {
        "data": [
            {
                 "id": "uuid",
                 "task_id": "task_uuid",
                 "report": "Report Content",
                 "created_by": "User"
            }
        ],
        "pagination": {}
    }
}
```
