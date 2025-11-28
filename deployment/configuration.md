# Configuration System

The configuration system manages whitelists, blacklists, and application settings that control what gets deployed and how the system behaves.

## Prerequisites

Before using the configuration system, you must have:
- Project folder with `hh/deploy/conf/` directory structure
- Configuration files must exist (they are part of the codebase)

The configuration system is used by:
- **File deployment** (`file-deployment.md`): Reads all whitelists to determine what gets deployed
- **HTTP/NGINX deployment** (`http-nginx.md`): Reads whitelists to configure static file serving
- **Site assets deployment** (`site-assets.md`): Uses whitelists to determine which files are deployed
- **Installation system** (`installation.md`): Uses `HENHOUSE_TIERS` to determine user tiers

## Configuration Files Location

**Directory**: `hh/deploy/conf/`

All configuration files are whitelisted to survive deployment cleanup (see `file-deployment.md`). The `conf/` folder is included in `DEPLOY_WHITELIST` so it remains in `/srv/{project_name}/hh/deploy/conf/` after deployment.

## Deploy Whitelist

**File**: `hh/deploy/conf/deploy_whitelist.py`

Defines what stays in the `hh/deploy/` folder after deployment cleanup:

- **`DEPLOY_WHITELIST`**: Items preserved in deploy folder:
  - `'cache'` - Cache cleanup registry and utilities (see `cache.md`)
  - `'conf'` - Configuration whitelists (self-preserving)
  - `'maint'` - Maintenance helpers (see `maintenance.md`)
  - `'utils.py'` - General deployment utilities
- **`FLASK_APP_SOURCE`**: Path to Flask app source (`hh/deploy/flask/app.py`) - used by file deployment (see `file-deployment.md`)
- **`MAINTENANCE_APP_SOURCE`**: Path to maintenance worker (`hh/deploy/maintenance/worker.py`) - used by file deployment (see `file-deployment.md`)
- **`EXTRA_DEPLOY_FILES`**: Additional files deployed to `/srv/{project_name}`:
  - `hh/deploy/flask/http_client.py` (see `flask.md`)
  - `hh/deploy/flask/mcp_client.py` (see `flask.md`)
  - `hh/deploy/maint/maintenance_client.py` (see `maintenance.md`)

## Context Whitelist/Blacklist

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

These whitelists are used by file deployment (see `file-deployment.md`) to deploy context files to `/srv/{project_name}/context/`.

## File Type Whitelists

### Python Whitelist

**File**: `hh/deploy/conf/py_whitelist.py`

- **`PY_WHITELIST`**: Python files deployed to `/srv/{project_name}/site/py/`
- Currently includes: `hh/deploy/site/infographic/infographic.py`

Used by file deployment (see `file-deployment.md`) and site assets deployment (see `site-assets.md`).

### JavaScript Whitelist

**File**: `hh/deploy/conf/js_whitelist.py`

- **`JS_ALWAYS_INCLUDE`**: JavaScript files included on every page:
  - `seed.js`, `rpc-client.js`, `app.js`
- **`JS_WHITELIST`**: All JavaScript files that can be included via `gateway.add_js_link()`
  - Includes overlay system files, page data files, infographic files
  - Files deployed flat to `site/js/` (overlay subfolder files flattened)

Used by file deployment (see `file-deployment.md`), HTTP/NGINX deployment (see `http-nginx.md`), and site assets deployment (see `site-assets.md`).

### CSS Whitelist

**File**: `hh/deploy/conf/css_whitelist.py`

- **`CSS_ALWAYS_INCLUDE`**: CSS files included on every page:
  - `site.css`, `ansi-colors.css`, `tables.css`, `pygments.css`, `overlay.css`
- **`CSS_WHITELIST`**: All CSS files that can be included via `gateway.add_css_link()`
  - Includes tier-specific CSS files (site-guest.css, site-verified.css, site-admin.css, site-root.css)
  - Infographic CSS files

Used by file deployment (see `file-deployment.md`), HTTP/NGINX deployment (see `http-nginx.md`), and site assets deployment (see `site-assets.md`).

### Miscellaneous Whitelist

**File**: `hh/deploy/conf/misc_whitelist.py`

- Additional files and patterns for deployment
- Includes favicons, web manifests, and other static assets

Used by file deployment (see `file-deployment.md`), HTTP/NGINX deployment (see `http-nginx.md`), and site assets deployment (see `site-assets.md`).

## Application Actions

**File**: `hh/deploy/conf/application_actions.py`

Defines application action links for admin/root tier CRUD operations:

- **`populate_application_action_links(page_id=None)`**: Populates action links in gateway response
- Groups are created explicitly with names, then actions added to groups
- Actions have DOM IDs for JavaScript event handlers (no hrefs)
- Used for testing and development UI features

## Other Configuration Files

- **`deploy_whitelist.py`**: NGINX deployment whitelist configuration (used by HTTP/NGINX deployment - see `http-nginx.md`)
- **`site_links.py`**: Site navigation links configuration
- **`user_info.py`**: User information configuration
- **`user_account_suffixes.py`**: Defines `HENHOUSE_TIERS` constant (`['guest', 'verified', 'admin', 'root']`)
  - Used by installation system (see `installation.md`) to create tier users
  - Used by database deployment (see `database.md`) to create tier-specific database users
  - Used by Flask application management (see `flask.md`) to create tier-specific Flask instances
  - Used by HTTP/NGINX deployment (see `http-nginx.md`) to route subdomains to tier-specific Flask apps

## Deployment Utilities

**File**: `hh/deploy/utils.py`

Core utility function used throughout deployment:

- **`detect_project_context()`**: Detects project name and root directory
  - Walks up directory tree from current working directory
  - Looks for `hh/` directory to identify project root
  - Returns tuple: `(project_name, project_root_path)`
  - Used by cache cleanup (see `cache.md`), deployment scripts (see `file-deployment.md`), git operations (see `git.md`), and other utilities

The `utils.py` file is whitelisted in `DEPLOY_WHITELIST` to survive deployment cleanup.

## Integration with Other Systems

The configuration system integrates with:

1. **File Deployment** (`file-deployment.md`): 
   - Reads all whitelists to determine what gets deployed
   - The `conf/` folder is whitelisted to survive deployment cleanup
   - Uses `DEPLOY_WHITELIST` to determine which items stay in deploy folder

2. **HTTP/NGINX Deployment** (`http-nginx.md`): 
   - Reads whitelists (`JS_WHITELIST`, `CSS_WHITELIST`, `MISC_WHITELIST`, `CONTEXT_WHITELIST`) to configure static file serving
   - Generates NGINX location blocks for whitelisted files

3. **Site Assets Deployment** (`site-assets.md`): 
   - Uses whitelists to determine which CSS, JavaScript, and other files are deployed
   - All site assets are controlled by whitelist files

4. **Installation System** (`installation.md`): 
   - Uses `HENHOUSE_TIERS` from `user_account_suffixes.py` to determine user tiers

5. **Database Deployment** (`database.md`): 
   - Uses `HENHOUSE_TIERS` to determine which database users to create

6. **Flask Application Management** (`flask.md`): 
   - Uses `HENHOUSE_TIERS` to determine which Flask instances to create

7. **Cache Management** (`cache.md`): 
   - The `cache/` folder is whitelisted in `DEPLOY_WHITELIST` to survive deployment cleanup

8. **Maintenance Daemon** (`maintenance.md`): 
   - The `maint/` folder is whitelisted in `DEPLOY_WHITELIST` to survive deployment cleanup

## Deployment Workflow

Configuration files are automatically preserved during deployment:

**During File Deployment**:
- The `conf/` folder is whitelisted and survives deployment cleanup
- All whitelist files are read to determine what gets deployed
- Configuration files remain available in `/srv/{project_name}/hh/deploy/conf/` after deployment

**Modifying Whitelists**:
- Edit whitelist files in `hh/deploy/conf/`
- Run `sudo hen deploy` to apply changes
- Whitelist changes take effect on next deployment

See `workflows.md` for complete deployment workflow documentation.

