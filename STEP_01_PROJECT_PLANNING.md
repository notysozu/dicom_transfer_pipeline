# Step 1 Project Planning - DICOM Platform

## 1. Objective
Build two independent production-style systems:

1. `dicom_guardian` (Python): secure DICOM transfer, validation, integrity checks, forwarding, and monitoring APIs.
2. `dicom_ui` (Node.js + React): authentication, RBAC, operational dashboard, and control-plane APIs.

The systems remain independently deployable and communicate only via secured HTTPS APIs (plus DICOM TLS channels for modality/PACS traffic in guardian).

## 2. Scope Boundaries

### In Scope
- DICOM ingestion, validation, checksum, processing, transfer pipeline.
- Transfer records, logs, and system metrics.
- UI authentication, RBAC, user management, study/transfer/log views.
- TLS everywhere (browser, service-to-service, DICOM links).
- Modular codebase with explicit separation of concerns.

### Out of Scope (for current roadmap)
- Vendor-specific PACS integrations beyond standards-based DICOM networking.
- Multi-region HA deployment orchestration.
- Full SIEM integration and external observability stacks.

## 3. High-Level Architecture

### System A: `dicom_guardian`
- Runtime: Python 3.11+
- Main services:
  - DICOM Receiver (SCP)
  - Validation/Integrity Pipeline
  - PACS Sender (SCU)
  - FastAPI Monitoring/Control API
  - SQLite persistence layer
- Key properties:
  - Asynchronous processing (`asyncio`)
  - TLS for DICOM associations and HTTPS API
  - Deterministic transfer audit trail

### System B: `dicom_ui`
- Backend Runtime: Node.js 20+
- Frontend Runtime: React + Vite
- Main services:
  - HTTPS REST API (Express)
  - AuthN/AuthZ (JWT + RBAC)
  - Guardian API integration service
  - MongoDB persistence for users/audit
  - React dashboard SPA
- Key properties:
  - Strict role checks server-side
  - API aggregation over guardian endpoints
  - Operational visibility for studies and transfers

## 4. Trust Boundaries and Security Model
- Boundary 1: Browser -> UI Backend (HTTPS/TLS required)
- Boundary 2: UI Backend -> Guardian API (mTLS-ready TLS validation required)
- Boundary 3: Modality -> Guardian DICOM Receiver (DICOM over TLS)
- Boundary 4: Guardian -> PACS (DICOM over TLS)

Baseline security controls:
- JWT auth with expiration and signature validation.
- bcrypt password hashing.
- RBAC enforced at route middleware and sensitive controller logic.
- Certificate-based TLS with explicit key/cert loading.
- Integrity verification via SHA256 before transfer finalization.
- Immutable transfer/audit records (append-first behavior).

## 5. Role Model (Initial Contract)
- `SUPER_ADMIN`: full control, including system-level settings and all users.
- `ADMIN`: user management except `SUPER_ADMIN`, plus logs/transfers.
- `RADIOLOGIST`: study discovery and retrieval workflows.
- `TECHNICIAN`: upload/ingest monitoring and operational transfer checks.
- `VIEWER`: read-only dashboard access.

Authorization strategy:
- Role constants defined centrally in `dicom_ui` backend.
- Route-level permission matrix; deny by default.
- Explicit checks for role escalation operations.

## 6. Data Ownership and Storage Strategy

### Guardian (SQLite)
Owns:
- Transfer records
- Study metadata snapshots
- Integrity checksum records
- Pipeline events/logs

### UI (MongoDB)
Owns:
- Users and credentials
- Session/auth artifacts (stateless JWT; optional token revocation list later)
- UI audit events

Cross-system rule:
- UI never writes directly to guardian DB; it uses guardian APIs only.

## 7. API Contract Baseline (Guardian -> UI)
Initial endpoint set (versioned later):
- `GET /studies`
- `GET /transfers`
- `GET /logs`
- `POST /retrieve-study`
- `GET /health`
- `GET /metrics`

Contract requirements:
- HTTPS only
- Auth token validation (planned integration token/service auth in later steps)
- Structured JSON responses with stable identifiers

## 8. Reliability and Operational Requirements
- Retry strategy for PACS forwarding with bounded backoff.
- Idempotent transfer state transitions.
- Dead-letter/error status for unrecoverable studies.
- Health endpoints for readiness/liveness.
- File system separation for `incoming` and `processed` artifacts.

## 9. Coding and Quality Standards
- Clear module boundaries (receiver, sender, validator, api, db, security).
- Strong input validation at API boundaries.
- Deterministic logging fields (timestamp, study UID, transfer ID, status).
- Unit/integration tests added as components become available.
- No hardcoded secrets; environment-driven configuration.

## 10. Step Execution Strategy
- Follow the approved 100-step roadmap strictly.
- Complete one step at a time.
- Do not auto-advance without explicit `next`.
- Avoid retroactive edits unless requested.

## 11. Step 1 Acceptance Criteria
Step 1 is complete when:
- Architecture for both systems is clearly defined.
- Security boundaries and TLS obligations are explicit.
- Role model and data ownership are documented.
- API and reliability expectations are defined.
- Delivery discipline (stepwise build) is confirmed.
