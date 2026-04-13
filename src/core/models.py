from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Folder:
    id: str
    name: str
    parent_folder_id: str | None
    full_path: str
    created_at: str


@dataclass
class FileRecord:
    id: str
    folder_id: str | None
    filename: str
    storage_path: str
    size_bytes: int
    sha256_hash: str
    created_at: str
