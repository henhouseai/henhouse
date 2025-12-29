# Chapter 8: File Deployment

## Overview

Deploying populates `/srv` with the code that will run for web requests, MCP commands, and daemons. This automatically starts Flask applications and the maintenance daemon.

## Prerequisites

Before deploying, ensure you have:

1. **Chapter 5**: Installation completed
2. **Chapter 7**: Database setup completed
3. **Log out and log back in**: After installation, you must log out and log back in to refresh SSH group permissions

## Deployment Process

### Step 1: Deploy

After installation completes and you've logged back in:

```bash
# Deploy the application
sudo {hen_script_name} deploy
```

**What this does**:
- Copies whitelisted files to `/srv/{project_name}`
- Sets permissions and ownership
- Prepares the production environment
- Automatically stops and restarts Flask applications
- Automatically stops and restarts maintenance daemon

**Important**: You can't do NGINX deployment until code is deployed to `/srv` first, because NGINX configuration is generated from the deployed code.

## Technical Details: Deployment Process Flow

The `deploy` command (`hh/deploy/srv/deploy.py`) performs a comprehensive 16-step deployment process:

### Step 1: Stop Running Daemons

Before deployment begins, all running services are stopped:
- **Maintenance daemon**: Stopped via `run_maintenance_stop(project_name)`
- **Flask daemons**: Stopped via `run_flask_stop(project_name)`

This ensures clean deployment without running processes holding file locks.

### Step 2: Preserve Git Repository

The git repository is preserved across deployments:
- **Temporary move**: `/srv/{project_name}/git` → `/srv/{project_name}_git` (temporary location)
- **Restoration**: Git folder restored after deployment directory sterilization

This preserves the bare git repository and all git history created by the installation system.

### Step 3: Sterilize Deployment Directory

The entire `/srv/{project_name}` directory is cleaned:
- **Removes all contents** except preserved git folder
- If directory doesn't exist, creates it
- Ensures clean slate for each deployment

### Step 4: Deploy Main Code

Copies the entire `hh/` folder to `/srv/{project_name}/hh/`:
- Uses `shutil.copytree()` to copy entire directory structure
- All Python modules, subdirectories, and files are copied
- This is the core framework code

### Step 4.5: Deploy Extension Code (if exists)

Copies the entire `ext/` folder to `/srv/{project_name}/ext/` (if the folder exists):
- Uses `shutil.copytree()` to copy entire directory structure
- All Python modules, subdirectories, and files are copied
- This is project-specific customization code (optional)
- If `ext/` folder doesn't exist, this step is skipped

### Step 5: Clean Extension Deploy Folder (if ext/ was deployed)

**If ext/ folder was deployed**: The `ext/deploy/` folder is cleaned while preserving whitelisted items:
- Whitelisted items from `EXT_DEPLOY_WHITELIST` are temporarily moved out
- Entire `ext/deploy/` directory is removed
- `ext/deploy/` directory is recreated and whitelisted items are restored
- Base whitelist: `['conf']` (can be extended in `ext/deploy/conf/deploy_whitelist.py`)

### Step 6: Clean Deploy Folder (Preserve Whitelisted Items)

**Critical Process**: The `hh/deploy/` folder is cleaned while preserving essential items:

1. **Temporary preservation**: Whitelisted items moved to temporary locations:
   - `cache/` → `/srv/{project_name}/.{project_name}_cache_tmp`
   - `conf/` → `/srv/{project_name}/.{project_name}_conf_tmp`
   - `maint/` → `/srv/{project_name}/.{project_name}_maint_tmp`
   - `utils.py` → `/srv/{project_name}/.{project_name}_utils_py_tmp`

2. **Deploy folder removal**: Entire `hh/deploy/` directory is removed

3. **Recreate and restore**: Deploy directory recreated, whitelisted items restored

This ensures only essential deployment utilities remain in the deploy folder after deployment, while all deployment scripts (db/, flask/, http/, users/, etc.) are removed since they're only needed during deployment, not in production.

The whitelist is defined in `hh/deploy/conf/deploy_whitelist.py`.

### Step 7: Clean Cache Files

Removes all cache files from deployment:
- **`__pycache__` directories**: Recursively removed
- **`.pyc` files**: All Python bytecode files removed
- **Cache JSON files**: `*-reg.json`, `*.cycle.json`, `cache.json`, `*.cache` patterns
- **`.cache` directories**: Recursively removed

This ensures clean deployment without stale cache files.

### Step 8: Deploy Flask Applications

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

### Step 9: Deploy Maintenance Worker

Creates the maintenance worker script:
- **Source**: `hh/deploy/maintenance/worker.py`
- **Destination**: `/srv/{project_name}/{project_name}_maintenance.py`
- **Template replacement**: `__PROJECT_NAME__` replaced with actual project name

### Step 10: Deploy Extra Top-Level Files

Copies additional files specified in `EXTRA_DEPLOY_FILES`:
- `hh/deploy/flask/http_client.py` → `/srv/{project_name}/http_client.py`
- `hh/deploy/flask/mcp_client.py` → `/srv/{project_name}/mcp_client.py`
- `hh/deploy/maint/maintenance_client.py` → `/srv/{project_name}/maintenance_client.py`

These are entry point scripts used by the deployed applications.

### Step 11: Deploy Context Folders and Files

Deploys documentation and context files for agent visibility:
- **Destination**: `/srv/{project_name}/context/`
- **Whitelist**: Items from `CONTEXT_WHITELIST` (context/, planning/, hh/, top-level scripts, README.md, LICENSE, requirements.txt)
- **Blacklist filtering**: Excludes patterns from `CONTEXT_BLACKLIST` (.git, __pycache__, *.pyc, node_modules, .env, *.log, cache JSON files)
- **Structure**: Maintains directory structure under `context/` subdirectory

### Step 12: Deploy Site Files

Deploys static site assets to `/srv/{project_name}/site/`:
- **JavaScript files** (`JS_WHITELIST`): Deployed to `site/js/`
- **CSS files** (`CSS_WHITELIST`): Deployed to `site/css/`
- **Python files** (`PY_WHITELIST`): Deployed to `site/py/`
- **Miscellaneous files** (`MISC_WHITELIST`): Deployed to `site/` root

See "Site Assets Deployment" section below for details.

### Step 13: Set Ownership and Permissions

Sets proper Unix ownership and permissions:

- **Main deployment**: 
  - Owner: `{project_name}_root` (highest tier user)
  - Group: `{project_name}_deploy` (deployment group)
  - Directories: `0o750` (owner:rwx, group:r-x, others:---)
  - Files: `0o640` (owner:rw-, group:r--, others:---)

- **Git directory** (special permissions):
  - Owner: `{project_name}_root`
  - Group: `{project_name}` (project group, not deploy group)
  - Directories: `0o770` (owner:rwx, group:rwx, others:---)
  - Files: `0o660` (owner:rw-, group:rw-, others:---)

### Step 14: Set Up Cache Directory Permissions

Configures cache directories discovered via cache registry:
- **Discovery**: Uses `get_cache_directories()` from cache cleanup registry
- **Permissions**: `0o2775` (setgid for group write, owner:rwx, group:rwx, others:r-x)
- **Ownership**: `{project_name}_root:{project_name}_deploy`
- **Creation**: Creates cache directories if they don't exist

This allows all tier users (in deploy group) to write cache files via group permissions.

### Step 15: Set Up Logs Directory

Creates and configures logs directory:
- **Path**: `/srv/{project_name}/logs/`
- **Permissions**: `0o2775` (setgid for group write)
- **Ownership**: `{project_name}_root:{project_name}_deploy`
- **Purpose**: Flask daemons and maintenance worker write logs here

### Step 16: Restart Daemons

Starts services after deployment completes:
- **Flask daemons**: Started via `run_flask_start(project_name, start_port)`
- **Maintenance daemon**: Started via `run_maintenance_start(project_name)`
- Services start with new code and proper permissions in place

### Step 17: Clear Registry Cache

Calls `clean_all_caches()` from cache cleanup registry:
- Prevents permission issues from stale cache files
- Ensures clean state after deployment

## Technical Details: Integration with Other Systems

The `deploy` command integrates automatically with several other systems:

### Integration with Service Management

- **Automatic Daemon Management**: The `deploy` command automatically stops all running Flask and maintenance daemons before deployment begins (Step 1) and restarts them after deployment completes (Step 16)
- **No Manual Intervention**: You don't need to manually stop or start daemons during normal deployment cycles - the deploy command handles this automatically
- **Clean Deployment**: Stopping daemons before deployment ensures no running processes hold file locks or use old code during the deployment process
- **Service Restart**: After files are deployed and permissions are set, daemons restart automatically with the new code

### Integration with Database

- **No Database Changes Required**: Code deployments do not require any database schema changes or database operations
- **Database Independence**: The database remains unchanged during code deployments - only application code files are updated
- **Database Operations Separate**: Database initialization (`init-db`) and user creation (`add-db-users`) are one-time setup operations that happen before deployment, not during code deployments

### Integration with HTTP/NGINX

- **No NGINX Reconfiguration Required**: Code deployments do not require NGINX configuration changes
- **NGINX Configuration Separate**: NGINX configuration (`http-deploy`, `http-deploy-ssl`) is a one-time setup operation that happens after initial deployment
- **Static File Serving**: NGINX continues serving static files from `/srv/{project_name}/site/` without any configuration changes needed for code redeployments
- **Flask Proxy**: NGINX continues proxying to Flask daemons on the same ports - no port changes occur during code deployments

### Integration with Cache Management

- **Automatic Cache Clearing**: The `deploy` command automatically clears registry caches after deployment completes (Step 17)
- **Prevents Stale State**: Cache clearing ensures that registry caches, Python bytecode caches, and other cached files don't contain stale data from the previous deployment
- **Integration Point**: This integration ensures that when code is deployed, all cached data is refreshed to match the new code state
- **No Manual Steps Required**: Cache clearing happens automatically as part of the deployment operation

### Step 2: Verify Daemons

Check that Flask apps and maintenance daemon are running:

```bash
# Check Flask daemon status (4 instances, one per tier)
{hen_script_name} flask-status

# Check maintenance daemon status
{hen_script_name} maintenance-status
```

You should see:
- Four Flask daemons running (ports 5001-5004), one for each tier (guest, verified, admin, root)
- One maintenance daemon running for cache refresh and job processing

**Note**: If you need to stop them, use `{hen_script_name} flask-stop` and `{hen_script_name} maintenance-stop`, but note that they will automatically restart the next time you run `sudo {hen_script_name} deploy`.

**Auto-start on server reboot**: Auto-start on server reboot is not yet enabled. If your server reboots, you'll need to manually start the daemons using `sudo {hen_script_name} flask-start` and `sudo {hen_script_name} maintenance-start`.

### Step 3: Test Push/Pull/Deploy Cycle

Now test the full workflow:

```bash
# On developer box: make changes, commit, push
git push origin {project_name}

# On deployment box: pull and deploy
{hen_script_name} pull-project && sudo {hen_script_name} deploy
```

This is your standard deployment workflow: make changes locally, push to server, pull on server, and deploy.

## What This Enables

- **Production code deployment**: All whitelisted files copied to `/srv/{project_name}`
- **Entry points**: Can use `{hen_script_name}` command instead of `python hen.py` on server
- **Full deployment workflow**: Make changes locally, push, pull, and deploy in one cycle
- **Running Flask applications**: Four tier-based Flask daemons serving web and MCP requests
- **Maintenance daemon**: Background worker for cache refresh and job processing
- **Code ready for web requests, MCP commands, and daemons**

## Deployment Workflow

The standard deployment workflow is:

1. **On developer box**: Make changes, commit, push
   ```bash
   git add .
   git commit -m "your changes"
   git push origin {project_name}
   ```

2. **On deployment box**: Pull and deploy
   ```bash
   {hen_script_name} pull-project && sudo {hen_script_name} deploy
   ```

The `deploy` command automatically:
- Stops running daemons (see Technical Details: Integration with Other Systems)
- Copies whitelisted files
- Sets permissions
- Restarts daemons (see Technical Details: Integration with Other Systems)
- Clears caches (see Technical Details: Integration with Other Systems)

**Integration with Git Operations**: The standard deployment workflow is `pull-project` → `deploy`. The `pull-project` command syncs code from remote and clears caches, then `deploy` handles file copying and service management. These commands are designed to work together in a repeatable workflow.

## Site Assets Deployment

The deployment process includes deployment of static web assets (CSS, JavaScript, favicons, etc.) to `/srv/{project_name}/site/`. These assets are served directly by NGINX and are controlled by whitelist files.

### CSS Stylesheets

**Directory**: `/srv/{project_name}/site/css/`

The CSS system uses a separation of concerns approach:

**Base Stylesheet** (`site.css`):
- **Purpose**: Layout, structure, and formatting (no colors)
- **Content**: Box model, typography, container structure, link base styles, component layouts
- **Philosophy**: Defines *how* things are laid out, not *what* they look like

**Tier-Specific Color Schemes**:
Each user tier has its own color theme stylesheet:
- `site-guest.css`: Dark theme with blue accents (public/guest tier)
- `site-verified.css`: Color scheme for verified tier
- `site-admin.css`: Orange/amber theme (admin tier)
- `site-root.css`: Color scheme for root tier

**Color Organization**:
- Colors are defined in tier-specific files, not hardcoded in base styles
- Each tier file defines CSS variables and color values for body background, text colors, link colors, container backgrounds, borders, heading colors, status box colors, button colors, and border colors
- This allows visual identification of which portal/tier you're logged into

**Supporting Stylesheets** (always included):
- `ansi-colors.css`: ANSI terminal color codes for code output
- `tables.css`: Table styling and formatting
- `pygments.css`: Syntax highlighting for code blocks
- `overlay.css`: Overlay/modal dialog styling

### JavaScript Files

**Directory**: `/srv/{project_name}/site/js/`

**Note**: JavaScript files in this directory are compiled from TypeScript source.

**Source Directories**:
- **`hh/deploy/site/ts/`**: Framework TypeScript source files
- **`ext/deploy/site/ts/`**: Extension TypeScript source files (project-specific, optional)

**Compilation Process**:
1. TypeScript source files in `hh/deploy/site/ts/` and `ext/deploy/site/ts/` are compiled using `tsc` from project root (see `tsconfig.json`)
2. Compiled output preserves directory structure:
   - `hh/deploy/site/ts/**/*.ts` → `hh/deploy/site/js/hh/deploy/site/ts/**/*.js`
   - `ext/deploy/site/ts/**/*.ts` → `hh/deploy/site/js/ext/deploy/site/ts/**/*.js`
3. The entire `hh/deploy/site/js/` directory (containing both `hh/` and `ext/` compiled output) is whitelisted for deployment
4. All compiled JavaScript files (from both `hh/` and `ext/`) are placed in the same `hh/deploy/site/js/` directory, maintaining their original path structure within that directory

**Deployed Structure**:
- Main application files (`app.js`, `page-manager.js`, `rpc-client.js`)
- Page data handlers (`work-page-data.js`, `mcp-request-page-data.js`, etc.)
- Overlay system (`overlay/` subdirectory)
- Utility files (`debug-helper.js`, `upload-handler.js`, `seed.js`)

**Note**: TypeScript source files (`*.ts`) are not deployed - only the compiled JavaScript output is deployed to production.

### Favicon and Web Assets

**Top-level files** in `/srv/{project_name}/site/`:

- `favicon.ico`: Main favicon (15KB)
- `favicon-16x16.png`: 16x16 PNG favicon
- `favicon-32x32.png`: 32x32 PNG favicon
- `apple-touch-icon.png`: iOS home screen icon (9KB)
- `android-chrome-192x192.png`: Android icon 192x192 (10KB)
- `android-chrome-512x512.png`: Android icon 512x512 (35KB)
- `site.webmanifest`: PWA manifest file (defines icons, theme colors)
- `ajaxloading.gif`: Loading animation (404B)

### Python Files

**Directory**: `/srv/{project_name}/site/py/`

Python files can be deployed to the site directory (currently includes `infographic.py` for the infographic module).

### Infographic Module

**Directory**: `/srv/{project_name}/site/infographic/`

**Note**: This is a standalone, project-specific module for creating flowcharts and diagrams. It's currently used for Henhouse's self-documentation but is not part of the core system.

**Purpose**: Demonstrates how to add custom modules to the site deployment:
1. Add files to `hh/deploy/site/infographic/`
2. Whitelist CSS/JS files in respective whitelists
3. Files are automatically deployed with the rest of the site

## Technical Details: Site Assets Deployment Process

The deploy script (`hh/deploy/srv/deploy.py`) handles site folder deployment:

1. **Site Directory Setup**:
   - Creates `/srv/{project_name}/site/` directory
   - Clears existing site directory if present

2. **JavaScript Deployment**:
   - Reads `JS_WHITELIST` from `hh/deploy/conf/js_whitelist.py`
   - Base whitelist includes `'hh/deploy/site/js'` (entire compiled TypeScript output directory)
   - Extension whitelist can add `'ext/deploy/site/js'` or individual files
   - For each whitelisted directory, recursively finds all `.js` files using `rglob('*.js')`
   - Copies all `.js` files to `site/js/`, preserving subdirectory structure
   - No special processing - just copies the compiled TypeScript output as-is

3. **CSS Deployment**:
   - Reads `CSS_WHITELIST` from `hh/deploy/conf/css_whitelist.py`
   - Copies whitelisted CSS files to `site/css/`
   - Includes base stylesheet and tier-specific color schemes

4. **Python File Deployment**:
   - Reads `PY_WHITELIST` from `hh/deploy/conf/py_whitelist.py`
   - Copies whitelisted Python files to `site/py/` (if any)

5. **Miscellaneous File Deployment**:
   - Reads `MISC_WHITELIST` from `hh/deploy/conf/misc_whitelist.py`
   - Copies whitelisted files to `site/` (top level)
   - Handles both files and directories (favicons, web manifest, etc.)

**Deployment Statistics**: The deploy script logs counts of deployed items (JS, CSS, PY, MISC) for verification.

**Source Directory Structure**: Site assets are organized in `hh/deploy/site/`:
- **`css/`**: Stylesheets (tier-specific color schemes, layout, syntax highlighting)
- **`js/`**: JavaScript files (compiled from TypeScript source in `ts/` subdirectory)
- **`infographic/`**: Standalone infographic module (optional, project-specific)
- **Top-level files**: Favicon files, `site.webmanifest`, `ajaxloading.gif`

**Integration with HTTP/NGINX**: Site assets deployed to `/srv/{project_name}/site/` are served directly by NGINX (see Chapter 9). NGINX reads the same whitelist files to generate location blocks for static file serving. Static files are served with no-cache headers (`Cache-Control: no-cache, no-store, must-revalidate`) to prevent stale content.

## Technical Details: File Whitelisting System

All site assets are controlled by whitelist files in `hh/deploy/conf/`:

- **`css_whitelist.py`**: Defines `CSS_ALWAYS_INCLUDE` and `CSS_WHITELIST`
- **`js_whitelist.py`**: Defines `JS_WHITELIST` and `JS_ALWAYS_INCLUDE`
- **`py_whitelist.py`**: Defines `PY_WHITELIST` (if Python files are needed)
- **`misc_whitelist.py`**: Defines `MISC_WHITELIST` for top-level files

**Path Format**: All paths in whitelists are relative to project root (above `hh/` folder).

**Key Principle**: Only explicitly whitelisted files are deployed. Everything else is excluded by default.

## Troubleshooting

### Permission Denied During Deploy

**Problem**: Deploy fails with permission errors

**Solutions**:
1. Ensure you're running with sudo: `sudo {hen_script_name} deploy`
2. Verify you logged out and back in after installation (group permissions)
3. Check `/srv/{project_name}` directory permissions

### Daemons Don't Start

**Problem**: Flask or maintenance daemons don't start after deploy

**Solutions**:
1. Check daemon status: `{hen_script_name} flask-status` and `{hen_script_name} maintenance-status`
2. Check log files: `/srv/{project_name}/logs/flask_{project_name}_{tier}.log`
3. Verify database is accessible (see Chapter 7)
4. Manually start daemons: `sudo {hen_script_name} flask-start` and `sudo {hen_script_name} maintenance-start`

### Files Not Deployed

**Problem**: Some files are missing after deployment

**Solutions**:
1. Check whitelist configuration (see `configuration.md`)
2. Verify files are in correct directories (`hh/` or `ext/`)
3. Check for blacklist patterns that might exclude your files
4. Review deployment output for errors

## Next Steps

After file deployment is complete:

1. **HTTP/NGINX**: Configure web server (see Chapter 9)
2. **Daemon Management**: Verify and manage Flask and maintenance daemons (see Chapter 10)

