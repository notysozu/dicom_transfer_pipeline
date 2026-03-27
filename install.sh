#!/usr/bin/env bash

OS_FAMILY=""
OS_NAME=""
PACKAGE_MANAGER=""

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

main() {
  detect_os
  detect_package_manager
}

main "$@"
