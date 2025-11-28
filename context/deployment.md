# Henhouse Deployment System Architecture

This document covers the comprehensive deployment system for Henhouse, from initial server setup through ongoing maintenance and code synchronization.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Installation System](#2-installation-system)
3. [Database Deployment](#3-database-deployment)
4. [File Deployment](#4-file-deployment)
5. [Flask Application Management](#5-flask-application-management)
6. [HTTP/NGINX Deployment](#6-httpnginx-deployment)
7. [Maintenance Daemon](#7-maintenance-daemon)
8. [Git Operations](#8-git-operations)
9. [Cache Management](#9-cache-management)
10. [Configuration System](#10-configuration-system)
11. [User Management](#11-user-management)
12. [Deployment Workflows](#12-deployment-workflows)

## Agent Quick Reference

- **Installation**: `install` command creates 4 system users, sets up permissions, transfers SSH keys
- **Database Setup**: `init-db` → `add-db-users` → `init-homepage` sequence
- **Deployment**: `deploy` command copies whitelisted files to `/srv/{project_name}`, manages services
- **Flask Management**: `flask-start`, `flask-stop`, `flask-status` for application lifecycle
- **HTTP Deployment**: `http-deploy-ssl` for HTTPS with SSL certificates
- **Maintenance**: `maintenance-start`, `maintenance-stop`, `maintenance-status` for daemon management
- **Git Sync**: `pull-project` (server gets code), `push-project` (server sends code)
- **Project Detection**: Automatic detection from folder name and owner
- **Deploy Folder Cleanup**: After deployment, deploy folder is wiped except for whitelisted items (cache/, conf/, maint/, utils.py)

## Agent Training Notes

### Deployment Prerequisites
- SSH access must be passwordless between laptop/desktop and server
- DNS must be configured for main domain, admin.{domain}, panel.{domain}
- Requires sudo/root privileges for installation and deployment
- Project name detected from folder name, project owner from folder ownership

### User Tier System
- Four tiers: guest, verified, admin, root (mapped to {project}_guest, etc.)
- Each tier has separate database credentials, filesystem permissions, access levels
- Only root tier can run Python directly; others access via MCP protocol through Flask
- Credential files: `~/.{project_name}.cnf` in each user's home directory

### Deployment Flow
1. **Install**: Create users, groups, permissions, SSH keys, credential files
2. **Database**: Initialize schema, create users, create homepage
3. **Deploy**: Copy files to /srv, set permissions, start services
4. **HTTP**: Configure NGINX with SSL certificates
5. **Maintenance**: Start background daemon for cache refresh and job processing

### File Whitelisting
- Only whitelisted files are deployed to /srv/{project_name}
- Whitelists defined in `hh/deploy/conf/` (py_whitelist, js_whitelist, css_whitelist, etc.)
- Static site files in `hh/deploy/site/` automatically included
- Configuration files and sensitive data excluded by default
- **Deploy folder cleanup**: After deployment, the deploy folder itself is wiped clean EXCEPT for whitelisted items: cache/, conf/, maint/, and utils.py

---

## 1. System Overview

The Henhouse deployment system is a comprehensive, automated infrastructure for deploying and maintaining a multi-tier web application with background processing, database management, and code synchronization capabilities.

### Architecture Philosophy

The deployment system follows a **"set it up once, deploy repeatedly"** philosophy:

- **Initial Setup**: One-time configuration of users, databases, HTTP servers, and infrastructure
- **Repeatable Deployment**: Simple two-command workflow (`pull_project` → `sudo hen deploy`) for all subsequent updates
- **Rollback Capability**: Easy recovery to any previous commit via git reset and redeploy
- **Stage Branch Recovery**: Mechanism for creating recovery points and referencing previous working states

### Core Components

The deployment system consists of 12 major components:

1. **Installation System**: Creates Unix users, groups, SSH keys, credential files, and git repositories
2. **Database Deployment**: Manages MySQL database initialization, user creation, and schema management
3. **File Deployment**: Copies whitelisted files to `/srv/{project_name}`, manages permissions, and cleans deploy folder
4. **Flask Application Management**: Manages tier-based Flask daemon lifecycle (4 instances, one per tier)
5. **HTTP/NGINX Deployment**: Configures reverse proxy with SSL certificates for web access
6. **Maintenance Daemon**: Background worker for cache refresh and job queue processing
7. **Git Operations**: Synchronizes code between development and production environments
8. **Cache Management**: Registry-based system for cleaning various caches throughout the system
9. **Configuration System**: Manages whitelists, blacklists, and application settings
10. **User Management**: Provides installation and uninstallation of complete user infrastructure
11. **Site Assets Deployment**: Deploys CSS, JavaScript, favicons, and other static web assets
12. **Deployment Workflows**: Standardized processes for normal operations, rollbacks, and recovery

### Deployment Target

All deployment operations target `/srv/{project_name}/` as the production root:

- **Code**: `hh/` folder structure deployed to `/srv/{project_name}/hh/`
- **Site Assets**: Static files deployed to `/srv/{project_name}/site/`
- **Logs**: Application logs in `/srv/{project_name}/logs/`
- **Cache**: Cache directories in `/srv/{project_name}/` (various locations)
- **Git Repository**: Bare repo at `/srv/{project_name}/git/{project_name}.git`

### Tier-Based Architecture

The system uses a four-tier user model:

- **Guest Tier**: Public access, limited permissions, dark blue theme
- **Verified Tier**: Authenticated users, moderate permissions, distinct color theme
- **Admin Tier**: Administrative access, elevated permissions, orange/amber theme
- **Root Tier**: Full system access, highest permissions, distinct color theme

Each tier has:
- Separate Unix user account (`{project_name}_{tier}`)
- Separate database credentials
- Separate Flask application instance (different port)
- Separate NGINX server block (for admin/panel subdomains)
- Distinct visual theme (color scheme) for web interface

### Security Model

- **File Permissions**: Tier-based ownership with deploy group for shared access
- **Database Access**: Tier-based MySQL users with appropriate permissions
- **Process Isolation**: Each Flask instance runs as its corresponding Unix user
- **Network Security**: Flask apps listen on localhost only, proxied by NGINX
- **HTTP Basic Auth**: Admin and panel subdomains protected with `.htpasswd` files
- **SSL/TLS**: HTTPS deployment with Let's Encrypt certificates

### File Whitelisting System

The deployment uses a comprehensive whitelisting system:

- **Python Files**: `py_whitelist.py` defines which Python files are deployed
- **JavaScript Files**: `js_whitelist.py` defines which JS files are deployed
- **CSS Files**: `css_whitelist.py` defines which stylesheets are deployed
- **Miscellaneous Files**: `misc_whitelist.py` defines other static assets
- **Context Files**: `context_whitelist.py` and `context_blacklist.py` control documentation deployment
- **Deploy Folder**: `deploy_whitelist.py` defines what survives deploy folder cleanup

**Key Principle**: Only explicitly whitelisted files are deployed. Everything else is excluded by default.

### Service Management

The system manages multiple background services:

- **Flask Applications**: 4 instances (one per tier), managed via `flask_start`/`flask_stop`/`flask_status`
- **Maintenance Daemon**: Single background worker, managed via `maintenance_start`/`maintenance_stop`/`maintenance_status`
- **NGINX**: System service, managed via `http_deploy`/`http_deploy_ssl`/`http_remove`

All services are automatically restarted during deployment.

### Development-to-Production Workflow

The standard workflow after initial setup:

1. **Development** (on laptop): Make changes, test locally
2. **Stage Push** (on laptop): `hen push_project --message "description"` creates stage branch
3. **Pull** (on server): `hen pull_project` gets latest code
4. **Deploy** (on server): `sudo hen deploy` copies files, restarts services
5. **Verify**: Check web interface, logs, functionality

**Rollback Process**:
1. **Reset** (on server): `git reset --hard {commit_hash}` to previous stable point
2. **Deploy** (on server): `sudo hen deploy` redeploys previous version
3. **Document** (optional): `hen push_project --message "emergency revert"` to create recovery point

### Key Design Principles

1. **Separation of Concerns**: Each component has a single, well-defined responsibility
2. **Idempotency**: Deployment operations can be run multiple times safely
3. **Reversibility**: All operations can be rolled back or undone
4. **Traceability**: Stage branches and logs provide audit trail
5. **Automation**: Minimal manual intervention required after initial setup
6. **Safety**: Extensive validation and error checking at every step
7. **Modularity**: Components can be used independently or together

### Integration with Henhouse Core

The deployment system integrates with core Henhouse components:

- **Gateway**: All commands use Gateway for dispatch, error handling, and response management
- **Page System**: Deployed pages are served via Flask applications
- **Registry System**: Command registry is cleared after deployment to reload new commands
- **Cache System**: Cache cleanup registry is used during deployment and pull operations
- **MCP Backend**: Flask applications expose MCP protocol for external tool integration
- **Maintenance Backend**: Background daemon uses maintenance backend for tool execution

This deployment system enables Henhouse to be a self-documenting, self-deploying platform where the deployment process itself is part of the system being deployed.

---

## 2. Installation System

The installation system creates the complete user and group infrastructure needed for a Henhouse deployment. It sets up four tier-based system users, transfers SSH keys, creates credential files, initializes git repositories, and configures convenience scripts.

### Install Command

**File**: `hh/deploy/users/install.py`

The `install` command performs complete system initialization:

**Prerequisites**:
- Must run with sudo/root privileges (checked via `gateway.os.require_privileged()`)
- Requires 4 passwords (one per tier: guest, verified, admin, root)
- Password arguments: `-password1/-pwd1/-p1`, `-password2/-pwd2/-p2`, `-password3/-pwd3/-p3`, `-password4/-pwd4/-p4`
- Optional: `-hen <script_name>` to use custom script name (defaults to 'hen')
- Optional: `-user_key <ssh_key>` to add additional SSH key to all users
- Optional: `-clean` to remove existing .git directory before reinstall

**Project Detection**:
- **Project name**: Automatically detected from folder name containing `hh/` directory
- **Project owner**: Automatically detected from folder ownership (UID lookup)
- These values determine file ownerships, permissions, and user access throughout deployment

### Installation Process Flow

1. **Validation**:
   - Checks for existing setup (users, groups, directories, git repo)
   - Checks for script name conflicts in `/root/` and project owner's home
   - Validates all four passwords are provided

2. **Core Groups Creation** (before users):
   - `{project_name}` - Main project group
   - `{project_name}_deploy` - Deployment group (all tier users)
   - `{project_name}_admin` - Admin group (admin tier user's primary group)

3. **User Creation**:
   - Creates 4 system users: `{project_name}_guest`, `{project_name}_verified`, `{project_name}_admin`, `{project_name}_root`
   - Each user: system user (`-r` flag), `/bin/bash` shell, home directory at `/home/{user}`
   - Admin tier user gets `{project_name}_admin` as primary group
   - All users get `{project_name}_deploy` as supplementary group
   - Highest tier (root) user gets both `{project_name}` and `{project_name}_deploy` groups

4. **SSH Key Management**:
   - **Auto-scan**: Scans project owner's `~/.ssh/authorized_keys` and `~/.ssh/*.pub` files
   - **Generate**: Creates new SSH keypair for each tier user (`ssh-keygen -t rsa -b 4096`)
   - **Transfer**: Adds all discovered keys (auto-scanned + user-provided) to each tier user's `authorized_keys`
   - All users own their own `.ssh` directories and files

5. **Credential Files**:
   - Creates `~/.{project_name}.cnf` for each tier user
   - Format: INI-style with `[client]` section containing `user`, `password`, `host=localhost`, `database={project_name}`
   - Permissions: `0o600` (read/write for owner only)
   - Owned by respective user

6. **Git Repository Setup**:
   - Creates `/srv/{project_name}/git/{project_name}.git` bare repository
   - Initializes git in project folder if not already a repo
   - Configures git user: `{project_name} System` / `system@{project_name}.local`
   - Creates initial commit with all files
   - Renames branch to `{project_name}` (regardless of git default)
   - Adds bare repo as `origin` remote and pushes
   - Sets bare repo HEAD to `{project_name}` branch
   - Ownership: `{project_owner}:{project_name}` with `0o770` directories, `0o660` files

7. **Convenience Scripts**:
   - **Tier users**: Creates `gateway.py` and `{hen_script_name}` in each user's home
     - `gateway.py`: Modified `hen.py` with `/srv/{project_name}` added to Python path
     - `{hen_script_name}`: Wrapper script that calls `python3 gateway.py "$@"`
   - **Project owner (human user)**: Creates `{hen_script_name}` in `/home/{project_owner}/`
     - Points to project folder's `hen.py` (for testing experimental code)
   - **Root user**: Creates `{hen_script_name}` in `/root/`
     - Points to project folder's `hen.py` with cache cleanup after execution

8. **PATH Configuration**:
   - Updates `.profile` for all tier users: `export PATH="/home/{user}:$PATH"`
   - Updates `.profile` for project owner and root: `export PATH="{user_home}:/root:$PATH"`
   - All users can now run `hen` command from anywhere

9. **HTTP Basic Auth Files**:
   - Creates `/var/www/.htpasswd_{admin_tier}` for admin subdomain
   - Creates `/var/www/.htpasswd_panel` for root/panel subdomain
   - Uses `htpasswd -b` for batch mode password setting

10. **Directory Setup**:
    - Creates `/srv/images/{project_name}` with `deleted/` subdirectory
    - Creates `/srv/files/{project_name}`
    - Permissions: `0o2775` (setgid for group write), owned by `{project_name}_root:{project_name}_admin`

11. **Group Membership**:
    - Adds current user (running install) to all project groups
    - Adds project owner to all project groups
    - Adds `www-data` to `{project_name}_deploy` and `{project_name}_admin` groups

12. **Project Ownership**:
    - Sets entire project folder ownership to `{project_owner}:{project_name}`
    - Sets setgid bit (`0o2750`) on directories so new files inherit group ownership

**See also**: `hh/deploy/users/install.py` function `install`

### User Account Utilities

**File**: `hh/deploy/users/user_accounts.py`

Provides helper functions for user account management:

- **`create_user_config_file(user, project_name, password)`**: Creates credential file
- **`update_user_paths(project_name)`**: Updates PATH in all tier users' `.profile` files
- **`create_user_gateway_scripts(project_name, hen_script_name)`**: Creates `gateway.py` for tier users
- **`create_user_hen_scripts(project_name, hen_script_name)`**: Creates `hen` wrapper scripts for tier users
- **`setup_user_convenience_scripts(...)`**: Sets up convenience scripts for human/root users
- **`setup_human_user_home(...)`**: Sets up project owner's home directory
- **`setup_root_user_script(...)`**: Sets up root user's convenience script with cache cleanup
- **`detect_project_owner(project_path)`**: Detects project folder owner via UID lookup

### SSH Key Management

**File**: `hh/deploy/users/access.py`

Provides SSH key scanning and management:

- **`auto_scan_user_keys(project_owner)`**: Scans project owner's SSH keys
  - Reads `~/.ssh/authorized_keys`
  - Reads `~/.ssh/id_rsa.pub` and other `*.pub` files
  - Returns list of public keys
- **`generate_ssh_keys(user, project_name)`**: Generates new SSH keypair for user
  - Creates `~/.ssh/id_rsa` and `~/.ssh/id_rsa.pub`
  - Returns public key and file paths
- **`add_user_key(user, user_key)`**: Adds SSH key to user's `authorized_keys`
  - Appends key to `~/.ssh/authorized_keys`
  - Sets proper ownership

### User Tier Configuration

**File**: `hh/deploy/conf/user_account_suffixes.py`

Defines the four user tiers:

- **`HENHOUSE_TIERS`**: `['guest', 'verified', 'admin', 'root']`
- Used throughout deployment system to generate user names: `{project_name}_{tier}`
- Order matters: first is lowest privilege, last is highest privilege

---

## 3. Database Deployment

The database deployment system manages MySQL database initialization, user creation, permissions, and data management for both the main application database and the cache database.

### Database Architecture

Henhouse uses a two-database architecture:

- **Main Database**: `{project_name}` - Contains all application tables (pages, images, agents, work dockets, etc.)
- **Cache Database**: `{project_name}_cache` - Contains cache tables (pages, images, files) for performance optimization

Both databases use:
- **Character Set**: `utf8mb4`
- **Collation**: `utf8mb4_unicode_ci`
- **Engine**: InnoDB (for foreign key support)

### Database Initialization

**File**: `hh/deploy/db/init_db.py`

The `init_db` command initializes both databases and creates all required tables:

**Prerequisites**:
- Must run with root MySQL access
- Requires: `-password <root_password>` (MySQL root password)
- Requires: `--confirm` flag (safety check)

**Process Flow**:

1. **Database Creation**:
   - Creates `{project_name}` database if not exists
   - Creates `{project_name}_cache` database if not exists
   - Uses `CREATE DATABASE IF NOT EXISTS` with utf8mb4 charset

2. **Schema Execution**:
   - Executes `hh/deploy/db/init.sql` on main database
   - Executes `hh/deploy/db/init_cache.sql` on cache database
   - Uses `mysql` command-line client with root credentials

3. **Verification**:
   - Verifies tables were created in main database
   - Verifies tables were created in cache database
   - Returns table counts for both databases

**SQL Files**:
- **`init.sql`**: Creates all application tables (pages, images, files, image_instances, links, image_links, etc.)
- **`init_cache.sql`**: Creates cache tables (pages, images, files) with JSON columns for cached data

**See also**: `hh/deploy/db/init_db.py` function `init_db`

### Database User Management

**File**: `hh/deploy/db/add_db_users.py`

The `add_db_users` command creates database users for each tier with appropriate permissions:

**Prerequisites**:
- Must run with root MySQL access
- Requires: `-password <root_password>` (MySQL root password)
- Requires: User credential files must exist (`~/.{project_name}.cnf` for each tier user)

**Process Flow**:

1. **Password Reading**:
   - Reads password from each tier user's credential file: `~/.{project_name}.cnf`
   - Parses INI-style config file to extract password
   - Skips tier if password file not found

2. **User Creation/Update**:
   - Checks if user already exists
   - **If exists**: Updates password and checks/updates permissions
   - **If new**: Creates user with `CREATE USER {username}@'%' IDENTIFIED BY {password}`

3. **Permission Granting**:
   - Grants permissions on both main and cache databases
   - Permissions are tier-specific (see Tier Permissions below)
   - Uses `GRANT {permission} ON {database}.* TO {username}@'%'`

4. **Privilege Flushing**:
   - Executes `FLUSH PRIVILEGES` after all changes

**Tier Permissions**:

- **guest**: `SELECT` only (read-only access)
- **verified**: `SELECT`, `INSERT` (read and moderate write)
- **admin**: `SELECT`, `INSERT`, `UPDATE`, `DELETE` (full CRUD)
- **root**: `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, `ALTER`, `INDEX`, `REFERENCES` (full database management)

**Permission Validation**:
- Checks that users have NO global privileges (all should be 'N' in `mysql.user`)
- Verifies database-specific privileges in `mysql.db`
- Updates missing permissions without revoking extra permissions (to avoid breaking existing functionality)

**See also**: `hh/deploy/db/add_db_users.py` functions `add_db_users`, `create_database_user`, `get_tier_permissions`, `check_and_update_permissions`

### Database User Removal

**File**: `hh/deploy/db/remove_db_users.py`

The `remove_db_users` command removes database users for all tiers:

**Prerequisites**:
- Must run with root MySQL access
- Requires: `-password <root_password>` (MySQL root password)

**Process Flow**:

1. **User Removal**:
   - Checks if user exists before attempting removal
   - Drops user with `DROP USER {username}@'%'`
   - Flushes privileges after removal
   - Verifies user was removed successfully

2. **Result Tracking**:
   - Tracks which users were removed, not found, or failed
   - Returns status for each tier user

**See also**: `hh/deploy/db/remove_db_users.py` functions `remove_db_users`, `remove_database_user`

### Database Checking

**File**: `hh/deploy/db/check_db.py`

The `check_db` command verifies database connectivity and lists all tables:

**Prerequisites**:
- Requires: `-password <root_password>` (MySQL root password)

**Process Flow**:

1. **Table Discovery**:
   - Executes `SHOW TABLES` to get all table names
   - For each table, executes `SELECT COUNT(*)` to get row counts

2. **Result Formatting**:
   - Formats table information for display
   - Returns table count and detailed table info with row counts

**See also**: `hh/deploy/db/check_db.py` function `check_db`

### Database Export

**File**: `hh/deploy/db/export_db.py`

The `export_db` command exports a database to a SQL file:

**Prerequisites**:
- Requires: `-password <root_password>` (MySQL root password)
- Optional: `-database <db_name>` (defaults to main database)
- Optional: `-cache` flag (exports cache database instead)

**Process Flow**:

1. **Target Database Selection**:
   - Uses `-database` argument if provided
   - Uses `-cache` flag to select cache database
   - Defaults to main database (`{project_name}`)

2. **Table Information Collection**:
   - Collects table names and row counts before export
   - Uses main connection or cache connection as appropriate

3. **mysqldump Execution**:
   - Creates export file: `database_dumps/{project_name}_export_{timestamp}.sql`
   - Uses `mysqldump` with options:
     - `--single-transaction`: Consistent snapshot
     - `--skip-add-drop-table`: Preserves existing table structure
     - `--disable-keys`: Faster import
     - `--extended-insert`: More efficient SQL
   - Wraps export with transaction control:
     - `SET FOREIGN_KEY_CHECKS=0` at start
     - `SET UNIQUE_CHECKS=0` at start
     - `SET AUTOCOMMIT=0` and `START TRANSACTION` at start
     - `COMMIT` and re-enable checks at end

4. **File Ownership**:
   - Sets ownership to current user (from `SUDO_USER` or `USER` environment)

**Export Location**: `{project_path}/database_dumps/`

**See also**: `hh/deploy/db/export_db.py` function `export_db`

### Database Import

**File**: `hh/deploy/db/import_db.py`

The `import_db` command imports a database from a SQL file:

**Prerequisites**:
- Requires: `-password <root_password>` (MySQL root password)
- Requires: `-filename <path>` (path to SQL file to import)
- Optional: `-database <db_name>` (defaults to main database)
- Optional: `-cache` flag (imports to cache database instead)

**Process Flow**:

1. **File Validation**:
   - Checks that import file exists
   - Gets file size for reporting

2. **Target Database Selection**:
   - Uses `-database` argument if provided
   - Uses `-cache` flag to select cache database
   - Defaults to main database (`{project_name}`)

3. **Pre-Import Table Information**:
   - Collects current table names and row counts (before import)

4. **MySQL Import Execution**:
   - Uses `mysql` command-line client to import SQL file
   - Pipes SQL file content to mysql stdin

5. **Post-Import Verification**:
   - Collects final table names and row counts (after import)
   - Returns comparison data

**See also**: `hh/deploy/db/import_db.py` function `import_db`

### Database Cleaning

**File**: `hh/deploy/db/clean_db.py`

The `clean_db` command removes all tables from both databases:

**Prerequisites**:
- Must run with root MySQL access
- Requires: `-password <root_password>` (MySQL root password)
- Requires: `--confirm` flag (safety check)

**Process Flow**:

1. **Clean Script Execution**:
   - Executes `hh/deploy/db/clean.sql` on main database
   - Executes `hh/deploy/db/clean_cache.sql` on cache database
   - Uses `mysql` command-line client with root credentials

2. **Verification**:
   - Verifies all tables were dropped
   - Checks both main and cache databases
   - Returns remaining table counts (should be 0)

**SQL Files**:
- **`clean.sql`**: Drops all application tables (disables foreign key checks, drops all tables, re-enables checks)
- **`clean_cache.sql`**: Drops all cache tables

**Warning**: This operation is destructive and cannot be undone. Use `export_db` first to create a backup.

**See also**: `hh/deploy/db/clean_db.py` function `clean_db`

### Homepage Initialization

**File**: `hh/deploy/db/init_homepage.py`

The `init_homepage` command creates the initial homepage (page ID 1):

**Prerequisites**:
- Pages table must be empty (safety check)
- Requires database connection (uses current user's credentials)

**Process Flow**:

1. **Safety Check**:
   - Verifies `pages` table is empty
   - Fails if table contains any records

2. **Homepage Creation**:
   - Inserts page with ID 1
   - Sets `parent = 0` (root page)
   - Sets `name = {project_name}`
   - Sets `text = 'Hello, World!'`
   - Sets `class = 'page'`
   - Sets `visibility = 1`, `displayStyle = 1`
   - Records current database user and timestamp

**Usage**: Run once after database initialization when pages table is empty.

**See also**: `hh/deploy/db/init_homepage.py` functions `init_homepage`, `create_homepage`, `check_pages_empty`

### Database Connection Management

The database system uses Gateway's connection management:

- **Root Connection**: Created automatically when `-password` argument is provided
  - Provides root MySQL access for administrative operations
  - Used by: `init_db`, `add_db_users`, `remove_db_users`, `check_db`, `export_db`, `import_db`, `clean_db`

- **Tier User Connections**: Created from credential files
  - Each tier user has `~/.{project_name}.cnf` with database credentials
  - Used for normal application operations

- **Cache Connection**: Access via `gateway.conn.cache`
  - RootConnection provides root access to cache database
  - Used for cache table operations

### SQL Schema Files

**Main Database Schema** (`init.sql`):
- Creates all application tables with foreign key relationships
- Includes: agents, pages, images, work dockets, subscriptions, watercooler, etc.
- Uses InnoDB engine for transaction support and foreign keys

**Cache Database Schema** (`init_cache.sql`):
- Creates three cache tables: `pages`, `images`, `files`
- Each table has JSON columns for cached data
- Includes `cache_built_at` timestamp for cache freshness tracking

**Clean Scripts**:
- `clean.sql`: Drops all main database tables
- `clean_cache.sql`: Drops all cache database tables
- Both disable foreign key checks during cleanup

---

## 4. File Deployment

The file deployment system orchestrates the complete process of copying files to `/srv/{project_name}`, managing service lifecycle, and setting up the production environment.

### Deploy Command

**File**: `hh/deploy/srv/deploy.py`

The `deploy` command performs a complete deployment with the following flow:

**Prerequisites**:
- Must run with sudo/root privileges (checked via `gateway.os.require_privileged()`)
- Optional: `-start_port <port>` to specify starting port for Flask apps (default: 5001)

**Project Detection**:
- Automatically detects project name by walking up directory tree looking for `hh/` directory
- Uses folder name as project name
- Source: project folder, Destination: `/srv/{project_name}`

### Deployment Process Flow

#### Step 1: Stop Running Daemons

Before deployment begins, all running services are stopped:
- **Maintenance daemon**: Stopped via `run_maintenance_stop(project_name)`
- **Flask daemons**: Stopped via `run_flask_stop(project_name)`

This ensures clean deployment without running processes holding file locks.

#### Step 2: Preserve Git Repository

The git repository is preserved across deployments:
- **Temporary move**: `/srv/{project_name}/git` → `/srv/{project_name}_git` (temporary location)
- **Restoration**: Git folder restored after deployment directory sterilization
- This preserves the bare git repository and all git history

#### Step 3: Sterilize Deployment Directory

The entire `/srv/{project_name}` directory is cleaned:
- **Removes all contents** except preserved git folder
- If directory doesn't exist, creates it
- Ensures clean slate for each deployment

#### Step 4: Deploy Main Code

Copies the entire `hh/` folder to `/srv/{project_name}/hh/`:
- Uses `shutil.copytree()` to copy entire directory structure
- All Python modules, subdirectories, and files are copied
- This is the core application code

#### Step 5: Clean Deploy Folder (Preserve Whitelisted Items)

**Critical Process**: The `hh/deploy/` folder is cleaned while preserving essential items:

1. **Temporary preservation**: Whitelisted items moved to temporary locations:
   - `cache/` → `/srv/{project_name}/.{project_name}_cache_tmp`
   - `conf/` → `/srv/{project_name}/.{project_name}_conf_tmp`
   - `maint/` → `/srv/{project_name}/.{project_name}_maint_tmp`
   - `utils.py` → `/srv/{project_name}/.{project_name}_utils_py_tmp`

2. **Deploy folder removal**: Entire `hh/deploy/` directory is removed

3. **Recreate and restore**: Deploy directory recreated, whitelisted items restored

This ensures only essential deployment utilities remain in the deploy folder after deployment, while all deployment scripts (db/, flask/, http/, users/, etc.) are removed since they're only needed during deployment, not in production.

#### Step 6: Clean Cache Files

Removes all cache files from deployment:
- **`__pycache__` directories**: Recursively removed
- **`.pyc` files**: All Python bytecode files removed
- **Cache JSON files**: `*-reg.json`, `*.cycle.json`, `cache.json`, `*.cache` patterns
- **`.cache` directories**: Recursively removed

This ensures clean deployment without stale cache files.

#### Step 7: Deploy Flask Applications

Creates tier-specific Flask application files:
- **Source**: `hh/deploy/flask/app.py`
- **Destination**: `/srv/{project_name}/{project_name}_{tier}.py` (one per tier)
- **Port assignment**: Each tier gets sequential port starting from `start_port`:
  - Tier 0 (guest): `start_port + 0`
  - Tier 1 (verified): `start_port + 1`
  - Tier 2 (admin): `start_port + 2`
  - Tier 3 (root): `start_port + 3`
- **Log file**: Each app gets tier-specific log file: `/srv/{project_name}/logs/flask_{project_name}_{tier}.log`
- **Content modification**: Port and log file paths are replaced in the source template

#### Step 8: Deploy Maintenance Worker

Creates the maintenance worker script:
- **Source**: `hh/deploy/maintenance/worker.py`
- **Destination**: `/srv/{project_name}/{project_name}_maintenance.py`
- **Template replacement**: `__PROJECT_NAME__` replaced with actual project name

#### Step 9: Deploy Extra Top-Level Files

Copies additional files specified in `EXTRA_DEPLOY_FILES`:
- `hh/deploy/flask/http_client.py` → `/srv/{project_name}/http_client.py`
- `hh/deploy/flask/mcp_client.py` → `/srv/{project_name}/mcp_client.py`
- `hh/deploy/maint/maintenance_client.py` → `/srv/{project_name}/maintenance_client.py`

These are entry point scripts used by the deployed applications.

#### Step 10: Deploy Context Folders and Files

Deploys documentation and context files for agent visibility:
- **Destination**: `/srv/{project_name}/context/`
- **Whitelist**: Items from `CONTEXT_WHITELIST` (context/, planning/, hh/, top-level scripts, README.md, LICENSE, requirements.txt)
- **Blacklist filtering**: Excludes patterns from `CONTEXT_BLACKLIST` (.git, __pycache__, *.pyc, node_modules, .env, *.log, cache JSON files)
- **Structure**: Maintains directory structure under `context/` subdirectory

#### Step 11: Deploy Site Files

Deploys static site assets to `/srv/{project_name}/site/`:

- **JavaScript files** (`JS_WHITELIST`):
  - Deployed to `site/js/`
  - Overlay subfolder files flattened to `site/js/` (no subdirectory)
  - Includes: seed.js, rpc-client.js, app.js, page-data files, overlay system files, infographic files

- **CSS files** (`CSS_WHITELIST`):
  - Deployed to `site/css/`
  - Includes: site.css, tier-specific CSS files, ansi-colors.css, tables.css, pygments.css, overlay.css, infographic CSS

- **Python files** (`PY_WHITELIST`):
  - Deployed to `site/py/`
  - Currently: infographic.py

- **Miscellaneous files** (`MISC_WHITELIST`):
  - Deployed to `site/` root
  - Can be files or directories (infographic directory, site.webmanifest, favicons, etc.)

#### Step 12: Set Ownership and Permissions

Sets proper Unix ownership and permissions:

- **Main deployment**: 
  - Owner: `{project_name}_root` (highest tier user)
  - Group: `{project_name}_deploy`
  - Directories: `0o750` (owner:rwx, group:r-x, others:---)
  - Files: `0o640` (owner:rw-, group:r--, others:---)

- **Git directory** (special permissions):
  - Owner: `{project_name}_root`
  - Group: `{project_name}` (project group, not deploy group)
  - Directories: `0o770` (owner:rwx, group:rwx, others:---)
  - Files: `0o660` (owner:rw-, group:rw-, others:---)

#### Step 13: Set Up Cache Directory Permissions

Configures cache directories discovered via cache registry:
- **Discovery**: Uses `get_cache_directories()` to find all registered cache directories
- **Permissions**: `0o2775` (setgid for group write, owner:rwx, group:rwx, others:r-x)
- **Ownership**: `{project_name}_root:{project_name}_deploy`
- **Creation**: Creates cache directories if they don't exist

This allows all tier users (in deploy group) to write cache files via group permissions.

#### Step 14: Set Up Logs Directory

Creates and configures logs directory:
- **Path**: `/srv/{project_name}/logs/`
- **Permissions**: `0o2775` (setgid for group write)
- **Ownership**: `{project_name}_root:{project_name}_deploy`
- **Purpose**: Flask daemons and maintenance worker write logs here

#### Step 15: Restart Daemons

Starts services after deployment completes:
- **Flask daemons**: Started via `run_flask_start(project_name, start_port)`
- **Maintenance daemon**: Started via `run_maintenance_start(project_name)`
- Services start with new code and proper permissions in place

#### Step 16: Clear Registry Cache

Calls `clean_all_caches()` to clear all registered caches:
- Prevents permission issues from stale cache files
- Ensures clean state after deployment

### Deploy Folder Cleanup Details

The deploy folder cleanup is a critical safety mechanism:

**Process**:
1. Each whitelisted item is moved to a uniquely named temporary location
2. Entire `hh/deploy/` directory is removed
3. `hh/deploy/` directory is recreated
4. Whitelisted items are restored from temporary locations

**Temporary naming**: `.{project_name}_{item_name}_tmp` (with `/` and `.` replaced with `_`)

**Why this matters**: Deployment scripts (db/, flask/, http/, users/, etc.) are only needed during deployment operations, not in production. Keeping them in production would be a security risk and waste of space.

### File Whitelisting System

Files are whitelisted through multiple configuration files in `hh/deploy/conf/`:

- **Python files**: `py_whitelist.py` → `PY_WHITELIST`
- **JavaScript files**: `js_whitelist.py` → `JS_WHITELIST`, `JS_ALWAYS_INCLUDE`
- **CSS files**: `css_whitelist.py` → `CSS_WHITELIST`, `CSS_ALWAYS_INCLUDE`
- **Miscellaneous files**: `misc_whitelist.py` → `MISC_WHITELIST`
- **Context files**: `context_whitelist.py` → `CONTEXT_WHITELIST`
- **Context blacklist**: `context_blacklist.py` → `CONTEXT_BLACKLIST` (patterns to exclude)
- **Deploy whitelist**: `deploy_whitelist.py` → `DEPLOY_WHITELIST`, `EXTRA_DEPLOY_FILES`

### Permission Model

The deployment uses a tiered permission model:

- **Owner**: `{project_name}_root` (highest tier user) - full read/write access
- **Group**: `{project_name}_deploy` - read access to code, write access to cache/logs via setgid
- **Others**: No access

**Setgid directories**: Cache and logs directories use setgid bit (`0o2775`) so new files created by any tier user inherit the deploy group, enabling group write access.

**See also**: `hh/deploy/srv/deploy.py` function `deploy`

---

## 5. Flask Application Management

The Flask application management system handles tier-based Flask daemon lifecycle, process management, logging, and HTTP/MCP request routing.

### Flask Architecture

Henhouse deploys multiple Flask application instances, one per user tier:

- **Guest tier**: `{project_name}_guest.py` on port 5001
- **Verified tier**: `{project_name}_verified.py` on port 5002
- **Admin tier**: `{project_name}_admin.py` on port 5003
- **Root tier**: `{project_name}_root.py` on port 5004

Each instance:
- Runs as its corresponding Unix user (`{project_name}_{tier}`)
- Serves content with tier-appropriate permissions
- Has its own log file: `/srv/{project_name}/logs/flask_{project_name}_{tier}.log`
- Listens on `127.0.0.1` (localhost only, proxied by NGINX)

### Flask Application Start

**File**: `hh/deploy/flask/flask_start.py`

The `flask_start` command starts Flask daemons for all tiers:

**Prerequisites**:
- Must run with sudo/root privileges
- Flask application files must be deployed (`{project_name}_{tier}.py`)

**Process Flow**:

1. **Remove Existing Logrotate Config**:
   - Removes any existing logrotate configuration (cleanup from previous runs)

2. **Start Daemons for Each Tier**:
   - For each tier, calls `start_flask_daemon(project_name, tier, port)`
   - Port assignment: `start_port + tier_index` (default start_port: 5001)

3. **Daemon Startup Process** (per tier):
   - **Check app file exists**: Verifies `{project_name}_{tier}.py` exists
   - **Check user exists**: Verifies Unix user exists
   - **Stop existing processes**: Finds and kills any running Flask processes for this tier (acts like restart)
   - **Start daemon**: Uses `sudo -u {user} bash -c "cd /srv/{project_name} && nohup python3 {app_path} < /dev/null &> /dev/null &"`
   - **Verify startup**: Waits 1 second, then checks `ps aux` to confirm process is running
   - **Logging**: Flask app handles its own logging internally (no shell redirection needed)

4. **Configure Logrotate**:
   - Creates `/etc/logrotate.d/{project_name}-flask` configuration
   - Configures hourly rotation, 24 rotations, compression
   - Restarts logrotate service

**Logrotate Configuration**:
- **Frequency**: Hourly rotation
- **Retention**: 24 rotations (24 hours)
- **Compression**: Enabled with delaycompress
- **Method**: copytruncate (keeps file open for continuous logging)

**See also**: `hh/deploy/flask/flask_start.py` functions `flask_start`, `run_flask_start`, `start_flask_daemon`, `setup_logrotate`

### Flask Application Stop

**File**: `hh/deploy/flask/flask_stop.py`

The `flask_stop` command stops Flask daemons for all tiers:

**Prerequisites**:
- Must run with sudo/root privileges

**Process Flow**:

1. **Stop Daemons for Each Tier**:
   - For each tier, calls `stop_flask_daemon(project_name, tier)`

2. **Daemon Stop Process** (per tier):
   - **Find processes**: Uses `ps aux` to find processes running `{project_name}_{tier}.py`
   - **Extract PIDs**: Parses process list to get process IDs
   - **Kill processes**: Sends SIGTERM to each PID via `gateway.os.kill_process(pid, force=False)`
   - **Return status**: Returns stopped PIDs or "not_running" if no processes found

3. **Remove Logrotate Config**:
   - Removes logrotate configuration if any daemons were stopped or all were not running
   - Restarts logrotate service

**See also**: `hh/deploy/flask/flask_stop.py` functions `flask_stop`, `run_flask_stop`, `stop_flask_daemon`, `remove_logrotate`

### Flask Application Status

**File**: `hh/deploy/flask/flask_status.py`

The `flask_status` command checks the status of Flask daemons:

**Process Flow**:

1. **Check Each Tier**:
   - For each tier, calls `get_flask_daemon_status(project_name, tier, port)`

2. **Status Check Process** (per tier):
   - **Check app file**: Verifies `{project_name}_{tier}.py` exists (returns "not_deployed" if missing)
   - **Check process**: Uses `ps aux` to find running processes
   - **Extract PIDs**: Parses process list to get all process IDs for this tier
   - **Return status**: Returns "running" with PIDs, "stopped", "not_deployed", or "error"

3. **Summary**:
   - Counts running, stopped, not_deployed, and error states
   - Returns detailed status for each tier plus summary

**See also**: `hh/deploy/flask/flask_status.py` functions `flask_status`, `get_flask_daemon_status`

### Flask Application (`app.py`)

**File**: `hh/deploy/flask/app.py`

The main Flask application handles HTTP requests and routes them to the Gateway system.

**Tier Detection**:
- Extracts tier from script name: `{project_name}_{tier}.py` → `tier`
- Falls back to environment variable or defaults to empty string

**Configuration**:
- **Project root**: `/srv/{project_name}`
- **Site directory**: `/srv/{project_name}/site`
- **Log file**: `/srv/{project_name}/logs/flask_{project_name}_{tier}.log`
- **Secret key**: Environment variable or default (should be changed in production)
- **Max upload size**: 50MB
- **Gateway concurrency**: Configurable via `GATEWAY_MAX_CONCURRENCY` (default: 4)

**Routes**:

1. **`/mcp` and `/mcp/<path:path>`** - MCP (Model Context Protocol) handler:
   - Accepts POST (JSON or multipart/form-data) and GET requests
   - Validates JSON-RPC 2.0 structure
   - Extracts path segments, query params, form fields, and file uploads
   - Routes to `mcp_client.py` via subprocess
   - Returns JSON-RPC 2.0 responses
   - Handles file uploads: saves to `/tmp` with UUID names, passes metadata via flags

2. **`/img/<path:image_path>`** - Image serving:
   - Only accepts numeric image IDs (strict validation)
   - Routes to `http_client.py` with `show-image --id {id}` command
   - Returns JSON or HTML based on response content

3. **`/` and `/<path:path>`** - Dynamic page routing:
   - Always routes to `show-page` command
   - **Numeric paths**: Treated as page ID (e.g., `/123` → `show-page --id 123`)
   - **Non-numeric paths**: Treated as page name (e.g., `/Bob/Sally` → `show-page --name Bob/Sally`)
   - Empty path defaults to page ID 1 (homepage)
   - Routes to `http_client.py` via subprocess
   - Returns JSON or HTML based on response content

4. **`/upload-file`** - File upload handler:
   - Accepts multipart/form-data POST requests
   - Saves files to `/tmp` with UUID names
   - Returns JSON with temp file paths and metadata
   - Used by MCP tools that need file uploads

**Gateway Integration**:
- All requests routed via subprocess to `http_client.py` or `mcp_client.py`
- Uses semaphore for concurrency control (prevents too many simultaneous Gateway calls)
- 10-second timeout per request
- Passes tier via `USER_TIER` environment variable

**Error Handling**:
- JSON-RPC 2.0 error responses for MCP requests
- HTML error pages for HTTP requests
- Fallback response shows tier and project configuration if Gateway fails

**See also**: `hh/deploy/flask/app.py` - Main Flask application

### MCP Client

**File**: `hh/deploy/flask/mcp_client.py`

Entry point for MCP (Model Context Protocol) requests from Flask.

**MCP Protocol Support**:
- **Protocol Version**: `2024-11-05`
- **Methods**: `initialize`, `tools/list`, `tools/call`, `prompts/list`, `resources/list`, `notifications/initialized`

**Process Flow**:

1. **Read JSON-RPC Request**:
   - Reads from stdin (POST body from Flask)
   - Validates JSON-RPC 2.0 structure

2. **Handle Protocol Methods**:
   - **`initialize`**: Returns server capabilities and info
   - **`tools/list`**: Returns tier-filtered tool list via `MCPWhitelist.list_tools(tier)`
   - **`tools/call`**: Validates tool access via `MCPWhitelist.validate_tool()`, routes to Gateway
   - **`prompts/list`**: Returns empty list (not implemented)
   - **`resources/list`**: Returns empty list (not implemented)

3. **Tool Execution**:
   - Validates tool name and arguments for tier
   - Builds argv: `[tool_name, --arg1, value1, ...]`
   - Dispatches to Gateway with "mcp" backend
   - Formats response as JSON-RPC 2.0

**Tier Detection**:
- Gets tier from `USER_TIER` environment variable (set by Flask app)
- Validates against `HENHOUSE_TIERS`
- Defaults to 'guest' if invalid

**See also**: `hh/deploy/flask/mcp_client.py` - MCP client entry point

### HTTP Client

**File**: `hh/deploy/flask/http_client.py`

Entry point for HTTP backend requests from Flask.

**Process Flow**:

1. **Parse Arguments**:
   - Gets argv from `sys.argv[1:]` (passed by Flask)

2. **Dispatch to Gateway**:
   - Calls `gateway.dispatch(argv, "http")`
   - Gets output from gateway response

3. **Return Result**:
   - Prints output to stdout (captured by Flask)
   - Returns exit code (0 for success, 1 for errors)

**Usage**: Used by Flask app for `show-page` and `show-image` commands via HTTP backend.

**See also**: `hh/deploy/flask/http_client.py` - HTTP client entry point

### Process Management

**Background Process Execution**:
- Flask daemons run as background processes using `nohup`
- Input/output redirected to `/dev/null` (Flask handles its own logging)
- Processes run as tier-specific Unix users via `sudo -u {user}`
- Working directory: `/srv/{project_name}`

**Process Discovery**:
- Uses `ps aux` to find running processes
- Searches for `{project_name}_{tier}.py` in process command line
- Extracts PIDs from process list (second column)

**Signal Handling**:
- Uses SIGTERM for graceful shutdown (via `gateway.os.kill_process(pid, force=False)`)
- Processes should handle SIGTERM to clean up and exit

### Logging System

**Log Files**:
- Location: `/srv/{project_name}/logs/flask_{project_name}_{tier}.log`
- Format: `%(asctime)s %(levelname)s %(message)s`
- Level: INFO
- Flask's built-in logging system writes directly to log files

**Logrotate**:
- Configuration: `/etc/logrotate.d/{project_name}-flask`
- Rotation: Hourly
- Retention: 24 rotations (24 hours)
- Compression: Enabled with delaycompress
- Method: copytruncate (allows continuous logging without file handle issues)

### Concurrency Control

**Gateway Semaphore**:
- Limits concurrent Gateway calls per Flask instance
- Default: 4 concurrent requests (`GATEWAY_MAX_CONCURRENCY`)
- Prevents resource exhaustion from too many simultaneous requests
- 10-second timeout for semaphore acquisition

**Request Timeout**:
- 10-second timeout for subprocess calls to Gateway
- Prevents hung requests from blocking Flask app

### Deployment Integration

Flask applications are deployed during the main `deploy` command:

1. **Template Processing**: `app.py` is copied and modified for each tier:
   - Port number replaced with tier-specific port
   - Log file path replaced with tier-specific path

2. **File Creation**: Creates `{project_name}_{tier}.py` in `/srv/{project_name}/`

3. **Service Start**: `deploy` command calls `run_flask_start()` after deployment completes

**See also**: Section 4 (File Deployment) for deployment process details

---

## 6. HTTP/NGINX Deployment

The HTTP/NGINX deployment system manages web server configuration for serving Henhouse applications through NGINX reverse proxy. It supports two-stage deployment: HTTP-only (Stage 1) and HTTPS with SSL (Stage 2).

### NGINX Architecture

NGINX serves as a reverse proxy in front of Flask applications:

- **Main domain** (e.g., `example.com`, `www.example.com`): Proxies to guest tier Flask (port 5001)
- **Admin subdomain** (`admin.example.com`): Proxies to admin tier Flask (port 5003) with HTTP Basic Auth
- **Panel subdomain** (`panel.example.com`): Proxies to root tier Flask (port 5004) with HTTP Basic Auth

**Configuration Files**:
- **Location**: `/etc/nginx/sites-available/{domain}`
- **Symlink**: `/etc/nginx/sites-enabled/{domain}` → `sites-available/{domain}`
- **Deployment Marker**: Config files include "Generated by henhouse deploy-http system" or "Generated by henhouse deploy-ssl system" markers

### HTTP Deployment (Stage 1)

**File**: `hh/deploy/http/http_deploy.py`

The `http_deploy` command creates HTTP-only NGINX configuration:

**Prerequisites**:
- Must run with sudo/root privileges
- Requires: `-domain <domain>` (e.g., `example.com`)
- DNS must be configured to point domains to the server

**Process Flow**:

1. **Generate NGINX Configuration**:
   - Calls `create_nginx_config(domain, project_name)`
   - Generates server blocks for main domain, admin, and panel subdomains
   - Includes static file locations from whitelists
   - Adds security headers, rate limiting, hidden file blocking

2. **Install Configuration**:
   - Writes config to `/etc/nginx/sites-available/{domain}`
   - Creates symlink in `/etc/nginx/sites-enabled/{domain}`
   - Tests configuration with `nginx -t`
   - Reloads NGINX with `systemctl reload nginx` (or restart if reload fails)
   - Cleans up bad config if test fails

3. **Verify Installation**:
   - Checks NGINX service status
   - Returns deployment summary with domain, subdomains, and whitelist info

**Configuration Features**:
- **Port**: 80 (HTTP only)
- **Server blocks**: 3 blocks (main, admin, panel)
- **Static file serving**: Direct NGINX serving for whitelisted files
- **Flask proxy**: All other requests proxied to Flask apps
- **Security headers**: X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy
- **Rate limiting**: General rate limit zone
- **Hidden file blocking**: Blocks access to hidden files (except `.well-known`)

**See also**: `hh/deploy/http/http_deploy.py` functions `http_deploy`, `create_nginx_config`, `install_nginx_config`

### SSL Deployment (Stage 2)

**File**: `hh/deploy/http/http_deploy_ssl.py`

The `http_deploy_ssl` command upgrades HTTP configuration to HTTPS:

**Prerequisites**:
- Must run with sudo/root privileges
- Requires: `-domain <domain>` (e.g., `example.com`)
- Optional: `-cert_path <path>` (defaults to `/etc/letsencrypt/live/{domain}`)
- SSL certificates must already be installed (e.g., via Let's Encrypt)

**Process Flow**:

1. **Generate SSL Configuration**:
   - Calls `create_nginx_ssl_config(domain, project_name, certificate_path)`
   - Generates HTTP-to-HTTPS redirect block for all domains
   - Generates HTTPS server blocks for main, admin, and panel
   - Uses same static locations and security features as HTTP config

2. **Install Configuration**:
   - **Overwrites** existing HTTP config in `/etc/nginx/sites-available/{domain}`
   - Ensures symlink exists in `sites-enabled`
   - Tests configuration with `nginx -t`
   - Reloads NGINX

3. **Verify Installation**:
   - Checks NGINX service status
   - Returns deployment summary with SSL certificate path

**Configuration Features**:
- **HTTP Redirect**: Redirects all HTTP (port 80) traffic to HTTPS (port 443)
- **HTTPS Server Blocks**: 3 HTTPS blocks (main, admin, panel)
- **SSL Certificates**: Uses Let's Encrypt certificates by default
- **HTTP/2**: Enabled for HTTPS connections
- **HSTS**: Strict-Transport-Security header included
- **Same Features**: All HTTP features plus SSL/TLS encryption

**Certificate Path**:
- Default: `/etc/letsencrypt/live/{domain}/`
- Certificate file: `fullchain.pem`
- Private key: `privkey.pem`

**See also**: `hh/deploy/http/http_deploy_ssl.py` functions `http_deploy_ssl`, `create_nginx_ssl_config`, `install_nginx_ssl_config`

### HTTP Removal

**File**: `hh/deploy/http/http_remove.py`

The `http_remove` command removes NGINX configuration:

**Prerequisites**:
- Must run with sudo/root privileges
- Requires: `-domain <domain>`
- Optional: `-force` flag to skip safety checks

**Process Flow**:

1. **Safety Validation**:
   - Validates config file has deployment marker ("Generated by henhouse deploy-http system" or "Generated by henhouse deploy-ssl system")
   - Skips validation if `-force` flag is provided
   - Refuses to delete manually configured files (safety feature)

2. **Remove Configuration**:
   - Removes symlink from `/etc/nginx/sites-enabled/{domain}`
   - Removes config file from `/etc/nginx/sites-available/{domain}`
   - Tests NGINX configuration
   - Reloads NGINX

**Safety Feature**: Only deletes config files that were created by the deployment system (have deployment markers). This prevents accidental deletion of manually configured sites.

**See also**: `hh/deploy/http/http_remove.py` functions `http_remove`, `remove_nginx_config`, `validate_nginx_config_for_deletion`

### HTTP Status

**File**: `hh/deploy/http/http_status.py`

The `http_status` command scans and reports NGINX configuration status:

**Process Flow**:

1. **Scan NGINX Sites**:
   - Scans `/etc/nginx/sites-available` for all config files
   - Checks `/etc/nginx/sites-enabled` for enabled sites (symlinks)
   - Reads each config file to detect:
     - **Henhouse marker**: "Generated by henhouse deploy-http system" or "Generated by henhouse deploy-ssl system"
     - **SSL presence**: Checks for `ssl_certificate`, `listen 443`, or `ssl http2`

2. **Categorize Sites**:
   - **active_henhouse**: Enabled + has Henhouse marker
   - **available_henhouse**: Not enabled + has Henhouse marker
   - **active_other**: Enabled + no marker (manually configured)
   - **available_other**: Not enabled + no marker

3. **Check NGINX Service**:
   - Checks if NGINX service is active via `systemctl is-active nginx`

4. **Return Summary**:
   - Returns categorized sites with SSL status and deployment stage
   - Stage 1 = HTTP only, Stage 2 = HTTPS

**See also**: `hh/deploy/http/http_status.py` functions `http_status`, `scan_nginx_sites`, `categorize_sites`, `check_nginx_status`

### NGINX Configuration Helpers

**File**: `hh/deploy/http/nginx_config_helpers.py`

Provides helper functions for generating NGINX configuration blocks:

**Key Functions**:

- **`get_server_configs(domain, project_name)`**: Returns server configuration definitions
  - Detects Flask ports from deployed app files
  - Returns 3 server configs: main (guest), admin, panel (root)
  - Falls back to default ports (5001, 5002, 5003, 5004) if files not found

- **`generate_server_block(...)`**: Generates HTTP server block
  - Server names, port, static locations, label
  - Includes security headers, rate limiting, hidden file blocking
  - Adds HTTP Basic Auth for admin/panel subdomains
  - Flask proxy configuration

- **`generate_https_server_block(...)`**: Generates HTTPS server block
  - Same as HTTP block plus SSL certificate configuration
  - HTTP/2 enabled
  - HSTS header included

- **`generate_http_redirect_block(all_domains)`**: Generates HTTP-to-HTTPS redirect
  - Listens on port 80
  - Returns 301 redirect to HTTPS

- **`get_security_headers()`**: Standard security headers for HTTP
- **`get_security_headers_ssl()`**: Security headers for HTTPS (includes HSTS)
- **`get_rate_limiting()`**: Rate limiting configuration
- **`get_block_hidden_files()`**: Blocks hidden files (allows `.well-known` for Let's Encrypt)
- **`get_auth_block(project_name, tier)`**: HTTP Basic Auth configuration
  - Admin tier: uses `/var/www/.htpasswd_admin`
  - Root tier: uses `/var/www/.htpasswd_panel`
  - Other tiers: no auth

- **`get_flask_proxy_block(port)`**: Flask reverse proxy configuration
  - Proxy to `http://127.0.0.1:{port}`
  - Sets proxy headers (Host, X-Real-IP, X-Forwarded-For, X-Forwarded-Proto)
  - 50MB max body size for file uploads

- **`detect_flask_ports(project_name)`**: Detects actual Flask ports from deployed app files
  - Reads `{project_name}_{tier}.py` files
  - Extracts port number from `port = XXXX` pattern
  - Falls back to defaults if files not found

**See also**: `hh/deploy/http/nginx_config_helpers.py` - All helper functions

### NGINX Static File Whitelist

**File**: `hh/deploy/http/nginx_whitelist.py`

Generates NGINX location blocks for static file serving:

**Process Flow**:

1. **Collect Static Directories**:
   - From `JS_WHITELIST`: adds `site/js/`
   - From `CSS_WHITELIST`: adds `site/css/`
   - From `MISC_WHITELIST`: adds `site/`, `site/css/`, or `site/js/` based on path
   - From `CONTEXT_WHITELIST`: adds context folders (e.g., `context/`, `planning/`)

2. **Generate Location Blocks**:
   - Always includes `/srv/images/{project_name}/` and `/srv/files/{project_name}/`
   - Generates location blocks for each static directory
   - Each block:
     - Maps URL path to filesystem alias
     - Sets `expires off` and `Cache-Control: no-cache, no-store, must-revalidate`
     - Prevents caching of static files

3. **Return Summary**:
   - Returns config string and summary counts (JS files, CSS files, misc files, context folders)

**Static File Locations**:
- `/site/js/` → `/srv/{project_name}/site/js/`
- `/site/css/` → `/srv/{project_name}/site/css/`
- `/site/` → `/srv/{project_name}/site/` (for misc files like favicon.ico)
- `/context/` → `/srv/{project_name}/context/` (for context documentation)
- `/srv/images/` → `/srv/images/{project_name}/` (for image storage)
- `/srv/files/` → `/srv/files/{project_name}/` (for file storage)

**See also**: `hh/deploy/http/nginx_whitelist.py` functions `generate_nginx_static_locations`, `_generate_location_blocks`

### NGINX Configuration Structure

**HTTP Configuration (Stage 1)**:
```
# Main site (Guest tier)
server {
    listen 80;
    server_name example.com www.example.com;
    # Security headers, rate limiting, static locations, Flask proxy
}

# Admin subdomain
server {
    listen 80;
    server_name admin.example.com;
    # HTTP Basic Auth, security headers, rate limiting, static locations, Flask proxy
}

# Panel subdomain
server {
    listen 80;
    server_name panel.example.com;
    # HTTP Basic Auth, security headers, rate limiting, static locations, Flask proxy
}
```

**HTTPS Configuration (Stage 2)**:
```
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name example.com www.example.com admin.example.com panel.example.com;
    return 301 https://$host$request_uri;
}

# Main site HTTPS (Guest tier)
server {
    listen 443 ssl http2;
    server_name example.com www.example.com;
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    # Security headers (including HSTS), rate limiting, static locations, Flask proxy
}

# Admin subdomain HTTPS
server {
    listen 443 ssl http2;
    server_name admin.example.com;
    # SSL certs, HTTP Basic Auth, security headers, rate limiting, static locations, Flask proxy
}

# Panel subdomain HTTPS
server {
    listen 443 ssl http2;
    server_name panel.example.com;
    # SSL certs, HTTP Basic Auth, security headers, rate limiting, static locations, Flask proxy
}
```

### Security Features

**Security Headers**:
- **X-Frame-Options**: `SAMEORIGIN` (prevents clickjacking)
- **X-Content-Type-Options**: `nosniff` (prevents MIME sniffing)
- **X-XSS-Protection**: `1; mode=block` (XSS protection)
- **Referrer-Policy**: `strict-origin-when-cross-origin`
- **Strict-Transport-Security** (HTTPS only): `max-age=31536000; includeSubDomains` (HSTS)

**Rate Limiting**:
- **General zone**: For main site (guest tier)
- **Admin zone**: For admin and panel subdomains
- **Burst**: 20 for general, 100 for admin
- **No delay**: Immediate enforcement

**Hidden File Blocking**:
- Blocks all hidden files (starting with `.`)
- **Exception**: Allows `.well-known/acme-challenge/` for Let's Encrypt certificate validation
- Prevents access to sensitive files like `.htpasswd`, `.env`, etc.

**HTTP Basic Authentication**:
- **Admin subdomain**: Uses `/var/www/.htpasswd_admin`
- **Panel subdomain**: Uses `/var/www/.htpasswd_panel`
- Credentials created during `install` command
- Main site (guest tier): No authentication

### Deployment Workflow

**Typical Deployment Sequence**:

1. **Initial Setup**: Run `install` command (creates users, .htpasswd files)
2. **Database Setup**: Run `init-db` and `add-db-users`
3. **Deploy Application**: Run `deploy` command (copies files, starts Flask)
4. **HTTP Deployment (Stage 1)**: Run `http-deploy -domain example.com`
   - Creates HTTP-only configuration
   - Site accessible via HTTP
5. **SSL Certificate Installation**: Install SSL certificates (e.g., via Let's Encrypt)
   - Outside scope of Henhouse (use certbot or similar)
6. **SSL Deployment (Stage 2)**: Run `http-deploy-ssl -domain example.com`
   - Upgrades to HTTPS
   - Adds HTTP-to-HTTPS redirect
   - Site accessible via HTTPS

**Monitoring**:
- Use `http-status` to check deployment status
- Shows active/available sites, SSL status, deployment stage
- Categorizes Henhouse vs manually configured sites

---

## 7. Maintenance Daemon

The maintenance daemon system consists of two distinct components with different deployment and access patterns:

- **`hh/deploy/maintenance/`**: Daemon management commands (start, stop, status) - stays in project folder, only accessible by human users or root tier
- **`hh/deploy/maint/`**: Maintenance tools and utilities - gets deployed to `/srv/{project_name}`, accessible by all agent tiers

### Architecture Overview

The maintenance daemon (`worker.py`) runs continuously in the background, monitoring the job queue and stale caches. It executes maintenance tools from the `maint/` folder, which are registered as maintenance backend tools and accessible to all agent tiers.

**Key Distinction**:
- **maintenance/**: Administrative commands for managing the daemon itself (start/stop/status) - privileged access only
- **maint/**: Operational tools that the daemon uses (cache refresh, job queue, orphan checks) - deployed and accessible to all tiers

### Maintenance Daemon Management (maintenance/)

**Directory**: `hh/deploy/maintenance/`

These commands manage the lifecycle of the maintenance daemon process. They remain in the project folder and are only accessible by human users or root tier agents.

#### Maintenance Worker

**File**: `hh/deploy/maintenance/worker.py`

The core daemon that runs continuously, monitoring and processing maintenance tasks:

**Key Features**:
- **Continuous Loop**: Runs indefinitely with configurable delay (default: 5 seconds)
- **Work Detection**: Checks for pending jobs and stale caches via `maintenance-jobs-status` command
- **Work Prioritization**: Processes pending jobs first (by priority), then stale cache refreshes
- **Job Queue Integration**: Updates job status (pending/running/done/error) via `update-maintenance-job`
- **Adaptive Sleep**: 0.5 second delay when work is done, full delay when idle
- **Heartbeat Logging**: Logs status every 15 minutes when idle
- **Graceful Shutdown**: Handles SIGINT/SIGTERM signals

**Work Cycle Flow**:

1. **Get Status**: Calls `maintenance-jobs-status` to check for work
2. **Build Work Docket**: Creates ordered list of tasks:
   - Pending jobs from `maintenance_jobs` table (by job_type)
   - Stale page cache refreshes
   - Stale image cache refreshes
   - Stale file cache refreshes
3. **Execute Tasks**: Runs each task via `maintenance_client.py`
4. **Handle Responses**: Updates job status for job queue items, logs results for cache refreshes
5. **Sleep**: Adaptive delay based on work status

**Logging**:
- **Location**: `/srv/{project_name}/logs/maintenance_{project_name}.log` (deployed) or `{project_root}/logs/maintenance_{project_name}.log` (local dev)
- **Level**: Configurable via `MAINTENANCE_LOG_LEVEL` environment variable (default: DEBUG)
- **Output**: Both stderr (terminal) and log file
- **Heartbeat**: Logs status every 15 minutes when idle

**Process Management**:
- **Deployed**: Runs as `{project_name}_root` user, script at `/srv/{project_name}/{project_name}_maintenance.py`
- **Local Dev**: Runs as current user, script at `{project_root}/hh/deploy/maintenance/worker.py`
- **Discovery**: Uses `maintenance_client.py` path resolution (deployed vs. local)

#### Maintenance Start

**File**: `hh/deploy/maintenance/maintenance_start.py`

Starts the maintenance daemon process:

**Prerequisites**:
- Must run with sudo/root privileges on deployed systems
- Requires ProcessManager (psutil) for cross-platform process management

**Process Flow**:

1. **Check Privileges**: Validates sudo access on deployed systems
2. **Find Worker**: Locates worker script (deployed vs. local)
3. **Stop Existing**: Kills any running maintenance processes (acts like restart)
4. **Start Daemon**: 
   - **Deployed**: Runs as `{project_name}_root` user in `/srv/{project_name}`
   - **Local**: Runs as current user in project root
   - Uses `start_background_process()` with log file redirection
5. **Verify**: Waits 1 second, then checks process list to confirm startup

**Returns**: Status dict with `status` (started/failed/error), `pids`, `log_file`, `deployed`, `user`

#### Maintenance Stop

**File**: `hh/deploy/maintenance/maintenance_stop.py`

Stops the maintenance daemon process:

**Process Flow**:

1. **Find Processes**: Uses process filter (`{project_name}_maintenance.py` or `worker.py`)
2. **Kill Processes**: Sends termination signal to each running process
3. **Return Status**: Reports which PIDs were stopped

**Returns**: Status dict with `status` (stopped/not_running/error), `pids` (list of killed PIDs)

#### Maintenance Status

**File**: `hh/deploy/maintenance/maintenance_status.py`

Checks the status of the maintenance daemon:

**Process Flow**:

1. **Check Worker Exists**: Verifies worker script exists
2. **Find Processes**: Lists running processes matching filter
3. **Return Status**: Reports running/stopped/not_found

**Returns**: Status dict with `status` (running/stopped/not_found/error), `pids`, `deployed`, `worker_path`

### Maintenance Tools (maint/)

**Directory**: `hh/deploy/maint/`

These tools are deployed to `/srv/{project_name}` and are accessible by all agent tiers. They are registered as maintenance backend tools and can be called by the daemon or manually.

#### Maintenance Client

**File**: `hh/deploy/maint/maintenance_client.py`

Entry point for all maintenance commands. Acts as a thin wrapper around Gateway dispatch:

**Features**:
- UTF-8 encoding configuration for stdout/stderr
- Dispatches commands via Gateway with `"maintenance"` backend
- Returns JSON response to stdout
- Exit code: 1 if error, 0 if success

**Usage**: `python maintenance_client.py <command> [args...]`

#### Maintenance Jobs Status

**File**: `hh/deploy/maint/maintenance_jobs_status.py`

Checks what maintenance work needs to be done:

**Action** (`maintenance_jobs_status_action`):
- Counts stale pages (where `last_modified > cache_built_at` or `cache_built_at IS NULL`)
- Counts stale images (where `COALESCE(last_modified, uploaded) > cache_built_at` or `cache_built_at IS NULL`)
- Counts stale files (where `COALESCE(last_modified, uploaded) > cache_built_at` or `cache_built_at IS NULL`)
- Gets pending jobs by type from `maintenance_jobs` table (status='pending')
- Counts error jobs (status='error')
- Calculates `has_work` flag and `work_types` count

**Parser** (`maintenance_jobs_status_parser`):
- Renders table with stale counts, pending jobs, work status, error status
- Uses dynamic field types (work_available/no_work_available, job_errors/no_job_errors)

**Registered as**: Maintenance tool (accessible via maintenance backend)

#### Cache Refresh Tools

Three similar tools for refreshing stale caches:

**Files**:
- `hh/deploy/maint/page_cache_refresh.py`
- `hh/deploy/maint/image_cache_refresh.py`
- `hh/deploy/maint/file_cache_refresh.py`

**Common Pattern**:

1. **Action**:
   - Fetches one stale item ID (by `last_modified` DESC)
   - If none found, returns "no work" response
   - If found, rebuilds cache for that item:
     - **Pages**: Calls `get_page(id).show_page()` to rebuild cache
     - **Images**: Calls `get_image(id).show_image()` to rebuild cache
     - **Files**: Calls `get_file(id).get_usage_data()` to rebuild cache
   - Returns processed status, error (if any), and remaining count

2. **Parser**:
   - Renders table with item ID, refresh status, error (if any), remaining count
   - Uses conditional rows (only shows remaining if > 0)

**Registered as**: Maintenance tools (accessible via maintenance backend)

#### Job Queue Management

**File**: `hh/deploy/maint/job_queue.py`

Core functions for managing the maintenance job queue:

**Key Functions**:

- **`claim_next_maintenance_job(job_type)`**: Claims next pending job of specified type
  - Uses optimistic locking (tries up to 5 times)
  - Updates status to 'running', increments attempts, sets started_at
  - Falls back to running jobs if no pending jobs found
  - Returns deserialized job dict (with `payload` and `progress` parsed from JSON)

- **`update_maintenance_job(job_id, status, progress, error_message)`**: Updates job status
  - Updates `progress_json`, `error_message`, `status`
  - Sets `started_at` if status='running'
  - Sets `completed_at` if status in {'done', 'error'}
  - Always increments `attempts` and updates `updated_at`

**Job Status Flow**:
- **pending** → **running** (when claimed)
- **running** → **pending** (if still in progress, with updated progress)
- **running** → **done** (when complete)
- **running** → **error** (on failure)

#### Update Maintenance Job

**File**: `hh/deploy/maint/update_maintenance_job.py`

Command interface for updating maintenance job status:

**Action** (`update_maintenance_job_action`):
- Accepts: `job_id`, `status`, `progress` (JSON string), `error_message`
- Updates job in database via `job_queue.update_maintenance_job()`
- Returns update status

**Parser** (`update_maintenance_job_parser`):
- Renders table with job_id, status, update success/failure

**Registered as**: Maintenance tool (accessible via maintenance backend)

#### Orphan Checks

**File**: `hh/deploy/maint/orphan_checks.py`

Checks for orphaned database records (broken foreign key relationships):

**Checks Performed**:

1. **Orphan Pages**: Pages with missing parent pages
2. **Orphan Link Sources**: Links whose source page is missing
3. **Orphan Link Targets**: Links whose target page is missing
4. **Orphan Image Pages**: Image links whose page is missing
5. **Orphan Image Targets**: Image links whose image is missing
6. **Orphan Image Group Pages**: Image groups pointing to missing pages
7. **Orphan Image Group Images**: Image groups pointing to missing images
8. **Orphan File Group Pages**: File groups pointing to missing pages
9. **Orphan File Group Files**: File groups pointing to missing files

**Action** (`orphan_check_action`):
- Runs all checks and returns counts and ID lists

**Parser** (`orphan_check_parser`):
- Renders table with counts and ID previews (first 20 IDs)
- Conditionally shows IDs column only if orphans found

**Registered as**: Maintenance tool (accessible via maintenance backend)

#### Maintenance Ping

**File**: `hh/deploy/maint/maintenance_ping.py`

Testing and debugging tool for maintenance commands:

**Features**:
- Runs maintenance commands in loops (default: 5 cycles)
- Parses JSON responses
- Builds error summaries (by type, duplicates)
- Builds debug summaries (nested tree: module → file → function with timestamps)
- Retries with `-log` flag on errors
- Prints formatted summaries

**Usage**: `python maintenance_ping.py <command> [args...] [--cycles N] [--delay SECONDS]`

#### Additional Utilities

**Files**:
- `hh/deploy/maint/regex_text.py`: Text processing utilities (regex operations)
- `hh/deploy/maint/config_labels.py`: Configuration labels for maintenance tools

### Deployment Integration

**Deploy Whitelist**: The `maint/` folder is whitelisted in `DEPLOY_WHITELIST`, so it survives deployment cleanup and is available in `/srv/{project_name}/hh/deploy/maint/`.

**Maintenance Worker Deployment**: During deployment, `worker.py` is copied to `/srv/{project_name}/{project_name}_maintenance.py` for execution.

**Maintenance Client Deployment**: `maintenance_client.py` is deployed to `/srv/{project_name}/maintenance_client.py` (top level) for easy access.

### Access Control

- **maintenance/** commands: Only accessible by human users or root tier (stays in project folder)
- **maint/** tools: Accessible by all agent tiers (deployed, registered as maintenance backend tools)

### Registration Pattern

Maintenance tools register themselves using:

```python
from hh.gateway.registry.maintenance import register_maintenance_tool
from hh.gateway.registry.registry import register_action, register_command, register_parser

@register_action("tool_name")
@register_command("tool_name")
def tool_name_action() -> bool:
    # Action logic
    pass

@register_parser("tool_name")
def tool_name_parser() -> bool:
    # Parser logic
    pass

register_maintenance_tool("tool_name")
```

This makes them accessible via the maintenance backend and discoverable by the daemon.

---

## 8. Git Operations

The git operations system provides commands for syncing code between development environments (laptop) and deployment servers. It supports pulling the latest code from remote repositories and pushing changes via stage branches.

### Architecture Overview

The git system uses a stage branch workflow:
- **Pull**: Hard resets local repository to `origin/{project_name}` for clean state
- **Push**: Creates timestamped stage branches with commit messages for syncing changes
- **Project Detection**: Automatically detects project name and repository root
- **Cache Management**: Automatically clears caches after pull operations

### Pull Project

**File**: `hh/deploy/git/pull_project.py`

Pulls the latest code from remote and resets to a clean state:

**Command**: `pull_project`

**Process Flow**:

1. **Detect Project Context**:
   - Uses `detect_project_context()` to find project name and repository root
   - Validates that repository root exists

2. **Check Current Branch**:
   - Runs `git branch --show-current` to determine current branch
   - Logs current branch name

3. **Switch to Project Branch**:
   - If not already on `{project_name}` branch, switches to it
   - Uses `git checkout {project_name}`
   - Tracks whether branch switch occurred

4. **Fetch from Remote**:
   - Runs `git fetch origin` to get latest remote refs
   - Does not merge or modify working directory yet

5. **Hard Reset to Remote**:
   - Runs `git reset --hard origin/{project_name}`
   - **Discards all local changes** (clean state)
   - Ensures local matches remote exactly

6. **Get Git Information**:
   - **Short Hash**: `git rev-parse --short HEAD` (7 characters)
   - **Commit Message**: `git log -1 --pretty=format:%s` (first line only)
   - **Time Ago**: `git log -1 --pretty=format:%ar` (relative time)

7. **Clear All Caches**:
   - Calls `clean_all_caches()` from cache cleanup registry
   - Clears registered caches, `__pycache__` directories, `.pyc` files
   - Collects list of cleared cache items for reporting

**Returns**: Status dict with:
- `project_name`: Project name
- `project_path`: Repository root path
- `current_branch`: Branch name before switch
- `branch_switched`: Boolean indicating if branch switch occurred
- `short_hash`: 7-character commit hash
- `commit_message`: First line of commit message
- `time_ago`: Relative time string (e.g., "2 hours ago")
- `cache_cleared`: List of cleared cache file/directory paths
- `status`: "pulled"

**Parser**: `render_pull_project.py` renders table with project info, branch status, commit details, and cache clearing results.

**Use Cases**:
- Syncing server code to match remote after deployment
- Recovering to a known good state from remote
- Pulling latest changes from another development machine
- Resetting local changes to match remote exactly

### Push Project

**File**: `hh/deploy/git/push_project.py`

Pushes local changes to remote via a stage branch:

**Command**: `push_project --message "your message"`

**Prerequisites**:
- **Message Required**: `--message` argument is mandatory
- Must be run from a git repository (validates `.git` directory exists)

**Process Flow**:

1. **Validate Message**:
   - Checks that `--message` argument is provided and non-empty
   - Returns error if message is missing

2. **Detect Project Context**:
   - Uses `detect_project_context()` to find project name and repository root
   - Validates that repository root is a git repository

3. **Create Stage Signal File**:
   - Writes message to `{repo_root}/stage` file
   - Used as a signal file for deployment processes
   - UTF-8 encoded with Unix line endings

4. **Build Stage Branch Name**:
   - Format: `stage/linux/{timestamp}-{sanitized_message}`
   - **Timestamp**: `YYYY-MM-DD-HHMMSS` (UTC)
   - **Message Sanitization**: Converts to safe git ref slug:
     - Unicode normalize and ASCII fold
     - Lowercase
     - Replace whitespace with hyphens
     - Remove disallowed characters
     - Collapse multiple hyphens
   - Example: `stage/linux/2024-01-15-143022-deploy-fix`

5. **Create/Checkout Branch**:
   - Uses `git checkout -B {branch}` to create or reset branch
   - Forces branch to current HEAD state

6. **Stage All Changes**:
   - Runs `git add -A` to stage all changes (including deletions)
   - Captures all modifications in working directory

7. **Detect Changes**:
   - Runs `git status --porcelain` to check if anything is staged
   - If no changes, uses `--allow-empty` flag for commit

8. **Create Commit**:
   - **Title**: `Stage: {message}`
   - **Body/Trailers**:
     ```
     Stage-Done: true
     Env: linux
     Hook: {message}
     ```
   - Uses `--allow-empty` if no changes detected (allows empty commits)

9. **Push to Remote**:
   - Runs `git push -u origin {branch}` to push and set upstream
   - Creates branch on remote if it doesn't exist

**Returns**: Status dict with:
- `project_name`: Project name
- `project_path`: Repository root path
- `message`: Original push message
- `branch`: Created stage branch name
- `title`: Commit title
- `has_changes`: Boolean indicating if changes were committed
- `stage_file_created`: Boolean (always true)
- `status`: "pushed"

**Parser**: `render_push_project.py` renders table with project info, message, branch name, change status, and stage file creation.

**Use Cases**:
- Pushing development changes from laptop to server
- Creating deployment snapshots with descriptive messages
- Syncing code between development environments
- Creating recovery points before major changes

### Stage Branch Workflow

The stage branch system provides a structured way to sync code:

**Branch Naming Convention**:
- Format: `stage/{environment}/{timestamp}-{description}`
- **Environment**: Currently hardcoded to `"linux"` (for server deployment)
- **Timestamp**: UTC timestamp for chronological ordering
- **Description**: Sanitized message from user

**Commit Structure**:
- **Title**: Descriptive message prefixed with "Stage: "
- **Trailers**: Structured metadata for automation:
  - `Stage-Done: true` - Marks commit as stage operation
  - `Env: linux` - Deployment environment
  - `Hook: {message}` - Original user message

**Stage Signal File**:
- Created at `{repo_root}/stage` with the push message
- Used by deployment processes to detect stage operations
- UTF-8 encoded, single line

### Helper Functions

**File**: `hh/deploy/git/push_project.py`

- **`run_git(repo_path, args, check=True)`**: Executes git commands with proper error handling
  - Uses `git -C {repo_path}` for directory context
  - Returns `(exit_code, stdout, stderr)` tuple
  - Raises `RuntimeError` if `check=True` and command fails

- **`sanitize_for_ref(text)`**: Converts arbitrary text to safe git ref slug
  - Unicode normalization (NFKD)
  - ASCII folding
  - Lowercase conversion
  - Whitespace to hyphens
  - Character sanitization
  - Hyphen collapsing

- **`build_stage_names(env, hook_id, desc)`**: Builds stage branch name, tag, and title
  - Generates timestamp
  - Sanitizes hook_id and description
  - Constructs branch name and commit title

- **`write_stage_signal(repo_path, text)`**: Writes stage signal file
  - Creates `{repo_path}/stage` file
  - UTF-8 encoding with Unix line endings

### Integration with Deployment

**Pull Integration**:
- Used during deployment recovery operations
- Ensures server code matches remote exactly
- Clears caches to prevent stale state issues

**Push Integration**:
- Used to sync development changes to server
- Stage branches can be checked out on server for deployment
- Stage signal file can trigger automated deployment processes

### Configuration Labels

**File**: `hh/deploy/git/config_labels.py`

Defines render labels for CLI output:
- Git repository labels
- Pull project status labels (branch, hash, message, time)
- Push project status labels (message, branch, changes, stage file)

### Error Handling

Both commands use Gateway error reporting:
- **Pull**: Reports errors for branch switch failures, fetch failures, reset failures, cache cleanup failures
- **Push**: Reports errors for missing message, invalid repository, git command failures

All git operations use `run_git()` with `check=True` by default, which raises exceptions on failure for proper error propagation.

---

## 9. Cache Management

The cache management system provides a centralized registry for cleaning various caches throughout the Henhouse system. It uses a decorator-based registration pattern that allows any module to register its own cache cleanup function.

### Cache Cleanup Registry

**File**: `hh/deploy/cache/cache_cleanup_registry.py`

The registry system scans the codebase for `@register_cache_cleanup` decorators and provides centralized cache cleanup functionality.

#### Key Functions

- **`register_cache_cleanup(cache_name, cache_dir=None)`**: Decorator for registering cache cleanup methods
  - `cache_name`: Unique identifier for the cache (e.g., 'page_classes', 'tp_decorators')
  - `cache_dir`: Optional relative path to cache directory (e.g., 'hh/page/cache') - used for permission management
- **`discover_cache_cleanups()`**: Scans codebase and loads all registered cleanup functions
- **`clean_cache(cache_name)`**: Cleans a specific cache by name
- **`clean_all_caches()`**: Cleans all registered caches and aggregates results
- **`get_cache_directories()`**: Returns list of all cache directory paths (used by deployment for permission setting)
- **`get_deployment_paths()`**: Returns both project root and `/srv/{project_name}` paths for cleaning

#### Registration Pattern

Modules register their cleanup functions using the decorator:

```python
from hh.deploy.cache.cache_cleanup_registry import register_cache_cleanup

@register_cache_cleanup('page_classes', cache_dir='hh/page/cache')
def cleanup_page_class_cache():
    # Clean up page class cache
    cache_file.unlink()
    _page_class_registry.clear()
    return {'success': True, 'cache_files': 1, 'cache_files_list': ['hh/page/cache/page-classes.json']}
```

#### Discovery Process

1. Scans `hh/` directory tree for files containing `@register_cache_cleanup`
2. Imports those modules to trigger registration
3. Populates global `_cleanup_registry` dictionary
4. Tracks cache directories in `_cache_dir_registry` for permission management

### Clear Cache Command

**File**: `hh/deploy/cache/clear_cache.py`

The `clear_cache` command uses the registry to clean all registered caches:

- Calls `clean_all_caches()` to execute all registered cleanup functions
- Aggregates results (pycache_dirs, pyc_files, cache_files, cache_dirs)
- Returns detailed results including success/failure counts and item lists

**See also**: `hh/deploy/cache/clear_cache.py` function `clear_cache`

### Built-in Cleanups

The system includes a built-in cleanup for Python bytecode:
- **`cleanup_python_bytecode()`**: Removes all `__pycache__` directories and `.pyc` files
- Cleans both project root and `/srv/{project_name}` deployment paths
- Registered as `'python_bytecode'` cache (no cache_dir since it's system-wide)

### Integration with Deployment

- Cache directories are discovered via `get_cache_directories()` during deployment
- Used to set proper permissions on cache directories in `/srv/{project_name}`
- Both project root and deployment paths are cleaned during cache operations

---

## 10. Configuration System

The configuration system manages whitelists, blacklists, and application settings that control what gets deployed and how the system behaves.

### Configuration Files Location

**Directory**: `hh/deploy/conf/`

All configuration files are whitelisted to survive deployment cleanup (see [File Deployment](#4-file-deployment)).

### Deploy Whitelist

**File**: `hh/deploy/conf/deploy_whitelist.py`

Defines what stays in the `hh/deploy/` folder after deployment cleanup:

- **`DEPLOY_WHITELIST`**: Items preserved in deploy folder:
  - `'cache'` - Cache cleanup registry and utilities
  - `'conf'` - Configuration whitelists (self-preserving)
  - `'maint'` - Maintenance helpers shared with deployment scripts
  - `'utils.py'` - General deployment utilities
- **`FLASK_APP_SOURCE`**: Path to Flask app source (`hh/deploy/flask/app.py`)
- **`MAINTENANCE_APP_SOURCE`**: Path to maintenance worker (`hh/deploy/maintenance/worker.py`)
- **`EXTRA_DEPLOY_FILES`**: Additional files deployed to `/srv/{project_name}`:
  - `hh/deploy/flask/http_client.py`
  - `hh/deploy/flask/mcp_client.py`
  - `hh/deploy/maint/maintenance_client.py`

### Context Whitelist/Blacklist

**Files**: `hh/deploy/conf/context_whitelist.py`, `hh/deploy/conf/context_blacklist.py`

Controls what gets deployed for agent visibility (context documentation, planning docs, source code):

- **`CONTEXT_WHITELIST`**: Folders/files included in deployment:
  - `'context'`, `'planning'`, `'hh'` - Documentation and source
  - Top-level scripts: `hen.py`, `hen.ps1`, `stage.py`, `stage.ps1`, `mcp_wrapper.py`
  - Project files: `README.md`, `LICENSE`, `requirements.txt`
- **`CONTEXT_BLACKLIST`**: Patterns excluded from deployment:
  - `.git`, `__pycache__`, `*.pyc`, `.pytest_cache`
  - `node_modules`, `.env`, `*.log`
  - Cache JSON files: `*-reg.json`, `*.cycle.json`, `cache.json`, `*.cache.json`

### File Type Whitelists

#### Python Whitelist

**File**: `hh/deploy/conf/py_whitelist.py`

- **`PY_WHITELIST`**: Python files deployed to `/srv/{project_name}/site/py/`
- Currently includes: `hh/deploy/site/infographic/infographic.py`

#### JavaScript Whitelist

**File**: `hh/deploy/conf/js_whitelist.py`

- **`JS_ALWAYS_INCLUDE`**: JavaScript files included on every page:
  - `seed.js`, `rpc-client.js`, `app.js`
- **`JS_WHITELIST`**: All JavaScript files that can be included via `gateway.add_js_link()`
  - Includes overlay system files, page data files, infographic files
  - Files deployed flat to `site/js/` (overlay subfolder files flattened)

#### CSS Whitelist

**File**: `hh/deploy/conf/css_whitelist.py`

- **`CSS_ALWAYS_INCLUDE`**: CSS files included on every page:
  - `site.css`, `ansi-colors.css`, `tables.css`, `pygments.css`, `overlay.css`
- **`CSS_WHITELIST`**: All CSS files that can be included via `gateway.add_css_link()`
  - Includes tier-specific CSS files (site-guest.css, site-verified.css, site-admin.css, site-root.css)
  - Infographic CSS files

#### Miscellaneous Whitelist

**File**: `hh/deploy/conf/misc_whitelist.py`

- Additional files and patterns for deployment

### Application Actions

**File**: `hh/deploy/conf/application_actions.py`

Defines application action links for admin/root tier CRUD operations:

- **`populate_application_action_links(page_id=None)`**: Populates action links in gateway response
- Groups are created explicitly with names, then actions added to groups
- Actions have DOM IDs for JavaScript event handlers (no hrefs)
- Used for testing and development UI features

### Other Configuration Files

- **`deploy_whitelist.py`**: NGINX deployment whitelist configuration
- **`site_links.py`**: Site navigation links configuration
- **`user_info.py`**: User information configuration
- **`user_account_suffixes.py`**: Defines `HENHOUSE_TIERS` constant

### Deployment Utilities

**File**: `hh/deploy/utils.py`

Core utility function used throughout deployment:

- **`detect_project_context()`**: Detects project name and root directory
  - Walks up directory tree from current working directory
  - Looks for `hh/` directory to identify project root
  - Returns tuple: `(project_name, project_root_path)`
  - Used by cache cleanup, deployment scripts, and other utilities

---

## 11. User Management

The user management system provides comprehensive installation and uninstallation of the complete user infrastructure, with extensive safety checks to prevent accidental deletion of non-project users.

### Uninstall Command

**File**: `hh/deploy/users/uninstall.py`

The `uninstall` command safely removes all project users, groups, and deployment infrastructure:

**Prerequisites**:
- Must run with sudo/root privileges
- Automatically detects project name and owner
- Discovers `hen` script name from tier user directories

**Optional Arguments**:
- `-remove_user <user1,user2,...>`: Additional users to remove beyond the 4 tier users

### Uninstall Process Flow

1. **User Removal** (with safety validation):
   - Validates each user before deletion (see Safety Checks below)
   - Changes home directory ownership back to user before deletion
   - Removes users with `userdel -r` (removes home directory)
   - Handles leftover home directories for non-existent users
   - Tracks which project users were actually removed

2. **Project Directory Removal**:
   - Only removes `/srv/{project_name}` if highest tier user doesn't exist
   - **Preserves**: `/srv/images/{project_name}` and `/srv/files/{project_name}` are left untouched
   - Safety check: Won't delete if highest tier user still exists

3. **Group Cleanup**:
   - Removes project owner from `{project_name}` group BEFORE deleting group
   - Deletes groups: `{project_name}`, `{project_name}_deploy`, `{project_name}_admin`

4. **Script Cleanup** (only if project users were removed):
   - **Human user (project owner)**: Removes `{hen_script_name}` and PATH modification from `.profile`
   - **Root user**: Removes `{hen_script_name}` and PATH modification from `.profile`
   - Safety check: Only cleans up if at least one project user was actually removed (prevents accidental deletion on second uninstall run)

5. **HTTP Basic Auth Cleanup**:
   - Removes users from `/var/www/.htpasswd_{admin_tier}` and `/var/www/.htpasswd_panel`
   - Uses `htpasswd -D` to delete users from files

6. **Project Group Ownership Reset**:
   - Resets project folder group ownership to project owner's primary group
   - Deletes all project groups

**See also**: `hh/deploy/users/uninstall.py` function `uninstall`

### Safety Validation System

The uninstall process includes extensive safety checks to prevent accidental deletion of non-project users:

#### User Validation (`validate_user_for_deletion`)

Validates users before deletion:

1. **System User Check**: UID must be < 1000 (system users only)
2. **Shell Check**: Shell must be `/bin/bash`
3. **Home Directory Check**: Home must be `/home/{user}`
4. **Naming Pattern Check**: User must match `{project_name}_*` pattern

#### Directory Validation (`validate_user_directory_for_deletion`)

Validates leftover home directories before deletion:

1. **Existence Check**: Directory must exist
2. **Path Check**: Must be under `/home/`
3. **Ownership Check**: Must be owned by expected user (UID match)
4. **Structure Check**: Must have expected agent user structure:
   - `.profile` (custom profile)
   - `gateway.py` (gateway script)
   - `hen` or custom name (hen wrapper)
   - `.ssh` directory (with only expected files: `id_rsa`, `id_rsa.pub`, `authorized_keys`)
   - `.{project_name}.cnf` (config file)
   - No unexpected non-hidden files

**Safety Philosophy**: The system is designed to be conservative - it will skip deletion rather than risk deleting something that doesn't match the expected project user pattern.

### Script Name Discovery

**Function**: `discover_script_names(project_name)`

Automatically discovers the `hen` script name used during installation:

- Checks first tier user's home directory
- Looks for executable files containing `'python3 gateway'`
- Defaults to `'hen'` if not found
- Used during uninstall to clean up the correct script names

### Integration Points

- **Project Detection**: Uses `detect_project_context()` from `hh/deploy/utils.py`
- **User Detection**: Uses `gateway.os.get_user_by_name()` and `gateway.os.user_exists()`
- **Group Detection**: Uses `gateway.os.group_exists()`
- **File Operations**: Uses `gateway.files.chown()`, `gateway.files.chmod()` for permission management
- **Cache Cleanup**: Calls `clean_all_caches()` at end of both install and uninstall to prevent permission issues

---

## 12. Site Assets Deployment

The site folder contains all static web assets (CSS, JavaScript, favicons, etc.) that are deployed to `/srv/{project_name}/site/` and served by the web application.

### Directory Structure

**Directory**: `hh/deploy/site/`

**Subdirectories**:
- **`css/`**: Stylesheets (tier-specific color schemes, layout, syntax highlighting)
- **`js/`**: JavaScript files (compiled from TypeScript source)
- **`infographic/`**: Standalone infographic module (optional, project-specific)

**Top-level files**:
- Favicon files (`.ico`, `.png` variants)
- `site.webmanifest` (PWA manifest)
- `ajaxloading.gif` (loading animation)

### CSS Stylesheets

**Directory**: `hh/deploy/site/css/`

The CSS system uses a separation of concerns approach:

#### Base Stylesheet

**File**: `site.css`
- **Purpose**: Layout, structure, and formatting (no colors)
- **Content**: Box model, typography, container structure, link base styles, component layouts
- **Philosophy**: Defines *how* things are laid out, not *what* they look like

#### Tier-Specific Color Schemes

Each user tier has its own color theme stylesheet:

- **`site-guest.css`**: Dark theme with blue accents (public/guest tier)
- **`site-verified.css`**: Color scheme for verified tier
- **`site-admin.css`**: Orange/amber theme (admin tier)
- **`site-root.css`**: Color scheme for root tier

**Color Organization**:
- Colors are defined in tier-specific files, not hardcoded in base styles
- Each tier file defines CSS variables and color values for:
  - Body background and text colors
  - Link colors (normal, hover, visited)
  - Container backgrounds and borders
  - Heading colors
  - Status box colors
  - Button colors
  - Border colors
- This allows visual identification of which portal/tier you're logged into

**Example Structure**:
```css
/* site-guest.css - Dark theme color scheme */
body {
    color: #d4d4d4;
    background: #0d1117;
}
a {
    color: #79c0ff;  /* Subdued blue theme */
}
.container {
    background: #161b22;
    border: 1px solid #30363d;
}
```

#### Supporting Stylesheets

**Always Included** (via `CSS_ALWAYS_INCLUDE`):
- **`ansi-colors.css`**: ANSI terminal color codes for code output
- **`tables.css`**: Table styling and formatting
- **`pygments.css`**: Syntax highlighting for code blocks
- **`overlay.css`**: Overlay/modal dialog styling

**Whitelisting**: All CSS files are whitelisted in `hh/deploy/conf/css_whitelist.py`:
- `CSS_ALWAYS_INCLUDE`: Files loaded on every page
- `CSS_WHITELIST`: All available CSS files (can be included via `gateway.add_css_link()`)

### JavaScript Files

**Directory**: `hh/deploy/site/js/`

**Note**: JavaScript files in this directory are compiled from TypeScript source. See TypeScript documentation in context files for development details.

**Structure**:
- Main application files (`app.js`, `page-manager.js`, `rpc-client.js`)
- Page data handlers (`work-page-data.js`, `mcp-request-page-data.js`, etc.)
- Overlay system (`overlay/` subdirectory)
- Utility files (`debug-helper.js`, `upload-handler.js`, `seed.js`)

**Whitelisting**: JavaScript files are whitelisted in `hh/deploy/conf/js_whitelist.py` and deployed to `/srv/{project_name}/site/js/`.

### Favicon and Web Assets

**Top-level files** in `hh/deploy/site/`:

- **`favicon.ico`**: Main favicon (15KB)
- **`favicon-16x16.png`**: 16x16 PNG favicon
- **`favicon-32x32.png`**: 32x32 PNG favicon
- **`apple-touch-icon.png`**: iOS home screen icon (9KB)
- **`android-chrome-192x192.png`**: Android icon 192x192 (10KB)
- **`android-chrome-512x512.png`**: Android icon 512x512 (35KB)
- **`site.webmanifest`**: PWA manifest file (defines icons, theme colors)
- **`ajaxloading.gif`**: Loading animation (404B)

**Whitelisting**: All misc files are whitelisted in `hh/deploy/conf/misc_whitelist.py` and deployed to `/srv/{project_name}/site/` (top level).

### Infographic Module

**Directory**: `hh/deploy/site/infographic/`

**Note**: This is a standalone, project-specific module for creating flowcharts and diagrams. It's currently used for Henhouse's self-documentation but is not part of the core system.

**Purpose**: Demonstrates how to add custom modules to the site deployment:
1. Add files to `hh/deploy/site/infographic/`
2. Whitelist CSS/JS files in respective whitelists
3. Files are automatically deployed with the rest of the site

**Status**: Not documented in detail - project-specific customization example.

### Deployment Integration

**Deploy Script Integration** (`hh/deploy/srv/deploy.py`):

The deploy script handles site folder deployment:

1. **Site Directory Setup**:
   - Creates `/srv/{project_name}/site/` directory
   - Clears existing site directory if present

2. **JavaScript Deployment**:
   - Reads `JS_WHITELIST` from `hh/deploy/conf/js_whitelist.py`
   - Copies whitelisted JS files to `site/js/`
   - Preserves subdirectory structure (e.g., `overlay/`)

3. **CSS Deployment**:
   - Reads `CSS_WHITELIST` from `hh/deploy/conf/css_whitelist.py`
   - Copies whitelisted CSS files to `site/css/`

4. **Python File Deployment**:
   - Reads `PY_WHITELIST` from `hh/deploy/conf/py_whitelist.py`
   - Copies whitelisted Python files to `site/py/` (if any)

5. **Miscellaneous File Deployment**:
   - Reads `MISC_WHITELIST` from `hh/deploy/conf/misc_whitelist.py`
   - Copies whitelisted files to `site/` (top level)
   - Handles both files and directories

**Deployment Statistics**: The deploy script logs counts of deployed items (JS, CSS, PY, MISC) for verification.

### File Whitelisting System

All site assets are controlled by whitelist files in `hh/deploy/conf/`:

- **`css_whitelist.py`**: Defines `CSS_ALWAYS_INCLUDE` and `CSS_WHITELIST`
- **`js_whitelist.py`**: Defines `JS_WHITELIST` and `JS_ALWAYS_INCLUDE`
- **`py_whitelist.py`**: Defines `PY_WHITELIST` (if Python files are needed)
- **`misc_whitelist.py`**: Defines `MISC_WHITELIST` for top-level files

**Path Format**: All paths in whitelists are relative to project root (above `hh/` folder).

---

## 13. Deployment Workflows

The complete deployment workflow ties together all the individual components into repeatable, automated processes for syncing code between development and production environments.

### Standard Deployment Workflow

**Repeatable Deployment Process**:

Once the initial setup is complete (installation, database initialization, HTTP configuration), the standard workflow is:

1. **Pull Latest Code**:
   ```bash
   hen pull_project
   ```
   - Fetches latest from remote
   - Hard resets to `origin/{project_name}`
   - Clears all caches
   - Ensures clean state

2. **Deploy Everything**:
   ```bash
   sudo hen deploy
   ```
   - Stops running daemons (Flask, maintenance)
   - Copies all whitelisted files to `/srv/{project_name}`
   - Cleans deploy folder (preserves whitelisted items)
   - Sets permissions
   - Restarts daemons
   - Clears registry cache

**Result**: Fresh instance of latest code running on server.

**Key Point**: After initial setup, you never need to run installation, database setup, or HTTP configuration again. The repeatable workflow is just `pull_project` → `sudo hen deploy`.

### Rollback Workflow

**Recovering to Previous Stable Point**:

If you need to rollback to a previous commit:

1. **Reset to Specific Commit**:
   ```bash
   git reset --hard {commit_hash}
   ```
   - Replace `{commit_hash}` with the hash of the stable commit
   - Can find hash via `git log` or GitHub interface

2. **Deploy Rolled-Back Version**:
   ```bash
   sudo hen deploy
   ```
   - Deploys the rolled-back code state
   - All services restart with previous version

3. **Verify and Document** (Optional):
   ```bash
   hen push_project --message "emergency revert - {description}"
   ```
   - Creates stage branch documenting the rollback
   - Useful for tracking what was reverted and why

**Result**: Server running previous stable version.

### Stage Branch Recovery Workflow

**Using Stage Branches for Recovery**:

Stage branches provide a mechanism for recovering and referencing previous working states:

1. **Create Stage Branch from Server**:
   ```bash
   hen push_project --message "emergency revert - {description}"
   ```
   - Creates timestamped stage branch: `stage/linux/{timestamp}-{description}`
   - Pushes current server state to remote
   - Creates `stage` signal file in repository

2. **Pull Stage Branch on Laptop**:
   ```bash
   hen pull_project
   ```
   - Or manually: `git checkout stage/linux/{timestamp}-{description}`
   - Extracts the stage branch to local repository

3. **Access Stage Folder**:
   - After pull, `{repo_root}/stage` file contains the recovery message
   - Can use this to:
     - **Manual Recovery**: Review files in that commit, copy specific files back
     - **Agent Recovery**: Point agent to stage folder: "Look in the stage folder, see the previous working version that you forgot how it worked. I've recovered a copy for you."
     - **Interactive Recovery**: Use git's interactive tools to selectively restore files

4. **Selective File Recovery** (Optional):
   ```bash
   git checkout stage/linux/{timestamp}-{description} -- {file_path}
   ```
   - Restores specific files from stage branch
   - Allows granular recovery without full rollback

**Result**: Previous working state available for reference and recovery.

### Development-to-Production Sync Workflow

**Syncing Changes from Laptop to Server**:

1. **On Laptop - Push Changes**:
   ```bash
   hen push_project --message "deploy fix for X"
   ```
   - Creates stage branch with descriptive message
   - Pushes all local changes to remote

2. **On Server - Pull and Deploy**:
   ```bash
   hen pull_project
   sudo hen deploy
   ```
   - Pulls the stage branch (or merge it into main branch first)
   - Deploys the changes

**Result**: Changes synced from development to production.

### Complete Workflow Summary

**Initial Setup** (One-time):
1. `sudo hen install` - Create users, groups, SSH keys, git repo
2. `sudo hen init_db` - Initialize databases
3. `sudo hen add_db_users` - Create database users
4. `sudo hen http_deploy` - Configure NGINX (HTTP)
5. `sudo hen http_deploy_ssl` - Configure NGINX (HTTPS, optional)
6. `sudo hen deploy` - Deploy initial code

**Ongoing Operations** (Repeatable):
- **Standard Deploy**: `hen pull_project` → `sudo hen deploy`
- **Rollback**: `git reset --hard {hash}` → `sudo hen deploy`
- **Recovery**: `hen push_project --message "..."` → `hen pull_project` → review stage folder
- **Development Sync**: `hen push_project --message "..."` (laptop) → `hen pull_project` + `sudo hen deploy` (server)

**Key Benefits**:
- **Repeatable**: Same process every time
- **Reversible**: Easy rollback to any commit
- **Traceable**: Stage branches document recovery points
- **Recoverable**: Stage folder provides reference for agents/humans
- **Simple**: After setup, only two commands needed for normal deployment

### Integration Points

All workflows integrate with:

- **Git Operations**: `pull_project`, `push_project` for code sync
- **File Deployment**: `deploy` script for copying files
- **Service Management**: Automatic daemon restart (Flask, maintenance)
- **Cache Management**: Automatic cache clearing on pull
- **Database**: No database changes needed for code deployments
- **HTTP/NGINX**: No reconfiguration needed for code deployments

**See Also**:
- [Git Operations](#8-git-operations) for pull/push details
- [File Deployment](#4-file-deployment) for deploy script details
- [Maintenance Daemon](#7-maintenance-daemon) for background processing
- [Flask Application Management](#5-flask-application-management) for web services

