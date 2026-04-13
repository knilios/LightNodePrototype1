from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import Header, HTTPException

from src.database.db import get_connection

PBKDF2_ITERATIONS = 240000
TOKEN_TTL_HOURS = 24


def _now() -> datetime:
    return datetime.now(UTC)


def _now_iso() -> str:
    return _now().isoformat()


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, iterations_raw, salt_hex, digest_hex = stored_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False

    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


def create_user(username: str, password: str, role: str = "user") -> dict[str, Any]:
    username = username.strip().lower()
    if not username:
        raise ValueError("Username is required")

    connection = get_connection()
    existing = connection.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing is not None:
        raise ValueError("Username already exists")

    user_id = str(uuid4())
    created_at = _now_iso()
    password_hash = hash_password(password)

    connection.execute(
        "INSERT INTO users(id, username, password_hash, role, is_active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
        (user_id, username, password_hash, role, created_at),
    )
    connection.commit()

    return {
        "id": user_id,
        "username": username,
        "role": role,
        "is_active": True,
        "created_at": created_at,
    }


def list_users() -> list[dict[str, Any]]:
    connection = get_connection()
    rows = connection.execute(
        "SELECT id, username, role, is_active, created_at FROM users ORDER BY created_at"
    ).fetchall()
    return [dict(row) for row in rows]


def set_user_active(username: str, active: bool) -> bool:
    connection = get_connection()
    cursor = connection.execute(
        "UPDATE users SET is_active = ? WHERE username = ?",
        (1 if active else 0, username.strip().lower()),
    )
    connection.commit()
    return cursor.rowcount > 0


def reset_password(username: str, new_password: str) -> bool:
    connection = get_connection()
    new_hash = hash_password(new_password)
    cursor = connection.execute(
        "UPDATE users SET password_hash = ? WHERE username = ?",
        (new_hash, username.strip().lower()),
    )
    connection.commit()
    return cursor.rowcount > 0


def _get_user_by_username(username: str) -> dict[str, Any] | None:
    connection = get_connection()
    row = connection.execute(
        "SELECT id, username, password_hash, role, is_active, created_at FROM users WHERE username = ?",
        (username.strip().lower(),),
    ).fetchone()
    return dict(row) if row else None


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    user = _get_user_by_username(username)
    if user is None:
        return None
    if int(user["is_active"]) != 1:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def issue_token(user_id: str, extension_id: str | None = None) -> dict[str, Any]:
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    token_id = str(uuid4())
    issued_at = _now()
    expires_at = issued_at + timedelta(hours=TOKEN_TTL_HOURS)

    connection = get_connection()
    connection.execute(
        "INSERT INTO auth_tokens(id, token_hash, user_id, extension_id, issued_at, expires_at, revoked_at) VALUES (?, ?, ?, ?, ?, ?, NULL)",
        (
            token_id,
            token_hash,
            user_id,
            extension_id,
            issued_at.isoformat(),
            expires_at.isoformat(),
        ),
    )
    connection.commit()

    return {
        "access_token": raw_token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
    }


def issue_access_token_for_user(
    username: str,
    extension_id: str | None = None,
    days_valid: int = 30,
) -> dict[str, Any]:
    user = _get_user_by_username(username)
    if user is None:
        raise ValueError("User not found")
    if int(user["is_active"]) != 1:
        raise ValueError("User inactive")

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    token_id = str(uuid4())
    issued_at = _now()
    expires_at = issued_at + timedelta(days=days_valid)

    connection = get_connection()
    connection.execute(
        "INSERT INTO auth_tokens(id, token_hash, user_id, extension_id, issued_at, expires_at, revoked_at) VALUES (?, ?, ?, ?, ?, ?, NULL)",
        (
            token_id,
            token_hash,
            user["id"],
            extension_id,
            issued_at.isoformat(),
            expires_at.isoformat(),
        ),
    )
    connection.commit()

    return {
        "token_id": token_id,
        "access_token": raw_token,
        "token_type": "bearer",
        "issued_at": issued_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "extension_id": extension_id,
    }


def revoke_token(raw_token: str) -> None:
    token_hash = _hash_token(raw_token)
    connection = get_connection()
    connection.execute(
        "UPDATE auth_tokens SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
        (_now_iso(), token_hash),
    )
    connection.commit()


def revoke_user_tokens(user_id: str) -> None:
    connection = get_connection()
    connection.execute(
        "UPDATE auth_tokens SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
        (_now_iso(), user_id),
    )
    connection.commit()


def _get_token_record(raw_token: str) -> dict[str, Any] | None:
    token_hash = _hash_token(raw_token)
    connection = get_connection()
    row = connection.execute(
        """
        SELECT
            t.id as token_id,
            t.user_id,
            t.extension_id,
            t.issued_at,
            t.expires_at,
            t.revoked_at,
            u.username,
            u.role,
            u.is_active
        FROM auth_tokens t
        JOIN users u ON u.id = t.user_id
        WHERE t.token_hash = ?
        """,
        (token_hash,),
    ).fetchone()
    return dict(row) if row else None


def list_tokens(username: str | None = None) -> list[dict[str, Any]]:
    connection = get_connection()

    if username:
        user = _get_user_by_username(username)
        if user is None:
            raise ValueError("User not found")

        rows = connection.execute(
            """
            SELECT
                t.id,
                t.user_id,
                u.username,
                t.extension_id,
                t.issued_at,
                t.expires_at,
                t.revoked_at
            FROM auth_tokens t
            JOIN users u ON u.id = t.user_id
            WHERE t.user_id = ?
            ORDER BY t.issued_at DESC
            """,
            (user["id"],),
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT
                t.id,
                t.user_id,
                u.username,
                t.extension_id,
                t.issued_at,
                t.expires_at,
                t.revoked_at
            FROM auth_tokens t
            JOIN users u ON u.id = t.user_id
            ORDER BY t.issued_at DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def revoke_token_by_id(token_id: str) -> bool:
    connection = get_connection()
    cursor = connection.execute(
        "UPDATE auth_tokens SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
        (_now_iso(), token_id),
    )
    connection.commit()
    return cursor.rowcount > 0


def get_auth_context(
    authorization: str | None = Header(default=None),
    x_extension_id: str | None = Header(default=None),
) -> dict[str, Any]:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization scheme")

    raw_token = authorization.split(" ", 1)[1].strip()
    if not raw_token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token_record = _get_token_record(raw_token)
    if token_record is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    if token_record["revoked_at"] is not None:
        raise HTTPException(status_code=401, detail="Token revoked")

    if int(token_record["is_active"]) != 1:
        raise HTTPException(status_code=401, detail="User inactive")

    expires_at = datetime.fromisoformat(token_record["expires_at"])
    if expires_at <= _now():
        raise HTTPException(status_code=401, detail="Token expired")

    token_extension = token_record.get("extension_id")
    if token_extension and x_extension_id and token_extension != x_extension_id:
        raise HTTPException(status_code=401, detail="Extension identity mismatch")

    return {
        "token": raw_token,
        "token_id": token_record["token_id"],
        "user_id": token_record["user_id"],
        "username": token_record["username"],
        "role": token_record["role"],
        "extension_id": x_extension_id or token_extension,
    }
