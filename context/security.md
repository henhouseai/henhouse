# Security Posture and Explicit Choices

This document captures the current, explicit security model of Henhouse after the recent hardening work. It is a policy description, not a backlog.

## Credentials and Identity

### Root Install Configuration File
The installer requires a single configuration file that serves as the source of truth for all passwords and connection details:

**Location**: `/root/.{project}-install.cnf`  
**Permissions**: Mode 600 (readable/writable by root only)  
**Owner**: root:root  
**Retention**: Not deleted on uninstall (retained for reinstall)

**Contents** (all passwords must be set, no placeholders):
- Database hosts: `db_host`, `cache_host`
- SSL CA paths: `ssl_ca_path`, `cache_ssl_ca_path`
- MySQL root passwords: `mysql_root_password_main`, `mysql_root_password_cache`
- **Four tier database passwords**: `password_guest`, `password_verified`, `password_admin`, `password_root` (used for both main and cache databases)
- **Two htaccess passwords**: `htaccess_admin_password`, `htaccess_panel_password`
- Entry script name: `hen_script_name`
- Optional SSH key: `user_key`

### Password Distribution and Storage

#### Database Tier Passwords (4 passwords)
These passwords are used for MySQL connections to both the main and cache databases. They are stored in **plaintext** (required by MySQL client libraries) in user configuration files:

**Distribution**:
- Each tier user (`{project}_guest`, `{project}_verified`, `{project}_admin`, `{project}_root`) receives their tier's password in `~/.{project}.cnf`
- Human users (created during install) receive the `password_root` in their `~/.{project}.cnf`
- Root user receives the `password_root` in `/root/.{project}.cnf`

**File locations and permissions**:
- `/home/{project}_guest/.{project}.cnf` (mode 600, owner={project}_guest)
- `/home/{project}_verified/.{project}.cnf` (mode 600, owner={project}_verified)
- `/home/{project}_admin/.{project}.cnf` (mode 600, owner={project}_admin)
- `/home/{project}_root/.{project}.cnf` (mode 600, owner={project}_root)
- `/home/{human_user}/.{project}.cnf` (mode 600, owner={human_user}) - for each human user
- `/root/.{project}.cnf` (mode 600, owner=root)

**File contents**: Each file contains the user's DB password, database name, hosts (main/cache), and SSL CA paths. These are runtime credentials; if you can run as the user, you can use its DB credentials.

#### htaccess Passwords (2 passwords)
These passwords are used for HTTP Basic Authentication on admin and panel subdomains. They are **hashed** (not stored in plaintext) in htaccess files:

**Distribution**:
- `htaccess_admin_password` → hashed and stored in `/var/www/.htpasswd_admin` (used by admin subdomain)
- `htaccess_panel_password` → hashed and stored in `/var/www/.htpasswd_panel` (used by panel subdomain)

**Hashing**: The installer uses the `htpasswd` command to hash passwords before storing them. The plaintext passwords never appear in the htaccess files.

**MCP Configuration** (developer boxes only):
- The `htaccess_panel_password` must also be manually added to the MCP config file (`henhouse.cnf` in the MCP section) on developer boxes
- This config file is **user-created** (not automated by the installer)
- Used for MCP client authentication to the restricted MCP server through NGINX
- Transmitted over HTTPS (encrypted in transit)
- Location and format are user-determined; the installer does not create or manage this file

#### MySQL Root Passwords (2 passwords)
These passwords are used exclusively for database administration operations. See the "Database Root Password Security" section below for details.

### OS ↔ DB Identity
- Password reuse across OS/DB/htaccess remains in place (explicit choice). SSH keys are primary; Unix passwords are locked for service users.
- Unified OS/DB identity: acceptable on trusted hosts; risk is credential exposure to any process running as that user.

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

## Database Root Password Security
- **RootConnection usage**: The `RootConnection` module is exclusively used by database deployment commands in `hh/deploy/db/` (init_db, add_db_users, remove_db_users, check_db, clean_db, export_db, import_db). No other parts of the system use root database credentials.
- **Password storage locations**: MySQL root passwords exist in only two places:
  1. `/root/.{project}-install.cnf` (mode 600, root:root) - the canonical install config file, retained for reinstall
  2. Temporary MySQL option files (mode 600) - created on-demand for subprocess MySQL/mysqldump commands, immediately deleted after use
- **No command-line exposure**: Passwords are **never** passed as command-line arguments to MySQL/mysqldump. All subprocess calls use `--defaults-file` pointing to temporary option files with restricted permissions (0600). This prevents passwords from appearing in process lists (`ps aux`) or command history.
- **Temporary file lifecycle**: Temporary option files are created with `tempfile.NamedTemporaryFile`, set to mode 0600 (root-only read), used for the MySQL command, then immediately unlinked. Even if cleanup fails, the files remain root-accessible only and are in a temporary directory.

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

