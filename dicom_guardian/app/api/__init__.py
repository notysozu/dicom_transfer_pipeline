"""FastAPI route modules for dicom_guardian."""

from app.api.routes import api_router, log_router, metrics_router, study_router, system_router, transfer_router

__all__ = [
    "api_router",
    "log_router",
    "metrics_router",
    "study_router",
    "system_router",
    "transfer_router",
]
