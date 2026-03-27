"""FastAPI route registration for dicom_guardian (Steps 56-60)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.database.db import check_database_health, list_integrity_events, list_studies, list_transfers
from app.security.tls import tls_diagnostics


api_router = APIRouter(tags=["guardian-api"])
system_router = APIRouter(prefix="/system", tags=["system"])
study_router = APIRouter(prefix="/studies", tags=["studies"])
transfer_router = APIRouter(prefix="/transfers", tags=["transfers"])
log_router = APIRouter(prefix="/logs", tags=["logs"])
metrics_router = APIRouter(prefix="/metrics", tags=["metrics"])


@system_router.get("/health")
def health() -> dict[str, object]:
    """Return minimal service health without exposing sensitive content."""
    tls_info = tls_diagnostics()
    db_ok = check_database_health()

    return {
        "service": "dicom_guardian",
        "status": "ok" if db_ok else "degraded",
        "database": {"healthy": db_ok},
        "tls": {
            "cert_file": tls_info["cert_file"],
            "ca_file": tls_info["ca_file"],
            "cert_exists": tls_info["cert_exists"],
            "ca_exists": tls_info["ca_exists"],
        },
    }


@system_router.get("/info")
def info() -> dict[str, object]:
    """Return static API discovery metadata for Guardian control-plane clients."""
    return {
        "service": "dicom_guardian",
        "api_version": "0.1.0",
        "available_endpoints": [
            "/api/system/health",
            "/api/system/info",
        ],
        "next_phase": [
            "study listing endpoints",
            "transfer monitoring endpoints",
            "log retrieval endpoints",
            "metrics endpoints",
        ],
    }


@study_router.get("")
def studies(
    patient_id: str | None = Query(default=None, description="Exact patient identifier filter"),
    modality: str | None = Query(default=None, description="Exact modality filter, e.g. CT or MR"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of studies to return"),
) -> dict[str, object]:
    """Return study metadata records for dashboard and control-plane clients."""
    items = list_studies(
        patient_id=patient_id,
        modality=modality,
        limit=limit,
    )
    return {
        "count": len(items),
        "filters": {
            "patient_id": patient_id,
            "modality": modality,
            "limit": limit,
        },
        "studies": items,
    }


@transfer_router.get("")
def transfers(
    status: str | None = Query(default=None, description="Transfer status filter"),
    study_instance_uid: str | None = Query(default=None, description="Exact study instance UID filter"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of transfers to return"),
) -> dict[str, object]:
    """Return transfer status records for monitoring and operations clients."""
    items = list_transfers(
        status=status,
        study_instance_uid=study_instance_uid,
        limit=limit,
    )
    return {
        "count": len(items),
        "filters": {
            "status": status,
            "study_instance_uid": study_instance_uid,
            "limit": limit,
        },
        "transfers": items,
    }


@log_router.get("")
def logs(
    sop_instance_uid: str | None = Query(default=None, description="Exact SOP Instance UID filter"),
    study_instance_uid: str | None = Query(default=None, description="Exact Study Instance UID filter"),
    status: str | None = Query(default=None, description="Integrity status filter"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of log events to return"),
) -> dict[str, object]:
    """Return persisted integrity log events for monitoring and audit clients."""
    items = list_integrity_events(
        sop_instance_uid=sop_instance_uid,
        study_instance_uid=study_instance_uid,
        status=status,
        limit=limit,
    )
    return {
        "count": len(items),
        "filters": {
            "sop_instance_uid": sop_instance_uid,
            "study_instance_uid": study_instance_uid,
            "status": status,
            "limit": limit,
        },
        "logs": items,
    }


@metrics_router.get("")
def metrics() -> dict[str, object]:
    """Return aggregated operational metrics for Guardian monitoring clients."""
    studies = list_studies(limit=1000)
    transfers_received = list_transfers(status="RECEIVED", limit=1000)
    transfers_validated = list_transfers(status="VALIDATED", limit=1000)
    transfers_queued = list_transfers(status="QUEUED", limit=1000)
    transfers_sent = list_transfers(status="SENT", limit=1000)
    transfers_failed = list_transfers(status="FAILED", limit=1000)
    transfers_retrying = list_transfers(status="RETRYING", limit=1000)
    healthy_logs = list_integrity_events(status="HEALTHY", limit=1000)
    corrupted_logs = list_integrity_events(status="CORRUPTED", limit=1000)
    error_logs = list_integrity_events(status="ERROR", limit=1000)

    return {
        "service": "dicom_guardian",
        "metrics": {
            "studies_total": len(studies),
            "transfers_total": (
                len(transfers_received)
                + len(transfers_validated)
                + len(transfers_queued)
                + len(transfers_sent)
                + len(transfers_failed)
                + len(transfers_retrying)
            ),
            "transfers_by_status": {
                "RECEIVED": len(transfers_received),
                "VALIDATED": len(transfers_validated),
                "QUEUED": len(transfers_queued),
                "SENT": len(transfers_sent),
                "FAILED": len(transfers_failed),
                "RETRYING": len(transfers_retrying),
            },
            "integrity_events_total": len(healthy_logs) + len(corrupted_logs) + len(error_logs),
            "integrity_by_status": {
                "HEALTHY": len(healthy_logs),
                "CORRUPTED": len(corrupted_logs),
                "ERROR": len(error_logs),
            },
        },
    }


api_router.include_router(system_router)
api_router.include_router(study_router)
api_router.include_router(transfer_router)
api_router.include_router(log_router)
api_router.include_router(metrics_router)
