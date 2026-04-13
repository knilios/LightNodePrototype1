from __future__ import annotations

from src.core.storage import StorageUnavailableError, ensure_storage_ready
from src.database.db import get_connection


def health_status() -> dict:
    db_ok = True
    storage_ok = True

    try:
        connection = get_connection()
        connection.execute("SELECT 1")
    except Exception:
        db_ok = False

    try:
        ensure_storage_ready()
    except StorageUnavailableError:
        storage_ok = False

    return {
        "status": "ok" if db_ok and storage_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "storage": "ok" if storage_ok else "error",
    }
