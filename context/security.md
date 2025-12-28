# Security Posture and Explicit Choices

This document captures the current, explicit security model of Henhouse after the recent hardening work. It is a policy description, not a backlog.

## Credentials and Identity
- Per-user credential files: each Unix user has `~/.{project}.cnf` (mode 0600, owner=user) containing that user’s DB password and hosts (main/cache) plus SSL CA paths. These are runtime credentials; if you can run as the user, you can use its DB creds.
- OS ↔ DB identity is unified by design. Password reuse across OS/DB is still in place (explicit choice). SSH keys are primary; Unix passwords are locked for service users.
- Root canonical config: `/root/.{project}-install.cnf` (mode 600, root:root) holds hosts, SSL CA paths, MySQL root passwords (main/cache), tier DB passwords, htaccess passwords, hen script name, optional user_key. It is the single source of truth for installs/reinstalls; not deleted on uninstall.

## Transport Security
- MySQL TLS is required: server presents fullchain, `require_secure_transport=ON`; clients use `ssl_verify_mode=2` and hostname checking; no plaintext fallback.
- Client configs carry `ssl_ca` (and cache `ssl_ca`), so laptop/server connections must include CA and match host SANs. Remote laptop connections are expected to use TLS; plaintext is not supported.
- Optional future hardening: client certs (mTLS) to eliminate DB passwords in transit.

## Installer Behavior
- Config-driven only: no CLI passwords. If the install config is missing, a template is created and install exits with instructions.
- `hen_script_name` comes from the config and must **not** already exist in `/root`; fail fast otherwise.
- SSH-only posture: Unix passwords are locked; at least one SSH key is required (config `user_key` or auto-scanned); fail if none found.
- User `.cnf` files are emitted with main/cache hosts and SSL CAs from the root config (no hardcoded domains).
- htaccess passwords come from the root config.
- Root connections (`-root` flag, sudo required) read MySQL root creds/hosts/SSL CAs from the install config; CLI root password is removed.
- Manifest tracking: `manifest_users` stores uid + installed_at/removed_at per created user (written on install, removal stamped on uninstall; manual clear required before reinstall). `manifest_sites` tracks deployed domains (http/https); uninstall refuses to run while entries remain—remove sites first.

## Host/Network Posture
- MySQL grants are currently permissive (`%`) for dev convenience; tighten to specific hosts/IPs once TLS clients are in place (or use mTLS/client certs) and after multi-host testing.
- Plan: firewall + MySQL host restrictions + TLS/mTLS when splitting DB/cache to separate hosts.

## Runtime Data and Uninstall
- Uninstall should **not** delete the root install config or uploaded data (`/srv/{project}` assets, DB) unless explicitly requested (e.g., db clean). Secrets file is retained for reinstall.

## Testing Expectations
- Full reinstall on a clean host (including new mini-PC) with config-driven installer, `-root` flow, TLS main/cache from server and laptop.
- Validate failure paths: missing config creates template; invalid fields/paths fail with clear errors.
- Validate success paths: TLS required, hostname verification, SSL CA readable, hen script name uniqueness.

## Known Explicit Choices (with tradeoffs)
- Unified OS/DB identity and per-user secrets in home dirs: acceptable on trusted hosts; risk is credential exposure to any process running as that user.
- Password reuse across OS/DB/htaccess remains; improving separation is a potential future enhancement.
- TLS is mandatory; backward compatibility/plaintext is intentionally not supported.

