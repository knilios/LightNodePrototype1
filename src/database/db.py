from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "lightnode.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

_connection: sqlite3.Connection | None = None


def _configure_connection(connection: sqlite3.Connection) -> None:
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA journal_mode = WAL;")
    connection.execute("PRAGMA synchronous = FULL;")


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        _configure_connection(_connection)
    return _connection


def init_database() -> None:
    connection = get_connection()
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    connection.executescript(schema_sql)
    connection.commit()


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    connection = get_connection()
    try:
        connection.execute("BEGIN;")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
