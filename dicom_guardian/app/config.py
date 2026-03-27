"""Central configuration management for dicom_guardian.

Step 9 defines typed settings objects and validation helpers.
Step 10 adds environment variable binding.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class ApiConfig:
    host: str
    port: int


@dataclass(frozen=True)
class DicomConfig:
    ae_title: str
    host: str
    port: int


@dataclass(frozen=True)
class PacsConfig:
    ae_title: str
    host: str
    port: int


@dataclass(frozen=True)
class DatabaseConfig:
    path: Path


@dataclass(frozen=True)
class TlsConfig:
    cert_file: Path
    key_file: Path
    ca_file: Path


@dataclass(frozen=True)
class LoggingConfig:
    level: str


@dataclass(frozen=True)
class GuardianConfig:
    environment: str
    api: ApiConfig
    dicom: DicomConfig
    pacs: PacsConfig
    database: DatabaseConfig
    tls: TlsConfig
    logging: LoggingConfig


DEFAULT_CONFIG: dict[str, Any] = {
    "environment": "development",
    "api": {
        "host": "0.0.0.0",
        "port": 8443,
    },
    "dicom": {
        "ae_title": "DICOM_GUARDIAN",
        "host": "0.0.0.0",
        "port": 11112,
    },
    "pacs": {
        "ae_title": "PACS_SERVER",
        "host": "127.0.0.1",
        "port": 11113,
    },
    "database": {
        "path": "./dicom_guardian.db",
    },
    "tls": {
        "cert_file": "./certificates/server.pem",
        "key_file": "./certificates/key.pem",
        "ca_file": "./certificates/ca.pem",
    },
    "logging": {
        "level": "INFO",
    },
}


def _merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively merge nested dictionaries."""
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            merged[key] = _merge(base[key], value)
        else:
            merged[key] = value
    return merged


def _validate_port(value: int, field_name: str) -> int:
    if not 1 <= int(value) <= 65535:
        raise ValueError(f"{field_name} must be between 1 and 65535")
    return int(value)


def _validate_non_empty(value: str, field_name: str) -> str:
    cleaned = str(value).strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty")
    return cleaned


def _pick_env(env: Mapping[str, str], primary_key: str, legacy_key: str | None = None) -> str | None:
    """Get environment value by primary key with optional legacy key fallback."""
    if primary_key in env:
        return env[primary_key]
    if legacy_key and legacy_key in env:
        return env[legacy_key]
    return None


def _env_to_overrides(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Map flat environment variables to nested guardian config overrides."""
    source = env or os.environ
    overrides: dict[str, Any] = {}

    environment = _pick_env(source, "ENVIRONMENT", "environment")
    if environment:
        overrides["environment"] = environment

    api_host = _pick_env(source, "API_HOST", "api_host")
    api_port = _pick_env(source, "API_PORT", "api_port")
    if api_host or api_port:
        overrides["api"] = {}
        if api_host:
            overrides["api"]["host"] = api_host
        if api_port:
            overrides["api"]["port"] = int(api_port)

    dicom_ae_title = _pick_env(source, "DICOM_AE_TITLE", "dicom_ae_title")
    dicom_host = _pick_env(source, "DICOM_HOST", "dicom_host")
    dicom_port = _pick_env(source, "DICOM_PORT", "dicom_port")
    if dicom_ae_title or dicom_host or dicom_port:
        overrides["dicom"] = {}
        if dicom_ae_title:
            overrides["dicom"]["ae_title"] = dicom_ae_title
        if dicom_host:
            overrides["dicom"]["host"] = dicom_host
        if dicom_port:
            overrides["dicom"]["port"] = int(dicom_port)

    pacs_ae_title = _pick_env(source, "PACS_AE_TITLE", "pacs_ae_title")
    pacs_host = _pick_env(source, "PACS_HOST", "pacs_host")
    pacs_port = _pick_env(source, "PACS_PORT", "pacs_port")
    if pacs_ae_title or pacs_host or pacs_port:
        overrides["pacs"] = {}
        if pacs_ae_title:
            overrides["pacs"]["ae_title"] = pacs_ae_title
        if pacs_host:
            overrides["pacs"]["host"] = pacs_host
        if pacs_port:
            overrides["pacs"]["port"] = int(pacs_port)

    database_path = _pick_env(source, "DATABASE_PATH", "database_path")
    if database_path:
        overrides["database"] = {"path": database_path}

    tls_cert_file = _pick_env(source, "TLS_CERT_FILE", "tls_cert_file")
    tls_key_file = _pick_env(source, "TLS_KEY_FILE", "tls_key_file")
    tls_ca_file = _pick_env(source, "TLS_CA_FILE", "tls_ca_file")
    if tls_cert_file or tls_key_file or tls_ca_file:
        overrides["tls"] = {}
        if tls_cert_file:
            overrides["tls"]["cert_file"] = tls_cert_file
        if tls_key_file:
            overrides["tls"]["key_file"] = tls_key_file
        if tls_ca_file:
            overrides["tls"]["ca_file"] = tls_ca_file

    log_level = _pick_env(source, "LOG_LEVEL", "log_level")
    if log_level:
        overrides["logging"] = {"level": log_level}

    return overrides


def load_config(
    overrides: Mapping[str, Any] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    use_env: bool = True,
) -> GuardianConfig:
    """Build typed guardian settings from defaults, env vars, and overrides."""
    raw: dict[str, Any] = dict(DEFAULT_CONFIG)
    if use_env:
        raw = _merge(raw, _env_to_overrides(env))
    if overrides:
        raw = _merge(raw, overrides)

    cfg = GuardianConfig(
        environment=_validate_non_empty(raw["environment"], "environment"),
        api=ApiConfig(
            host=_validate_non_empty(raw["api"]["host"], "api.host"),
            port=_validate_port(raw["api"]["port"], "api.port"),
        ),
        dicom=DicomConfig(
            ae_title=_validate_non_empty(raw["dicom"]["ae_title"], "dicom.ae_title"),
            host=_validate_non_empty(raw["dicom"]["host"], "dicom.host"),
            port=_validate_port(raw["dicom"]["port"], "dicom.port"),
        ),
        pacs=PacsConfig(
            ae_title=_validate_non_empty(raw["pacs"]["ae_title"], "pacs.ae_title"),
            host=_validate_non_empty(raw["pacs"]["host"], "pacs.host"),
            port=_validate_port(raw["pacs"]["port"], "pacs.port"),
        ),
        database=DatabaseConfig(path=Path(raw["database"]["path"])),
        tls=TlsConfig(
            cert_file=Path(raw["tls"]["cert_file"]),
            key_file=Path(raw["tls"]["key_file"]),
            ca_file=Path(raw["tls"]["ca_file"]),
        ),
        logging=LoggingConfig(
            level=_validate_non_empty(raw["logging"]["level"], "logging.level"),
        ),
    )

    return cfg
