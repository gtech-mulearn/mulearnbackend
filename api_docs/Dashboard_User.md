# Dashboard User Management API Reference

## User Management

### List Users
**Endpoint:** `/api/v1/dashboard/user/`
**Method:** `GET`
**Brief:** List all users with pagination and filtering.
**Permissions:** Admin
**Query Params:** `muid`, `full_name`, `email`, `mobile`, `user_lvl_link_user__level__name`
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "User Lists Fetched Successfully"
        ]
    },
    "response": {
        "data": [
            {
                "id": "uuid",
                "full_name": "Full Name",
                "muid": "user@mulearn",
                "discord_id": "123456789",
                "email": "user@example.com",
                "mobile": "9876543210",
                "created_at": "2023-01-01T00:00:00Z",
                "karma": 100,
                "level": "Level 1"
            }
        ],
        "pagination": {
            "count": 100,
            "totalPages": 10,
            "isNext": true,
            "isPrev": false,
            "nextPage": 2
        }
    }
}
```

### User Details
**Endpoint:** `/api/v1/dashboard/user/<str:user_id>/`
**Method:** `GET`
**Brief:** Get details of a specific user.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "User Details Fetched Successfully"
        ]
    },
    "response": {
        "user_id": "uuid",
        "full_name": "Full Name",
        "email": "user@example.com",
        "mobile": "9876543210",
        "gender": "Male",
        "discord_id": "123456789",
        "dob": "2000-01-01",
        "role": ["Student", "Intern"],
        "organizations": [
            {
                "org": "uuid",
                "org_type": "College",
                 "department": "uuid",
                 "graduation_year": "2024",
                 "country": "uuid",
                 "state": "uuid",
                 "district": "uuid"
            }
        ],
        "department": "uuid",
        "graduation_year": "2024",
        "interest_groups": [
            {
                "id": "uuid",
                "name": "Web Development",
                "karma": 500
            }
        ],
        "district": "uuid"
    }
}
```

### Edit User
**Endpoint:** `/api/v1/dashboard/user/<str:user_id>/`
**Method:** `PATCH`
**Brief:** Edit user details.
**Permissions:** Admin
**Request Body:**
```json
{
  "full_name": "New Name",
  "email": "new.email@example.com",
  "mobile": "9876543210",
  "gender": "Male",
  "dob": "2000-01-01",
  "orgs": ["org_uuid_1", "org_uuid_2"],
  "roles": ["role_uuid_1"],
  "igs": ["ig_uuid_1"],
  "department": "dept_uuid",
  "graduation_year": "2025",
  "district": "district_uuid"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "User Details Updated Successfully"
        ]
    },
    "response": {}
}
```

### Delete User
**Endpoint:** `/api/v1/dashboard/user/<str:user_id>/`
**Method:** `DELETE`
**Brief:** Delete a user.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "User Deleted Successfully"
        ]
    },
    "response": {}
}
```

### User Verification List
**Endpoint:** `/api/v1/dashboard/user/verification/`
**Method:** `GET`
**Brief:** List unverified user lists.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "Verification List Fetched Successfully"
        ]
    },
    "response": {
        "data": [
            {
                "id": "uuid",
                "user_id": "user_id",
                 "discord_id": "discord_id",
                 "muid": "muid",
                 "full_name": "Full Name",
                 "role_title": "Role Title",
                 "email": "email",
                 "mobile": "mobile"
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

### Edit User Verification
**Endpoint:** `/api/v1/dashboard/user/verification/<str:link_id>/`
**Method:** `PATCH`
**Brief:** Update user verification status.
**Permissions:** Admin
**Request Body:**
```json
{
    "verified": true
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "User Role Verified Successfully"
        ]
    },
    "response": {
        "user_role_link": {
            "verified": true,
            "user_id": "user_uuid",
            "role_id": "role_uuid"
        }
    }
}
```

### Delete User Verification
**Endpoint:** `/api/v1/dashboard/user/verification/<str:link_id>/`
**Method:** `DELETE`
**Brief:** Delete a verification link.
**Permissions:** Admin
**Sample Response:**
```json
{
     "hasError": false,
    "statusCode": 200,
     "message": {
        "general": [
            "User Role Verification Deleted Successfully"
        ]
    },
    "response": {}
}
```

### User Search
**Endpoint:** `/api/v1/dashboard/user/search/`
**Method:** `GET`
**Brief:** Search public users.
**Query Params:** `role`, `ig_id`, `org_id`, `search`
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Users Fetched Successfully"
        ]
    },
     "response": [
         {
             "id": "uuid",
             "full_name": "Full Name",
             "muid": "muid"
         }
     ]
}
```

### Forgot Password
**Endpoint:** `/api/v1/dashboard/user/forgot-password/`
**Method:** `POST`
**Brief:** Initiate forgot password flow.
**Request Body:**
```json
{
  "emailOrMuid": "string"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Password Reset Email Sent Successfully"
        ]
    },
    "response": {}
}
```

### Reset Password Verify Token
**Endpoint:** `/api/v1/dashboard/user/reset-password/verify-token/<str:token>/`
**Method:** `POST`
**Brief:** Verify reset password token.
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "Token is Valid"
        ]
    },
    "response": {}
}
```

### Reset Password Confirm
**Endpoint:** `/api/v1/dashboard/user/reset-password/<str:token>/`
**Method:** `POST`
**Brief:** Set new password.
**Request Body:**
```json
{
  "password": "new_secure_password"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "Password Reset Successfully"
        ]
    },
    "response": {}
}
```

### User Info
**Endpoint:** `/api/v1/dashboard/user/info/`
**Method:** `GET`
**Brief:** Get current user info.
**Sample Response:**
```json
{
     "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "User Info Fetched Successfully"
        ]
    },
    "response": {
         "muid": "muid",
         "full_name": "Full Name",
         "email": "email",
         "mobile": "mobile",
         "gender": "gender",
         "dob": "date",
         "exist_in_guild": true,
         "joined": "date",
         "roles": ["role1", "role2"],
         "profile_pic": "url",
         "dynamic_type": ["type1"],
         "user_domains": ["domain1"],
         "user_endgoals": ["endgoal1"],
         "interested_in_work": true,
         "interested_in_gig_work": false
    }
}
```

### User Organization Link
**Endpoint:** `/api/v1/dashboard/user/organization/`
**Method:** `POST`
**Brief:** Link user to an organization.
**Request Body:**
```json
{
    "org_id": "uuid"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Organization Linked Successfully"
        ]
    },
    "response": {}
}
```

### List User Organization Links
**Endpoint:** `/api/v1/dashboard/user/organization/list/`
**Method:** `GET`
**Brief:** Get user's organization links.
**Sample Response:**
```json
{
     "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "User Organizations Fetched Successfully"
        ]
    },
    "response": [
        {
            "org": "uuid",
            "org_type": "type"
        }
    ]
}
```

### User Preferences
**Endpoint:** `/api/v1/dashboard/user/preferences/`
**Method:** `GET` / `PATCH`
**Brief:** Get or update user work preferences.
**Request Body (PATCH):**
```json
{
    "interested_in_work": true,
    "interested_in_gig_work": false
}
```
**Sample Response (GET):**
```json
{
     "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "User Preferences Fetched Successfully"
        ]
    },
     "response": {
         "interested_in_work": true,
         "interested_in_gig_work": false
     }
}
```

## Role Management

### List Roles
**Endpoint:** `/api/v1/dashboard/roles/`
**Method:** `GET`
**Brief:** List all roles.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "Roles Fetched Successfully"
        ]
    },
    "response": {
        "data": [
            {
                "id": "uuid",
                "title": "Role Title",
                "description": "Role Description",
                "updated_by": "User Name",
                "updated_at": "date",
                "created_by": "User Name",
                "created_at": "date",
                "members": 10
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

### Create Role
**Endpoint:** `/api/v1/dashboard/roles/`
**Method:** `POST`
**Brief:** Create a new role.
**Permissions:** Admin
**Request Body:**
```json
{
  "title": "New Role",
  "description": "Description of the role"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Role Created Successfully"
        ]
    },
    "response": {
        "id": "uuid",
        "title": "New Role",
        "description": "Description of the role",
         "updated_by": "User Name",
        "updated_at": "date",
        "members": 0
    }
}
```

### Edit Role
**Endpoint:** `/api/v1/dashboard/roles/<str:roles_id>/`
**Method:** `PATCH`
**Brief:** Edit an existing role.
**Permissions:** Admin
**Request Body:**
```json
{
    "title": "Updated Role Title",
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
             "Role Updated Successfully"
        ]
    },
    "response": {
        "id": "uuid",
        "title": "Updated Role Title",
        "description": "Updated Description",
        "updated_by": "User Name",
        "updated_at": "date",
        "members": 10
    }
}
```

### Delete Role
**Endpoint:** `/api/v1/dashboard/roles/<str:roles_id>/`
**Method:** `DELETE`
**Brief:** Delete a role.
**Permissions:** Admin
**Sample Response:**
```json
{
     "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "Role Deleted Successfully"
        ]
    },
    "response": {}
}
```

### User Role Search
**Endpoint:** `/api/v1/dashboard/roles/user-role/<str:role_id>/`
**Method:** `GET`
**Brief:** Search users with a specific role.
**Permissions:** Admin
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Users Fetched Successfully"
        ]
    },
    "response": {
        "data": [
            {
                "id": "uuid",
                "full_name": "Full Name",
                "muid": "muid"
            }
        ],
        "pagination": {}
    }
}
```

### Bulk Assign Roles
**Endpoint:** `/api/v1/dashboard/roles/bulk-assign/<str:role_id>/`
**Method:** `POST`
**Brief:** Assign a role to multiple users.
**Permissions:** Admin
**Request Body:**
```json
{
  "users": ["user_id_1", "user_id_2"]
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Roles Assigned Successfully"
        ]
    },
    "response": {}
}
```

### Bulk Remove Roles
**Endpoint:** `/api/v1/dashboard/roles/bulk-assign/<str:role_id>/`
**Method:** `PATCH`
**Brief:** Remove a role from multiple users.
**Permissions:** Admin
**Request Body:**
```json
{
  "users": ["user_id_1", "user_id_2"]
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Roles Removed Successfully"
        ]
    },
    "response": {}
}
```

### Bulk Assign from Excel
**Endpoint:** `/api/v1/dashboard/roles/bulk-assign-excel/`
**Method:** `POST`
**Brief:** Bulk assign roles using an Excel file.
**Permissions:** Admin
**Form Data:** `user_role_excel`: file
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Failed"
        ]
    },
    "response": {
        "Success": [
            {
                "muid": "valid_muid",
                "role": "valid_role"
            }
        ],
        "Failed": [
             {
                 "muid": "invalid_muid",
                 "role": "role",
                 "error": "User not found"
             }
        ]
    }
}
```

### Role Base Template
**Endpoint:** `/api/v1/dashboard/roles/base-template/`
**Method:** `GET`
**Brief:** Download role assignment Excel template.
**Sample Response:** (File Download)

## Profile Management

### User Profile
**Endpoint:** `/api/v1/dashboard/profile/user-profile/<str:muid>/`
**Method:** `GET`
**Brief:** Get public profile of a user.
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "User Profile Fetched Successfully"
        ]
    },
    "response": {
        "id": "uuid",
        "joined": "date",
        "full_name": "Full Name",
        "gender": "gender",
        "muid": "muid",
        "roles": ["role1", "role2"],
        "college_id": "uuid",
        "college_code": "code",
        "org_district_id": "uuid",
        "karma": 1000,
        "rank": 5,
        "karma_distribution": [
             {
                 "task_type": "type",
                 "karma": 100
             }
        ],
        "level": "Level 1",
        "profile_pic": "url",
        "interest_groups": [
            {
                "id": "uuid",
                "name": "name",
                "karma": 100
            }
        ],
        "is_public": true,
        "percentile": 90
    }
}
```

### Edit Profile
**Endpoint:** `/api/v1/dashboard/profile/`
**Method:** `PATCH`
**Brief:** Edit current user's profile.
**Request Body:**
```json
{
    "full_name": "New Name",
    "gender": "Male",
    "dob": "2000-01-01",
    "mobile": "9876543210"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
         "general": [
             "User Profile Updated Successfully"
         ]
    },
    "response": {}
}
```

### User Log
**Endpoint:** `/api/v1/dashboard/profile/user-log/<str:muid>/`
**Method:** `GET`
**Brief:** Get karma activity log of a user.
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "User Log Fetched Successfully"
        ]
    },
    "response": {
        "data": [
            {
                "task_name": "Task Title",
                "karma": 10,
                "created_date": "date"
            }
        ],
        "pagination": {}
    }
}
```

### Share Profile
**Endpoint:** `/api/v1/dashboard/profile/share-user-profile/<str:uuid>/`
**Method:** `GET`
**Brief:** Generate QR code for user profile.
**Sample Response:** (Image/File Download)

### User Levels
**Endpoint:** `/api/v1/dashboard/profile/get-user-levels/<str:muid>/`
**Method:** `GET`
**Brief:** Get levels and tasks completion status for a user.
**Sample Response:**
```json
{
     "hasError": false,
    "statusCode": 200,
     "message": {
         "general": [
             "User Levels Fetched Successfully"
         ]
     },
     "response": [
         {
             "level_number": 1,
             "name": "Level 1",
              "tasks": [
                  {
                      "task_name": "Introduction",
                      "hashtag": "#intro",
                      "completed": true,
                      "karma": 10
                  }
              ]
         }
     ]
}
```

### User Rank
**Endpoint:** `/api/v1/dashboard/profile/rank/<str:muid>/`
**Method:** `GET`
**Brief:** Get user's rank.
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "User Rank Fetched Successfully"
        ]
    },
    "response": {
        "rank": 5
    }
}
```

### Socials
**Endpoint:** `/api/v1/dashboard/profile/socials/`
**Method:** `GET` / `PUT`
**Brief:** Get or update user social media links.
**Request Body (PUT):**
```json
{
    "github": "username",
    "linkedin": "username",
    "instagram": "username"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Socials Fetched Successfully"
        ]
    },
    "response": {
        "github": "username",
        "linkedin": "username",
        "instagram": "username"
    }
}
```

### Reset Password (Auth)
**Endpoint:** `/api/v1/dashboard/profile/reset-password/`
**Method:** `POST`
**Brief:** Reset password for logged-in user.
**Request Body:**
```json
{
    "old_password": "old_password",
    "new_password": "new_secure_password"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
         "general": [
             "Password Reset Successfully"
         ]
    },
    "response": {}
}
```

### Karma Feed
**Endpoint:** `/api/v1/dashboard/profile/karma-feed/`
**Method:** `GET`
**Brief:** Get karma feed stats (top user, top college).
**Sample Response:**
```json
{
     "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
             "Karma Feed Fetched Successfully"
        ]
    },
    "response": {
         "top_user": {
             "full_name": "Name",
             "profile_pic": "url",
             "karma": 10000
         },
         "top_college": {
             "name": "College Name",
              "karma": 50000
         }
    }
}
```
