#!/usr/bin/env bash
set -euo pipefail

OS_FAMILY=""
OS_NAME=""
PACKAGE_MANAGER=""
REPO_URL="${REPO_URL:-https://github.com/example/dicom_transfer_pipeline.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/dicom_transfer_pipeline}"
PROJECT_ROOT=""
START_TARGET="${START_TARGET:-guardian}"
USE_COLOR=0

configure_output() {
  if [[ -t 1 ]] && [[ "${NO_COLOR:-0}" != "1" ]]; then
    USE_COLOR=1
  fi
}

log_info() {
  if [[ "$USE_COLOR" -eq 1 ]]; then
    printf '\033[1;34m→\033[0m %s\n' "$1"
  else
    printf '-> %s\n' "$1"
  fi
}

log_success() {
  if [[ "$USE_COLOR" -eq 1 ]]; then
    printf '\033[1;32m✓\033[0m %s\n' "$1"
  else
    printf '[ok] %s\n' "$1"
  fi
}

log_error() {
  if [[ "$USE_COLOR" -eq 1 ]]; then
    printf '\033[1;31m✗\033[0m %s\n' "$1" >&2
  else
    printf '[error] %s\n' "$1" >&2
  fi
}

on_error() {
  log_error "install.sh failed on line $1"
}

detect_os() {
  local uname_out
  uname_out="$(uname -s)"

  case "$uname_out" in
    Darwin)
      OS_FAMILY="macos"
      OS_NAME="macOS"
      ;;
    Linux)
      OS_FAMILY="linux"
      if [[ -f /etc/os-release ]]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        OS_NAME="${PRETTY_NAME:-Linux}"
      else
        OS_NAME="Linux"
      fi
      ;;
    *)
      OS_FAMILY="unsupported"
      OS_NAME="$uname_out"
      ;;
  esac
}

detect_package_manager() {
  if [[ "$OS_FAMILY" == "macos" ]] && command -v brew >/dev/null 2>&1; then
    PACKAGE_MANAGER="brew"
    return
  fi

  if command -v apt-get >/dev/null 2>&1; then
    PACKAGE_MANAGER="apt"
  elif command -v dnf >/dev/null 2>&1; then
    PACKAGE_MANAGER="dnf"
  elif command -v pacman >/dev/null 2>&1; then
    PACKAGE_MANAGER="pacman"
  elif command -v brew >/dev/null 2>&1; then
    PACKAGE_MANAGER="brew"
  else
    PACKAGE_MANAGER="unknown"
  fi
}

install_missing_packages() {
  local packages=("$@")

  log_info "Installing system packages with $PACKAGE_MANAGER: ${packages[*]}"

  case "$PACKAGE_MANAGER" in
    apt)
      sudo apt-get update
      sudo apt-get install -y "${packages[@]}"
      ;;
    dnf)
      sudo dnf install -y "${packages[@]}"
      ;;
    pacman)
      sudo pacman -Sy --noconfirm "${packages[@]}"
      ;;
    brew)
      brew install "${packages[@]}"
      ;;
    *)
      return 1
      ;;
  esac
}

install_system_dependencies() {
  local missing=()

  command -v git >/dev/null 2>&1 || missing+=("git")
  command -v openssl >/dev/null 2>&1 || missing+=("openssl")
  command -v curl >/dev/null 2>&1 || missing+=("curl")
  command -v wget >/dev/null 2>&1 || missing+=("wget")
  command -v python3 >/dev/null 2>&1 || missing+=("python3")
  command -v npm >/dev/null 2>&1 || missing+=("npm")

  if [[ "${#missing[@]}" -gt 0 ]]; then
    install_missing_packages "${missing[@]}"
  else
    log_success "System dependencies already available"
  fi
}

prepare_repository() {
  if [[ -d "$INSTALL_DIR/.git" ]]; then
    PROJECT_ROOT="$INSTALL_DIR"
    log_info "Updating existing repository in $PROJECT_ROOT"
    git -C "$PROJECT_ROOT" pull --ff-only
    log_success "Repository updated"
    return
  fi

  if [[ -d "$INSTALL_DIR" ]] && [[ ! -z "$(find "$INSTALL_DIR" -mindepth 1 -maxdepth 1 2>/dev/null)" ]]; then
    PROJECT_ROOT="$INSTALL_DIR"
    log_info "Using existing directory at $PROJECT_ROOT"
    return
  fi

  log_info "Cloning repository into $INSTALL_DIR"
  git clone "$REPO_URL" "$INSTALL_DIR"
  PROJECT_ROOT="$INSTALL_DIR"
  log_success "Repository cloned"
}

setup_project_dependencies() {
  if [[ -d "$PROJECT_ROOT/dicom_guardian" ]]; then
    log_info "Installing Python dependencies"
    (
      cd "$PROJECT_ROOT/dicom_guardian"
      if [[ ! -d .venv ]]; then
        python3 -m venv .venv
      fi
      .venv/bin/pip install --upgrade pip
      .venv/bin/pip install -r requirements-dev.txt
    )
    log_success "Python environment ready"
  fi

  if [[ -d "$PROJECT_ROOT/dicom_ui" ]]; then
    log_info "Installing Node.js workspace dependencies"
    (
      cd "$PROJECT_ROOT/dicom_ui"
      npm ci
    )
    log_success "Node.js dependencies ready"
  fi
}

configure_environment() {
  if [[ -f "$PROJECT_ROOT/dicom_guardian/.env.example" ]] && [[ ! -f "$PROJECT_ROOT/dicom_guardian/.env" ]]; then
    cp "$PROJECT_ROOT/dicom_guardian/.env.example" "$PROJECT_ROOT/dicom_guardian/.env"
    log_success "Created dicom_guardian/.env from example"
  fi

  if [[ -f "$PROJECT_ROOT/dicom_ui/.env.example" ]] && [[ ! -f "$PROJECT_ROOT/dicom_ui/.env" ]]; then
    cp "$PROJECT_ROOT/dicom_ui/.env.example" "$PROJECT_ROOT/dicom_ui/.env"
    log_success "Created dicom_ui/.env from example"
  fi

  if [[ -f "$PROJECT_ROOT/dicom_ui/frontend/.env.example" ]] && [[ ! -f "$PROJECT_ROOT/dicom_ui/frontend/.env" ]]; then
    cp "$PROJECT_ROOT/dicom_ui/frontend/.env.example" "$PROJECT_ROOT/dicom_ui/frontend/.env"
    log_success "Created dicom_ui/frontend/.env from example"
  fi
}

build_project() {
  if [[ -x "$PROJECT_ROOT/scripts/generate_tls_certs.sh" ]]; then
    log_info "Generating local TLS certificates"
    "$PROJECT_ROOT/scripts/generate_tls_certs.sh"
    log_success "TLS certificates generated"
  fi

  if [[ -d "$PROJECT_ROOT/dicom_ui" ]]; then
    log_info "Building frontend workspace"
    (
      cd "$PROJECT_ROOT/dicom_ui"
      npm run build --workspace frontend
    )
    log_success "Frontend build completed"
  fi
}

start_application() {
  log_info "Starting application target: $START_TARGET"
  case "$START_TARGET" in
    guardian)
      (
        cd "$PROJECT_ROOT/dicom_guardian"
        exec .venv/bin/python -m app.main
      )
      ;;
    ui-backend)
      (
        cd "$PROJECT_ROOT/dicom_ui/backend"
        exec npm start
      )
      ;;
    ui-frontend)
      (
        cd "$PROJECT_ROOT/dicom_ui/frontend"
        exec npm run dev -- --host 0.0.0.0
      )
      ;;
    *)
      echo "Unsupported START_TARGET: $START_TARGET" >&2
      return 1
      ;;
  esac
}

main() {
  trap 'on_error $LINENO' ERR
  configure_output
  detect_os
  detect_package_manager
  install_system_dependencies
  prepare_repository
  setup_project_dependencies
  configure_environment
  build_project
  start_application
}

main "$@"
