# Auth API Reference

## Authentication

### Google Mobile Authentication
**Endpoint:** `/api/v1/user/auth/google-mobile-login/`
**Method:** `POST`
**Brief:** Authenticate user using Google Mobile ID token. This is a proxy endpoint that forwards the request to the central auth server.
**Request Body:**
```json
{
    "id_token": "google_id_token_string"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {
        "general": [
            "Access Granted"
        ]
    },
    "response": {
        "accessToken": "access_token_string",
        "refreshToken": "refresh_token_string"
    }
}
```

### Apple Mobile Authentication
**Endpoint:** `/api/v1/user/auth/apple-mobile-login/`
**Method:** `POST`
**Brief:** Authenticate user using Apple Mobile Identity token. This is a proxy endpoint that forwards the request to the central auth server.
**Request Body:**
```json
{
    "identity_token": "apple_identity_token_string",
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
            "Access Granted"
        ]
    },
    "response": {
        "accessToken": "access_token_string",
        "refreshToken": "refresh_token_string"
    }
}
```

### Refresh Token
**Endpoint:** `/api/v1/user/auth/refresh-token/`
**Method:** `POST`
**Brief:** Refresh access token using a refresh token. This is a proxy endpoint.
**Request Body:**
```json
{
    "refreshToken": "valid_refresh_token_string"
}
```
**Sample Response:**
```json
{
    "hasError": false,
    "statusCode": 200,
    "message": {},
    "response": {
        "accessToken": "new_access_token_string",
        "refreshToken": "new_refresh_token_string"
    }
}
```
