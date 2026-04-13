from __future__ import annotations

from src.database.db import init_database


if __name__ == "__main__":
    init_database()
    print("Database initialized")
