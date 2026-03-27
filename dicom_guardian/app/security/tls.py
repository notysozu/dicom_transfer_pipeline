"""TLS configuration and SSL context builders for dicom_guardian (Step 22)."""

from __future__ import annotations

import ssl
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import TlsConfig, load_config


@dataclass(frozen=True)
class ResolvedTlsFiles:
    cert_file: Path
    key_file: Path
    ca_file: Path


def _resolve(path: Path) -> Path:
    return path.expanduser().resolve()


def resolve_tls_files(config: TlsConfig | None = None) -> ResolvedTlsFiles:
    """Resolve TLS file paths from config to absolute filesystem paths."""
    tls_config = config or load_config().tls
    return ResolvedTlsFiles(
        cert_file=_resolve(tls_config.cert_file),
        key_file=_resolve(tls_config.key_file),
        ca_file=_resolve(tls_config.ca_file),
    )


def validate_tls_files(config: TlsConfig | None = None) -> ResolvedTlsFiles:
    """Validate certificate/key/CA files exist and are readable."""
    resolved = resolve_tls_files(config)

    missing: list[str] = []
    for file_path in (resolved.cert_file, resolved.key_file, resolved.ca_file):
        if not file_path.exists():
            missing.append(str(file_path))
        elif not file_path.is_file():
            raise ValueError(f"TLS path is not a file: {file_path}")

    if missing:
        raise FileNotFoundError(f"TLS files missing: {missing}")

    for file_path in (resolved.cert_file, resolved.key_file, resolved.ca_file):
        if not file_path.stat().st_size:
            raise ValueError(f"TLS file is empty: {file_path}")

    return resolved


def create_api_server_ssl_context(config: TlsConfig | None = None) -> ssl.SSLContext:
    """Create TLS server context for FastAPI HTTPS endpoint."""
    files = validate_tls_files(config)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.options |= ssl.OP_NO_COMPRESSION
    context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20")
    context.load_cert_chain(certfile=str(files.cert_file), keyfile=str(files.key_file))
    context.load_verify_locations(cafile=str(files.ca_file))
    return context


def create_dicom_server_ssl_context(
    config: TlsConfig | None = None,
    *,
    require_client_cert: bool = True,
) -> ssl.SSLContext:
    """Create TLS server context for DICOM Storage SCP associations."""
    files = validate_tls_files(config)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.options |= ssl.OP_NO_COMPRESSION
    context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20")
    context.load_cert_chain(certfile=str(files.cert_file), keyfile=str(files.key_file))
    context.load_verify_locations(cafile=str(files.ca_file))
    context.verify_mode = ssl.CERT_REQUIRED if require_client_cert else ssl.CERT_OPTIONAL
    return context


def create_outbound_client_ssl_context(
    config: TlsConfig | None = None,
    *,
    check_hostname: bool = True,
    present_client_certificate: bool = True,
) -> ssl.SSLContext:
    """Create TLS client context for outbound connections (PACS/API)."""
    files = validate_tls_files(config)

    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=str(files.ca_file))
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.options |= ssl.OP_NO_COMPRESSION
    context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20")
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = check_hostname

    if present_client_certificate:
        context.load_cert_chain(certfile=str(files.cert_file), keyfile=str(files.key_file))

    return context


def tls_diagnostics(config: TlsConfig | None = None) -> dict[str, Any]:
    """Return a diagnostics snapshot for observability and startup checks."""
    files = validate_tls_files(config)
    return {
        "cert_file": str(files.cert_file),
        "key_file": str(files.key_file),
        "ca_file": str(files.ca_file),
        "cert_exists": files.cert_file.exists(),
        "key_exists": files.key_file.exists(),
        "ca_exists": files.ca_file.exists(),
        "cert_size": files.cert_file.stat().st_size,
        "key_size": files.key_file.stat().st_size,
        "ca_size": files.ca_file.stat().st_size,
    }
