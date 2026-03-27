# Install Automation Analysis

Date: 2026-03-27

## Repository Shape

- Monorepo with two application areas:
  - `dicom_guardian`: Python service for DICOM ingest, validation, forwarding, and FastAPI control endpoints
  - `dicom_ui`: Node.js workspace containing:
    - `backend`: Express API
    - `frontend`: React + Vite single-page app

## Languages And Versions

- Python: `>=3.11` from [`dicom_guardian/pyproject.toml`](/home/sonukumar/Documents/projects/dicom_transfer_pipeline/dicom_guardian/pyproject.toml)
- Node.js: `>=20` from [`dicom_ui/package.json`](/home/sonukumar/Documents/projects/dicom_transfer_pipeline/dicom_ui/package.json), [`dicom_ui/backend/package.json`](/home/sonukumar/Documents/projects/dicom_transfer_pipeline/dicom_ui/backend/package.json), and [`dicom_ui/frontend/package.json`](/home/sonukumar/Documents/projects/dicom_transfer_pipeline/dicom_ui/frontend/package.json)
- PowerShell target: Windows PowerShell `5.1+` required by planned installer

## Frameworks And Build Systems

- Python service:
  - Build backend: `setuptools`
  - API framework: `FastAPI`
  - Runtime server: `uvicorn`
  - DICOM libraries: `pydicom`, `pynetdicom`
- Node.js UI:
  - Workspace manager: `npm` workspaces
  - Backend framework: `Express`
  - Frontend framework: `React`
  - Frontend build tool: `Vite`
  - Data/auth dependencies: `mongoose`, `jsonwebtoken`, `bcrypt`, `dotenv`

## Package Managers

- Python: `pip` inside a local virtual environment created by `python3.11 -m venv`
- JavaScript: `npm` with workspace installs rooted in `dicom_ui`

## External And System Dependencies

- OpenSSL tooling is required for local certificate generation via [`scripts/generate_tls_certs.sh`](/home/sonukumar/Documents/projects/dicom_transfer_pipeline/scripts/generate_tls_certs.sh)
- Git is required for clone-based installer flows
- Python build/runtime prerequisites:
  - Python `3.11+`
  - `venv`
- Node build/runtime prerequisites:
  - Node.js `20+`
  - `npm`
- Runtime services:
  - MongoDB for `dicom_ui/backend`
  - TLS certificate files for both services

## Dependency Install Commands

- Python development install:
  - `cd dicom_guardian && make install-dev`
- Python runtime install:
  - `cd dicom_guardian && make install`
- Node workspace install:
  - `cd dicom_ui && npm ci`

## Build Commands

- Frontend build:
  - `cd dicom_ui && npm run build --workspace frontend`
- No dedicated Python artifact build command is defined beyond environment setup

## Run Commands

- Python secure runtime:
  - `cd dicom_guardian && make run-secure`
- Node backend development:
  - `cd dicom_ui && make dev-backend`
- Node frontend development:
  - `cd dicom_ui && make dev-frontend`
- Node backend production-style start:
  - `cd dicom_ui/backend && npm start`

## Required Environment Variables

### dicom_guardian

- `ENVIRONMENT`
- `API_HOST`
- `API_PORT`
- `DICOM_AE_TITLE`
- `DICOM_HOST`
- `DICOM_PORT`
- `PACS_AE_TITLE`
- `PACS_HOST`
- `PACS_PORT`
- `DATABASE_PATH`
- `TLS_CERT_FILE`
- `TLS_KEY_FILE`
- `TLS_CA_FILE`
- `LOG_LEVEL`

### dicom_ui

- `NODE_ENV`
- `LOG_LEVEL`
- `UI_BACKEND_HOST`
- `UI_BACKEND_PORT`
- `TLS_CERT_PATH`
- `TLS_KEY_PATH`
- `TLS_CA_PATH`
- `TLS_REJECT_UNAUTHORIZED`
- `JWT_SECRET`
- `JWT_EXPIRES_IN`
- `BCRYPT_SALT_ROUNDS`
- `MONGODB_URI`
- `MONGODB_MAX_POOL_SIZE`
- `MONGODB_MIN_POOL_SIZE`
- `MONGODB_SERVER_SELECTION_TIMEOUT_MS`
- `GUARDIAN_BASE_URL`
- `GUARDIAN_API_TIMEOUT_MS`
- `GUARDIAN_TLS_CA_PATH`
- `VITE_API_BASE_URL`
- `SEED_SUPER_ADMIN_USERNAME`
- `SEED_SUPER_ADMIN_EMAIL`
- `SEED_SUPER_ADMIN_PASSWORD`
- `SEED_SUPER_ADMIN_FIRST_NAME`
- `SEED_SUPER_ADMIN_LAST_NAME`
- `SEED_SUPER_ADMIN_DEPARTMENT`

## Installer Constraints

- Installers must be idempotent and avoid reinstalling dependencies unnecessarily.
- Installers should not log secret values or echo `.env` contents.
- Installers must avoid copying unsafe defaults from local untracked files that appear to contain real credentials.
- Frontend build currently has a pre-existing syntax failure in `dicom_ui/frontend/src/pages/DashboardPage.jsx`, so installer build behavior should handle known build failure explicitly rather than claim a clean production build.
