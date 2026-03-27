# Security Policy

## Reporting a Vulnerability

Do not open a public issue for suspected vulnerabilities, leaked credentials, exposed certificates, or protected health information concerns. Report security issues privately to the repository maintainers and include:

- A clear description of the issue
- Affected files, modules, or environments
- Reproduction steps if they can be shared safely
- Recommended containment or rotation actions when credentials or keys are involved

## Sensitive Material Handling

- Never commit `.env` files, private keys, certificate keypairs, or production connection strings.
- Treat DICOM payloads and logs as potentially sensitive.
- Rotate any credential or certificate that may have been exposed in Git history or shared artifacts.

## Remediation Expectations

Maintainers should acknowledge reports promptly, validate impact, and coordinate a fix before public disclosure when that is reasonably possible.
