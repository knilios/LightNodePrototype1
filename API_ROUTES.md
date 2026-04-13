# LightNode Prototype API Routes

Base URL: http://127.0.0.1:8000

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

Possible status values:
- status: ok | degraded
- database: ok | error
- storage: ok | error

---

## 2) Create Folder

### POST /folders
Creates a folder.

Request body (application/json):
```json
{
  "name": "demo",
  "parent_folder_id": null
}
```

Notes:
- parent_folder_id is optional.
- name must not contain / or \\.

Response 200:
```json
{
  "id": "7d57e211-5e08-4bcb-93c7-162de557ef29",
  "name": "demo",
  "parent_folder_id": null,
  "full_path": "/demo",
  "created_at": "2026-04-11T07:34:02.679326+00:00"
}
```

Error responses:
- 400 invalid folder name or invalid parent
- 500 internal error

---

## 3) Upload File

### POST /upload
Uploads a file as multipart/form-data.

Form fields:
- file (required, file)
- folder_id (optional, text)

Behavior:
- If folder_id is provided, file is stored under that folder path.
- If folder_id is not provided, file is stored at root.

Response 200:
```json
{
  "id": "08aa0b77-c9e1-41df-80ea-fdec27c5e2fc",
  "folder_id": "3fce4d38-043f-4a1a-a053-17a76b1e7dcb",
  "filename": "sample.txt",
  "storage_path": "demo2/08aa0b77-c9e1-41df-80ea-fdec27c5e2fc_sample.txt",
  "size_bytes": 17,
  "sha256_hash": "337810826bbe8d591a91aceedad0f9bc758cfa81033255a8550ec4904e5ba43a",
  "created_at": "2026-04-11T07:34:13.540017+00:00"
}
```

Error responses:
- 400 filename missing
- 404 folder not found
- 500 upload failed

---

## 4) List Files

### GET /files
Returns all files, newest first.

Optional query params:
- folder_id (string)

Example:
- GET /files
- GET /files?folder_id=3fce4d38-043f-4a1a-a053-17a76b1e7dcb

Response 200:
```json
[
  {
    "id": "08aa0b77-c9e1-41df-80ea-fdec27c5e2fc",
    "folder_id": "3fce4d38-043f-4a1a-a053-17a76b1e7dcb",
    "filename": "sample.txt",
    "storage_path": "demo2/08aa0b77-c9e1-41df-80ea-fdec27c5e2fc_sample.txt",
    "size_bytes": 17,
    "sha256_hash": "337810826bbe8d591a91aceedad0f9bc758cfa81033255a8550ec4904e5ba43a",
    "created_at": "2026-04-11T07:34:13.540017+00:00"
  }
]
```

---

## 5) Download File

### GET /files/{file_id}/download
Downloads the file by id.

Path param:
- file_id (UUID string)

Response 200:
- Binary file response
- Content-Disposition attachment with original filename

Error responses:
- 404 file metadata not found
- 404 file payload missing on disk

---

## 6) Search Files

### GET /search
Filename-only search.

Query params:
- q (string, required)

Example:
- GET /search?q=Jang

Response 200:
```json
[
  {
    "id": "a2bdfbc2-572f-4517-b1e7-e7539446860d",
    "folder_id": null,
    "filename": "I4(art)_Jang_drawing1_v1.jpg",
    "storage_path": "a2bdfbc2-572f-4517-b1e7-e7539446860d_I4(art)_Jang_drawing1_v1.jpg",
    "size_bytes": 53418,
    "sha256_hash": "8a756bd3a79b34da4c79b7ab76b7dc57a5c1057ab79cf93452cefe5b31e25d1a",
    "created_at": "2026-04-11T09:16:52.654586+00:00"
  }
]
```

Behavior note:
- Search matches filename text only.
- Empty q returns an empty list.

---

## 7) List Root Contents (like `ls /`)

### GET /root
Lists all folders and files at the root level (like Linux `ls /` or `cd C:\` on Windows).

Response 200:
```json
{
  "folder": {
    "id": "root",
    "name": "/",
    "parent_folder_id": null,
    "full_path": "/",
    "created_at": null
  },
  "contents": [
    {
      "type": "folder",
      "id": "7d57e211-5e08-4bcb-93c7-162de557ef29",
      "name": "demo",
      "created_at": "2026-04-11T07:34:02.679326+00:00"
    },
    {
      "type": "file",
      "id": "a2bdfbc2-572f-4517-b1e7-e7539446860d",
      "name": "I4(art)_Jang_drawing1_v1.jpg",
      "size_bytes": 53418,
      "created_at": "2026-04-11T09:16:52.654586+00:00"
    }
  ]
}
```

---

## 8) Health

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

Possible status values:
- status: ok | degraded
- database: ok | error
- storage: ok | error

### GET /folders/{folder_id}/contents
Lists all subfolders and files in a folder, with metadata (like Linux `ls` output).

Path param:
- folder_id (UUID string)

Response 200:
```json
{
  "folder": {
    "id": "3fce4d38-043f-4a1a-a053-17a76b1e7dcb",
    "name": "demo2",
    "parent_folder_id": null,
    "full_path": "/demo2",
    "created_at": "2026-04-11T07:34:12.000000+00:00"
  },
  "contents": [
    {
      "type": "folder",
      "id": "af12cd45-abcd-4567-ef89-123456789abc",
      "name": "subfolder",
      "created_at": "2026-04-11T08:00:00.000000+00:00"
    },
    {
      "type": "file",
      "id": "08aa0b77-c9e1-41df-80ea-fdec27c5e2fc",
      "name": "sample.txt",
      "size_bytes": 17,
      "created_at": "2026-04-11T07:34:13.540017+00:00"
    }
  ]
}
```

Error responses:
- 404 folder not found
- 500 internal error

---

## Minimal cURL Examples

Create folder:
```bash
curl -X POST http://127.0.0.1:8000/folders \
  -H "Content-Type: application/json" \
  -d '{"name":"demo"}'
```

Upload:
```bash
curl -X POST http://127.0.0.1:8000/upload \
  -F "folder_id=<folder-id>" \
  -F "file=@sample.txt"
```

List:
```bash
curl "http://127.0.0.1:8000/files"
```

Search:
```bash
curl "http://127.0.0.1:8000/search?q=sample"
```

List root (ls /):
```bash
curl "http://127.0.0.1:8000/root"
```

List folder contents (ls):
```bash
curl "http://127.0.0.1:8000/folders/<folder-id>/contents"
```

Download:
```bash
curl -o downloaded.bin "http://127.0.0.1:8000/files/<file-id>/download"
```
