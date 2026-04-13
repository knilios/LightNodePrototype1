# LightNode Prototype API Routes

Base URL: http://127.0.0.1:8000

## Authentication Model

- API is the source of truth for identity and accountability.
- All endpoints require `Authorization: Bearer <token>` except:
  - `GET /health`
  - `POST /auth/login`
- Optional request headers:
  - `X-Extension-Id`: caller extension identity for audit attribution.
  - `X-Request-Id`: request correlation id.

---

## 1) Health

### GET /health
Checks API, database, and storage health.

Response 200:
```json
{
  "status": "ok",
  "database": "ok",
  "storage": "ok"
}
```

---

## 2) Login

### POST /auth/login
Authenticates user credentials and returns bearer token.

Request body (application/json):
```json
{
  "username": "alice",
  "password": "secret123"
}
```

Response 200:
```json
{
  "access_token": "<opaque-token>",
  "token_type": "bearer",
  "expires_at": "2026-04-14T10:00:00+00:00",
  "user": {
    "id": "<user-id>",
    "username": "alice",
    "role": "user"
  }
}
```

Error responses:
- 401 invalid credentials

---

## 3) Logout

### POST /auth/logout
Revokes current bearer token.

Headers:
- `Authorization: Bearer <token>`

Response 200:
```json
{
  "status": "ok"
}
```

---

## 4) Current User

### GET /auth/me
Returns current authenticated identity.

Headers:
- `Authorization: Bearer <token>`

Response 200:
```json
{
  "id": "<user-id>",
  "username": "alice",
  "role": "user",
  "extension_id": "mcp-extension"
}
```

---

## 5) Create Folder

### POST /folders
Creates a folder.

Headers:
- `Authorization: Bearer <token>`

Request body (application/json):
```json
{
  "name": "demo",
  "parent_folder_id": null
}
```

Response 200:
```json
{
  "id": "<folder-id>",
  "name": "demo",
  "parent_folder_id": null,
  "full_path": "/demo",
  "created_at": "2026-04-11T07:34:02.679326+00:00"
}
```

---

## 6) Upload File

### POST /upload
Uploads a file as multipart/form-data.

Headers:
- `Authorization: Bearer <token>`

Form fields:
- `file` (required, file)
- `folder_id` (optional, text)

Response 200:
```json
{
  "id": "<file-id>",
  "folder_id": "<folder-id-or-null>",
  "filename": "sample.txt",
  "storage_path": "demo/<file-id>_sample.txt",
  "size_bytes": 17,
  "sha256_hash": "<sha256>",
  "created_at": "2026-04-11T07:34:13.540017+00:00"
}
```

---

## 7) List Files

### GET /files
Returns files, newest first.

Headers:
- `Authorization: Bearer <token>`

Optional query params:
- `folder_id`

---

## 8) Download File

### GET /files/{file_id}/download
Downloads file payload by id.

Headers:
- `Authorization: Bearer <token>`

Response 200:
- Binary file response

---

## 9) Search Files

### GET /search?q=<text>
Filename-only search.

Headers:
- `Authorization: Bearer <token>`

---

## 10) List Root Contents (like ls /)

### GET /root
Lists root-level folders and files.

Headers:
- `Authorization: Bearer <token>`

---

## 11) List Folder Contents (like ls)

### GET /folders/{folder_id}/contents
Lists subfolders and files for a folder.

Headers:
- `Authorization: Bearer <token>`

---

## Host-Only User Management CLI

Run from host machine shell:

```bash
python -m src.database.manage_users create-user alice --role user
python -m src.database.manage_users list-users
python -m src.database.manage_users reset-password alice
python -m src.database.manage_users deactivate-user alice
python -m src.database.manage_users activate-user alice
```

No public signup endpoint exists in API.
