"""FastAPI application bootstrap for dicom_guardian (Step 56)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI

from app.api.routes import api_router
from app.config import GuardianConfig, load_config
from app.database.db import check_database_health, initialize_database
from app.security.tls import validate_tls_files


API_TITLE = "DICOM Guardian API"
API_VERSION = "0.1.0"
API_PREFIX = "/api"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Validate critical dependencies before serving API traffic."""
    config: GuardianConfig = app.state.config
    validate_tls_files(config.tls)
    initialize_database(config.database.path)

    if not check_database_health(config.database.path):
        raise RuntimeError("Database health check failed during startup")

    app.state.startup_state = {
        "service": "dicom_guardian",
        "api_prefix": API_PREFIX,
        "version": API_VERSION,
        "environment": config.environment,
    }
    yield


def create_app(config: GuardianConfig | None = None) -> FastAPI:
    """Create the Guardian FastAPI application and register API routers."""
    runtime_config = config or load_config()

    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.state.config = runtime_config
    app.include_router(api_router, prefix=API_PREFIX)

    @app.get("/", tags=["system"])
    def root() -> dict[str, object]:
        """Return top-level API metadata and discovery information."""
        return {
            "service": "dicom_guardian",
            "api": {
                "title": API_TITLE,
                "version": API_VERSION,
                "prefix": API_PREFIX,
                "docs_url": "/docs",
                "openapi_url": "/openapi.json",
            },
        }

    return app


app = create_app()


def run_secure_api() -> None:
    """Run the Guardian FastAPI service with HTTPS enabled."""
    config = load_config()
    tls_files = validate_tls_files(config.tls)

    uvicorn.run(
        "app.main:app",
        host=config.api.host,
        port=config.api.port,
        ssl_certfile=str(tls_files.cert_file),
        ssl_keyfile=str(tls_files.key_file),
        reload=False,
        workers=1,
    )


if __name__ == "__main__":
    run_secure_api()
