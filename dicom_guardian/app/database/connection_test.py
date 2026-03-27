"""Database connection test utility for dicom_guardian (Step 20)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.database.db import check_database_health, initialize_database

REQUIRED_MIGRATIONS = {
    (1, "0001_bootstrap_sqlite_init"),
    (2, "0002_transfer_schema"),
    (3, "0003_metadata_schema"),
}


def run_database_connection_test(db_path: str | Path | None = None) -> bool:
    resolved = initialize_database(db_path)

    health_ok = check_database_health(resolved)
    if not health_ok:
        print("[guardian-db-test] health check failed")
        return False

    with sqlite3.connect(resolved) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT version, name FROM schema_migrations ORDER BY version;")
        migrations = set(cursor.fetchall())

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]

    missing = REQUIRED_MIGRATIONS.difference(migrations)
    if missing:
        print(f"[guardian-db-test] missing migrations: {sorted(missing)}")
        return False

    print(f"[guardian-db-test] database={resolved}")
    print(f"[guardian-db-test] tables={tables}")
    print(f"[guardian-db-test] migrations={sorted(migrations)}")
    print("[guardian-db-test] result=PASS")
    return True


if __name__ == "__main__":
    ok = run_database_connection_test()
    raise SystemExit(0 if ok else 1)
