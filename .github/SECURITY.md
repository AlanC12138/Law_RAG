# Security Policy

## Reporting a vulnerability

Please report security issues **privately** rather than opening a public issue.

Use GitHub's private vulnerability reporting: go to the repository's
**Security** tab → **Report a vulnerability**. That opens a private advisory
visible only to the maintainer.

Please include what you were doing, what happened, and how to reproduce it.
You should get an acknowledgement within a week.

## Supported versions

This is a personal project under active development. Fixes land on the latest
release only; there are no long-term support branches.

| Version | Supported |
| ------- | --------- |
| 0.3.x   | Yes       |
| < 0.3   | No        |

## Deployment expectations

Law RAG is designed to be **self-hosted inside a trusted network**. It handles
privileged legal documents, so a few things matter before you run it anywhere
real:

- **Change the seeded admin password.** `ADMIN_PASSWORD` defaults to `changeme`
  and the account is created on first startup. Change it immediately.
- **Set a strong `SECRET_KEY`.** It signs every JWT. `setup.sh` / `setup.bat`
  generate one; do not reuse a default or a short string.
- **Do not expose the stack directly to the internet.** The compose file
  publishes Postgres (5432) and Qdrant (6333) on the host for local
  development convenience. Remove those port mappings, or firewall them, in
  any deployment that is not your own machine.
- **Keep `.env` out of version control.** It is gitignored; keep it that way.

## Scope

Reports about this repository's own code, configuration and CI are in scope.
Vulnerabilities in third-party dependencies are best reported upstream — though
please do tell us if this project is affected, so the dependency can be pinned
or patched here.
