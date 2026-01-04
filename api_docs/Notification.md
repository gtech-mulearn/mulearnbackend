# Notification API Reference

## List Notifications
**Endpoint:** `/api/v1/notification/list/`
**Method:** `GET`
**Brief:** Get all notifications for the authenticated user.

**Response Body:**
```json
{
  "response": [
    {
      "id": "uuid",
      "title": "string",
      "description": "string",
      "created_at": "datetime",
      "url": "string"
    }
  ]
}
```

## Delete Notification
**Endpoint:** `/api/v1/notification/delete/id/<str:notification_id>/`
**Method:** `DELETE`
**Brief:** Delete a specific notification by ID.

**Response Body:**
```json
{
  "general_message": "Notification deleted successfully",
  "statusCode": 200
}
```

## Delete All Notifications
**Endpoint:** `/api/v1/notification/delete/all/`
**Method:** `DELETE`
**Brief:** Delete all notifications for the authenticated user.

**Response Body:**
```json
{
  "general_message": "All notification deleted successfully",
  "statusCode": 200
}
```
