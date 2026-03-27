"""Security test suite for dicom_guardian (Step 30)."""

from __future__ import annotations

import ssl

from app.config import load_config
from app.security.tls import (
    create_api_server_ssl_context,
    create_dicom_server_ssl_context,
    create_outbound_client_ssl_context,
    tls_diagnostics,
    validate_tls_files,
)


def run_security_tests() -> bool:
    cfg = load_config()

    files = validate_tls_files(cfg.tls)
    if not (files.cert_file.exists() and files.key_file.exists() and files.ca_file.exists()):
        print("[guardian-security-test] FAIL tls files missing")
        return False

    diagnostics = tls_diagnostics(cfg.tls)
    if diagnostics["cert_size"] <= 0 or diagnostics["key_size"] <= 0 or diagnostics["ca_size"] <= 0:
        print("[guardian-security-test] FAIL tls file size invalid")
        return False

    api_ctx = create_api_server_ssl_context(cfg.tls)
    dicom_ctx = create_dicom_server_ssl_context(cfg.tls, require_client_cert=True)
    outbound_ctx = create_outbound_client_ssl_context(
        cfg.tls,
        check_hostname=False,
        present_client_certificate=True,
    )

    if api_ctx.minimum_version < ssl.TLSVersion.TLSv1_2:
        print("[guardian-security-test] FAIL api minimum TLS version")
        return False

    if dicom_ctx.verify_mode != ssl.CERT_REQUIRED:
        print("[guardian-security-test] FAIL dicom verify mode")
        return False

    if outbound_ctx.verify_mode != ssl.CERT_REQUIRED:
        print("[guardian-security-test] FAIL outbound verify mode")
        return False

    print("[guardian-security-test] PASS")
    print(f"[guardian-security-test] cert={diagnostics['cert_file']}")
    print(f"[guardian-security-test] ca={diagnostics['ca_file']}")
    print(f"[guardian-security-test] api_min_tls={api_ctx.minimum_version.name}")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if run_security_tests() else 1)
