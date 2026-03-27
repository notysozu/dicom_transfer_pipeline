"""SQLite bootstrap, connection management, and DB helper functions."""

from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Mapping, Sequence

from app.config import load_config
from app.dicom.checksum import detect_file_corruption, generate_file_checksum, verify_file_checksum
from app.database.models import (
    BOOTSTRAP_MIGRATION_INSERT,
    INTEGRITY_EVENTS_BY_INSTANCE_INDEX,
    INTEGRITY_EVENTS_BY_STUDY_INDEX,
    INTEGRITY_EVENTS_TABLE,
    INTEGRITY_SCHEMA_MIGRATION_INSERT,
    INSTANCE_METADATA_BY_SERIES_INDEX,
    INSTANCE_METADATA_BY_STUDY_INDEX,
    INSTANCE_METADATA_TABLE,
    METADATA_SCHEMA_MIGRATION_INSERT,
    SCHEMA_MIGRATIONS_TABLE,
    STUDY_METADATA_BY_DATE_INDEX,
    STUDY_METADATA_BY_PATIENT_INDEX,
    STUDY_METADATA_TABLE,
    SYSTEM_STATE_TABLE,
    SYSTEM_STATE_UPSERT,
    TRANSFERS_BY_STATUS_INDEX,
    TRANSFERS_BY_STUDY_INDEX,
    TRANSFERS_BY_TRANSFER_UID_INDEX,
    TRANSFERS_TABLE,
    TRANSFER_SCHEMA_MIGRATION_INSERT,
)

SQLITE_TIMEOUT_SECONDS = 30.0
DEFAULT_QUERY_LIMIT = 100
MAX_QUERY_LIMIT = 1000
TRANSFER_STATUS_VALUES = {"RECEIVED", "VALIDATED", "QUEUED", "SENT", "FAILED", "RETRYING"}
SHA256_HEX_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def _apply_pragmas(connection: sqlite3.Connection) -> None:
    """Apply production-oriented SQLite PRAGMA settings."""
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA synchronous=NORMAL;")
    connection.execute("PRAGMA foreign_keys=ON;")
    connection.execute("PRAGMA busy_timeout=5000;")


def _resolve_db_path(db_path: str | Path | None = None) -> Path:
    if db_path is not None:
        resolved = Path(db_path)
    else:
        resolved = load_config().database.path
    return resolved.expanduser().resolve()


def create_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Create a configured SQLite connection."""
    resolved = _resolve_db_path(db_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        resolved,
        timeout=SQLITE_TIMEOUT_SECONDS,
        isolation_level=None,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    _apply_pragmas(connection)
    return connection


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def _rows_to_dicts(rows: Sequence[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def _validate_limit(limit: int) -> int:
    parsed = int(limit)
    if parsed < 1:
        raise ValueError("limit must be greater than 0")
    return min(parsed, MAX_QUERY_LIMIT)


def _validate_transfer_status(status: str) -> str:
    normalized = status.strip().upper()
    if normalized not in TRANSFER_STATUS_VALUES:
        raise ValueError(f"invalid transfer status: {normalized}")
    return normalized


def _validate_sha256_digest(digest: str) -> str:
    normalized = str(digest).strip().lower()
    if not SHA256_HEX_PATTERN.match(normalized):
        raise ValueError("checksum_sha256 must be a 64-character lowercase hexadecimal SHA256 digest")
    return normalized


def _validate_integrity_event_type(event_type: str) -> str:
    normalized = str(event_type).strip().upper()
    allowed = {"CHECKSUM_VERIFIED", "CORRUPTION_DETECTED", "INTEGRITY_ERROR"}
    if normalized not in allowed:
        raise ValueError(f"invalid integrity event type: {normalized}")
    return normalized


def _validate_integrity_status(status: str) -> str:
    normalized = str(status).strip().upper()
    allowed = {"HEALTHY", "CORRUPTED", "ERROR"}
    if normalized not in allowed:
        raise ValueError(f"invalid integrity status: {normalized}")
    return normalized


@contextmanager
def get_connection(db_path: str | Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Yield a managed SQLite connection and always close it."""
    connection = create_connection(db_path=db_path)
    try:
        yield connection
    finally:
        connection.close()


def initialize_database(db_path: str | Path | None = None) -> Path:
    """Initialize SQLite database and all currently defined schemas."""
    resolved = _resolve_db_path(db_path)

    with get_connection(resolved) as connection:
        connection.execute("BEGIN;")
        try:
            connection.execute(SCHEMA_MIGRATIONS_TABLE)
            connection.execute(SYSTEM_STATE_TABLE)
            connection.execute(SYSTEM_STATE_UPSERT)
            connection.execute(BOOTSTRAP_MIGRATION_INSERT)
            connection.execute(TRANSFERS_TABLE)
            connection.execute(TRANSFERS_BY_STUDY_INDEX)
            connection.execute(TRANSFERS_BY_STATUS_INDEX)
            connection.execute(TRANSFERS_BY_TRANSFER_UID_INDEX)
            connection.execute(TRANSFER_SCHEMA_MIGRATION_INSERT)
            connection.execute(STUDY_METADATA_TABLE)
            connection.execute(INSTANCE_METADATA_TABLE)
            connection.execute(STUDY_METADATA_BY_DATE_INDEX)
            connection.execute(STUDY_METADATA_BY_PATIENT_INDEX)
            connection.execute(INSTANCE_METADATA_BY_STUDY_INDEX)
            connection.execute(INSTANCE_METADATA_BY_SERIES_INDEX)
            connection.execute(METADATA_SCHEMA_MIGRATION_INSERT)
            connection.execute(INTEGRITY_EVENTS_TABLE)
            connection.execute(INTEGRITY_EVENTS_BY_STUDY_INDEX)
            connection.execute(INTEGRITY_EVENTS_BY_INSTANCE_INDEX)
            connection.execute(INTEGRITY_SCHEMA_MIGRATION_INSERT)
            connection.execute("COMMIT;")
        except Exception:
            connection.execute("ROLLBACK;")
            raise

    return resolved


def check_database_health(db_path: str | Path | None = None) -> bool:
    """Return True when the database responds to a simple health query."""
    with get_connection(db_path) as connection:
        row = connection.execute("SELECT 1 AS ok;").fetchone()
        return bool(row and row["ok"] == 1)


def create_transfer_record(
    *,
    transfer_uid: str,
    study_instance_uid: str,
    source_ae_title: str,
    destination_ae_title: str,
    file_path: str,
    file_size_bytes: int,
    status: str = "RECEIVED",
    sop_instance_uid: str | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Insert a new transfer record and return the created row."""
    status_value = _validate_transfer_status(status)
    if file_size_bytes < 0:
        raise ValueError("file_size_bytes must be >= 0")

    query = """
    INSERT INTO transfers (
        transfer_uid,
        study_instance_uid,
        sop_instance_uid,
        source_ae_title,
        destination_ae_title,
        file_path,
        file_size_bytes,
        status
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """

    with get_connection(db_path) as connection:
        connection.execute("BEGIN;")
        try:
            connection.execute(
                query,
                (
                    transfer_uid,
                    study_instance_uid,
                    sop_instance_uid,
                    source_ae_title,
                    destination_ae_title,
                    file_path,
                    int(file_size_bytes),
                    status_value,
                ),
            )
            row = connection.execute(
                "SELECT * FROM transfers WHERE transfer_uid = ?;",
                (transfer_uid,),
            ).fetchone()
            connection.execute("COMMIT;")
        except Exception:
            connection.execute("ROLLBACK;")
            raise

    result = _row_to_dict(row)
    if result is None:
        raise RuntimeError("failed to create transfer record")
    return result


def get_transfer_by_uid(transfer_uid: str, db_path: str | Path | None = None) -> dict[str, Any] | None:
    """Fetch a transfer record by unique transfer UID."""
    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM transfers WHERE transfer_uid = ?;",
            (transfer_uid,),
        ).fetchone()
    return _row_to_dict(row)


def list_transfers(
    *,
    status: str | None = None,
    study_instance_uid: str | None = None,
    limit: int = DEFAULT_QUERY_LIMIT,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """List transfer records using optional status/study filters."""
    filters: list[str] = []
    params: list[Any] = []

    if status is not None:
        filters.append("status = ?")
        params.append(_validate_transfer_status(status))
    if study_instance_uid is not None:
        filters.append("study_instance_uid = ?")
        params.append(study_instance_uid)

    where_clause = ""
    if filters:
        where_clause = f"WHERE {' AND '.join(filters)}"

    query = f"""
    SELECT * FROM transfers
    {where_clause}
    ORDER BY updated_at DESC
    LIMIT ?;
    """
    params.append(_validate_limit(limit))

    with get_connection(db_path) as connection:
        rows = connection.execute(query, tuple(params)).fetchall()
    return _rows_to_dicts(rows)


def update_transfer_status(
    *,
    transfer_uid: str,
    status: str,
    failure_reason: str | None = None,
    retry_count: int | None = None,
    mark_sent: bool = False,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Update transfer status and return the updated row."""
    status_value = _validate_transfer_status(status)
    update_fields = [
        "status = ?",
        "failure_reason = ?",
        "updated_at = datetime('now')",
    ]
    params: list[Any] = [status_value, failure_reason]

    if retry_count is not None:
        if retry_count < 0:
            raise ValueError("retry_count must be >= 0")
        update_fields.append("retry_count = ?")
        params.append(retry_count)

    if mark_sent:
        update_fields.append("sent_at = datetime('now')")

    params.append(transfer_uid)

    query = f"""
    UPDATE transfers
    SET {", ".join(update_fields)}
    WHERE transfer_uid = ?;
    """

    with get_connection(db_path) as connection:
        connection.execute("BEGIN;")
        try:
            result = connection.execute(query, tuple(params))
            if result.rowcount == 0:
                raise ValueError(f"transfer_uid not found: {transfer_uid}")
            row = connection.execute(
                "SELECT * FROM transfers WHERE transfer_uid = ?;",
                (transfer_uid,),
            ).fetchone()
            connection.execute("COMMIT;")
        except Exception:
            connection.execute("ROLLBACK;")
            raise

    updated = _row_to_dict(row)
    if updated is None:
        raise RuntimeError("transfer status update failed")
    return updated


def increment_transfer_retry(
    transfer_uid: str,
    *,
    failure_reason: str | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Increment retry count and move transfer to RETRYING state."""
    with get_connection(db_path) as connection:
        connection.execute("BEGIN;")
        try:
            result = connection.execute(
                """
                UPDATE transfers
                SET
                    status = 'RETRYING',
                    retry_count = retry_count + 1,
                    failure_reason = ?,
                    updated_at = datetime('now')
                WHERE transfer_uid = ?;
                """,
                (failure_reason, transfer_uid),
            )
            if result.rowcount == 0:
                raise ValueError(f"transfer_uid not found: {transfer_uid}")
            row = connection.execute(
                "SELECT * FROM transfers WHERE transfer_uid = ?;",
                (transfer_uid,),
            ).fetchone()
            connection.execute("COMMIT;")
        except Exception:
            connection.execute("ROLLBACK;")
            raise

    updated = _row_to_dict(row)
    if updated is None:
        raise RuntimeError("transfer retry update failed")
    return updated


def record_rejected_transfer(
    *,
    transfer_uid: str,
    source_file_path: str,
    rejection_file_path: str,
    failure_reason: str,
    study_instance_uid: str = "",
    sop_instance_uid: str | None = None,
    source_ae_title: str = "UNKNOWN_MODALITY",
    destination_ae_title: str = "REJECTED",
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Create a rejected transfer record with FAILED status."""
    source_path = Path(source_file_path).expanduser().resolve()
    file_size = source_path.stat().st_size if source_path.exists() else 0

    created = create_transfer_record(
        transfer_uid=transfer_uid,
        study_instance_uid=study_instance_uid or "UNAVAILABLE_STUDY_UID",
        sop_instance_uid=sop_instance_uid,
        source_ae_title=source_ae_title,
        destination_ae_title=destination_ae_title,
        file_path=rejection_file_path,
        file_size_bytes=file_size,
        status="FAILED",
        db_path=db_path,
    )

    return update_transfer_status(
        transfer_uid=created["transfer_uid"],
        status="FAILED",
        failure_reason=failure_reason,
        db_path=db_path,
    )


def upsert_study_metadata(
    metadata: Mapping[str, Any],
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Upsert study metadata keyed by study_instance_uid."""
    study_instance_uid = str(metadata.get("study_instance_uid", "")).strip()
    if not study_instance_uid:
        raise ValueError("study_instance_uid is required")

    query = """
    INSERT INTO study_metadata (
        study_instance_uid,
        patient_id,
        patient_name,
        accession_number,
        study_date,
        study_time,
        modality,
        study_description,
        referring_physician_name,
        institution_name,
        source_ae_title,
        total_instances,
        updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    ON CONFLICT(study_instance_uid) DO UPDATE SET
        patient_id = excluded.patient_id,
        patient_name = excluded.patient_name,
        accession_number = excluded.accession_number,
        study_date = excluded.study_date,
        study_time = excluded.study_time,
        modality = excluded.modality,
        study_description = excluded.study_description,
        referring_physician_name = excluded.referring_physician_name,
        institution_name = excluded.institution_name,
        source_ae_title = excluded.source_ae_title,
        total_instances = excluded.total_instances,
        updated_at = datetime('now');
    """

    values = (
        study_instance_uid,
        metadata.get("patient_id"),
        metadata.get("patient_name"),
        metadata.get("accession_number"),
        metadata.get("study_date"),
        metadata.get("study_time"),
        metadata.get("modality"),
        metadata.get("study_description"),
        metadata.get("referring_physician_name"),
        metadata.get("institution_name"),
        metadata.get("source_ae_title"),
        int(metadata.get("total_instances", 0)),
    )

    with get_connection(db_path) as connection:
        connection.execute("BEGIN;")
        try:
            connection.execute(query, values)
            row = connection.execute(
                "SELECT * FROM study_metadata WHERE study_instance_uid = ?;",
                (study_instance_uid,),
            ).fetchone()
            connection.execute("COMMIT;")
        except Exception:
            connection.execute("ROLLBACK;")
            raise

    result = _row_to_dict(row)
    if result is None:
        raise RuntimeError("failed to upsert study metadata")
    return result


def upsert_instance_metadata(
    metadata: Mapping[str, Any],
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Upsert instance metadata keyed by sop_instance_uid."""
    study_instance_uid = str(metadata.get("study_instance_uid", "")).strip()
    sop_instance_uid = str(metadata.get("sop_instance_uid", "")).strip()
    file_path = str(metadata.get("file_path", "")).strip()
    if not study_instance_uid:
        raise ValueError("study_instance_uid is required")
    if not sop_instance_uid:
        raise ValueError("sop_instance_uid is required")
    if not file_path:
        raise ValueError("file_path is required")

    with get_connection(db_path) as connection:
        study_row = connection.execute(
            "SELECT study_instance_uid FROM study_metadata WHERE study_instance_uid = ?;",
            (study_instance_uid,),
        ).fetchone()
    if study_row is None:
        raise ValueError(
            f"study_instance_uid not found in study_metadata: {study_instance_uid}. "
            "Create or upsert the study record before storing instance metadata."
        )

    query = """
    INSERT INTO instance_metadata (
        study_instance_uid,
        sop_instance_uid,
        series_instance_uid,
        sop_class_uid,
        instance_number,
        transfer_syntax_uid,
        file_path,
        checksum_sha256
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(sop_instance_uid) DO UPDATE SET
        study_instance_uid = excluded.study_instance_uid,
        series_instance_uid = excluded.series_instance_uid,
        sop_class_uid = excluded.sop_class_uid,
        instance_number = excluded.instance_number,
        transfer_syntax_uid = excluded.transfer_syntax_uid,
        file_path = excluded.file_path,
        checksum_sha256 = excluded.checksum_sha256;
    """

    values = (
        study_instance_uid,
        sop_instance_uid,
        metadata.get("series_instance_uid"),
        metadata.get("sop_class_uid"),
        metadata.get("instance_number"),
        metadata.get("transfer_syntax_uid"),
        file_path,
        metadata.get("checksum_sha256"),
    )

    with get_connection(db_path) as connection:
        connection.execute("BEGIN;")
        try:
            connection.execute(query, values)
            row = connection.execute(
                "SELECT * FROM instance_metadata WHERE sop_instance_uid = ?;",
                (sop_instance_uid,),
            ).fetchone()
            connection.execute("COMMIT;")
        except Exception:
            connection.execute("ROLLBACK;")
            raise

    result = _row_to_dict(row)
    if result is None:
        raise RuntimeError("failed to upsert instance metadata")
    return result


def get_instance_by_sop_uid(
    sop_instance_uid: str,
    *,
    db_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """Fetch an instance metadata row by SOP Instance UID."""
    normalized_uid = str(sop_instance_uid).strip()
    if not normalized_uid:
        raise ValueError("sop_instance_uid is required")

    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM instance_metadata WHERE sop_instance_uid = ?;",
            (normalized_uid,),
        ).fetchone()
    return _row_to_dict(row)


def store_instance_checksum(
    *,
    sop_instance_uid: str,
    checksum_sha256: str,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Persist a SHA256 checksum against an existing instance metadata record."""
    normalized_uid = str(sop_instance_uid).strip()
    if not normalized_uid:
        raise ValueError("sop_instance_uid is required")
    normalized_digest = _validate_sha256_digest(checksum_sha256)

    with get_connection(db_path) as connection:
        connection.execute("BEGIN;")
        try:
            result = connection.execute(
                """
                UPDATE instance_metadata
                SET checksum_sha256 = ?
                WHERE sop_instance_uid = ?;
                """,
                (normalized_digest, normalized_uid),
            )
            if result.rowcount == 0:
                raise ValueError(f"sop_instance_uid not found: {normalized_uid}")
            row = connection.execute(
                "SELECT * FROM instance_metadata WHERE sop_instance_uid = ?;",
                (normalized_uid,),
            ).fetchone()
            connection.execute("COMMIT;")
        except Exception:
            connection.execute("ROLLBACK;")
            raise

    updated = _row_to_dict(row)
    if updated is None:
        raise RuntimeError("failed to store instance checksum")
    return updated


def calculate_and_store_instance_checksum(
    *,
    sop_instance_uid: str,
    file_path: str | Path,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Generate a SHA256 digest from disk and store it for the target SOP instance."""
    checksum = generate_file_checksum(file_path)
    return store_instance_checksum(
        sop_instance_uid=sop_instance_uid,
        checksum_sha256=checksum.digest,
        db_path=db_path,
    )


def verify_instance_checksum(
    *,
    sop_instance_uid: str,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Verify the stored checksum for an instance against the file on disk."""
    instance = get_instance_by_sop_uid(sop_instance_uid, db_path=db_path)
    if instance is None:
        raise ValueError(f"sop_instance_uid not found: {sop_instance_uid}")

    stored_digest = str(instance.get("checksum_sha256") or "").strip().lower()
    if not stored_digest:
        raise ValueError(f"checksum_sha256 is not stored for sop_instance_uid: {sop_instance_uid}")

    verification = verify_file_checksum(
        file_path=instance["file_path"],
        expected_digest=stored_digest,
    )
    return {
        "sop_instance_uid": str(instance["sop_instance_uid"]),
        "study_instance_uid": str(instance["study_instance_uid"]),
        "file_path": str(instance["file_path"]),
        "stored_checksum_sha256": stored_digest,
        "computed_checksum_sha256": verification.actual_digest,
        "is_match": verification.is_match,
        "file_size_bytes": verification.file_size_bytes,
        "algorithm": verification.algorithm,
    }


def detect_instance_corruption(
    *,
    sop_instance_uid: str,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Detect corruption for an instance by comparing stored and current file checksums."""
    instance = get_instance_by_sop_uid(sop_instance_uid, db_path=db_path)
    if instance is None:
        raise ValueError(f"sop_instance_uid not found: {sop_instance_uid}")

    stored_digest = str(instance.get("checksum_sha256") or "").strip().lower()
    if not stored_digest:
        raise ValueError(f"checksum_sha256 is not stored for sop_instance_uid: {sop_instance_uid}")

    detection = detect_file_corruption(
        file_path=instance["file_path"],
        expected_digest=stored_digest,
    )
    return {
        "sop_instance_uid": str(instance["sop_instance_uid"]),
        "study_instance_uid": str(instance["study_instance_uid"]),
        "file_path": str(instance["file_path"]),
        "stored_checksum_sha256": stored_digest,
        "computed_checksum_sha256": detection.actual_digest,
        "status": detection.status,
        "is_corrupted": detection.is_corrupted,
        "reason": detection.reason,
        "file_size_bytes": detection.file_size_bytes,
        "algorithm": detection.algorithm,
    }


def record_integrity_event(
    *,
    sop_instance_uid: str,
    study_instance_uid: str,
    event_type: str,
    status: str,
    file_path: str,
    reason: str,
    expected_checksum_sha256: str | None = None,
    computed_checksum_sha256: str | None = None,
    file_size_bytes: int | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Persist an integrity audit event for a DICOM instance."""
    normalized_sop_uid = str(sop_instance_uid).strip()
    normalized_study_uid = str(study_instance_uid).strip()
    normalized_file_path = str(file_path).strip()
    normalized_reason = str(reason).strip()
    normalized_event_type = _validate_integrity_event_type(event_type)
    normalized_status = _validate_integrity_status(status)

    if not normalized_sop_uid:
        raise ValueError("sop_instance_uid is required")
    if not normalized_study_uid:
        raise ValueError("study_instance_uid is required")
    if not normalized_file_path:
        raise ValueError("file_path is required")
    if not normalized_reason:
        raise ValueError("reason is required")

    expected_digest = None
    if expected_checksum_sha256:
        expected_digest = _validate_sha256_digest(expected_checksum_sha256)

    computed_digest = None
    if computed_checksum_sha256:
        computed_digest = _validate_sha256_digest(computed_checksum_sha256)

    if file_size_bytes is not None and int(file_size_bytes) < 0:
        raise ValueError("file_size_bytes must be >= 0")

    query = """
    INSERT INTO integrity_events (
        sop_instance_uid,
        study_instance_uid,
        event_type,
        status,
        expected_checksum_sha256,
        computed_checksum_sha256,
        file_path,
        file_size_bytes,
        reason
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    with get_connection(db_path) as connection:
        connection.execute("BEGIN;")
        try:
            cursor = connection.execute(
                query,
                (
                    normalized_sop_uid,
                    normalized_study_uid,
                    normalized_event_type,
                    normalized_status,
                    expected_digest,
                    computed_digest,
                    normalized_file_path,
                    file_size_bytes,
                    normalized_reason,
                ),
            )
            row = connection.execute(
                "SELECT * FROM integrity_events WHERE id = ?;",
                (cursor.lastrowid,),
            ).fetchone()
            connection.execute("COMMIT;")
        except Exception:
            connection.execute("ROLLBACK;")
            raise

    result = _row_to_dict(row)
    if result is None:
        raise RuntimeError("failed to record integrity event")
    return result


def list_integrity_events(
    *,
    sop_instance_uid: str | None = None,
    study_instance_uid: str | None = None,
    status: str | None = None,
    limit: int = DEFAULT_QUERY_LIMIT,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """List integrity events with optional instance, study, and status filters."""
    filters: list[str] = []
    params: list[Any] = []

    if sop_instance_uid is not None:
        filters.append("sop_instance_uid = ?")
        params.append(str(sop_instance_uid).strip())
    if study_instance_uid is not None:
        filters.append("study_instance_uid = ?")
        params.append(str(study_instance_uid).strip())
    if status is not None:
        filters.append("status = ?")
        params.append(_validate_integrity_status(status))

    where_clause = ""
    if filters:
        where_clause = f"WHERE {' AND '.join(filters)}"

    query = f"""
    SELECT * FROM integrity_events
    {where_clause}
    ORDER BY created_at DESC, id DESC
    LIMIT ?;
    """
    params.append(_validate_limit(limit))

    with get_connection(db_path) as connection:
        rows = connection.execute(query, tuple(params)).fetchall()
    return _rows_to_dicts(rows)


def detect_and_log_instance_corruption(
    *,
    sop_instance_uid: str,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run corruption detection for an instance and persist the result as an integrity event."""
    detection = detect_instance_corruption(
        sop_instance_uid=sop_instance_uid,
        db_path=db_path,
    )
    event = record_integrity_event(
        sop_instance_uid=detection["sop_instance_uid"],
        study_instance_uid=detection["study_instance_uid"],
        event_type="CORRUPTION_DETECTED" if detection["is_corrupted"] else "CHECKSUM_VERIFIED",
        status=detection["status"],
        file_path=detection["file_path"],
        reason=detection["reason"],
        expected_checksum_sha256=detection["stored_checksum_sha256"],
        computed_checksum_sha256=detection["computed_checksum_sha256"],
        file_size_bytes=detection["file_size_bytes"],
        db_path=db_path,
    )
    return {
        "detection": detection,
        "event": event,
    }


def list_studies(
    *,
    patient_id: str | None = None,
    modality: str | None = None,
    limit: int = DEFAULT_QUERY_LIMIT,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """List studies with optional patient/modality filtering."""
    filters: list[str] = []
    params: list[Any] = []
    if patient_id:
        filters.append("patient_id = ?")
        params.append(patient_id)
    if modality:
        filters.append("modality = ?")
        params.append(modality)

    where_clause = ""
    if filters:
        where_clause = f"WHERE {' AND '.join(filters)}"

    query = f"""
    SELECT * FROM study_metadata
    {where_clause}
    ORDER BY study_date DESC, updated_at DESC
    LIMIT ?;
    """
    params.append(_validate_limit(limit))

    with get_connection(db_path) as connection:
        rows = connection.execute(query, tuple(params)).fetchall()
    return _rows_to_dicts(rows)


def list_instances_by_study(
    study_instance_uid: str,
    *,
    limit: int = DEFAULT_QUERY_LIMIT,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """List DICOM instances for a study ordered by instance number."""
    query = """
    SELECT * FROM instance_metadata
    WHERE study_instance_uid = ?
    ORDER BY instance_number ASC, id ASC
    LIMIT ?;
    """
    with get_connection(db_path) as connection:
        rows = connection.execute(
            query,
            (study_instance_uid, _validate_limit(limit)),
        ).fetchall()
    return _rows_to_dicts(rows)


if __name__ == "__main__":
    target = initialize_database()
    print(f"Initialized SQLite database at: {target}")
