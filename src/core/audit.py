from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.database.db import get_connection


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def log_audit(
    actor_user_id: str | None,
    action: str,
    status: str,
    request_id: str | None = None,
    extension_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    connection = get_connection()
    connection.execute(
        """
        INSERT INTO audit_logs(
            id,
            actor_user_id,
            action,
            target_type,
            target_id,
            status,
            request_id,
            extension_id,
            metadata_json,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            actor_user_id,
            action,
            target_type,
            target_id,
            status,
            request_id,
            extension_id,
            json.dumps(metadata or {}, ensure_ascii=True),
            _now_iso(),
        ),
    )
    connection.commit()
