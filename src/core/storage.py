from __future__ import annotations

import hashlib
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

BASE_DIR = Path(__file__).resolve().parents[2]
FILES_ROOT = BASE_DIR / "data" / "files"


class StorageUnavailableError(Exception):
    pass


def ensure_storage_ready() -> None:
    try:
        FILES_ROOT.mkdir(parents=True, exist_ok=True)
        probe_file = FILES_ROOT / ".write_probe"
        probe_file.write_text("ok", encoding="utf-8")
        probe_file.unlink(missing_ok=True)
    except OSError as exc:
        raise StorageUnavailableError("Storage path is unavailable or not writable") from exc


def save_stream_to_storage(file_stream, relative_folder_path: str, original_filename: str, target_file_id: str) -> dict:
    ensure_storage_ready()

    clean_folder = relative_folder_path.strip("/")
    destination_folder = FILES_ROOT / clean_folder if clean_folder else FILES_ROOT
    destination_folder.mkdir(parents=True, exist_ok=True)

    safe_name = original_filename.replace("/", "_").replace("\\", "_")
    destination_file = destination_folder / f"{target_file_id}_{safe_name}"

    hasher = hashlib.sha256()
    size_bytes = 0

    with NamedTemporaryFile(delete=False, dir=destination_folder, prefix="upload_", suffix=".tmp") as temp_file:
        temp_path = Path(temp_file.name)
        while True:
            chunk = file_stream.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
            temp_file.write(chunk)
            size_bytes += len(chunk)
        temp_file.flush()
        os.fsync(temp_file.fileno())

    temp_path.replace(destination_file)

    return {
        "storage_path": str(destination_file.relative_to(FILES_ROOT)).replace("\\", "/"),
        "size_bytes": size_bytes,
        "sha256_hash": hasher.hexdigest(),
    }


def resolve_storage_path(storage_path: str) -> Path:
    path = (FILES_ROOT / storage_path).resolve()
    root_resolved = FILES_ROOT.resolve()
    if root_resolved not in path.parents and path != root_resolved:
        raise FileNotFoundError("Invalid storage path")
    return path
