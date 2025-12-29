# Chapter 5: Installation

## Overview

The Henhouse installation process sets up the complete system infrastructure, including user accounts, groups, file permissions, git repositories, and entry point scripts. This chapter covers the installation process and configuration.

## Prerequisites

Before running the installer, ensure you have completed:

1. **Chapter 1**: DNS, NGINX, and domain setup
2. **Chapter 2**: MySQL server setup
3. **Chapter 3**: SSL certificates (can be done after installation, but database operations will fail until SSL is configured)
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

All values in the `[install]` section must be set to real values (no placeholders):

```ini
[install]
# Database hosts (use your DB/cache subdomains)
db_host = db.yourdomain.tld
cache_host = cache.yourdomain.tld

# Entry point script name (defaults to hen)
hen_script_name = hen

# SSL CA paths (absolute paths)
ssl_ca_path = /etc/mysql/ssl/ca.pem
cache_ssl_ca_path = /etc/mysql/ssl/ca.pem

# MySQL root passwords (per DB host)
mysql_root_password_main = your_secure_password
mysql_root_password_cache = your_secure_password

# DB user passwords (guest, verified, admin, root)
password_guest = your_secure_password
password_verified = your_secure_password
password_admin = your_secure_password
password_root = your_secure_password

# htaccess passwords
htaccess_admin_password = your_secure_password
htaccess_panel_password = your_secure_password

# Flask daemon starting port (reserves 100 ports: start_port through start_port+99)
flask_start_port = 5001
```

### Configuration Validation

The installer validates that:
- All required fields are present
- No placeholder values remain (`CHANGE_ME`, `yourdomain.tld`, `example.com`)
- `hen_script_name` doesn't conflict with existing scripts
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
   - Includes SSL CA paths for secure connections

6. **Sets Up Git Repository**:
   - Creates `/srv/{project_name}/git/{project_name}.git` (bare repository)
   - Initializes git in project directory if needed
   - Pushes code to bare repository
   - Configures Git safe.directory for shared repository access

7. **Creates Entry Point Scripts**:
   - `/root/{hen_script_name}` - Root user entry script
   - `/home/{project_owner}/{hen_script_name}` - Human user entry script
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
    - `/var/www/.htpasswd_admin` - Admin subdomain authentication
    - `/var/www/.htpasswd_panel` - Panel subdomain authentication

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

**Tier users**: Creates `gateway.py` and `{hen_script_name}` in each user's home
- `gateway.py`: Modified `hen.py` with `/srv/{project_name}` added to Python path
- `{hen_script_name}`: Wrapper script that calls `python3 gateway.py "$@"`

**Project owner (human user)**: Creates `{hen_script_name}` in `/home/{project_owner}/`
- Points to project folder's `hen.py` (for testing experimental code)

**Root user**: Creates `{hen_script_name}` in `/root/`
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
ls -la /root/{hen_script_name}
ls -la /home/{project_owner}/{hen_script_name}
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
{hen_script_name} command-list
```

You should no longer need to run `python -m hh.gateway.main` - the entry script handles it.

### 4. Database Setup

After installation, set up the database:

```bash
sudo {hen_script_name} init-db -root -confirm
sudo {hen_script_name} add-db-users -root
```

**Note**: These commands require:
- SSL certificates to be configured (see Chapter 3)
- MySQL root user to have access from deployment box IP (see Chapter 2)
- `-root` flag and sudo privileges

### 5. Expected Warnings

After installation, you may see database connection warnings when running commands:

```
Failed to initialize database connections: Access denied for user...
```

This is **expected** if:
- Database hasn't been initialized yet (`init-db` not run)
- SSL certificates aren't configured yet
- Database doesn't exist yet

These warnings are non-fatal and can be ignored until database setup is complete.

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

| Field | Description | Example |
|-------|-------------|---------|
| `db_host` | Database host subdomain | `db.example.com` |
| `cache_host` | Cache database host subdomain | `cache.example.com` |
| `hen_script_name` | Entry point script name | `hen` |
| `ssl_ca_path` | SSL CA certificate path for main DB | `/etc/mysql/ssl/ca.pem` |
| `cache_ssl_ca_path` | SSL CA certificate path for cache DB | `/etc/mysql/ssl/ca.pem` |
| `mysql_root_password_main` | MySQL root password for main DB | (secure password) |
| `mysql_root_password_cache` | MySQL root password for cache DB | (secure password) |
| `password_guest` | Guest tier database password | (secure password) |
| `password_verified` | Verified tier database password | (secure password) |
| `password_admin` | Admin tier database password | (secure password) |
| `password_root` | Root tier database password | (secure password) |
| `htaccess_admin_password` | HTTP Basic Auth for admin subdomain | (secure password) |
| `htaccess_panel_password` | HTTP Basic Auth for panel subdomain | (secure password) |
| `flask_start_port` | Starting port for Flask daemons | `5001` |

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
2. Run uninstall first if users exist: `sudo {hen_script_name} uninstall`
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
4. **HTTP/NGINX**: Configure web server (see Chapter 9)
5. **Daemon Management**: Verify and manage Flask and maintenance daemons (see Chapter 10)

