# dicom_guardian

Production-style Python service for secure DICOM ingestion, validation, integrity verification, and forwarding to PACS.

## Scope (Roadmap-Aligned)
- DICOM receive pipeline (SCP)
- Metadata validation and checksum workflows
- Secure forwarding to PACS (SCU)
- Transfer and audit persistence (SQLite)
- Monitoring/control APIs (FastAPI)

## Design Principles
- Security-first: TLS on all network paths
- Reliability: explicit status lifecycle and retry-ready transfer model
- Traceability: deterministic transfer records and logs
- Modularity: clear separation of DICOM, pipeline, API, security, and DB layers

## Repository Status
This repository is initialized in **Step 2**. Application module scaffolding and implementation are introduced in later steps of the roadmap.
