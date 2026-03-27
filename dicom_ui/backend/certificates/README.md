# Backend TLS Certificates

This directory is reserved for `dicom_ui` backend TLS materials.

Generated files (Step 21):
- `ui-server.pem`, `ui-server.key`
- compatibility names: `server.pem`, `key.pem`
- `ca.pem` (UI server trust chain CA copy)
- `guardian-ca.pem` (for UI -> Guardian TLS trust validation)

Generation command:
```bash
cd /home/sonukumar/Documents/projects/dicom_system
./scripts/generate_tls_certs.sh
```

Do not commit production private keys.
