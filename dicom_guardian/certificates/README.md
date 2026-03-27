# Certificates Directory

This directory is reserved for TLS certificate assets used by `dicom_guardian`.

Generated files (Step 21):
- `ca.pem`, `ca.key` (internal development CA)
- `guardian-server.pem`, `guardian-server.key`
- `modality-client.pem`, `modality-client.key`
- `pacs-server.pem`, `pacs-server.key`
- compatibility names: `server.pem`, `key.pem`

Generation command:
```bash
cd /home/sonukumar/Documents/projects/dicom_system
./scripts/generate_tls_certs.sh
```

Do not commit real private keys in production repositories.
