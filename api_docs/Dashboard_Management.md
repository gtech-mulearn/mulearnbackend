# Dashboard Management API Reference

## Referral Management

### List Referrals
**Endpoint:** `/api/v1/dashboard/referral/`
**Method:** `GET`
**Brief:** List all referrals.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "Referrals Fetched Successfully"
        ]
    },
    "response": {
        "data": [
            {
                "id": "uuid",
                "full_name": "Full Name",
                "muid": "muid",
                "karma": 100,
                "level": "Level Name"
            }
        ],
        "pagination": {}
    }
}
```

### Send Referral Email
**Endpoint:** `/api/v1/dashboard/referral/send-referral/`
**Method:** `POST`
**Brief:** Send referral invites via email.
**Permissions:** Admin
**Request Body:**
```json
{
    "email": "user@example.com"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Referral Email Sent Successfully"
        ]
    },
    "response": {}
}
```

## Karma Voucher Management

### List Vouchers
**Endpoint:** `/api/v1/dashboard/karma-voucher/`
**Method:** `GET`
**Brief:** List all karma vouchers.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "Vouchers Fetched Successfully"
        ]
    },
     "response": {
        "data": [
             {
                 "id": "uuid",
                 "code": "CODE",
                 "user": "User Name",
                 "task": "Task Title",
                 "karma": 100,
                 "month": "January",
                 "week": "W1",
                 "claimed": false,
                 "description": "desc",
                 "event": "event",
                 "created_by": "User",
                 "updated_by": "User",
                 "created_at": "date",
                 "updated_at": "date",
                 "muid": "muid"
             }
        ],
        "pagination": {}
     }
}
```

### Create Voucher
**Endpoint:** `/api/v1/dashboard/karma-voucher/`
**Method:** `POST`
**Brief:** Create a new karma voucher.
**Permissions:** Admin
**Request Body:**
```json
{
    "user": "muid_or_email",
    "task": "task_uuid",
    "karma": 100,
    "month": "January",
    "week": "W1"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Voucher Created Successfully"
        ]
    },
    "response": {
        "code": "CODE",
        "month": "January",
        "week": "W1"
    }
}
```

### Edit Voucher
**Endpoint:** `/api/v1/dashboard/karma-voucher/<str:voucher_id>/`
**Method:** `PUT`
**Brief:** Edit an existing voucher.
**Permissions:** Admin
**Request Body:**
```json
{
    "new_karma": 200
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
         "general": [
             "Voucher Updated Successfully"
         ]
    },
    "response": {}
}
```

### Delete Voucher
**Endpoint:** `/api/v1/dashboard/karma-voucher/<str:voucher_id>/`
**Method:** `DELETE`
**Brief:** Delete a voucher.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Voucher Deleted Successfully"
        ]
    },
    "response": {}
}
```

### Import Vouchers
**Endpoint:** `/api/v1/dashboard/karma-voucher/import/`
**Method:** `POST`
**Brief:** Import vouchers from CSV.
**Permissions:** Admin
**Form Data:** `voucher_data`: file
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Vouchers Imported Successfully"
        ]
    },
    "response": {}
}
```

### Get Base Template
**Endpoint:** `/api/v1/dashboard/karma-voucher/get-base-template/`
**Method:** `GET`
**Brief:** Download base template for voucher import.
**Sample Response:** (File Download)

## Dynamic Management

### List Dynamic Roles
**Endpoint:** `/api/v1/dashboard/dynamic-management/roles/`
**Method:** `GET`
**Brief:** List dynamic roles.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
         "general": [
             "Dynamic Roles Fetched Successfully"
         ]
    },
    "response": {
        "data": [
            {
                "type": "type",
                "roles": [
                    {
                        "id": "uuid",
                        "role": "Role Title"
                    }
                ]
            }
        ],
        "pagination": {}
    }
}
```

### Create Dynamic Role
**Endpoint:** `/api/v1/dashboard/dynamic-management/roles/`
**Method:** `POST`
**Brief:** Create a dynamic role.
**Permissions:** Admin
**Request Body:**
```json
{
    "type": "type",
    "role": "role_uuid"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Dynamic Role Created Successfully"
        ]
    },
    "response": {}
}
```

### Edit Dynamic Role
**Endpoint:** `/api/v1/dashboard/dynamic-management/roles/<str:role_id>/`
**Method:** `PATCH`
**Brief:** Edit a dynamic role.
**Permissions:** Admin
**Request Body:**
```json
{
    "new_role": "role_uuid"
}
```
**Sample Response:**
```json
{
     "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Dynamic Role Updated Successfully"
        ]
    },
    "response": {}
}
```

### Delete Dynamic Role
**Endpoint:** `/api/v1/dashboard/dynamic-management/roles/<str:role_id>/`
**Method:** `DELETE`
**Brief:** Delete a dynamic role.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
         "general": [
             "Dynamic Role Deleted Successfully"
         ]
    },
    "response": {}
}
```

### List Dynamic Users
**Endpoint:** `/api/v1/dashboard/dynamic-management/users/`
**Method:** `GET`
**Brief:** List dynamic users.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Dynamic Users Fetched Successfully"
        ]
    },
    "response": {
        "data": [
            {
                "type": "type",
                "users": [
                    {
                         "dynamic_user_id": "uuid",
                         "user_id": "uuid",
                         "full_name": "Name",
                         "muid": "muid",
                         "email": "email"
                    }
                ]
            }
        ],
        "pagination": {}
    }
}
```

### Create Dynamic User
**Endpoint:** `/api/v1/dashboard/dynamic-management/users/`
**Method:** `POST`
**Brief:** Create a dynamic user.
**Permissions:** Admin
**Request Body:**
```json
{
    "type": "type",
    "user": "muid_or_email"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Dynamic User Created Successfully"
        ]
    },
    "response": {}
}
```

## Error Log Management

### Get Error Logs
**Endpoint:** `/api/v1/dashboard/error-log/`
**Method:** `GET`
**Brief:** Get error logs (admin only).
**Permissions:** Admin
**Sample Response:** (File Download or Text content)

### Clear Error Logs
**Endpoint:** `/api/v1/dashboard/error-log/`
**Method:** `POST`
**Brief:** Clear error logs.
**Permissions:** Admin
**Request Body:**
```json
{
    "type": "backend"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Error Log Cleared Successfully"
        ]
    },
    "response": {}
}
```
