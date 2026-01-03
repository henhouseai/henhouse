# Chapter 5: Installation

## Overview

The Henhouse installation process sets up the complete system infrastructure, including user accounts, groups, file permissions, git repositories, and entry point scripts. This chapter covers the installation process and configuration.

## Prerequisites

Before running the installer, ensure you have completed:

1. **Chapter 1**: DNS, NGINX, and domain setup
2. **Chapter 2**: MySQL server setup
   - **For localhost**: MySQL installed and root password set (no SSL required)
   - **For public deployment**: MySQL installed, root password set, and SSL certificates configured (if `mysql_tls_enabled = 1`)
3. **Chapter 3**: SSL certificates
   - **For localhost**: Not required (can skip if `mysql_tls_enabled = 0` and `ssl_enabled = 0`)
   - **For public deployment**: Required if `mysql_tls_enabled = 1` or `ssl_enabled = 1` (can be done after installation, but database operations will fail until SSL is configured)
4. **Chapter 4**: Smoke check (optional, but recommended)

## Install Configuration File

### Location

The installer uses a single configuration file:
- **Path**: `/root/.{project}-install.cnf`
- **Permissions**: Mode 600 (readable/writable by root only)
- **Owner**: root:root
- **Retention**: Not deleted on uninstall (retained for reinstall)

### First Run: Template Creation

On the first run, if the config file doesn't exist, the installer creates a template:

```bash
sudo python -m hh.gateway.main install
```

The installer will:
1. Create `/root/.{project}-install.cnf` with placeholder values
2. Display a formatted message showing the template was created
3. Return success (not an error)
4. Prompt you to edit the template and rerun

### Editing the Template

Edit the config file:

```bash
sudo vi /root/.{project}-install.cnf
```

Or use nano:

```bash
sudo nano /root/.{project}-install.cnf
```

### Required Configuration Values

The template is pre-configured for **local network deployment** (simplest setup). For local deployment, you only need to change the passwords and domain name. All other values are already set correctly.

**For local network deployment** (default - minimal changes needed):
- `db_host = localhost` (already set - used for database connections)
- `cache_host = localhost` (already set - used for cache database connections)
- `mysql_tls_enabled = 0` (plain text connections, no SSL required)
- `ssl_enabled = 0` (HTTP-only, no SSL required)
- `domain = example.local` (already set - change to your desired `.local` domain name)

**You only need to change:**
- All password fields (replace `CHANGE_ME` with your secure passwords)
- `domain` field (change `example.local` to your desired domain name, e.g., `mysite.local`)

**For public-facing deployment**, uncomment and set the public values, and enable TLS/SSL:
- Uncomment `db_host` and `cache_host` lines, set to your subdomains
- Set `mysql_tls_enabled = 1` (TLS/SSL recommended for public deployments)
- Set `ssl_enabled = 1` (HTTPS recommended for public deployments)
- Set `domain` to your public domain name

**Example template** (what you'll see in the generated file):

```ini
[install]

# ========================================
# Entry Point Script
# ========================================
# Entry point script name (defaults to hen)
entry_point_script_name = hen

# ========================================
# Database Configuration
# ========================================
# Database hosts
# For localhost deployment (default - no changes needed for local testing):
db_host = localhost
cache_host = localhost
# For public deployment with subdomains:
# db_host = db.example.tld
# cache_host = cache.example.tld

# MySQL root passwords (per DB host)
mysql_root_password_main = CHANGE_ME
mysql_root_password_cache = CHANGE_ME

# MySQL TLS/SSL Configuration
# TLS enabled (1 = enabled, 0 = disabled)
# For localhost deployment (plain text connections recommended for initial testing):
mysql_tls_enabled = 0
# For public deployment (TLS/SSL recommended):
# mysql_tls_enabled = 1

# MySQL SSL Certificate Paths
# SSL CA paths (absolute paths, only used if mysql_tls_enabled = 1)
# For localhost deployment (self-signed certificates):
ssl_ca_path = /etc/mysql/ssl/ca.pem
cache_ssl_ca_path = /etc/mysql/ssl/ca.pem
# For public deployment (Let's Encrypt certificates):
# ssl_ca_path = /etc/mysql/ssl/ca.pem
# cache_ssl_ca_path = /etc/mysql/ssl/ca.pem

# MySQL SSL Directory and Certificate Paths
# MySQL SSL directory (where SSL certificates are stored)
mysql_ssl_dir = /etc/mysql/ssl
# MySQL server certificate path (full path to server certificate)
mysql_server_cert_path = /etc/mysql/ssl/server-cert.pem
# MySQL server key path (full path to server private key)
mysql_server_key_path = /etc/mysql/ssl/server-key.pem
# MySQL configuration file path
mysql_config_path = /etc/mysql/mysql.conf.d/mysqld.cnf

# ========================================
# Application Passwords
# ========================================
# DB user passwords (guest, verified, admin, root)
password_guest = CHANGE_ME
password_verified = CHANGE_ME
password_admin = CHANGE_ME
password_root = CHANGE_ME

# HTTP Basic Auth passwords
# Leave htaccess_guest_password blank for public access, set password for private site
htaccess_guest_password = 
htaccess_admin_password = CHANGE_ME
htaccess_panel_password = CHANGE_ME

# ========================================
# Flask Daemon Configuration
# ========================================
# Flask daemon starting port (reserves 100 ports: start_port through start_port+99)
flask_start_port = 5001

# ========================================
# HTTP/NGINX Deployment Settings
# ========================================
# Domain name for web deployment
# For local network deployment (default - configure /etc/hosts on developer box):
domain = example.local
# For public deployment with domain name:
# domain = example.tld
# For local network deployment (IP address):
# domain = 192.168.1.100

# SSL/TLS Configuration
# SSL enabled (1 = enabled, 0 = disabled)
# For localhost deployment (HTTP-only recommended for initial testing):
ssl_enabled = 0
# For public deployment (HTTPS recommended):
# ssl_enabled = 1

# SSL Certificate Directories
# Let's Encrypt certificate directory (for public deployments)
ssl_cert_dir_letsencrypt = /etc/letsencrypt/live
# Self-signed certificate directory (for local/testing deployments)
ssl_cert_dir_self_signed = /etc/nginx/ssl

# Local Deployment IP Binding
# IP pattern for local deployments (e.g., '192.168.1.' for subnet, '192.168.1.100' for specific IP)
# Only used for local deployments (.local domains, localhost, or private IP addresses)
# This restricts NGINX to bind only to matching IPs, preventing external access
local_allow_block = 192.168.1.

# NGINX Configuration Directories
# NGINX sites-available directory (where config files are stored)
nginx_sites_available = /etc/nginx/sites-available
# NGINX sites-enabled directory (where symlinks to enabled sites are stored)
nginx_sites_enabled = /etc/nginx/sites-enabled
# Webroot directory for Let's Encrypt ACME challenges
webroot_dir = /var/www/html
# HTTP Basic Auth htpasswd directory (where .htpasswd files are stored)
htpasswd_dir = /var/www
```

### TLS/SSL Configuration Notes

**For local network deployment** (default):
- `mysql_tls_enabled = 0` and `ssl_enabled = 0` are set by default
- No SSL certificates required
- Plain text connections for MySQL, HTTP-only for web
- Simplest setup - just change passwords and domain name, then configure `/etc/hosts` on your developer box

**Enabling TLS/SSL for local deployments** (optional):
- You can enable TLS/SSL for local network deployments if desired
- Set `mysql_tls_enabled = 1` and/or `ssl_enabled = 1`
- Requires additional steps: generate self-signed certificates (see Chapter 3)
- Useful for testing SSL/TLS functionality locally

**For public-facing deployment** (recommended):
- **TLS/SSL is strongly recommended** for public deployments
- Set `mysql_tls_enabled = 1` (encrypted database connections)
- Set `ssl_enabled = 1` (HTTPS for web access)
- Requires SSL certificate setup (see Chapter 3)
- Use Let's Encrypt certificates for production deployments

### Configuration Validation

The installer validates that:
- All required fields are present
- No placeholder values remain (`CHANGE_ME`, `yourdomain.tld`, `example.com`)
- `entry_point_script_name` doesn't conflict with existing scripts
- `flask_start_port` doesn't conflict with other active installations (checks 100-port range)

## Installation Process

### Running the Installer

After editing the config file, run the installer again:

```bash
sudo python -m hh.gateway.main install
```

The installer requires:
- **Sudo/root privileges**: Must run as root or with sudo
- **Project context**: Must be run from within the project directory

### What the Installer Does

1. **Validates Configuration**:
   - Checks all required fields are set
   - Validates no placeholder values
   - Checks for port conflicts with other installations
   - Verifies script name doesn't conflict

2. **Creates Core Groups**:
   - `{project_name}` - Project group
   - `{project_name}_deploy` - Deployment group
   - `{project_name}_admin` - Admin group

3. **Creates User Accounts**:
   - `{project_name}_guest` - Guest tier user
   - `{project_name}_verified` - Verified tier user
   - `{project_name}_admin` - Admin tier user
   - `{project_name}_root` - Root tier user

4. **Sets Up SSH Access**:
   - Auto-scans project owner's `~/.ssh/authorized_keys`
   - Copies SSH keys to all tier users
   - Generates SSH keys for each tier user

5. **Creates User Config Files**:
   - `~/.{project}.cnf` for each user with database credentials
   - Includes SSL CA paths for secure connections (only if `mysql_tls_enabled = 1`)
   - For localhost with `mysql_tls_enabled = 0`, creates plain text connection configs

6. **Sets Up Git Repository**:
   - Creates `/srv/{project_name}/git/{project_name}.git` (bare repository)
   - Initializes git in project directory if needed
   - Pushes code to bare repository
   - Configures Git safe.directory for shared repository access

7. **Creates Entry Point Scripts**:
   - `/root/{entry_point_script_name}` - Root user entry script
   - `/home/{project_owner}/{entry_point_script_name}` - Human user entry script
   - Wrapper scripts for all tier users

8. **Sets Up Directories**:
   - `/srv/{project_name}/` - Main project directory
   - `/srv/images/{project_name}/` - Image storage
   - `/srv/files/{project_name}/` - File storage
   - `/srv/audio/{project_name}/` - Audio storage
   - `/srv/video/{project_name}/` - Video storage

9. **Sets Permissions**:
   - Project directory: `{project_owner}:{project_name}` group
   - `/srv/` subdirectories: Appropriate group ownership
   - Git repository: Proper permissions for shared access

10. **Creates HTTP Basic Auth Files**:
    - `{htpasswd_dir}/.htpasswd_admin` - Admin subdomain authentication (default: `/var/www/.htpasswd_admin`)
    - `{htpasswd_dir}/.htpasswd_panel` - Panel subdomain authentication (default: `/var/www/.htpasswd_panel`)
    - `{htpasswd_dir}/.htpasswd_guest` - Guest subdomain authentication (only if `htaccess_guest_password` is set)

## Technical Details: Installation Process Implementation

The installation command (`hh/deploy/users/install.py`) performs a comprehensive system initialization:

### Project Detection

**Function**: `detect_project_context()` from `hh/deploy/utils.py`

- **Project name**: Automatically detected from folder name containing `hh/` directory
- **Project owner**: Automatically detected from folder ownership (UID lookup)
- **Detection method**: Walks up from current working directory (`Path.cwd()`) until it finds a directory containing an `hh/` folder
- **Critical requirement**: You MUST `cd` into the project directory before running install

These values determine file ownerships, permissions, and user access throughout deployment.

### User Creation Process

**File**: `hh/deploy/users/user_accounts.py`

Each tier user is created with:
- System user flag (`-r` flag for `useradd`)
- Shell: `/bin/bash`
- Home directory: `/home/{user}`
- Primary group: Admin tier user gets `{project_name}_admin`, others get default
- Supplementary groups: All users get `{project_name}_deploy` group

**Group Structure**:
- `{project_name}`: Main project group (root tier user's primary group)
- `{project_name}_deploy`: Deployment group (all tier users)
- `{project_name}_admin`: Admin group (admin tier user's primary group)

### SSH Key Management

**File**: `hh/deploy/users/access.py`

**Auto-scan process**:
- Reads project owner's `~/.ssh/authorized_keys` file
- Extracts all non-comment lines (public keys)
- Copies all discovered keys to each tier user's `authorized_keys`

**Key generation**:
- Creates new SSH keypair for each tier user: `ssh-keygen -t rsa -b 4096`
- Stores in `~/.ssh/id_rsa` and `~/.ssh/id_rsa.pub`
- Adds public key to user's `authorized_keys`

**Critical requirement**: Passwordless SSH keys must be set up in project owner's account BEFORE running install. The installer scans `~/.ssh/authorized_keys` and will fail if none are found.

### Credential File Creation

**Function**: `create_user_config_file(user, project_name, password)`

Each tier user receives `~/.{project_name}.cnf` with:
- Format: INI-style with `[client]` section
- Contents: `user`, `password`, `host=db.{project_name}.ai`, `database={project_name}`, `ssl_ca` path
- Permissions: `0o600` (read/write for owner only)
- Ownership: Owned by respective user

These credential files are used by the database deployment system to create MySQL users with matching passwords.

### Git Repository Setup

**Process**:
1. Creates `/srv/{project_name}/git/{project_name}.git` bare repository
2. Initializes git in project folder if not already a repo
3. Configures git user: `{project_name} System` / `system@{project_name}.local`
4. Creates initial commit with all files
5. Renames branch to `{project_name}` (regardless of git default)
6. Adds bare repo as `origin` remote and pushes
7. Sets bare repo HEAD to `{project_name}` branch

**Ownership**: `{project_owner}:{project_name}` with `0o770` directories, `0o660` files

This git repository is used by the git operations system for code synchronization.

### Entry Point Scripts

**Tier users**: Creates `gateway.py` and `{entry_point_script_name}` in each user's home
- `gateway.py`: Modified `hen.py` with `/srv/{project_name}` added to Python path
- `{entry_point_script_name}`: Wrapper script that calls `python3 gateway.py "$@"`

**Project owner (human user)**: Creates `{entry_point_script_name}` in `/home/{project_owner}/`
- Points to project folder's `hen.py` (for testing experimental code)

**Root user**: Creates `{entry_point_script_name}` in `/root/`
- Points to project folder's `hen.py` with cache cleanup after execution

**PATH Configuration**: Updates `.profile` for all users to add their home directory (or `/root` for root) to PATH.

### Directory Setup

**Media directories** created:
- `/srv/images/{project_name}/` with `deleted/` subdirectory
- `/srv/files/{project_name}/` with `deleted/` subdirectory
- `/srv/audio/{project_name}/` with `deleted/` subdirectory
- `/srv/video/{project_name}/` with `deleted/` subdirectory

**Permissions**: `0o2775` (setgid for group write), owned by `{project_name}_root:{project_name}_admin`

These directories are used by the file deployment system for storing uploaded media.

### HTTP Basic Auth Files

**Files created**:
- `/var/www/.htpasswd_admin` - Admin subdomain authentication
- `/var/www/.htpasswd_panel` - Panel subdomain authentication

**Process**: Uses `htpasswd -b` for batch mode password setting. Passwords are hashed (not stored in plaintext) using the `htpasswd` command.

These files are used by the HTTP/NGINX deployment system for subdomain authentication.

## Post-Installation Steps

### 1. Log Out and Log Back In

**Critical**: After installation, log out and log back in via SSH to refresh group permissions.

Group memberships are set during installation, but they don't take effect in your current session until you log out and log back in.

### 2. Verify Installation

**Check Group Ownership**:
```bash
ls -la /path/to/project
```
Should show group ownership changed to `{project_name}`.

**Check `/srv` Directory**:
```bash
ls -la /srv
```
Should show project subdirectories (images, files, audio, video, git).

**Check User Accounts**:
```bash
ls -la /home
```
Should show four new user accounts: `{project}_guest`, `{project}_verified`, `{project}_admin`, `{project}_root`.

**Check Entry Scripts**:
```bash
ls -la /root/{entry_point_script_name}
ls -la /home/{project_owner}/{entry_point_script_name}
```
Should show entry scripts exist.

**Verify Group Permissions**:
After logging back in:
```bash
ls -la /srv/{project_name}
```
Should now be accessible (group permissions activated).

### 3. Test Entry Scripts

After logging back in, test the entry script:

```bash
{entry_point_script_name} command-list
```

You should no longer need to run `python -m hh.gateway.main` - the entry script handles it.

### 4. Database Setup

After installation, set up the database:

```bash
sudo {entry_point_script_name} init-db -root -confirm
sudo {entry_point_script_name} add-db-users -root
```

**Note**: These commands require:
- `-root` flag and sudo privileges
- **For localhost**: MySQL root password set (no SSL required if `mysql_tls_enabled = 0`)
- **For public deployment**: SSL certificates configured (if `mysql_tls_enabled = 1`) and MySQL root user access from deployment box IP (see Chapter 2)

### 5. Expected Warnings

After installation, you may see database connection warnings when running commands:

```
Failed to initialize database connections: Access denied for user...
```

This is **expected** if:
- Database hasn't been initialized yet (`init-db` not run)
- SSL certificates aren't configured yet (only if `mysql_tls_enabled = 1`)
- Database doesn't exist yet

These warnings are non-fatal and can be ignored until database setup is complete. For localhost deployments with `mysql_tls_enabled = 0`, you won't see SSL-related warnings.

## Port Management

### Flask Daemon Ports

Each installation reserves a block of 100 ports starting from `flask_start_port`:
- Ports `{flask_start_port}` through `{flask_start_port + 99}` are reserved
- Default: `5001` (reserves ports 5001-5100)
- Installer checks for conflicts with other active installations

### Port Conflict Detection

The installer automatically:
- Scans for other active installations
- Checks their `flask_start_port` values
- Validates no port range overlap
- Reports conflicts before proceeding

**Example**: If `henhouse` uses port 5001, `foxhouse` must use a different port (e.g., 5101).

## Configuration Reference

### Install Config Fields

| Field | Description | Default | Example |
|-------|-------------|---------|---------|
| `entry_point_script_name` | Entry point script name | `hen` | `hen` |
| `db_host` | Database host | `localhost` | `db.example.com` |
| `cache_host` | Cache database host | `localhost` | `cache.example.com` |
| `mysql_root_password_main` | MySQL root password for main DB | (required) | (secure password) |
| `mysql_root_password_cache` | MySQL root password for cache DB | (required) | (secure password) |
| `mysql_tls_enabled` | Enable TLS for MySQL connections | `0` (disabled) | `1` (enabled) |
| `mysql_ssl_dir` | MySQL SSL certificate directory | `/etc/mysql/ssl` | `/etc/mysql/ssl` |
| `mysql_server_cert_path` | MySQL server certificate path | `/etc/mysql/ssl/server-cert.pem` | (configurable) |
| `mysql_server_key_path` | MySQL server key path | `/etc/mysql/ssl/server-key.pem` | (configurable) |
| `mysql_config_path` | MySQL configuration file path | `/etc/mysql/mysql.conf.d/mysqld.cnf` | (configurable) |
| `ssl_ca_path` | SSL CA certificate path for main DB | `/etc/mysql/ssl/ca.pem` | (only if `mysql_tls_enabled = 1`) |
| `cache_ssl_ca_path` | SSL CA certificate path for cache DB | `/etc/mysql/ssl/ca.pem` | (only if `mysql_tls_enabled = 1`) |
| `password_guest` | Guest tier database password | (required) | (secure password) |
| `password_verified` | Verified tier database password | (required) | (secure password) |
| `password_admin` | Admin tier database password | (required) | (secure password) |
| `password_root` | Root tier database password | (required) | (secure password) |
| `htaccess_guest_password` | HTTP Basic Auth for guest (blank = public) | (empty) | (optional password) |
| `htaccess_admin_password` | HTTP Basic Auth for admin subdomain | (required) | (secure password) |
| `htaccess_panel_password` | HTTP Basic Auth for panel subdomain | (required) | (secure password) |
| `flask_start_port` | Starting port for Flask daemons | `5001` | `5001` |
| `domain` | Domain name for web deployment | `example.local` | `example.com` |
| `ssl_enabled` | Enable SSL/HTTPS for web | `0` (disabled) | `1` (enabled) |
| `ssl_cert_dir_letsencrypt` | Let's Encrypt certificate directory | `/etc/letsencrypt/live` | (configurable) |
| `ssl_cert_dir_self_signed` | Self-signed certificate directory | `/etc/nginx/ssl` | (configurable) |
| `local_allow_block` | IP pattern for local deployments | `192.168.1.` | (configurable) |
| `nginx_sites_available` | NGINX sites-available directory | `/etc/nginx/sites-available` | (configurable) |
| `nginx_sites_enabled` | NGINX sites-enabled directory | `/etc/nginx/sites-enabled` | (configurable) |
| `webroot_dir` | Webroot for Let's Encrypt challenges | `/var/www/html` | (configurable) |
| `htpasswd_dir` | HTTP Basic Auth htpasswd directory | `/var/www` | (configurable) |

## Troubleshooting

### Template Creation Shows as Error

**Problem**: First run shows an error instead of template creation message

**Solution**: This should not happen - template creation is a success case. If you see an error, check installer logs.

### Configuration Validation Fails

**Problem**: Installer rejects config with "placeholder detected" error

**Solution**: 
1. Check all fields are set to real values
2. Remove any `CHANGE_ME`, `yourdomain.tld`, or `example.com` placeholders
3. Verify passwords are set (not empty)

### Port Conflict Detected

**Problem**: Installer reports port conflict

**Solution**:
1. Check other active installations: Look for other `.*-install.cnf` files in `/root/`
2. Choose a different `flask_start_port` (e.g., 5101, 5201, etc.)
3. Ensure the new port range (100 ports) doesn't overlap

### User Creation Fails

**Problem**: Installer fails to create users

**Solution**:
1. Check for existing users: `id {project}_guest`
2. Run uninstall first if users exist: `sudo {entry_point_script_name} uninstall`
3. Verify no conflicting user accounts

### Git Repository Setup Fails

**Problem**: Git repository creation fails

**Solution**:
1. Check `/srv/{project_name}/git/` directory permissions
2. Verify project owner is detected correctly
3. Check for existing git repository conflicts

## What Installation Enables

- **Git repository on server**: Bare repo at `/srv/{project_name}/git/{project_name}.git`
- **Tier-based Unix users**: Four users (guest, verified, admin, root) with proper permissions
- **Media directories**: `/srv/images/`, `/srv/files/`, `/srv/audio/`, `/srv/video/` with proper permissions
- **Entry point scripts**: Convenience scripts for all users
- **HTTP Basic Auth files**: Authentication files for admin and panel subdomains

## Testing Installation with Git Sync

After installation, you can immediately test git sync workflows between your developer box and server. The git repository is created during installation, so you can start syncing code right away - even before deploying to `/srv/{project_name}/`.

See **Chapter 6: Git and Staging Workflows** for complete details on:
- Setting up developer box to clone from server
- Basic git sync workflows
- Stage branch recovery mechanisms
- Syncing code in both directions (laptop ↔ server)

All git sync workflows can be tested before running `deploy`. The only thing in `/srv` at this point is the git repository.

## Next Steps

After successful installation:

1. **Git Sync Setup** (Optional): Set up git sync between developer box and server (see Chapter 6)
2. **Database Setup**: Run `init-db` and `add-db-users` (see Chapter 7)
3. **File Deployment**: Deploy your code to `/srv/` (see Chapter 8)
4. **Deployment**: Deploy code and configure web server (see Chapter 8)
5. **Daemon Management**: Verify and manage Flask and maintenance daemons (see Chapter 10)

