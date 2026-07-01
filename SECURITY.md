# Security Policy

**Please don't disclose security-related issues publicly. See [Reporting a vulnerability](#reporting-a-vulnerability) below.**

## Reporting a vulnerability

If you discover a security vulnerability, please report it privately via
**GitHub Private Vulnerability Reporting**: go to the repository's **Security**
tab and click **"Report a vulnerability"**. This opens a private advisory that
is visible only to the maintainer and provides a structured workflow for triage
and a coordinated fix.

All reports will be addressed promptly. Thank you for helping keep this project
and its users safe.

## Secrets

This repository is public. It contains **no** credentials or personal data:
Lovebox-login, box-id and the birthday/activity data all come from environment
variables at runtime (see `.env.example`). The real `.env` and any
`*.local.json` files are git-ignored and must never be committed.
