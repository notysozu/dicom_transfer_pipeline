#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GUARDIAN_CERT_DIR="$ROOT_DIR/dicom_guardian/certificates"
UI_CERT_DIR="$ROOT_DIR/dicom_ui/backend/certificates"

DAYS_CA="${DAYS_CA:-3650}"
DAYS_CERT="${DAYS_CERT:-825}"

OPENSSL_BIN="${OPENSSL_BIN:-openssl}"

ensure_openssl() {
  if ! command -v "$OPENSSL_BIN" >/dev/null 2>&1; then
    echo "[tls-gen] openssl not found: $OPENSSL_BIN" >&2
    exit 1
  fi
}

write_san_config() {
  local path="$1"
  local common_name="$2"

  cat > "$path" <<SAN
[req]
default_bits = 4096
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn

[dn]
C = US
ST = CA
L = SanFrancisco
O = Hospital Imaging Platform
OU = Engineering
CN = ${common_name}

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = ${common_name}
IP.1 = 127.0.0.1
SAN
}

generate_root_ca() {
  local ca_key="$GUARDIAN_CERT_DIR/ca.key"
  local ca_cert="$GUARDIAN_CERT_DIR/ca.pem"

  "$OPENSSL_BIN" genrsa -out "$ca_key" 4096
  "$OPENSSL_BIN" req -x509 -new -nodes \
    -key "$ca_key" \
    -sha256 \
    -days "$DAYS_CA" \
    -subj "/C=US/ST=CA/L=SanFrancisco/O=Hospital Imaging Platform/OU=PKI/CN=hospital-root-ca" \
    -out "$ca_cert"

  chmod 600 "$ca_key"
  chmod 644 "$ca_cert"
}

generate_signed_cert() {
  local common_name="$1"
  local cert_prefix="$2"
  local target_dir="$3"

  local key_file="$target_dir/${cert_prefix}.key"
  local csr_file="$target_dir/${cert_prefix}.csr"
  local cert_file="$target_dir/${cert_prefix}.pem"
  local san_file="$target_dir/${cert_prefix}.cnf"

  write_san_config "$san_file" "$common_name"

  "$OPENSSL_BIN" genrsa -out "$key_file" 4096
  "$OPENSSL_BIN" req -new -key "$key_file" -out "$csr_file" -config "$san_file"
  "$OPENSSL_BIN" x509 -req \
    -in "$csr_file" \
    -CA "$GUARDIAN_CERT_DIR/ca.pem" \
    -CAkey "$GUARDIAN_CERT_DIR/ca.key" \
    -CAcreateserial \
    -out "$cert_file" \
    -days "$DAYS_CERT" \
    -sha256 \
    -extensions req_ext \
    -extfile "$san_file"

  chmod 600 "$key_file"
  chmod 644 "$cert_file"
}

prepare_directories() {
  mkdir -p "$GUARDIAN_CERT_DIR" "$UI_CERT_DIR"

  rm -f \
    "$GUARDIAN_CERT_DIR"/*.pem \
    "$GUARDIAN_CERT_DIR"/*.key \
    "$GUARDIAN_CERT_DIR"/*.csr \
    "$GUARDIAN_CERT_DIR"/*.cnf \
    "$GUARDIAN_CERT_DIR"/*.srl \
    "$UI_CERT_DIR"/*.pem \
    "$UI_CERT_DIR"/*.key \
    "$UI_CERT_DIR"/*.csr \
    "$UI_CERT_DIR"/*.cnf \
    "$UI_CERT_DIR"/*.srl
}

copy_ca_for_ui() {
  cp "$GUARDIAN_CERT_DIR/ca.pem" "$UI_CERT_DIR/ca.pem"
  cp "$GUARDIAN_CERT_DIR/ca.pem" "$UI_CERT_DIR/guardian-ca.pem"
  chmod 644 "$UI_CERT_DIR/ca.pem" "$UI_CERT_DIR/guardian-ca.pem"
}

install_compatibility_filenames() {
  cp "$GUARDIAN_CERT_DIR/guardian-server.pem" "$GUARDIAN_CERT_DIR/server.pem"
  cp "$GUARDIAN_CERT_DIR/guardian-server.key" "$GUARDIAN_CERT_DIR/key.pem"

  cp "$UI_CERT_DIR/ui-server.pem" "$UI_CERT_DIR/server.pem"
  cp "$UI_CERT_DIR/ui-server.key" "$UI_CERT_DIR/key.pem"

  chmod 600 "$GUARDIAN_CERT_DIR/key.pem" "$UI_CERT_DIR/key.pem"
  chmod 644 "$GUARDIAN_CERT_DIR/server.pem" "$UI_CERT_DIR/server.pem"
}

main() {
  ensure_openssl
  prepare_directories

  echo "[tls-gen] generating root CA"
  generate_root_ca

  echo "[tls-gen] generating guardian server certificate"
  generate_signed_cert "dicom-guardian.local" "guardian-server" "$GUARDIAN_CERT_DIR"

  echo "[tls-gen] generating modality client certificate"
  generate_signed_cert "dicom-modality.local" "modality-client" "$GUARDIAN_CERT_DIR"

  echo "[tls-gen] generating pacs server certificate"
  generate_signed_cert "dicom-pacs.local" "pacs-server" "$GUARDIAN_CERT_DIR"

  echo "[tls-gen] generating ui server certificate"
  generate_signed_cert "dicom-ui.local" "ui-server" "$UI_CERT_DIR"

  copy_ca_for_ui
  install_compatibility_filenames

  echo "[tls-gen] complete"
  echo "[tls-gen] guardian certs: $GUARDIAN_CERT_DIR"
  echo "[tls-gen] ui certs: $UI_CERT_DIR"
}

main "$@"
