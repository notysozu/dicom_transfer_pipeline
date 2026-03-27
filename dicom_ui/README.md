# dicom_ui

Production-style clinical dashboard and control-plane system for DICOM operations.

## Scope (Roadmap-Aligned)
- HTTPS API backend (Node.js + Express)
- Authentication and RBAC
- User management workflows
- Study, transfer, and log visualization
- React + Vite operational dashboard frontend

## Architecture Boundary
- `backend/`: API, auth, role enforcement, integration service to `dicom_guardian`
- `frontend/`: React SPA for clinical and operations workflows

## Integration Contract
`dicom_ui` backend communicates with `dicom_guardian` only through secure HTTPS endpoints.

## Repository Status
This repository baseline is initialized in **Step 3**. Runtime setup and implementation arrive in later steps.
