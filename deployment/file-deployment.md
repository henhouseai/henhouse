# File Deployment

The file deployment system orchestrates the complete process of copying files to `/srv/{project_name}`, managing service lifecycle, and setting up the production environment.

## Prerequisites

Before running file deployment, you must have:
- Installation system completed (see `installation.md`) - users and groups must exist
- Sudo/root privileges
- Project folder with `hh/` directory structure
- All whitelist configuration files in place (see `configuration.md`)

The file deployment system depends on the installation system because it uses the users and groups created during installation to set proper file ownership and permissions.

## Deploy Command

**File**: `hh/deploy/srv/deploy.py`

The `deploy` command performs a complete deployment with the following flow:

**Prerequisites**:
- Must run with sudo/root privileges (checked via `gateway.os.require_privileged()`)
- Optional: `-start_port <port>` to specify starting port for Flask apps (default: 5001)

**Project Detection**:
- Automatically detects project name by walking up directory tree looking for `hh/` directory
- Uses folder name as project name
- Source: project folder, Destination: `/srv/{project_name}`

## Deployment Process Flow

### Step 1: Stop Running Daemons

Before deployment begins, all running services are stopped:
- **Maintenance daemon**: Stopped via `run_maintenance_stop(project_name)` (see `maintenance.md`)
- **Flask daemons**: Stopped via `run_flask_stop(project_name)` (see `flask.md`)

This ensures clean deployment without running processes holding file locks.

### Step 2: Preserve Git Repository

The git repository is preserved across deployments:
- **Temporary move**: `/srv/{project_name}/git` → `/srv/{project_name}_git` (temporary location)
- **Restoration**: Git folder restored after deployment directory sterilization
- This preserves the bare git repository and all git history created by the installation system (see `installation.md`)

### Step 3: Sterilize Deployment Directory

The entire `/srv/{project_name}` directory is cleaned:
- **Removes all contents** except preserved git folder
- If directory doesn't exist, creates it
- Ensures clean slate for each deployment

### Step 4: Deploy Main Code

Copies the entire `hh/` folder to `/srv/{project_name}/hh/`:
- Uses `shutil.copytree()` to copy entire directory structure
- All Python modules, subdirectories, and files are copied
- This is the core application code

### Step 5: Clean Deploy Folder (Preserve Whitelisted Items)

**Critical Process**: The `hh/deploy/` folder is cleaned while preserving essential items:

1. **Temporary preservation**: Whitelisted items moved to temporary locations:
   - `cache/` → `/srv/{project_name}/.{project_name}_cache_tmp` (see `cache.md`)
   - `conf/` → `/srv/{project_name}/.{project_name}_conf_tmp` (see `configuration.md`)
   - `maint/` → `/srv/{project_name}/.{project_name}_maint_tmp` (see `maintenance.md`)
   - `utils.py` → `/srv/{project_name}/.{project_name}_utils_py_tmp`

2. **Deploy folder removal**: Entire `hh/deploy/` directory is removed

3. **Recreate and restore**: Deploy directory recreated, whitelisted items restored

This ensures only essential deployment utilities remain in the deploy folder after deployment, while all deployment scripts (db/, flask/, http/, users/, etc.) are removed since they're only needed during deployment, not in production.

The whitelist is defined in `hh/deploy/conf/deploy_whitelist.py` (see `configuration.md`).

### Step 6: Clean Cache Files

Removes all cache files from deployment:
- **`__pycache__` directories**: Recursively removed
- **`.pyc` files**: All Python bytecode files removed
- **Cache JSON files**: `*-reg.json`, `*.cycle.json`, `cache.json`, `*.cache` patterns
- **`.cache` directories**: Recursively removed

This ensures clean deployment without stale cache files. The cache management system (see `cache.md`) handles cache cleanup operations.

### Step 7: Deploy Flask Applications

Creates tier-specific Flask application files:
- **Source**: `hh/deploy/flask/app.py` (see `flask.md`)
- **Destination**: `/srv/{project_name}/{project_name}_{tier}.py` (one per tier)
- **Port assignment**: Each tier gets sequential port starting from `start_port`:
  - Tier 0 (guest): `start_port + 0`
  - Tier 1 (verified): `start_port + 1`
  - Tier 2 (admin): `start_port + 2`
  - Tier 3 (root): `start_port + 3`
- **Log file**: Each app gets tier-specific log file: `/srv/{project_name}/logs/flask_{project_name}_{tier}.log`
- **Content modification**: Port and log file paths are replaced in the source template

These Flask applications are managed by the Flask application management system (see `flask.md`).

### Step 8: Deploy Maintenance Worker

Creates the maintenance worker script:
- **Source**: `hh/deploy/maintenance/worker.py` (see `maintenance.md`)
- **Destination**: `/srv/{project_name}/{project_name}_maintenance.py`
- **Template replacement**: `__PROJECT_NAME__` replaced with actual project name

The maintenance worker is managed by the maintenance daemon system (see `maintenance.md`).

### Step 9: Deploy Extra Top-Level Files

Copies additional files specified in `EXTRA_DEPLOY_FILES`:
- `hh/deploy/flask/http_client.py` → `/srv/{project_name}/http_client.py` (see `flask.md`)
- `hh/deploy/flask/mcp_client.py` → `/srv/{project_name}/mcp_client.py` (see `flask.md`)
- `hh/deploy/maint/maintenance_client.py` → `/srv/{project_name}/maintenance_client.py` (see `maintenance.md`)

These are entry point scripts used by the deployed applications.

### Step 10: Deploy Context Folders and Files

Deploys documentation and context files for agent visibility:
- **Destination**: `/srv/{project_name}/context/`
- **Whitelist**: Items from `CONTEXT_WHITELIST` (context/, planning/, hh/, top-level scripts, README.md, LICENSE, requirements.txt)
- **Blacklist filtering**: Excludes patterns from `CONTEXT_BLACKLIST` (.git, __pycache__, *.pyc, node_modules, .env, *.log, cache JSON files)
- **Structure**: Maintains directory structure under `context/` subdirectory

The context whitelist and blacklist are defined in `hh/deploy/conf/context_whitelist.py` and `hh/deploy/conf/context_blacklist.py` (see `configuration.md`).

### Step 11: Deploy Site Files

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

All whitelists are defined in `hh/deploy/conf/` (see `configuration.md` and `site-assets.md`).

### Step 12: Set Ownership and Permissions

Sets proper Unix ownership and permissions:

- **Main deployment**: 
  - Owner: `{project_name}_root` (highest tier user, created by installation system - see `installation.md`)
  - Group: `{project_name}_deploy` (deployment group, created by installation system)
  - Directories: `0o750` (owner:rwx, group:r-x, others:---)
  - Files: `0o640` (owner:rw-, group:r--, others:---)

- **Git directory** (special permissions):
  - Owner: `{project_name}_root`
  - Group: `{project_name}` (project group, not deploy group)
  - Directories: `0o770` (owner:rwx, group:rwx, others:---)
  - Files: `0o660` (owner:rw-, group:rw-, others:---)

### Step 13: Set Up Cache Directory Permissions

Configures cache directories discovered via cache registry:
- **Discovery**: Uses `get_cache_directories()` from cache cleanup registry (see `cache.md`)
- **Permissions**: `0o2775` (setgid for group write, owner:rwx, group:rwx, others:r-x)
- **Ownership**: `{project_name}_root:{project_name}_deploy`
- **Creation**: Creates cache directories if they don't exist

This allows all tier users (in deploy group) to write cache files via group permissions. The cache management system (see `cache.md`) uses these directories.

### Step 14: Set Up Logs Directory

Creates and configures logs directory:
- **Path**: `/srv/{project_name}/logs/`
- **Permissions**: `0o2775` (setgid for group write)
- **Ownership**: `{project_name}_root:{project_name}_deploy`
- **Purpose**: Flask daemons (see `flask.md`) and maintenance worker (see `maintenance.md`) write logs here

### Step 15: Restart Daemons

Starts services after deployment completes:
- **Flask daemons**: Started via `run_flask_start(project_name, start_port)` (see `flask.md`)
- **Maintenance daemon**: Started via `run_maintenance_start(project_name)` (see `maintenance.md`)
- Services start with new code and proper permissions in place

### Step 16: Clear Registry Cache

Calls `clean_all_caches()` from cache cleanup registry (see `cache.md`):
- Prevents permission issues from stale cache files
- Ensures clean state after deployment

## Deploy Folder Cleanup Details

The deploy folder cleanup is a critical safety mechanism:

**Process**:
1. Each whitelisted item is moved to a uniquely named temporary location
2. Entire `hh/deploy/` directory is removed
3. `hh/deploy/` directory is recreated
4. Whitelisted items are restored from temporary locations

**Temporary naming**: `.{project_name}_{item_name}_tmp` (with `/` and `.` replaced with `_`)

**Why this matters**: Deployment scripts (db/, flask/, http/, users/, etc.) are only needed during deployment operations, not in production. Keeping them in production would be a security risk and waste of space.

The whitelist is defined in `hh/deploy/conf/deploy_whitelist.py` (see `configuration.md`):
- `cache/` - Cache cleanup registry and utilities (see `cache.md`)
- `conf/` - Configuration whitelists (see `configuration.md`)
- `maint/` - Maintenance helpers (see `maintenance.md`)
- `utils.py` - General deployment utilities

## File Whitelisting System

Files are whitelisted through multiple configuration files in `hh/deploy/conf/` (see `configuration.md`):

- **Python files**: `py_whitelist.py` → `PY_WHITELIST`
- **JavaScript files**: `js_whitelist.py` → `JS_WHITELIST`, `JS_ALWAYS_INCLUDE`
- **CSS files**: `css_whitelist.py` → `CSS_WHITELIST`, `CSS_ALWAYS_INCLUDE`
- **Miscellaneous files**: `misc_whitelist.py` → `MISC_WHITELIST`
- **Context files**: `context_whitelist.py` → `CONTEXT_WHITELIST`
- **Context blacklist**: `context_blacklist.py` → `CONTEXT_BLACKLIST` (patterns to exclude)
- **Deploy whitelist**: `deploy_whitelist.py` → `DEPLOY_WHITELIST`, `EXTRA_DEPLOY_FILES`

**Key Principle**: Only explicitly whitelisted files are deployed. Everything else is excluded by default.

## Permission Model

The deployment uses a tiered permission model based on users and groups created by the installation system (see `installation.md`):

- **Owner**: `{project_name}_root` (highest tier user) - full read/write access
- **Group**: `{project_name}_deploy` - read access to code, write access to cache/logs via setgid
- **Others**: No access

**Setgid directories**: Cache and logs directories use setgid bit (`0o2775`) so new files created by any tier user inherit the deploy group, enabling group write access. This allows all tier users to write cache files and logs without requiring root access.

## Integration with Other Systems

The file deployment system integrates with:

1. **Installation System** (`installation.md`): Uses users and groups created during installation to set file ownership and permissions.

2. **Database Deployment** (`database.md`): The deployed Flask applications connect to databases using tier-specific credentials established during database deployment.

3. **Flask Application Management** (`flask.md`): Creates tier-specific Flask application files and starts Flask daemons after deployment.

4. **Maintenance Daemon** (`maintenance.md`): Deploys maintenance worker script and starts maintenance daemon after deployment.

5. **HTTP/NGINX Deployment** (`http-nginx.md`): Deploys site files that are served by NGINX. The HTTP deployment system reads whitelists to configure static file serving.

6. **Git Operations** (`git.md`): Preserves the git repository created during installation across deployments.

7. **Cache Management** (`cache.md`): Discovers cache directories via cache registry and sets proper permissions. Clears all caches after deployment.

8. **Configuration System** (`configuration.md`): Reads all whitelist files to determine what gets deployed.

9. **Site Assets Deployment** (`site-assets.md`): Deploys CSS, JavaScript, and other static files from `hh/deploy/site/` to `/srv/{project_name}/site/`.

## Deployment Workflow

The file deployment command is the core of the repeatable deployment workflow:

**Standard Deployment**:
```bash
sudo hen deploy
```

This single command:
- Stops all services
- Copies all whitelisted files
- Sets permissions
- Restarts all services
- Clears caches

After initial setup (installation, database, HTTP), the standard workflow is:
1. `hen pull_project` (see `git.md`) - Get latest code
2. `sudo hen deploy` - Deploy everything

See `workflows.md` for complete deployment workflow documentation.

**See also**: `hh/deploy/srv/deploy.py` function `deploy`

