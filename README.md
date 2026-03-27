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
- On Linux, install scripts expect one of `apt`, `dnf`, or `pacman`; on macOS they use Homebrew; on Windows they use `winget` or Chocolatey
- `git`, `curl`, and `wget` are used by the automated installer paths

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

Generate local TLS materials before first run:

```bash
./scripts/generate_tls_certs.sh
```

Install the Python service dependencies and bootstrap its virtual environment:

```bash
cd dicom_guardian
make install-dev
```

Install the UI workspace dependencies and build the frontend:

```bash
cd ../dicom_ui
npm ci
npm run build --workspace frontend
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

## Contributing

Contribution expectations, review guidance, and local workflow notes live in [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This repository is available under the [MIT License](LICENSE).

## Troubleshooting

- If `npm ci` fails while installing `bcrypt`, confirm your Node.js version and native build tooling, then retry the workspace install.
- If the frontend build fails, inspect `dicom_ui/frontend/src/pages/DashboardPage.jsx` first; the repository currently has a known syntax issue there.
- If installer package detection fails, install the required runtimes manually and rerun the script.
- Review generated `.env` files before first start and replace placeholder secrets with environment-specific values.
