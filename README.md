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

## Prerequisites

- Python `3.11` or newer
- Node.js `20` or newer with `npm`
- OpenSSL tooling for local certificate generation
- Access to MongoDB for the `dicom_ui` backend runtime profile

## Installation

```bash
git clone <repository-url>
cd dicom_transfer_pipeline
```

Install the Python service dependencies:

```bash
cd dicom_guardian
make install-dev
```

Install the UI workspace dependencies:

```bash
cd ../dicom_ui
npm ci
```

## Usage

Run the secure DICOM service:

```bash
cd dicom_guardian
make run-secure
```

Start the backend and frontend independently during development:

```bash
cd dicom_ui
make dev-backend
make dev-frontend
```

## Tech Stack

- `dicom_guardian`: Python, FastAPI, `pydicom`, `pynetdicom`, SQLite, TLS tooling
- `dicom_ui` backend: Node.js, Express, Mongoose, JWT, bcrypt
- `dicom_ui` frontend: React, Vite, React Router
