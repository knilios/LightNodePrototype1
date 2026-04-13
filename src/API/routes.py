from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.core.audit import log_audit
from src.core.auth import authenticate_user, get_auth_context, issue_token, revoke_token
from src.core.files import create_file_record, get_file, list_files, search_files
from src.core.folders import create_folder, get_folder, list_folder_contents, list_root_contents
from src.core.health import health_status
from src.core.storage import resolve_storage_path, save_stream_to_storage

router = APIRouter()


class CreateFolderRequest(BaseModel):
    name: str
    parent_folder_id: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


def _request_id(request: Request) -> str | None:
    return request.headers.get("x-request-id")


def _extension_id(request: Request) -> str | None:
    return request.headers.get("x-extension-id")


@router.post("/auth/login")
def login_endpoint(payload: LoginRequest, request: Request):
    user = authenticate_user(payload.username, payload.password)
    if user is None:
        log_audit(
            actor_user_id=None,
            action="auth.login",
            status="denied",
            request_id=_request_id(request),
            extension_id=_extension_id(request),
            metadata={"username": payload.username.strip().lower()},
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = issue_token(user_id=user["id"], extension_id=_extension_id(request))
    log_audit(
        actor_user_id=user["id"],
        action="auth.login",
        status="success",
        request_id=_request_id(request),
        extension_id=_extension_id(request),
    )

    return {
        **token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
        },
    }


@router.post("/auth/logout")
def logout_endpoint(request: Request, auth=Depends(get_auth_context)):
    revoke_token(auth["token"])
    log_audit(
        actor_user_id=auth["user_id"],
        action="auth.logout",
        status="success",
        request_id=_request_id(request),
        extension_id=auth.get("extension_id"),
    )
    return {"status": "ok"}


@router.get("/auth/me")
def me_endpoint(auth=Depends(get_auth_context)):
    return {
        "id": auth["user_id"],
        "username": auth["username"],
        "role": auth["role"],
        "extension_id": auth.get("extension_id"),
    }


@router.post("/folders")
def create_folder_endpoint(payload: CreateFolderRequest, request: Request, auth=Depends(get_auth_context)):
    try:
        folder = create_folder(payload.name, payload.parent_folder_id)
        log_audit(
            actor_user_id=auth["user_id"],
            action="folder.create",
            status="success",
            request_id=_request_id(request),
            extension_id=auth.get("extension_id"),
            target_type="folder",
            target_id=folder["id"],
            metadata={"name": payload.name, "parent_folder_id": payload.parent_folder_id},
        )
        return folder
    except ValueError as exc:
        log_audit(
            actor_user_id=auth["user_id"],
            action="folder.create",
            status="denied",
            request_id=_request_id(request),
            extension_id=auth.get("extension_id"),
            metadata={"reason": str(exc), "name": payload.name},
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        log_audit(
            actor_user_id=auth["user_id"],
            action="folder.create",
            status="error",
            request_id=_request_id(request),
            extension_id=auth.get("extension_id"),
            metadata={"error": str(exc)},
        )
        raise HTTPException(status_code=500, detail="Unable to create folder") from exc


@router.post("/upload")
def upload_file_endpoint(
    request: Request,
    file: UploadFile = File(...),
    folder_id: str | None = Form(default=None),
    auth=Depends(get_auth_context),
):
    folder = None
    relative_folder_path = ""
    file_id = str(uuid4())
    filename = file.filename

    if not filename:
        log_audit(
            actor_user_id=auth["user_id"],
            action="file.upload",
            status="denied",
            request_id=_request_id(request),
            extension_id=auth.get("extension_id"),
            metadata={"reason": "missing_filename"},
        )
        raise HTTPException(status_code=400, detail="Filename is required")

    if folder_id:
        folder = get_folder(folder_id)
        if folder is None:
            log_audit(
                actor_user_id=auth["user_id"],
                action="file.upload",
                status="denied",
                request_id=_request_id(request),
                extension_id=auth.get("extension_id"),
                metadata={"reason": "folder_not_found", "folder_id": folder_id},
            )
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

        log_audit(
            actor_user_id=auth["user_id"],
            action="file.upload",
            status="success",
            request_id=_request_id(request),
            extension_id=auth.get("extension_id"),
            target_type="file",
            target_id=final_record["id"],
            metadata={"filename": filename, "folder_id": folder_id},
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
        log_audit(
            actor_user_id=auth["user_id"],
            action="file.upload",
            status="error",
            request_id=_request_id(request),
            extension_id=auth.get("extension_id"),
            metadata={"error": str(exc), "filename": filename},
        )
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc
    finally:
        file.file.close()


@router.get("/files")
def list_files_endpoint(request: Request, folder_id: str | None = None, auth=Depends(get_auth_context)):
    records = list_files(folder_id)
    log_audit(
        actor_user_id=auth["user_id"],
        action="file.list",
        status="success",
        request_id=_request_id(request),
        extension_id=auth.get("extension_id"),
        metadata={"folder_id": folder_id, "count": len(records)},
    )
    return records


@router.get("/files/{file_id}/download")
def download_file_endpoint(file_id: str, request: Request, auth=Depends(get_auth_context)):
    record = get_file(file_id)
    if record is None:
        log_audit(
            actor_user_id=auth["user_id"],
            action="file.download",
            status="denied",
            request_id=_request_id(request),
            extension_id=auth.get("extension_id"),
            target_type="file",
            target_id=file_id,
            metadata={"reason": "metadata_missing"},
        )
        raise HTTPException(status_code=404, detail="File not found")

    try:
        path = resolve_storage_path(record["storage_path"])
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File payload missing") from exc

    if not path.exists():
        log_audit(
            actor_user_id=auth["user_id"],
            action="file.download",
            status="error",
            request_id=_request_id(request),
            extension_id=auth.get("extension_id"),
            target_type="file",
            target_id=file_id,
            metadata={"reason": "payload_missing"},
        )
        raise HTTPException(status_code=404, detail="File payload missing")

    log_audit(
        actor_user_id=auth["user_id"],
        action="file.download",
        status="success",
        request_id=_request_id(request),
        extension_id=auth.get("extension_id"),
        target_type="file",
        target_id=file_id,
    )

    return FileResponse(path=path, filename=record["filename"])


@router.get("/search")
def search_files_endpoint(q: str, request: Request, auth=Depends(get_auth_context)):
    if not q.strip():
        log_audit(
            actor_user_id=auth["user_id"],
            action="file.search",
            status="success",
            request_id=_request_id(request),
            extension_id=auth.get("extension_id"),
            metadata={"query": q, "count": 0},
        )
        return []
    results = search_files(q)
    log_audit(
        actor_user_id=auth["user_id"],
        action="file.search",
        status="success",
        request_id=_request_id(request),
        extension_id=auth.get("extension_id"),
        metadata={"query": q, "count": len(results)},
    )
    return results


@router.get("/folders/{folder_id}/contents")
def list_folder_contents_endpoint(folder_id: str, request: Request, auth=Depends(get_auth_context)):
    try:
        result = list_folder_contents(folder_id)
        log_audit(
            actor_user_id=auth["user_id"],
            action="folder.list_contents",
            status="success",
            request_id=_request_id(request),
            extension_id=auth.get("extension_id"),
            target_type="folder",
            target_id=folder_id,
            metadata={"count": len(result["contents"])},
        )
        return result
    except ValueError as exc:
        log_audit(
            actor_user_id=auth["user_id"],
            action="folder.list_contents",
            status="denied",
            request_id=_request_id(request),
            extension_id=auth.get("extension_id"),
            target_type="folder",
            target_id=folder_id,
            metadata={"reason": str(exc)},
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        log_audit(
            actor_user_id=auth["user_id"],
            action="folder.list_contents",
            status="error",
            request_id=_request_id(request),
            extension_id=auth.get("extension_id"),
            target_type="folder",
            target_id=folder_id,
            metadata={"error": str(exc)},
        )
        raise HTTPException(status_code=500, detail="Unable to list folder contents") from exc


@router.get("/root")
def list_root_endpoint(request: Request, auth=Depends(get_auth_context)):
    try:
        result = list_root_contents()
        log_audit(
            actor_user_id=auth["user_id"],
            action="folder.list_root",
            status="success",
            request_id=_request_id(request),
            extension_id=auth.get("extension_id"),
            metadata={"count": len(result["contents"])},
        )
        return result
    except Exception as exc:
        log_audit(
            actor_user_id=auth["user_id"],
            action="folder.list_root",
            status="error",
            request_id=_request_id(request),
            extension_id=auth.get("extension_id"),
            metadata={"error": str(exc)},
        )
        raise HTTPException(status_code=500, detail="Unable to list root contents") from exc


@router.get("/health")
def health_endpoint():
    return health_status()
