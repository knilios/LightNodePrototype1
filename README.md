# LightNode Prototype (Python)

Minimal prototype implementing:
- create folder
- upload file (streamed)
- list files
- download file
- filename search

## Run

1. Create virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Start API:
   `uvicorn src.API.main:app --reload`

## Endpoints

- `POST /folders`
- `POST /upload` (multipart form-data: `file`, optional `folder_id`)
- `GET /files`
- `GET /files/{id}/download`
- `GET /search?q=<text>`
- `GET /health`
