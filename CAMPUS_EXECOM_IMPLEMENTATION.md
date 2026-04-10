# Campus Execom Management System - Implementation Guide

## Overview
This implementation adds a backend system to manage the campus Executive Committee (Execom), allowing admins to assign or remove users based on their roles.

## Changes Made

### 1. Database Model - `db/organization.py`
**New Model: `CampusExecom`**

```python
class CampusExecom(models.Model):
    id          = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4())
    org         = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='campus_execom_org')
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campus_execom_user')
    role        = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, related_name='campus_execom_role')
    updated_by  = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by', related_name='campus_execom_updated_by')
    updated_at  = models.DateTimeField(auto_now=True)
    created_by  = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by', related_name='campus_execom_created_by')
    created_at  = models.DateTimeField(auto_now_add=True)
```

**Database Table SQL:**
```sql
CREATE TABLE campus_execom (
  id VARCHAR(36) PRIMARY KEY,
  org_id VARCHAR(36) NOT NULL,
  user_id VARCHAR(36) NOT NULL,
  role_id VARCHAR(36),
  created_by_id VARCHAR(36) NOT NULL,
  updated_by_id VARCHAR(36) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY unique_org_user (org_id, user_id),
  FOREIGN KEY (org_id) REFERENCES organization(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
  FOREIGN KEY (role_id) REFERENCES role(id) ON DELETE SET NULL,
  FOREIGN KEY (created_by_id) REFERENCES user(id) ON DELETE RESTRICT,
  FOREIGN KEY (updated_by_id) REFERENCES user(id) ON DELETE RESTRICT,
  INDEX idx_org (org_id),
  INDEX idx_org_user (org_id, user_id)
);
```

### 2. Serializers - `api/dashboard/campus/serializers.py`

**CampusExecomSerializer:**
- Serializes full execom member details
- Read-only fields: id, user_id, full_name, muid, email, profile_pic, role_title, timestamps
- Writable field: role_id

**CampusExecomCreateSerializer:**
- Input validation for user_id and role_id
- Handles getting_or_create logic to update existing records
- Tracks created_by and updated_by

### 3. API Views - `api/dashboard/campus/campus_views.py`

**CampusExecomAPI (GET, POST)**
```python
class CampusExecomAPI(APIView):
    authentication_classes = [CustomizePermission]
    
    def get(self, request, org_id):
        # Returns all execom members for a campus with full details
        
    def post(self, request, org_id):
        # Adds a new member to execom or updates existing
        # Request body: { "user_id": "...", "role_id": "..." }
```

**CampusExecomDetailAPI (DELETE)**
```python
class CampusExecomDetailAPI(APIView):
    authentication_classes = [CustomizePermission]
    
    def delete(self, request, org_id, uid):
        # Removes a member from execom
```

### 4. URL Routes - `api/dashboard/campus/urls.py`

```python
# View all execom members
GET /api/campus/<org_id>/execom/

# Add new execom member
POST /api/campus/<org_id>/execom/
# Payload: { "user_id": "user-id", "role_id": "role-id" }

# Remove execom member
DELETE /api/campus/<org_id>/execom/<uid>/
```

## API Endpoints

| Method | Route | Description | Params |
|--------|-------|-------------|--------|
| GET | `/api/campus/:id/execom` | View all Execom members | campus_id |
| POST | `/api/campus/:id/execom` | Add member to Execom | user_id, role_id |
| DELETE | `/api/campus/:id/execom/:uid` | Remove member from Execom | campus_id, user_id |

## Response Format

### GET /api/campus/:id/execom
```json
{
  "response": [
    {
      "id": "execom-id",
      "user_id": "user-id",
      "full_name": "Member Name",
      "muid": "member@mulearn",
      "email": "member@example.com",
      "profile_pic": "https://...",
      "role_id": "role-id",
      "role_title": "Campus Lead",
      "created_at": "2026-04-10T00:00:00Z",
      "updated_at": "2026-04-10T00:00:00Z"
    }
  ]
}
```

### POST /api/campus/:id/execom
**Request:**
```json
{
  "user_id": "user-id",
  "role_id": "role-id"
}
```

**Response:**
```json
{
  "response": {
    "id": "execom-id",
    "user_id": "user-id",
    "full_name": "Member Name",
    "muid": "member@mulearn",
    "email": "member@example.com",
    "profile_pic": "https://...",
    "role_id": "role-id",
    "role_title": "Campus Lead",
    "created_at": "2026-04-10T00:00:00Z",
    "updated_at": "2026-04-10T00:00:00Z"
  }
}
```

### DELETE /api/campus/:id/execom/:uid
**Response:**
```json
{
  "status": "success",
  "general_message": "Execom member removed successfully"
}
```

## Features

✅ **Create/Assign Members**: Add users to campus execom with specific roles  
✅ **Read/View Members**: Get list of all execom members for a campus  
✅ **Update Roles**: Change a member's role by re-assigning (POST with existing user)  
✅ **Remove Members**: Delete execom members from campus  
✅ **Unique Constraint**: Each user can only have one execom position per campus  
✅ **Audit Trail**: Tracks created_by and updated_by for all operations  
✅ **Permission Control**: Only users with organization access can manage execom  

## Setup Instructions

### 1. Create Database Table
Run the SQL script provided above to create the `campus_execom` table.

### 2. Verify Branch
```bash
git branch
# Should show: * feat/campus-execom
```

### 3. Test the Implementation
```bash
# View all execom members
curl -X GET "http://localhost:8000/api/campus/<campus-id>/execom/" \
  -H "Authorization: Bearer <token>"

# Add new member
curl -X POST "http://localhost:8000/api/campus/<campus-id>/execom/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<user-id>",
    "role_id": "<role-id>"
  }'

# Remove member
curl -X DELETE "http://localhost:8000/api/campus/<campus-id>/execom/<user-id>/" \
  -H "Authorization: Bearer <token>"
```

## Files Modified

- `db/organization.py` - Added CampusExecom model
- `api/dashboard/campus/serializers.py` - Added serializers
- `api/dashboard/campus/campus_views.py` - Added API views
- `api/dashboard/campus/urls.py` - Added URL routes

## Git Branch
Branch: `feat/campus-execom`

To commit changes:
```bash
git add .
git commit -m "feat: implement campus execom management system"
```

## Future Enhancements

- Add bulk import of execom members
- Add role-based permissions specific to execom
- Add audit logs for all execom changes
- Add notification system when users are added/removed
- Add search and filter functionality
- Add pagination for large execom member lists
