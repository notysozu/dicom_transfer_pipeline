"""SQLite schema definitions for dicom_guardian.

Step 11 introduced internal initialization tables.
Step 12 adds transfer schema tables and indexes.
Step 13 adds metadata schema tables and indexes.
Step 40 adds integrity logging schema and indexes.
"""

SCHEMA_MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SYSTEM_STATE_TABLE = """
CREATE TABLE IF NOT EXISTS system_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    service_name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SYSTEM_STATE_UPSERT = """
INSERT INTO system_state (id, service_name)
VALUES (1, 'dicom_guardian')
ON CONFLICT(id) DO UPDATE SET
    service_name = excluded.service_name,
    updated_at = datetime('now');
"""

BOOTSTRAP_MIGRATION_INSERT = """
INSERT OR IGNORE INTO schema_migrations (version, name)
VALUES (1, '0001_bootstrap_sqlite_init');
"""

TRANSFERS_TABLE = """
CREATE TABLE IF NOT EXISTS transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transfer_uid TEXT NOT NULL UNIQUE,
    study_instance_uid TEXT NOT NULL,
    sop_instance_uid TEXT,
    source_ae_title TEXT NOT NULL,
    destination_ae_title TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL CHECK (file_size_bytes >= 0),
    status TEXT NOT NULL CHECK (
        status IN ('RECEIVED', 'VALIDATED', 'QUEUED', 'SENT', 'FAILED', 'RETRYING')
    ),
    retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    failure_reason TEXT,
    received_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    sent_at TEXT
);
"""

TRANSFERS_BY_STUDY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_transfers_study_instance_uid
ON transfers (study_instance_uid);
"""

TRANSFERS_BY_STATUS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_transfers_status
ON transfers (status, updated_at DESC);
"""

TRANSFERS_BY_TRANSFER_UID_INDEX = """
CREATE INDEX IF NOT EXISTS idx_transfers_transfer_uid
ON transfers (transfer_uid);
"""

TRANSFER_SCHEMA_MIGRATION_INSERT = """
INSERT OR IGNORE INTO schema_migrations (version, name)
VALUES (2, '0002_transfer_schema');
"""

STUDY_METADATA_TABLE = """
CREATE TABLE IF NOT EXISTS study_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    study_instance_uid TEXT NOT NULL UNIQUE,
    patient_id TEXT,
    patient_name TEXT,
    accession_number TEXT,
    study_date TEXT,
    study_time TEXT,
    modality TEXT,
    study_description TEXT,
    referring_physician_name TEXT,
    institution_name TEXT,
    source_ae_title TEXT,
    total_instances INTEGER NOT NULL DEFAULT 0 CHECK (total_instances >= 0),
    received_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

INSTANCE_METADATA_TABLE = """
CREATE TABLE IF NOT EXISTS instance_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    study_instance_uid TEXT NOT NULL,
    sop_instance_uid TEXT NOT NULL UNIQUE,
    series_instance_uid TEXT,
    sop_class_uid TEXT,
    instance_number INTEGER,
    transfer_syntax_uid TEXT,
    file_path TEXT NOT NULL,
    checksum_sha256 TEXT,
    received_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(study_instance_uid) REFERENCES study_metadata(study_instance_uid) ON DELETE CASCADE
);
"""

STUDY_METADATA_BY_DATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_study_metadata_study_date
ON study_metadata (study_date DESC);
"""

STUDY_METADATA_BY_PATIENT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_study_metadata_patient_id
ON study_metadata (patient_id);
"""

INSTANCE_METADATA_BY_STUDY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_instance_metadata_study_uid
ON instance_metadata (study_instance_uid);
"""

INSTANCE_METADATA_BY_SERIES_INDEX = """
CREATE INDEX IF NOT EXISTS idx_instance_metadata_series_uid
ON instance_metadata (series_instance_uid);
"""

METADATA_SCHEMA_MIGRATION_INSERT = """
INSERT OR IGNORE INTO schema_migrations (version, name)
VALUES (3, '0003_metadata_schema');
"""

INTEGRITY_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS integrity_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sop_instance_uid TEXT NOT NULL,
    study_instance_uid TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (
        event_type IN ('CHECKSUM_VERIFIED', 'CORRUPTION_DETECTED', 'INTEGRITY_ERROR')
    ),
    status TEXT NOT NULL CHECK (
        status IN ('HEALTHY', 'CORRUPTED', 'ERROR')
    ),
    expected_checksum_sha256 TEXT,
    computed_checksum_sha256 TEXT,
    file_path TEXT NOT NULL,
    file_size_bytes INTEGER,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(sop_instance_uid) REFERENCES instance_metadata(sop_instance_uid) ON DELETE CASCADE,
    FOREIGN KEY(study_instance_uid) REFERENCES study_metadata(study_instance_uid) ON DELETE CASCADE
);
"""

INTEGRITY_EVENTS_BY_STUDY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_integrity_events_study_uid
ON integrity_events (study_instance_uid, created_at DESC);
"""

INTEGRITY_EVENTS_BY_INSTANCE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_integrity_events_sop_uid
ON integrity_events (sop_instance_uid, created_at DESC);
"""

INTEGRITY_SCHEMA_MIGRATION_INSERT = """
INSERT OR IGNORE INTO schema_migrations (version, name)
VALUES (4, '0004_integrity_logging_schema');
"""
