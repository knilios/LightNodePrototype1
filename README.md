# LightNode Prototype (Python)

Minimal prototype implementing:
- create folder
- upload file (streamed)
- list files
- download file
- filename search
- users/password authentication with bearer tokens
- per-action audit logging

## Run

1. Create virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Start API:
   `uvicorn src.API.main:app --reload`

## Create first user (host-only)

Use shell commands on the host machine:

`python -m src.database.manage_users create-user admin --role admin`

Useful commands:
- `python -m src.database.manage_users list-users`
- `python -m src.database.manage_users reset-password admin`
- `python -m src.database.manage_users deactivate-user admin`
- `python -m src.database.manage_users activate-user admin`

## Login flow

1. `POST /auth/login` with username/password
2. Use returned bearer token in `Authorization` header for protected routes
3. `POST /auth/logout` to revoke token

## Access token alternative (host-issued)

Use a long-lived token generated on host as an alternative to username/password login:

- `python -m src.database.manage_users create-access-token mcp_server --days 30 --extension-id mcp`
- `python -m src.database.manage_users list-tokens --username mcp_server`
- `python -m src.database.manage_users revoke-token <token-id>`

Use the generated token exactly like login tokens:
- `Authorization: Bearer <access-token>`

## Endpoints

- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `POST /folders` (protected)
- `POST /upload` (protected)
- `GET /files` (protected)
- `GET /files/{id}/download` (protected)
- `GET /search?q=<text>` (protected)
- `GET /root` (protected)
- `GET /folders/{folder_id}/contents` (protected)
- `GET /health` (public)
