from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.core.files import create_file_record, get_file, list_files, search_files
from src.core.folders import create_folder, get_folder, list_folder_contents, list_root_contents
from src.core.health import health_status
from src.core.storage import resolve_storage_path, save_stream_to_storage

router = APIRouter()


class CreateFolderRequest(BaseModel):
    name: str
    parent_folder_id: str | None = None


@router.post("/folders")
def create_folder_endpoint(payload: CreateFolderRequest):
    try:
        return create_folder(payload.name, payload.parent_folder_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to create folder") from exc


@router.post("/upload")
def upload_file_endpoint(file: UploadFile = File(...), folder_id: str | None = Form(default=None)):
    folder = None
    relative_folder_path = ""
    file_id = str(uuid4())
    filename = file.filename

    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    if folder_id:
        folder = get_folder(folder_id)
        if folder is None:
            raise HTTPException(status_code=404, detail="Folder not found")
        relative_folder_path = folder["full_path"]

    try:
        temp_result = save_stream_to_storage(
            file_stream=file.file,
            relative_folder_path=relative_folder_path,
            original_filename=filename,
            target_file_id=file_id,
        )

        final_record = create_file_record(
            file_id=file_id,
            folder_id=folder["id"] if folder else None,
            filename=filename,
            storage_path=temp_result["storage_path"],
            size_bytes=temp_result["size_bytes"],
            sha256_hash=temp_result["sha256_hash"],
        )

        return final_record
    except HTTPException:
        raise
    except Exception as exc:
        # Best-effort cleanup prevents metadata/file drift during prototype errors.
        try:
            if "temp_result" in locals():
                candidate = resolve_storage_path(temp_result["storage_path"])
                if candidate.exists():
                    candidate.unlink()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc
    finally:
        file.file.close()


@router.get("/files")
def list_files_endpoint(folder_id: str | None = None):
    return list_files(folder_id)


@router.get("/files/{file_id}/download")
def download_file_endpoint(file_id: str):
    record = get_file(file_id)
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        path = resolve_storage_path(record["storage_path"])
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File payload missing") from exc

    if not path.exists():
        raise HTTPException(status_code=404, detail="File payload missing")

    return FileResponse(path=path, filename=record["filename"])


@router.get("/search")
def search_files_endpoint(q: str):
    if not q.strip():
        return []
    return search_files(q)


@router.get("/folders/{folder_id}/contents")
def list_folder_contents_endpoint(folder_id: str):
    try:
        return list_folder_contents(folder_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to list folder contents") from exc


@router.get("/root")
def list_root_endpoint():
    try:
        return list_root_contents()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to list root contents") from exc


@router.get("/health")
def health_endpoint():
    return health_status()
