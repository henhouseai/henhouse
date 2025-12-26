# Henhouse Deployment System Overview

- Henhouse deployment system is a comprehensive, automated infrastructure
- built around a **"set it up once, deploy repeatedly"** philosophy
- provides unified deployment and maintenance for multi-tier web applications

## Agent Quick Reference

This section provides essential command patterns and key concepts you'll encounter throughout the deployment documentation. Use this as a quick lookup while reading the detailed sections.

### Core Commands

- **Installation**: `sudo hen install` - One-time setup creating 4 tier-based system users, groups, SSH keys, credential files, git repository, and directory structure
- **Database Setup**: `sudo hen init-db` → `sudo hen add-db-users` → `sudo hen init-homepage` - Initialize databases, create tier-based MySQL users, create homepage
- **Deployment**: `sudo hen deploy` - Copies whitelisted files to `/srv/{project_name}`, manages permissions, stops/starts services, cleans caches
- **Flask Management**: `sudo hen flask-start`, `sudo hen flask-stop`, `sudo hen flask-status` - Manage 4 tier-based Flask daemon instances (ports 5001-5004)
- **HTTP Deployment**: `sudo hen http-deploy` (HTTP-only) → `sudo hen http-deploy-ssl` (HTTPS) - Configure NGINX reverse proxy with SSL certificates
- **Maintenance**: `sudo hen maintenance-start`, `sudo hen maintenance-stop`, `sudo hen maintenance-status` - Manage background daemon for cache refresh and job processing
- **Git Sync**: `hen pull-project` (server gets code from remote), `hen push-project --message "description"` (server sends code via stage branch)
- **Cache Cleanup**: `hen clear-cache` - Clears all registered caches (Python bytecode, registry caches, etc.)

### Key Concepts

- **Project Detection**: Automatic detection from folder name (project name) and folder ownership (project owner). Used throughout all deployment commands.
- **Tier System**: Four tiers (guest, verified, admin, root) with separate Unix users (`{project_name}_{tier}`), database credentials, Flask instances, and visual themes
- **File Whitelisting**: Only explicitly whitelisted files are deployed. Whitelists in `hh/deploy/conf/` control what gets copied to `/srv/{project_name}`
- **Deploy Folder Cleanup**: After deployment, `hh/deploy/` folder is wiped clean EXCEPT for whitelisted items: `cache/`, `conf/`, `maint/`, and `utils.py`
- **Service Coordination**: `deploy` command automatically stops Flask and maintenance daemons before deployment, then restarts them after
- **Stage Branches**: Git branches with format `stage/linux/{timestamp}-{description}` used for code synchronization and recovery points
- **Two-Stage HTTP Deployment**: Stage 1 (HTTP-only) for initial setup, Stage 2 (HTTPS) after SSL certificates are installed

### Important File Locations

- **Deployment Root**: `/srv/{project_name}/` - Production deployment target
- **Configuration**: `hh/deploy/conf/` - Whitelist files (py_whitelist.py, js_whitelist.py, css_whitelist.py, etc.)
- **Site Assets**: `hh/deploy/site/` - Static web files (CSS, JavaScript, favicons)
- **Git Repository**: `/srv/{project_name}/git/{project_name}.git` - Bare git repository
- **Logs**: `/srv/{project_name}/logs/` - Application logs (Flask, maintenance)
- **Credential Files**: `~/.{project_name}.cnf` - Database connection files in each tier user's home directory

### Command Patterns

- **Privileged Commands**: Most deployment commands require `sudo` or root privileges (installation, deployment, service management)
- **Unprivileged Commands**: Git operations (`pull-project`, `push-project`) and cache cleanup can run without sudo
- **Project Context**: All commands automatically detect project name and root directory - no need to specify manually
- **Error Handling**: All commands use Gateway for error reporting and formatted output (CLI tables)

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

## **Installation System**

- One-time setup of Unix users, groups, SSH keys, and credential files
- Creates four tier-based system users with proper permissions
- Initializes git repositories and convenience scripts
- Sets up directory structure and group memberships

## **Database Deployment**

- MySQL database initialization and schema management
- Tier-based database user creation with appropriate permissions
- Database export/import capabilities for backups and migrations
- Homepage initialization and data management

## **File Deployment**

- Whitelist-based file copying to `/srv/{project_name}`
- Permission management with tier-based ownership
- Deploy folder cleanup preserving essential utilities
- Cache file removal and directory sterilization
- **Framework vs Extension Separation**: `hh/` folder contains core framework code, `ext/` folder (optional) contains project-specific customizations

## **Flask Application Management**

- Tier-based Flask daemon lifecycle (4 instances, one per tier)
- Process management with start/stop/status commands
- Logging configuration with logrotate integration
- Concurrency control and request routing

## **HTTP/NGINX Deployment**

- Reverse proxy configuration with SSL certificate support
- Two-stage deployment: HTTP-only (Stage 1) and HTTPS (Stage 2)
- Static file serving and security header configuration
- HTTP Basic Auth for admin and panel subdomains

## **Maintenance Daemon**

- Background worker for cache refresh and job queue processing
- Continuous monitoring of stale caches and pending jobs
- Tool execution via maintenance backend
- Graceful shutdown and heartbeat logging

## **Git Operations**

- Code synchronization between development and production
- Stage branch workflow for deployment snapshots
- Pull operations with hard reset and cache clearing
- Push operations with timestamped branches and signal files

## **Cache Management**

- Registry-based system for cleaning various caches
- Decorator-based registration pattern for cache cleanup
- Automatic cache directory discovery for permission management
- Integration with deployment and pull operations

## **Configuration System**

- Whitelist/blacklist management for file deployment
- Context file deployment for agent visibility
- Application settings and tier configuration
- Project context detection and utilities

## **User Management**

- Complete user infrastructure installation and uninstallation
- Safety validation to prevent accidental deletion
- Script name discovery and cleanup
- Group membership and permission management

## **Site Assets Deployment**

- Static web assets (CSS, JavaScript, favicons) deployment
- Tier-specific color scheme stylesheets
- JavaScript compilation from TypeScript source
- File whitelisting and directory structure management

## **Deployment Workflows**

- Standardized processes for normal operations
- Rollback procedures for recovery to previous commits
- Stage branch recovery mechanisms
- Development-to-production sync workflows

## **Framework vs Extension Architecture**

Henhouse uses a two-folder architecture to separate framework code from project-specific customizations:

- **`hh/` folder**: Core Henhouse framework code (reusable across all projects)
  - Contains all framework functionality: Gateway, Page system, deployment system, etc.
  - Framework upgrades happen in `hh/` folder
  - Shared across all projects using Henhouse
  - Located at project root: `{project_name}/hh/`

- **`ext/` folder**: Project-specific customizations (optional, per-project)
  - Contains project-specific modules, page classes, whitelist extensions, etc.
  - Project work happens in `ext/` folder
  - Unique to each project
  - Located at project root: `{project_name}/ext/`

**Key Distinction for Agents**:
- **Framework Work**: Changes to `hh/` affect all projects using Henhouse. These are framework upgrades.
- **Project Work**: Changes to `ext/` affect only the current project. These are project-specific implementations.

**Extension System**:
- `ext/deploy/conf/` can extend whitelists (add items) or blacklist items (remove from base)
- `ext/deploy/db/schema_ext.sql` can add project-specific database tables
- `ext/deploy/site/` can add project-specific static assets
- Page classes in `ext/` are automatically discovered and registered alongside `hh/` page classes
- Registry scanning (`scan_for_decorator()`) searches both `hh/` and `ext/` for decorators

**Deployment**:
- Both `hh/` and `ext/` folders are deployed to `/srv/{project_name}/`
- `hh/deploy/` and `ext/deploy/` are cleaned after deployment, preserving only whitelisted items
- Whitelist extension system allows `ext/` to customize what gets deployed without modifying framework code

## **Current State of Deployment System**

- Fully operational deployment infrastructure
- All core components implemented and tested
- Production-ready with comprehensive error handling
- Supports multi-tier architecture with proper isolation
- Automated workflows reduce manual intervention to minimum
- Framework vs extension separation enables multi-project development

**Implementation Status:**

- All deployment components (Installation, Database, File Deployment, Flask, HTTP/NGINX, Maintenance, Git, Cache, Configuration, User Management, Site Assets, Workflows) are fully implemented and operational
- Two-stage HTTP deployment (HTTP-only and HTTPS) fully functional
- Stage branch workflow provides recovery and rollback capabilities
- File whitelisting system ensures only approved files are deployed
- Service management automates daemon lifecycle across all tiers

### **Deployment Architecture Map**

The following diagram shows the deployment system relationships and dependencies:

#### **Installation System**: one-time infrastructure setup

- *User Creation*: four tier-based Unix users (`{project_name}_{tier}`) with groups (`{project_name}`, `{project_name}_deploy`, `{project_name}_admin`)
- *SSH Key Management*: auto-scan from project owner's `~/.ssh/`, generate new keys, transfer to all tier users
- *Credential Files*: database connection files (`~/.{project_name}.cnf`) with INI format, `0o600` permissions
- *Git Repository*: bare repo initialization (`/srv/{project_name}/git/{project_name}.git`) and initial commit with `{project_name}` branch
- *Convenience Scripts*: `hen` wrapper scripts for all users, `gateway.py` for tier users, PATH configuration in `.profile`
- *Directory Setup*: `/srv/images/{project_name}/` and `/srv/files/{project_name}/` with setgid bit (`0o2775`) for group write
- *HTTP Basic Auth*: creates `.htpasswd_admin` and `.htpasswd_panel` files for subdomain authentication

#### **Database Deployment**: MySQL database management

- *Database Initialization*: main and cache database creation with schema execution (`init.sql`, `init_cache.sql`)
- *User Management*: tier-based MySQL users with appropriate permissions (guest: SELECT, verified: SELECT+INSERT, admin: CRUD, root: full management)
- *Export/Import*: backup and migration capabilities with transaction control and table information collection
- *Homepage Setup*: initial page creation (ID 1) with safety check (pages table must be empty)
- *Connection Management*: root connection for admin operations, tier user connections from credential files (`~/.{project_name}.cnf`)
- *Two-Database Architecture*: main database (`{project_name}`) for application tables, cache database (`{project_name}_cache`) for cached data

#### **File Deployment**: production code deployment

- *Framework vs Extension*: `hh/` folder contains core Henhouse framework (reusable across projects), `ext/` folder (optional) contains project-specific customizations
- *Whitelisting System*: Python, JavaScript, CSS, misc, context file whitelists from `hh/deploy/conf/` with extension support via `ext/deploy/conf/`
- *Extension Whitelists*: `ext/deploy/conf/` can extend base whitelists (add items) or blacklist items (remove from base)
- *File Copying*: whitelisted files to `/srv/{project_name}/` with deployment process that copies both `hh/` and `ext/` (if exists)
- *Permission Management*: tier-based ownership (`{project_name}_root:{project_name}_deploy`) with setgid bit for cache/logs
- *Deploy Folder Cleanup*: preserves cache/, conf/, maint/, utils.py in `hh/deploy/` and conf/ in `ext/deploy/` via temporary move and restore process
- *Cache Cleanup*: removes `__pycache__`, `.pyc`, cache JSON files, then clears all registered caches
- *Service Restart*: automatic Flask and maintenance daemon stop before deployment, start after deployment
- *Git Preservation*: git repository preserved across deployments via temporary move and restore

#### **Flask Application Management**: tier-based web services

- *Four Instances*: one Flask daemon per tier (ports 5001-5004), each runs as corresponding tier user
- *Process Management*: start/stop/status commands with PID tracking via `ps aux`
- *Logging*: tier-specific log files (`/srv/{project_name}/logs/flask_{project_name}_{tier}.log`) with logrotate (hourly, 24-hour retention)
- *Request Routing*: MCP protocol (`/mcp`), HTTP backend (`/` and `/<path>`), image serving (`/img/<id>`), file upload (`/upload-file`)
- *Concurrency Control*: semaphore-based Gateway call limiting (default: 4 concurrent requests, 10-second timeout)
- *User Isolation*: each instance runs as corresponding tier user (`{project_name}_{tier}`) with tier-specific database credentials
- *Tier Detection*: extracts tier from script name (`{project_name}_{tier}.py`) or environment variable

#### **HTTP/NGINX Deployment**: reverse proxy and SSL

- *NGINX Configuration*: server blocks for main domain and subdomains (main, admin, panel)
- *Two-Stage Deployment*: HTTP-only (Stage 1) and HTTPS (Stage 2) with HTTP-to-HTTPS redirect
- *Static File Serving*: direct NGINX serving for whitelisted assets (JS, CSS, misc, context files)
- *Security Headers*: X-Frame-Options, HSTS (HTTPS only), rate limiting, hidden file blocking
- *HTTP Basic Auth*: admin and panel subdomain protection using `.htpasswd` files from installation
- *SSL/TLS*: Let's Encrypt certificate integration (default path: `/etc/letsencrypt/live/{domain}/`)
- *Flask Proxy*: all non-static requests proxied to Flask applications (ports 5001-5004)

#### **Maintenance Daemon**: background processing

- *Worker Process*: continuous loop monitoring jobs and stale caches via `maintenance-jobs-status` command
- *Job Queue Integration*: pending job processing with priority, status updates (pending/running/done/error)
- *Cache Refresh*: stale page/image/file cache rebuilding via cache database queries and refresh tools
- *Tool Execution*: maintenance backend tool calls via Gateway dispatch through `maintenance_client.py`
- *Heartbeat Logging*: status logging every 15 minutes when idle, configurable log level
- *Graceful Shutdown*: SIGINT/SIGTERM signal handling, adaptive sleep (0.5s when work done, full delay when idle)
- *Architecture Distinction*: `maintenance/` (daemon management, privileged access) vs `maint/` (operational tools, deployed)

#### **Git Operations**: code synchronization

- *Pull Operations*: hard reset to `origin/{project_name}` with cache clearing via cache cleanup registry
- *Push Operations*: stage branch creation with timestamped names (`stage/linux/{timestamp}-{description}`)
- *Stage Branches*: structured branch naming with sanitized messages, commit trailers for automation
- *Signal Files*: `{repo_root}/stage` file for deployment processes, UTF-8 encoded with Unix line endings
- *Cache Integration*: automatic cache clearing after pull via `clean_all_caches()` from cache cleanup registry
- *Project Detection*: uses `detect_project_context()` to find project name and repository root

#### **Cache Management**: centralized cache cleanup

- *Registry System*: decorator-based cache cleanup registration (`@register_cache_cleanup`)
- *Discovery Process*: scans codebase for `@register_cache_cleanup` decorators, imports modules to trigger registration
- *Permission Management*: cache directory discovery for deployment permission setting (setgid bit for group write)
- *Integration Points*: deployment (permission setting, cache clearing), pull operations (automatic clearing), manual cleanup
- *Built-in Cleanups*: Python bytecode cleanup (`__pycache__`, `.pyc` files) plus registered cleanup functions

#### **Configuration System**: whitelists and settings

- *File Whitelists*: Python, JavaScript, CSS, misc, context, deploy whitelists in `hh/deploy/conf/`
- *Extension Whitelists*: `ext/deploy/conf/` can extend base whitelists (add items via `{name}.py`) or blacklist items (remove via `{name}_blacklist.py`)
- *Whitelist Extension Process*: Load base from `hh/deploy/conf/`, subtract blacklist from `ext/deploy/conf/`, add extension from `ext/deploy/conf/`
- *Blacklists*: patterns excluded from deployment (context blacklist for documentation)
- *Project Detection*: automatic project name and root discovery via `detect_project_context()` utility
- *Tier Configuration*: four-tier user model constants (`HENHOUSE_TIERS`) used throughout deployment system
- *Deploy Folder Preservation*: whitelist defines what survives deployment cleanup (cache/, conf/, maint/, utils.py in `hh/deploy/`, conf/ in `ext/deploy/`)

#### **User Management**: infrastructure lifecycle

- *Installation*: complete user, group, and credential setup
- *Uninstallation*: safe removal with extensive validation
- *Safety Checks*: prevents accidental deletion of non-project users
- *Script Cleanup*: removes convenience scripts and PATH modifications

#### **Site Assets Deployment**: static web files

- *CSS Deployment*: base stylesheet (`site.css`) and tier-specific color schemes (site-guest.css, site-admin.css, etc.)
- *JavaScript Deployment*: compiled TypeScript files deployed to `site/js/`
- *Favicon Deployment*: multiple format support (ICO, PNG variants, webmanifest)
- *Directory Structure*: organized deployment to `/srv/{project_name}/site/` via file deployment (see `file-deployment.md`)
- *Whitelist Integration*: all assets controlled by whitelists in `hh/deploy/conf/` (see `configuration.md`)

#### **Deployment Workflows**: standardized processes

- *Standard Deployment*: `pull_project` (see `git.md`) → `sudo hen deploy` (see `file-deployment.md`) workflow
- *Rollback Process*: git reset to previous commit and redeploy via `file-deployment.md`
- *Stage Branch Recovery*: recovery point creation via `git.md` push operations, reference via stage folder
- *Development Sync*: laptop push (see `git.md`) to server pull and deploy (see `git.md` and `file-deployment.md`)
- *Initial Setup*: One-time installation (see `installation.md`), database setup (see `database.md`), HTTP configuration (see `http-nginx.md`)

### **Key Dependency Notes**

- **Gateway is foundational**: All deployment commands use Gateway for dispatch, error handling, and response management. Gateway provides database connections, file operations, process management, and debug system integration.

- **Installation is prerequisite**: User infrastructure must exist before database, deployment, or service management. Installation creates tier users, groups, credential files, git repository, and directory structure that all other systems depend on.

- **Database setup is independent**: Can be initialized separately from file deployment, but requires credential files from installation. Database users are created using passwords from credential files created during installation. Extension schema (`ext/deploy/db/schema_ext.sql`) is executed after main schema if present.

- **File deployment coordinates services**: Automatically stops and restarts Flask and maintenance daemons. Preserves git repository and whitelisted deploy folder items (cache/, conf/, maint/, utils.py in `hh/deploy/`, conf/ in `ext/deploy/`) during cleanup. Deploys both `hh/` and `ext/` folders if present.

- **Git operations are independent**: Can sync code without affecting running services. Automatically clears caches after pull operations to prevent stale state issues.

- **Configuration drives deployment**: Whitelists determine what gets deployed, blacklists exclude patterns. Base whitelists in `hh/deploy/conf/` can be extended or modified via `ext/deploy/conf/` files. All file deployment decisions are driven by the combined whitelist system.

- **Services depend on deployment**: Flask and maintenance daemons require deployed code to function. Flask applications are created during deployment, maintenance worker is deployed during deployment.

- **Cache management is integrated**: Cache directories are discovered during deployment for permission setting. Cache cleanup happens automatically during deployment and pull operations.

- **HTTP/NGINX depends on installation and deployment**: Uses HTTP Basic Auth files from installation, serves static files from deployment, proxies to Flask applications created during deployment.

### **Deployment Architecture**

The deployment system follows a **"set it up once, deploy repeatedly"** philosophy:

- **Initial Setup**: One-time configuration of users, databases, HTTP servers, and infrastructure
- **Repeatable Deployment**: Simple two-command workflow (`pull_project` → `sudo hen deploy`) for all subsequent updates
- **Rollback Capability**: Easy recovery to any previous commit via git reset and redeploy
- **Stage Branch Recovery**: Mechanism for creating recovery points and referencing previous working states

#### **Deployment Target**

All deployment operations target `/srv/{project_name}/` as the production root:

- **Framework Code**: `hh/` folder structure deployed to `/srv/{project_name}/hh/` (core Henhouse framework)
- **Extension Code**: `ext/` folder structure deployed to `/srv/{project_name}/ext/` (project-specific customizations, optional)
- **Site Assets**: Static files deployed to `/srv/{project_name}/site/`
- **Logs**: Application logs in `/srv/{project_name}/logs/`
- **Cache**: Cache directories in `/srv/{project_name}/` (various locations)
- **Git Repository**: Bare repo at `/srv/{project_name}/git/{project_name}.git`

#### **Tier-Based Architecture**

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

#### **Security Model**

- **File Permissions**: Tier-based ownership with deploy group for shared access
- **Database Access**: Tier-based MySQL users with appropriate permissions
- **Process Isolation**: Each Flask instance runs as its corresponding Unix user
- **Network Security**: Flask apps listen on localhost only, proxied by NGINX
- **HTTP Basic Auth**: Admin and panel subdomains protected with `.htpasswd` files
- **SSL/TLS**: HTTPS deployment with Let's Encrypt certificates

#### **File Whitelisting System**

The deployment uses a comprehensive whitelisting system with extension support:

- **Base Whitelists**: Defined in `hh/deploy/conf/` (py_whitelist.py, js_whitelist.py, css_whitelist.py, etc.)
- **Extension Whitelists**: `ext/deploy/conf/` can extend base whitelists by adding items via `{name}.py` files
- **Extension Blacklists**: `ext/deploy/conf/` can remove items from base whitelists via `{name}_blacklist.py` files
- **Processing Order**: Load base → subtract blacklist → add extension
- **Python Files**: `py_whitelist.py` defines which Python files are deployed
- **JavaScript Files**: `js_whitelist.py` defines which JS files are deployed (can be extended via `ext/deploy/conf/js_whitelist.py`)
- **CSS Files**: `css_whitelist.py` defines which stylesheets are deployed (can be extended via `ext/deploy/conf/css_whitelist.py`)
- **Miscellaneous Files**: `misc_whitelist.py` defines other static assets
- **Context Files**: `context_whitelist.py` and `context_blacklist.py` control documentation deployment
- **Deploy Folder**: `deploy_whitelist.py` defines what survives deploy folder cleanup (separate whitelists for `hh/deploy/` and `ext/deploy/`)

**Key Principle**: Only explicitly whitelisted files are deployed. Everything else is excluded by default. Extension whitelists allow project-specific customizations without modifying framework code.

#### **Service Management**

The system manages multiple background services:

- **Flask Applications**: 4 instances (one per tier), managed via `flask_start`/`flask_stop`/`flask_status`
- **Maintenance Daemon**: Single background worker, managed via `maintenance_start`/`maintenance_stop`/`maintenance_status`
- **NGINX**: System service, managed via `http_deploy`/`http_deploy_ssl`/`http_remove`

All services are automatically restarted during deployment.

#### **Development-to-Production Workflow**

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

#### **Key Design Principles**

1. **Separation of Concerns**: Each component has a single, well-defined responsibility
2. **Idempotency**: Deployment operations can be run multiple times safely
3. **Reversibility**: All operations can be rolled back or undone
4. **Traceability**: Stage branches and logs provide audit trail
5. **Automation**: Minimal manual intervention required after initial setup
6. **Safety**: Extensive validation and error checking at every step
7. **Modularity**: Components can be used independently or together

#### **Integration with Henhouse Core**

The deployment system integrates with core Henhouse components:

- **Gateway**: All commands use Gateway for dispatch, error handling, and response management. Gateway provides database connections (main, cache), file operations, process management, and debug system integration. All deployment operations route through Gateway's single-shot command execution model.

- **Page System**: Deployed pages are served via Flask applications. The HTTP backend routes page requests to Gateway, which uses the Page system to retrieve and process content. Cache refresh operations integrate with the Page system's cache management.

- **Registry System**: Command registry is cleared after deployment to reload new commands. The registry system discovers action and backend handlers via decorator scanning, and deployment clears registry caches to ensure new commands are available.

- **Cache System**: Cache cleanup registry is used during deployment and pull operations. The cache management system discovers cache directories for permission setting and provides centralized cache cleanup functionality.

- **MCP Backend**: Flask applications expose MCP protocol for external tool integration. The MCP backend provides JSON-RPC 2.0 API access, and Flask applications route MCP requests through `mcp_client.py` to Gateway dispatch.

- **Maintenance Backend**: Background daemon uses maintenance backend for tool execution. Maintenance tools are registered via `register_maintenance_tool()` and executed through Gateway dispatch, same as other backends.

- **Render System**: Deployment commands use the Render system for formatted output (CLI tables). The Render system provides unified output formatting that works across all backends.

- **Debug System**: Deployment commands support debug flags and filtering. Debug output is captured through Gateway's debug system and formatted according to the active backend.

This deployment system enables Henhouse to be a self-documenting, self-deploying platform where the deployment process itself is part of the system being deployed. The deployment system uses the same Gateway, Registry, and Render systems that the application uses, creating a unified architecture.

---

### **Installation Architecture**

The installation system creates the complete user and group infrastructure needed for a Henhouse deployment. It sets up four tier-based system users, transfers SSH keys, creates credential files, initializes git repositories, and configures convenience scripts.

- One-time setup process with comprehensive validation
- Project name and owner auto-detection
- SSH key auto-scanning and generation
- Credential file creation for database access
- Git repository initialization with bare repo
- Convenience script deployment for all users

---

### **Database Deployment Architecture**

The database deployment system manages MySQL database initialization, user creation, permissions, and data management for both the main application database and the cache database.

- Two-database architecture (main and cache)
- Schema execution from SQL files
- Tier-based user creation with permission management
- Export/import capabilities for backups
- Homepage initialization for new deployments

---

### **File Deployment Architecture**

The file deployment system orchestrates the complete process of copying files to `/srv/{project_name}`, managing service lifecycle, and setting up the production environment.

- Whitelist-based file copying
- Permission management with tier-based ownership
- Deploy folder cleanup preserving essential utilities
- Service coordination (stop before deploy, start after)
- Cache cleanup and directory sterilization

---

### **Flask Application Management Architecture**

The Flask application management system handles tier-based Flask daemon lifecycle, process management, logging, and HTTP/MCP request routing.

- Four Flask instances (one per tier)
- Process lifecycle management
- Logging with logrotate integration
- Request routing (MCP, HTTP, images, pages)
- Concurrency control and timeout handling

---

### **HTTP/NGINX Deployment Architecture**

The HTTP/NGINX deployment system manages web server configuration for serving Henhouse applications through NGINX reverse proxy. It supports two-stage deployment: HTTP-only (Stage 1) and HTTPS with SSL (Stage 2).

- Reverse proxy configuration
- Two-stage deployment workflow
- Static file serving
- Security headers and rate limiting
- HTTP Basic Auth for subdomains
- SSL/TLS certificate integration

---

### **Maintenance Daemon Architecture**

The maintenance daemon system consists of two distinct components: daemon management commands (start/stop/status) and maintenance tools (cache refresh, job queue, orphan checks).

- Continuous background worker process
- Job queue monitoring and processing
- Stale cache detection and refresh
- Tool execution via maintenance backend
- Graceful shutdown and heartbeat logging

---

### **Git Operations Architecture**

The git operations system provides commands for syncing code between development environments (laptop) and deployment servers. It supports pulling the latest code from remote repositories and pushing changes via stage branches.

- Pull operations with hard reset
- Push operations with stage branch creation
- Stage branch workflow for recovery points
- Cache clearing integration
- Signal file creation for deployment processes

---

### **Cache Management Architecture**

The cache management system provides a centralized registry for cleaning various caches throughout the Henhouse system. It uses a decorator-based registration pattern that allows any module to register its own cache cleanup function.

- Registry-based cleanup system
- Decorator-based registration pattern
- Cache directory discovery
- Integration with deployment and pull operations

---

### **Configuration System Architecture**

The configuration system manages whitelists, blacklists, and application settings that control what gets deployed and how the system behaves.

- File type whitelists (Python, JavaScript, CSS, misc)
- Context whitelist and blacklist
- Deploy folder whitelist
- Project context detection
- Tier configuration constants

---

### **User Management Architecture**

The user management system provides comprehensive installation and uninstallation of the complete user infrastructure, with extensive safety checks to prevent accidental deletion of non-project users.

- Installation process with validation
- Uninstallation with safety checks
- User validation before deletion
- Script cleanup and PATH management
- Group membership management

---

### **Site Assets Deployment Architecture**

The site folder contains all static web assets (CSS, JavaScript, favicons, etc.) that are deployed to `/srv/{project_name}/site/` and served by the web application.

- CSS deployment with tier-specific color schemes
- JavaScript deployment from TypeScript source
- Favicon and web manifest deployment
- Directory structure management
- File whitelisting integration

---

### **Deployment Workflows Architecture**

The complete deployment workflow ties together all the individual components into repeatable, automated processes for syncing code between development and production environments.

- Standard deployment workflow
- Rollback procedures
- Stage branch recovery
- Development-to-production sync

---

## **Additional Reading**

The following documents provide detailed implementation information beyond this overview. Each document focuses on specific deployment subsystems with code-level details, file locations, function names, and architectural patterns.

**Most important documents for general deployment work:**

- **installation.md**: Essential reading for understanding initial system setup, user creation, SSH key management, and credential file setup. Required for any work involving user infrastructure or initial deployment.
- **file-deployment.md**: Essential reading for understanding the deployment process, file whitelisting, permission management, and service coordination. Required for any work involving code deployment or production environment setup.

### **installation.md**

- **User Creation**: Specific process for creating four tier-based system users with groups
- **SSH Key Management**: Auto-scanning, generation, and transfer mechanisms
- **Credential Files**: Database connection file creation and format
- **Git Repository Setup**: Bare repo initialization and initial commit process
- **Convenience Scripts**: Gateway and hen wrapper script deployment
- **File Locations**: Specific file paths, function names, and code patterns for installation

### **file-deployment.md**

- **Deployment Process**: Complete 16-step deployment flow with service coordination
- **File Whitelisting**: Whitelist system architecture and file type management
- **Permission Management**: Tier-based ownership and group permissions
- **Deploy Folder Cleanup**: Preservation of essential utilities during cleanup
- **Service Management**: Automatic daemon stop/start during deployment
- **File Locations**: Specific file paths, function names, and code patterns for deployment

### **database.md**

- **Database Initialization**: Schema execution and database creation process for main and cache databases
- **User Management**: Tier-based MySQL user creation with permissions (guest: SELECT, verified: SELECT+INSERT, admin: CRUD, root: full management)
- **Export/Import**: Backup and migration capabilities with transaction control
- **Homepage Setup**: Initial page creation process (page ID 1)
- **SQL Files**: Schema file structure (`init.sql`, `init_cache.sql`) and execution
- **Connection Management**: Root connection for admin operations, tier user connections from credential files
- **File Locations**: Specific file paths in `hh/deploy/db/`, function names, and code patterns

### **flask.md**

- **Daemon Lifecycle**: Start/stop/status command implementation with PID tracking
- **Process Management**: Process discovery via `ps aux`, graceful shutdown with SIGTERM
- **Logging System**: Tier-specific log files with logrotate integration (hourly rotation, 24-hour retention)
- **Request Routing**: MCP protocol handler, HTTP backend routing, image serving, dynamic page routing
- **Concurrency Control**: Semaphore-based Gateway call limiting (default: 4 concurrent requests)
- **Tier Detection**: Extracts tier from script name (`{project_name}_{tier}.py`)
- **File Locations**: Specific file paths in `hh/deploy/flask/`, function names, and code patterns

### **http-nginx.md**

- **NGINX Configuration**: Server block generation and installation with deployment markers
- **Two-Stage Deployment**: HTTP-only (Stage 1) and HTTPS (Stage 2) deployment workflows
- **Static File Serving**: Location block generation from whitelists (JS, CSS, misc, context files)
- **Security Features**: Security headers (X-Frame-Options, HSTS), rate limiting, hidden file blocking
- **SSL/TLS Integration**: Certificate path configuration (Let's Encrypt default) and HTTPS setup
- **HTTP Basic Auth**: Admin and panel subdomain protection using `.htpasswd` files
- **File Locations**: Specific file paths in `hh/deploy/http/`, function names, and code patterns

### **maintenance.md**

- **Worker Process**: Continuous loop with adaptive sleep, work detection, and graceful shutdown
- **Job Queue Integration**: Job claiming with optimistic locking, status updates (pending/running/done/error)
- **Cache Refresh Tools**: Stale cache detection via cache database, refresh process for pages/images/files
- **Tool Execution**: Maintenance backend tool calls via Gateway dispatch
- **Process Management**: Daemon start/stop/status commands with cross-platform support
- **Architecture Distinction**: `maintenance/` (daemon management) vs `maint/` (operational tools)
- **File Locations**: Specific file paths in `hh/deploy/maintenance/` and `hh/deploy/maint/`, function names, and code patterns

### **git.md**

- **Pull Operations**: Hard reset workflow to `origin/{project_name}`, automatic cache clearing
- **Push Operations**: Stage branch creation with timestamped names (`stage/linux/{timestamp}-{description}`)
- **Stage Branch Workflow**: Branch naming convention, commit structure with trailers, signal file creation
- **Helper Functions**: Git command execution with error handling, text sanitization for ref names
- **Cache Integration**: Automatic cache clearing after pull operations via cache cleanup registry
- **File Locations**: Specific file paths in `hh/deploy/git/`, function names, and code patterns

### **cache.md**

- **Registry System**: Decorator-based registration (`@register_cache_cleanup`) and discovery process
- **Cache Cleanup**: Built-in Python bytecode cleanup plus registered cleanup functions
- **Permission Management**: Cache directory discovery for deployment permission setting (setgid bit)
- **Integration Points**: Deployment (permission setting, cache clearing), pull operations (automatic clearing), manual cleanup
- **File Locations**: Specific file paths in `hh/deploy/cache/`, function names, and code patterns

### **configuration.md**

- **Whitelist Management**: File type whitelists (Python, JavaScript, CSS, misc), context whitelist/blacklist, deploy whitelist
- **Project Detection**: Automatic project name and root discovery via `detect_project_context()`
- **Tier Configuration**: Four-tier user model constants (`HENHOUSE_TIERS`) used throughout system
- **Deployment Utilities**: Core utility functions (`utils.py`) for project context detection
- **File Locations**: Specific file paths in `hh/deploy/conf/`, whitelist structure, and code patterns

### **user-management.md**

- **Installation Process**: Complete user infrastructure setup (covered in `installation.md`)
- **Uninstallation Process**: Safe removal with extensive validation to prevent accidental deletion
- **Safety Validation**: User and directory validation before deletion (UID check, shell check, naming pattern)
- **Script Cleanup**: Convenience script and PATH management cleanup
- **File Locations**: Specific file paths in `hh/deploy/users/`, function names, and code patterns

### **site-assets.md**

- **CSS Deployment**: Base stylesheet (`site.css`) and tier-specific color schemes (site-guest.css, site-admin.css, etc.)
- **JavaScript Deployment**: TypeScript compilation and file deployment to `site/js/`
- **Favicon Deployment**: Multiple format support (ICO, PNG variants, webmanifest)
- **Directory Structure**: Site folder organization (`css/`, `js/`, `infographic/`, top-level files)
- **File Locations**: Specific file paths in `hh/deploy/site/`, whitelist integration, and code patterns

### **workflows.md**

- **Standard Workflow**: Pull and deploy process (`pull_project` → `sudo hen deploy`)
- **Rollback Process**: Git reset and redeploy workflow for recovery to previous commits
- **Stage Branch Recovery**: Recovery point creation and reference via stage branches
- **Development Sync**: Laptop-to-server code synchronization workflow
- **Component Dependencies**: Detailed dependency chain and troubleshooting guidance

---

## **Future Development**

This section documents planned features and architectural expansions for the deployment system.

### **Deployment Automation**

- Automated deployment triggers from stage branch pushes
- Health check integration for deployment verification
- Automated rollback on health check failures
- Deployment status dashboard and monitoring

### **Multi-Environment Support**

- Support for staging, production, and development environments
- Environment-specific configuration management
- Parallel deployment to multiple environments
- Environment-specific whitelist/blacklist configuration

### **Enhanced Security**

- Automated SSL certificate renewal integration
- Security audit logging for deployment operations
- Automated security header updates
- Vulnerability scanning integration

### **Performance Optimization**

- Incremental deployment (only changed files)
- Deployment caching for faster subsequent deployments
- Parallel service restart for reduced downtime
- Deployment performance metrics and monitoring

