# Maintenance Daemon

The maintenance daemon system consists of two distinct components with different deployment and access patterns:

- **`hh/deploy/maintenance/`**: Daemon management commands (start, stop, status) - stays in project folder, only accessible by human users or root tier
- **`hh/deploy/maint/`**: Maintenance tools and utilities - gets deployed to `/srv/{project_name}`, accessible by all agent tiers

## Prerequisites

Before using the maintenance daemon system, you must have:
- Installation system completed (see `installation.md`) - `{project_name}_root` user must exist
- File deployment completed (see `file-deployment.md`) - maintenance worker must be deployed
- Database deployment completed (see `database.md`) - cache database must exist
- Sudo/root privileges for starting/stopping daemon

The maintenance daemon system depends on:
- **Installation system** (`installation.md`): Runs as `{project_name}_root` user created during installation
- **File deployment** (`file-deployment.md`): Maintenance worker and tools are deployed to `/srv/{project_name}`
- **Database deployment** (`database.md`): Uses cache database to track stale caches and job queue
- **Cache management** (`cache.md`): Refreshes stale caches discovered via cache database

## Architecture Overview

The maintenance daemon (`worker.py`) runs continuously in the background, monitoring the job queue and stale caches. It executes maintenance tools from the `maint/` folder, which are registered as maintenance backend tools and accessible to all agent tiers.

**Key Distinction**:
- **maintenance/**: Administrative commands for managing the daemon itself (start/stop/status) - privileged access only
- **maint/**: Operational tools that the daemon uses (cache refresh, job queue, orphan checks) - deployed and accessible to all tiers

## Maintenance Daemon Management (maintenance/)

**Directory**: `hh/deploy/maintenance/`

These commands manage the lifecycle of the maintenance daemon process. They remain in the project folder and are only accessible by human users or root tier agents.

### Maintenance Worker

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
   - Pending jobs from `maintenance_jobs` table (by job_type) - stored in main database (see `database.md`)
   - Stale page cache refreshes - detected via cache database (see `database.md`)
   - Stale image cache refreshes - detected via cache database
   - Stale file cache refreshes - detected via cache database
3. **Execute Tasks**: Runs each task via `maintenance_client.py`
4. **Handle Responses**: Updates job status for job queue items, logs results for cache refreshes
5. **Sleep**: Adaptive delay based on work status

**Logging**:
- **Location**: `/srv/{project_name}/logs/maintenance_{project_name}.log` (deployed) or `{project_root}/logs/maintenance_{project_name}.log` (local dev)
- **Level**: Configurable via `MAINTENANCE_LOG_LEVEL` environment variable (default: DEBUG)
- **Output**: Both stderr (terminal) and log file
- **Heartbeat**: Logs status every 15 minutes when idle
- Log directory created by file deployment system (see `file-deployment.md`)

**Process Management**:
- **Deployed**: Runs as `{project_name}_root` user (created by `installation.md`), script at `/srv/{project_name}/{project_name}_maintenance.py` (deployed by `file-deployment.md`)
- **Local Dev**: Runs as current user, script at `{project_root}/hh/deploy/maintenance/worker.py`
- **Discovery**: Uses `maintenance_client.py` path resolution (deployed vs. local)

### Maintenance Start

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
   - **Deployed**: Runs as `{project_name}_root` user (from `installation.md`) in `/srv/{project_name}` (from `file-deployment.md`)
   - **Local**: Runs as current user in project root
   - Uses `start_background_process()` with log file redirection
5. **Verify**: Waits 1 second, then checks process list to confirm startup

**Returns**: Status dict with `status` (started/failed/error), `pids`, `log_file`, `deployed`, `user`

### Maintenance Stop

**File**: `hh/deploy/maintenance/maintenance_stop.py`

Stops the maintenance daemon process:

**Process Flow**:

1. **Find Processes**: Uses process filter (`{project_name}_maintenance.py` or `worker.py`)
2. **Kill Processes**: Sends termination signal to each running process
3. **Return Status**: Reports which PIDs were stopped

**Returns**: Status dict with `status` (stopped/not_running/error), `pids` (list of killed PIDs)

### Maintenance Status

**File**: `hh/deploy/maintenance/maintenance_status.py`

Checks the status of the maintenance daemon:

**Process Flow**:

1. **Check Worker Exists**: Verifies worker script exists
2. **Find Processes**: Lists running processes matching filter
3. **Return Status**: Reports running/stopped/not_found

**Returns**: Status dict with `status` (running/stopped/not_found/error), `pids`, `deployed`, `worker_path`

## Maintenance Tools (maint/)

**Directory**: `hh/deploy/maint/`

These tools are deployed to `/srv/{project_name}` and are accessible by all agent tiers. They are registered as maintenance backend tools and can be called by the daemon or manually.

### Maintenance Client

**File**: `hh/deploy/maint/maintenance_client.py`

Entry point for all maintenance commands. Acts as a thin wrapper around Gateway dispatch:

**Features**:
- UTF-8 encoding configuration for stdout/stderr
- Dispatches commands via Gateway with `"maintenance"` backend
- Returns JSON response to stdout
- Exit code: 1 if error, 0 if success

**Usage**: `python maintenance_client.py <command> [args...]`

### Maintenance Jobs Status

**File**: `hh/deploy/maint/maintenance_jobs_status.py`

Checks what maintenance work needs to be done:

**Action** (`maintenance_jobs_status_action`):
- Counts stale pages (where `last_modified > cache_built_at` or `cache_built_at IS NULL`) - queries cache database (see `database.md`)
- Counts stale images (where `COALESCE(last_modified, uploaded) > cache_built_at` or `cache_built_at IS NULL`) - queries cache database
- Counts stale files (where `COALESCE(last_modified, uploaded) > cache_built_at` or `cache_built_at IS NULL`) - queries cache database
- Gets pending jobs by type from `maintenance_jobs` table (status='pending') - queries main database (see `database.md`)
- Counts error jobs (status='error')
- Calculates `has_work` flag and `work_types` count

**Parser** (`maintenance_jobs_status_parser`):
- Renders table with stale counts, pending jobs, work status, error status
- Uses dynamic field types (work_available/no_work_available, job_errors/no_job_errors)

**Registered as**: Maintenance tool (accessible via maintenance backend)

### Cache Refresh Tools

Three similar tools for refreshing stale caches:

**Files**:
- `hh/deploy/maint/page_cache_refresh.py`
- `hh/deploy/maint/image_cache_refresh.py`
- `hh/deploy/maint/file_cache_refresh.py`

**Common Pattern**:

1. **Action**:
   - Fetches one stale item ID (by `last_modified` DESC) from cache database (see `database.md`)
   - If none found, returns "no work" response
   - If found, rebuilds cache for that item:
     - **Pages**: Calls `get_page(id).show_page()` to rebuild cache
     - **Images**: Calls `get_image(id).show_image()` to rebuild cache
     - **Files**: Calls `get_file(id).get_usage_data()` to rebuild cache
   - Updates cache database with new `cache_built_at` timestamp
   - Returns processed status, error (if any), and remaining count

2. **Parser**:
   - Renders table with item ID, refresh status, error (if any), remaining count
   - Uses conditional rows (only shows remaining if > 0)

**Registered as**: Maintenance tools (accessible via maintenance backend)

These tools integrate with the cache management system (see `cache.md`) to refresh stale caches discovered via the cache database (see `database.md`).

### Job Queue Management

**File**: `hh/deploy/maint/job_queue.py`

Core functions for managing the maintenance job queue:

**Key Functions**:

- **`claim_next_maintenance_job(job_type)`**: Claims next pending job of specified type
  - Uses optimistic locking (tries up to 5 times)
  - Updates status to 'running', increments attempts, sets started_at
  - Falls back to running jobs if no pending jobs found
  - Returns deserialized job dict (with `payload` and `progress` parsed from JSON)
  - Jobs stored in `maintenance_jobs` table in main database (see `database.md`)

- **`update_maintenance_job(job_id, status, progress, error_message)`**: Updates job status
  - Updates `progress_json`, `error_message`, `status`
  - Sets `started_at` if status='running'
  - Sets `completed_at` if status in {'done', 'error'}
  - Always increments `attempts` and updates `updated_at`
  - Updates `maintenance_jobs` table in main database (see `database.md`)

**Job Status Flow**:
- **pending** → **running** (when claimed)
- **running** → **pending** (if still in progress, with updated progress)
- **running** → **done** (when complete)
- **running** → **error** (on failure)

### Update Maintenance Job

**File**: `hh/deploy/maint/update_maintenance_job.py`

Command interface for updating maintenance job status:

**Action** (`update_maintenance_job_action`):
- Accepts: `job_id`, `status`, `progress` (JSON string), `error_message`
- Updates job in database via `job_queue.update_maintenance_job()` (uses main database - see `database.md`)
- Returns update status

**Parser** (`update_maintenance_job_parser`):
- Renders table with job_id, status, update success/failure

**Registered as**: Maintenance tool (accessible via maintenance backend)

### Orphan Checks

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

All checks query the main database (see `database.md`).

**Action** (`orphan_check_action`):
- Runs all checks and returns counts and ID lists

**Parser** (`orphan_check_parser`):
- Renders table with counts and ID previews (first 20 IDs)
- Conditionally shows IDs column only if orphans found

**Registered as**: Maintenance tool (accessible via maintenance backend)

### Maintenance Ping

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

### Additional Utilities

**Files**:
- `hh/deploy/maint/regex_text.py`: Text processing utilities (regex operations)
- `hh/deploy/maint/config_labels.py`: Configuration labels for maintenance tools

## Deployment Integration

**Deploy Whitelist**: The `maint/` folder is whitelisted in `DEPLOY_WHITELIST` (see `configuration.md`), so it survives deployment cleanup and is available in `/srv/{project_name}/hh/deploy/maint/`.

**Maintenance Worker Deployment**: During file deployment (see `file-deployment.md`), `worker.py` is copied to `/srv/{project_name}/{project_name}_maintenance.py` for execution.

**Maintenance Client Deployment**: `maintenance_client.py` is deployed to `/srv/{project_name}/maintenance_client.py` (top level) for easy access by file deployment system (see `file-deployment.md`).

## Access Control

- **maintenance/** commands: Only accessible by human users or root tier (stays in project folder)
- **maint/** tools: Accessible by all agent tiers (deployed, registered as maintenance backend tools)

## Registration Pattern

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

## Integration with Other Systems

The maintenance daemon system integrates with:

1. **Installation System** (`installation.md`): Runs as `{project_name}_root` user created during installation.

2. **File Deployment** (`file-deployment.md`): Maintenance worker and tools are deployed to `/srv/{project_name}`. The file deployment system automatically starts the maintenance daemon after deployment.

3. **Database Deployment** (`database.md`): Uses cache database to track stale caches (`cache_built_at` timestamps). Uses main database to store and manage job queue (`maintenance_jobs` table).

4. **Cache Management** (`cache.md`): Refreshes stale caches discovered via cache database. Cache refresh tools update cache database with new `cache_built_at` timestamps.

5. **Configuration System** (`configuration.md`): The `maint/` folder is whitelisted in `DEPLOY_WHITELIST` to survive deployment cleanup.

## Deployment Workflow

The maintenance daemon is automatically managed during file deployment:

**During File Deployment**:
- Maintenance worker is deployed to `/srv/{project_name}/{project_name}_maintenance.py`
- Maintenance daemon is stopped before deployment
- Maintenance daemon is started after deployment

**Manual Management**:
```bash
sudo hen maintenance-start    # Start maintenance daemon
sudo hen maintenance-stop     # Stop maintenance daemon
hen maintenance-status        # Check status of maintenance daemon
```

See `workflows.md` for complete deployment workflow documentation.

