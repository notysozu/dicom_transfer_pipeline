#!/usr/bin/env bash

OS_FAMILY=""
OS_NAME=""

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

main() {
  detect_os
}

main "$@"
