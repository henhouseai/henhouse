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

---

---

---


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

