# DICOM Transfer Pipeline

Medical imaging transfer platform for secure DICOM ingestion, operational review, and TLS-protected study workflows.

![license](https://img.shields.io/github/license/notysozu/dicom_transfer_pipeline)
![last commit](https://img.shields.io/github/last-commit/notysozu/dicom_transfer_pipeline)
![python](https://img.shields.io/badge/python-3.11%2B-3776ab)
![node](https://img.shields.io/badge/node-20%2B-5fa04e)

<!-- AUDIT: Header lacks verifiable repository metadata such as license or last-commit badges, and the opening tagline could be sharper for discoverability. -->
DICOM Transfer Pipeline is a monorepo for teams that need to receive medical imaging studies, validate them, and review transfer activity through a secure web interface. It is built for platform engineers, imaging teams, and contributors who maintain DICOM routing and audit workflows across backend and frontend services. The repository brings the transfer engine and operator-facing control plane together so you can develop, configure, and troubleshoot the full workflow in one place. It is distinct in that it pairs a Python DICOM service with a Node.js and React operations UI under one TLS-aware setup path.

<!-- AUDIT: Features mix implementation details with benefits and omit why the workflow matters to operators or contributors. -->
## Features

- Receive and validate DICOM studies through a service designed for secure transfer workflows.
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

<!-- AUDIT: Installation is useful but does not end with a concrete verification step and does not explain the known frontend build limitation inline. -->
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

<!-- AUDIT: Usage lacks a minimal end-to-end example that shows the intended startup flow across both services. -->
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

Use the seeded or configured credentials from your local `.env` files to sign in through the UI once the backend and frontend are running.

<!-- TODO: add demo GIF -->

## Tech Stack

- `dicom_guardian`: Python, FastAPI, `pydicom`, `pynetdicom`, SQLite, TLS tooling
- `dicom_ui` backend: Node.js, Express, Mongoose, JWT, bcrypt
- `dicom_ui` frontend: React, Vite, React Router

<!-- AUDIT: README is missing a configuration reference table for the environment variables already documented elsewhere in the repo. -->
<!-- AUDIT: Repository structure is not obvious from the root README and needs an annotated directory overview for first-time contributors. -->
<!-- AUDIT: Project status and known limitations are only implied; a dedicated status section would make expectations clearer. -->
## Contributing

Contribution expectations, review guidance, and local workflow notes live in [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This repository is available under the [MIT License](LICENSE).

## Troubleshooting

- If `npm ci` fails while installing `bcrypt`, confirm your Node.js version and native build tooling, then retry the workspace install.
- If the frontend build fails, inspect `dicom_ui/frontend/src/pages/DashboardPage.jsx` first; the repository currently has a known syntax issue there.
- If installer package detection fails, install the required runtimes manually and rerun the script.
- Review generated `.env` files before first start and replace placeholder secrets with environment-specific values.
