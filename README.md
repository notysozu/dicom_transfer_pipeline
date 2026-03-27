# DICOM Transfer Pipeline

![repository status](https://img.shields.io/badge/status-active%20baseline-0a7ea4)
![python](https://img.shields.io/badge/python-3.11%2B-3776ab)
![node](https://img.shields.io/badge/node-20%2B-5fa04e)

This repository combines `dicom_guardian`, a Python service for secure DICOM ingestion and transfer, with `dicom_ui`, a Node.js and React control plane for operators who need to monitor studies, transfers, and audit activity over TLS-protected interfaces.

## Features

- Secure DICOM ingestion and forwarding pipeline with TLS-aware runtime settings
- HTTPS control-plane backend with authentication, RBAC, and audit-oriented models
- React dashboard frontend for login, study review, transfer tracking, and user management
- Local developer tooling for Python and Node.js workflows through subproject `Makefile` targets
