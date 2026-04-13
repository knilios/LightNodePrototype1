from __future__ import annotations

from datetime import datetime, UTC
from uuid import uuid4

from src.database.db import get_connection


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def create_folder(name: str, parent_folder_id: str | None) -> dict:
    if not name or "/" in name or "\\" in name:
        raise ValueError("Folder name is invalid")

    connection = get_connection()
    parent_path = ""
    if parent_folder_id:
        row = connection.execute(
            "SELECT id, full_path FROM folders WHERE id = ?",
            (parent_folder_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Parent folder not found")
        parent_path = row["full_path"]

    full_path = f"{parent_path}/{name}" if parent_path else f"/{name}"
    folder_id = str(uuid4())
    created_at = _now_iso()

    connection.execute(
        "INSERT INTO folders(id, name, parent_folder_id, full_path, created_at) VALUES (?, ?, ?, ?, ?)",
        (folder_id, name, parent_folder_id, full_path, created_at),
    )
    connection.commit()

    return {
        "id": folder_id,
        "name": name,
        "parent_folder_id": parent_folder_id,
        "full_path": full_path,
        "created_at": created_at,
    }


def get_folder(folder_id: str) -> dict | None:
    connection = get_connection()
    row = connection.execute(
        "SELECT id, name, parent_folder_id, full_path, created_at FROM folders WHERE id = ?",
        (folder_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def list_folder_contents(folder_id: str) -> dict:
    connection = get_connection()
    folder = get_folder(folder_id)
    if folder is None:
        raise ValueError("Folder not found")

    subfolders = connection.execute(
        "SELECT id, name, full_path, created_at FROM folders WHERE parent_folder_id = ? ORDER BY name",
        (folder_id,),
    ).fetchall()

    files = connection.execute(
        "SELECT id, filename, size_bytes, created_at FROM files WHERE folder_id = ? ORDER BY filename",
        (folder_id,),
    ).fetchall()

    contents = []
    for row in subfolders:
        contents.append({
            "type": "folder",
            "id": row["id"],
            "name": row["name"],
            "created_at": row["created_at"],
        })
    for row in files:
        contents.append({
            "type": "file",
            "id": row["id"],
            "name": row["filename"],
            "size_bytes": row["size_bytes"],
            "created_at": row["created_at"],
        })

    return {
        "folder": folder,
        "contents": contents,
    }


def list_root_contents() -> dict:
    connection = get_connection()
    subfolders = connection.execute(
        "SELECT id, name, full_path, created_at FROM folders WHERE parent_folder_id IS NULL ORDER BY name"
    ).fetchall()

    files = connection.execute(
        "SELECT id, filename, size_bytes, created_at FROM files WHERE folder_id IS NULL ORDER BY filename"
    ).fetchall()

    contents = []
    for row in subfolders:
        contents.append({
            "type": "folder",
            "id": row["id"],
            "name": row["name"],
            "created_at": row["created_at"],
        })
    for row in files:
        contents.append({
            "type": "file",
            "id": row["id"],
            "name": row["filename"],
            "size_bytes": row["size_bytes"],
            "created_at": row["created_at"],
        })

    return {
        "folder": {
            "id": "root",
            "name": "/",
            "parent_folder_id": None,
            "full_path": "/",
            "created_at": None,
        },
        "contents": contents,
    }
