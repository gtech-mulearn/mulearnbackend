# Url Shortener API Reference

## Create Short URL
**Endpoint:** `/api/v1/url-shortener/create/`
**Method:** `POST`
**Brief:** Create a new shortened URL.

**Request Body:**
```json
{
  "title": "string",
  "long_url": "string",
  "short_url": "string (optional)"
}
```

**Response Body:**
```json
{
  "general_message": "Url created successfully.",
  "statusCode": 200
}
```

## List Short URLs
**Endpoint:** `/api/v1/url-shortener/list/`
**Method:** `GET`
**Brief:** List all shortened URLs (paginated).
**Query Params:** `page`, `page_size`, `search` (title, short_url, long_url)

**Response Body:**
```json
{
  "response": {
    "data": [
      {
        "id": "uuid",
        "title": "string",
        "long_url": "string",
        "short_url": "string",
        "created_at": "datetime"
      }
    ],
    "pagination": {
      "count": 0,
      "total_pages": 0,
       "is_next": false,
       "is_prev": false,
       "next_page": 0
    }
  }
}
```

## Edit Short URL
**Endpoint:** `/api/v1/url-shortener/edit/<str:url_id>/`
**Method:** `PUT`
**Brief:** Edit an existing shortened URL.

**Request Body:**
```json
{
  "title": "string",
  "long_url": "string",
  "short_url": "string"
}
```

## Delete Short URL
**Endpoint:** `/api/v1/url-shortener/delete/<str:url_id>/`
**Method:** `DELETE`
**Brief:** Delete a shortened URL.

**Response Body:**
```json
{
  "general_message": "Url deleted successfully..",
  "statusCode": 200
}
```

## Get Analytics
**Endpoint:** `/api/v1/url-shortener/get-analytics/<str:url_id>/`
**Method:** `GET`
**Brief:** Get detailed analytics for a shortened URL.

**Response Body:**
```json
{
  "response": {
    "total_clicks": 0,
    "created_on": "YYYY-MM-DD",
    "browsers": { "chrome": 0 },
    "platforms": { "windows": 0 },
    "devices": { "desktop": 0 },
    "sources": { "direct": 0 },
    "ip_address": { "127.0.0.1": 0 },
    "city": { "kochi": 0 },
    "region": { "kerala": 0 },
    "countries": { "India": 0 },
    "time_based_data": { "all_time": [] },
    "long_url": "string",
    "short_url": "string",
    "title": "string"
  }
}
```
