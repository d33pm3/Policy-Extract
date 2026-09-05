# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.2.x   | Yes       |

## Reporting a vulnerability

Open a GitHub issue with the `security` label for non-sensitive defects.
Do not attach client policies, credentials, or production extracts.

If the finding involves credentials or a path that could leak a private
corpus, email the repository owner instead of filing a public issue.

## What this repository must never contain

- `.env` files, API keys, tokens, SSH keys, certificates, OAuth secrets
- Client or customer names, records, screenshots, or engagement packs
- Internal URLs, IPs, hostnames, or service-account names
- RAG dumps, embeddings, private prompts, or vector-store exports

A strong `.gitignore` is checked in. Pull requests that add any of the
above will be rejected.
