# DICOM Transfer Pipeline

Medical imaging transfer platform for secure DICOM ingestion, operational review, and TLS-protected study workflows.

![license](https://img.shields.io/github/license/notysozu/dicom_transfer_pipeline)
![last commit](https://img.shields.io/github/last-commit/notysozu/dicom_transfer_pipeline)
![python](https://img.shields.io/badge/python-3.11%2B-3776ab)
![node](https://img.shields.io/badge/node-20%2B-5fa04e)

DICOM Transfer Pipeline is a monorepo for teams that receive medical imaging studies, validate them, and review transfer activity through a secure web interface. It serves platform engineers, imaging teams, and contributors who maintain DICOM routing and audit workflows across backend and frontend services. The repository keeps the transfer engine and operator-facing control plane together so you can develop, configure, and troubleshoot the full workflow in one place. It pairs a Python DICOM service with a Node.js and React operations UI under one TLS-aware setup path.

## Features

- Receive and validate DICOM studies through a service built for secure transfer workflows.
- Review study, transfer, and user-management activity from a web UI built for operations teams.
- Protect service-to-service and user-facing traffic with TLS-aware local setup and certificate tooling.
- Run backend and frontend development flows from one repository instead of stitching together separate projects.
- Bootstrap common Python and Node.js tasks with documented `Makefile` and workspace commands.

## Prerequisites

- [Python](https://www.python.org/downloads/) `3.11` or newer
- [Node.js](https://nodejs.org/) `20` or newer, including `npm`
- [OpenSSL](https://www.openssl.org/source/) for local certificate generation
- [Git](https://git-scm.com/downloads) for cloning and updating the repository
- A reachable MongoDB instance for the `dicom_ui` backend runtime profile
- One supported package manager for automated setup:
  - Linux: `apt`, `dnf`, or `pacman`
  - macOS: `brew`
  - Windows: `winget` or Chocolatey
- `curl` or `wget` if you want to use the one-command Unix installers

## Installation

Choose either an automated installer for your platform or the manual setup flow below.

### Automated Installers

Run the Unix installer directly with `curl`:

```bash
curl -fsSL https://raw.githubusercontent.com/notysozu/dicom_transfer_pipeline/main/install.sh | bash
```

Or use `wget`:

```bash
wget -qO- https://raw.githubusercontent.com/notysozu/dicom_transfer_pipeline/main/install.sh | bash
```

On Windows PowerShell:

```powershell
iwr https://raw.githubusercontent.com/notysozu/dicom_transfer_pipeline/main/install.ps1 -UseBasicParsing | iex
```

Before using pipe-to-shell installers, review the raw scripts:

- `install.sh`: <https://raw.githubusercontent.com/notysozu/dicom_transfer_pipeline/main/install.sh>
- `install.ps1`: <https://raw.githubusercontent.com/notysozu/dicom_transfer_pipeline/main/install.ps1>
- Audit the scripts locally and prefer manual execution in regulated or production-adjacent environments.
- Override installer behavior with environment variables such as `INSTALL_DIR`, `REPO_URL`, and `START_TARGET`.
- Example: `INSTALL_DIR="$HOME/apps/dicom-transfer" START_TARGET=ui-backend curl -fsSL https://raw.githubusercontent.com/notysozu/dicom_transfer_pipeline/main/install.sh | bash`

### Manual Setup

```bash
git clone https://github.com/notysozu/dicom_transfer_pipeline.git
cd dicom_transfer_pipeline
```

Copy the shared template and generate local TLS materials:

```bash
cp .env.example .env
./scripts/generate_tls_certs.sh
```

Install the Python service dependencies and bootstrap its virtual environment:

```bash
cd dicom_guardian
make install-dev
cp .env.example .env
```

Install the UI workspace dependencies and build the frontend:

```bash
cd ../dicom_ui
npm ci
npm run build --workspace frontend
```

Verify the local toolchain is ready:

```bash
cd ..
python3 --version
node --version
```

If the frontend build fails, check the troubleshooting section before assuming your local setup is wrong.

## Usage

Start the DICOM service:

```bash
cd dicom_guardian
make run-secure
```

In a second terminal, start the control-plane backend:

```bash
cd dicom_ui
make dev-backend
```

In a third terminal, start the frontend:

```bash
cd dicom_ui
make dev-frontend
```

Use the seeded or configured credentials from your local `.env` files to sign in through the UI after the backend and frontend are running.

<!-- TODO: add demo GIF -->

## Configuration

Review the root [`.env.example`](.env.example), [dicom_guardian/.env.example](dicom_guardian/.env.example), and [dicom_ui/.env.example](dicom_ui/.env.example) files before you start the stack for the first time.

| Variable | Default | Description |
|---|---|---|
| `START_TARGET` | `guardian` | Selects which app the install scripts start by default. |
| `API_PORT` | `8443` | Exposes the `dicom_guardian` FastAPI service. |
| `DICOM_PORT` | `11112` | Exposes the DICOM listener for inbound studies. |
| `UI_BACKEND_PORT` | `9443` | Exposes the `dicom_ui` backend over HTTPS. |
| `MONGODB_URI` | `mongodb://localhost:27017/dicom_ui` | Required MongoDB connection string for the UI backend. |
| `JWT_SECRET` | none | Required signing secret for authentication tokens. |
| `GUARDIAN_BASE_URL` | `https://127.0.0.1:8443` | Connects the UI backend to `dicom_guardian`. |
| `VITE_API_BASE_URL` | `https://127.0.0.1:9443/api` | Points the frontend at the local backend API. |

## Tech Stack

| Area | Tools |
|---|---|
| Core runtimes | Python 3.11+, Node.js 20+ |
| Backend services | FastAPI, Uvicorn, Express, Mongoose |
| DICOM and security | `pydicom`, `pynetdicom`, OpenSSL, JWT, bcrypt |
| Frontend | React, Vite, React Router |
| Storage and state | SQLite for `dicom_guardian`, MongoDB for `dicom_ui` |
| Dev tooling | `make`, `pip`, `npm`, `pytest`, `ruff`, `mypy` |

## Project Structure

```text
.
├── dicom_guardian/   # Python DICOM service, FastAPI endpoints, and database helpers
├── dicom_ui/         # Node.js workspace with backend and frontend applications
│   ├── backend/      # Express API, auth, routes, models, and integration services
│   └── frontend/     # React dashboard, pages, client services, and styles
├── scripts/          # Shared repository scripts such as local TLS certificate generation
├── .github/          # Repository analysis notes and future GitHub automation files
├── .env.example      # Shared installer and local environment placeholders
├── install.sh        # Unix installer and bootstrap script
└── install.ps1       # Windows PowerShell installer and bootstrap script
```

## Contributing

Start with [CONTRIBUTING.md](CONTRIBUTING.md) for branch, review, and validation expectations. Open an issue before large changes, keep pull requests focused on one concern, and run the relevant project checks before asking for review. Contributor conduct is covered by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

This repository is available under the [MIT License](LICENSE).

## Troubleshooting

- If `npm ci` fails while installing `bcrypt`, confirm your Node.js version and native build tooling, then retry the workspace install.
- If the frontend build fails, inspect `dicom_ui/frontend/src/pages/DashboardPage.jsx` first; the repository currently has a known syntax issue there.
- If installer package detection fails, install the required runtimes manually and rerun the script.
- Review generated `.env` files before first start and replace placeholder secrets with environment-specific values.
