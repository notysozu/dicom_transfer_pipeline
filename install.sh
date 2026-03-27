#!/usr/bin/env bash

OS_FAMILY=""
OS_NAME=""
PACKAGE_MANAGER=""
REPO_URL="${REPO_URL:-https://github.com/example/dicom_transfer_pipeline.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/dicom_transfer_pipeline}"
PROJECT_ROOT=""

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
  fi
}

prepare_repository() {
  if [[ -d "$INSTALL_DIR/.git" ]]; then
    PROJECT_ROOT="$INSTALL_DIR"
    git -C "$PROJECT_ROOT" pull --ff-only
    return
  fi

  if [[ -d "$INSTALL_DIR" ]] && [[ ! -z "$(find "$INSTALL_DIR" -mindepth 1 -maxdepth 1 2>/dev/null)" ]]; then
    PROJECT_ROOT="$INSTALL_DIR"
    return
  fi

  git clone "$REPO_URL" "$INSTALL_DIR"
  PROJECT_ROOT="$INSTALL_DIR"
}

setup_project_dependencies() {
  if [[ -d "$PROJECT_ROOT/dicom_guardian" ]]; then
    (
      cd "$PROJECT_ROOT/dicom_guardian"
      if [[ ! -d .venv ]]; then
        python3 -m venv .venv
      fi
      .venv/bin/pip install --upgrade pip
      .venv/bin/pip install -r requirements-dev.txt
    )
  fi

  if [[ -d "$PROJECT_ROOT/dicom_ui" ]]; then
    (
      cd "$PROJECT_ROOT/dicom_ui"
      npm ci
    )
  fi
}

configure_environment() {
  if [[ -f "$PROJECT_ROOT/dicom_guardian/.env.example" ]] && [[ ! -f "$PROJECT_ROOT/dicom_guardian/.env" ]]; then
    cp "$PROJECT_ROOT/dicom_guardian/.env.example" "$PROJECT_ROOT/dicom_guardian/.env"
  fi

  if [[ -f "$PROJECT_ROOT/dicom_ui/.env.example" ]] && [[ ! -f "$PROJECT_ROOT/dicom_ui/.env" ]]; then
    cp "$PROJECT_ROOT/dicom_ui/.env.example" "$PROJECT_ROOT/dicom_ui/.env"
  fi

  if [[ -f "$PROJECT_ROOT/dicom_ui/frontend/.env.example" ]] && [[ ! -f "$PROJECT_ROOT/dicom_ui/frontend/.env" ]]; then
    cp "$PROJECT_ROOT/dicom_ui/frontend/.env.example" "$PROJECT_ROOT/dicom_ui/frontend/.env"
  fi
}

build_project() {
  if [[ -x "$PROJECT_ROOT/scripts/generate_tls_certs.sh" ]]; then
    "$PROJECT_ROOT/scripts/generate_tls_certs.sh"
  fi

  if [[ -d "$PROJECT_ROOT/dicom_ui" ]]; then
    (
      cd "$PROJECT_ROOT/dicom_ui"
      npm run build --workspace frontend
    )
  fi
}

main() {
  detect_os
  detect_package_manager
  install_system_dependencies
  prepare_repository
  setup_project_dependencies
  configure_environment
  build_project
}

main "$@"
