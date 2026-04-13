from __future__ import annotations

from datetime import datetime, UTC

from src.database.db import get_connection


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def create_file_record(
    file_id: str,
    folder_id: str | None,
    filename: str,
    storage_path: str,
    size_bytes: int,
    sha256_hash: str,
) -> dict:
    created_at = _now_iso()
    connection = get_connection()

    connection.execute(
        "INSERT INTO files(id, folder_id, filename, storage_path, size_bytes, sha256_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (file_id, folder_id, filename, storage_path, size_bytes, sha256_hash, created_at),
    )
    connection.commit()

    return {
        "id": file_id,
        "folder_id": folder_id,
        "filename": filename,
        "storage_path": storage_path,
        "size_bytes": size_bytes,
        "sha256_hash": sha256_hash,
        "created_at": created_at,
    }


def list_files(folder_id: str | None = None) -> list[dict]:
    connection = get_connection()
    if folder_id:
        rows = connection.execute(
            "SELECT id, folder_id, filename, storage_path, size_bytes, sha256_hash, created_at FROM files WHERE folder_id = ? ORDER BY created_at DESC",
            (folder_id,),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT id, folder_id, filename, storage_path, size_bytes, sha256_hash, created_at FROM files ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_file(file_id: str) -> dict | None:
    connection = get_connection()
    row = connection.execute(
        "SELECT id, folder_id, filename, storage_path, size_bytes, sha256_hash, created_at FROM files WHERE id = ?",
        (file_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def search_files(query: str) -> list[dict]:
    connection = get_connection()
    rows = connection.execute(
        "SELECT id, folder_id, filename, storage_path, size_bytes, sha256_hash, created_at FROM files WHERE filename LIKE ? ORDER BY created_at DESC",
        (f"%{query}%",),
    ).fetchall()
    return [dict(row) for row in rows]
