# Chapter 10: Flask and Maintenance Daemons

## Overview

Verify and manage the background services that power your Henhouse installation. Flask daemons serve web and MCP requests, while the maintenance daemon handles cache refresh and job processing.

## Prerequisites

Before managing daemons, ensure you have:

1. **Chapter 8**: File deployment completed (daemons are started automatically)
2. **Chapter 7**: Database setup completed (daemons need database access)

## Verify Daemon Status

Check that all services are running properly:

```bash
# Check Flask daemon status (4 instances, one per tier)
{hen_script_name} flask-status

# Check maintenance daemon status
{hen_script_name} maintenance-status
```

You should see:
- **Four Flask daemons running** (ports 5001-5004), one for each tier (guest, verified, admin, root)
- **One maintenance daemon running** for cache refresh and job processing

## Daemon Management

### Stop Daemons

If you need to stop daemons:

```bash
# Stop Flask daemons
sudo {hen_script_name} flask-stop

# Stop maintenance daemon
sudo {hen_script_name} maintenance-stop
```

**Important**: Every time you run `sudo {hen_script_name} deploy`, the daemons are automatically stopped before deployment and restarted after deployment. You don't need to manually manage them during normal deployment cycles.

### Start Daemons

If daemons are stopped, start them:

```bash
# Start Flask daemons
sudo {hen_script_name} flask-start

# Start maintenance daemon
sudo {hen_script_name} maintenance-start
```

**Auto-start on server reboot**: Auto-start on server reboot is not yet enabled. If your server reboots, you'll need to manually start the daemons using the commands above.

## What This Enables

- **Full system operation**: Web interface, MCP server, and automated maintenance all running
- **MCP commands in Cursor chat**: Agents can run MCP tools to update database content and make changes
- **Automated maintenance**: Cache refresh and job processing happen in the background
- **Customizable MCP server**: You can extend it with your own MCP commands in the `ext/` folder

## Flask Daemon Architecture

Henhouse deploys multiple Flask application instances, one per user tier:

- **Guest tier**: `{project_name}_guest.py` on port 5001 (or `flask_start_port`)
- **Verified tier**: `{project_name}_verified.py` on port 5002 (or `flask_start_port + 1`)
- **Admin tier**: `{project_name}_admin.py` on port 5003 (or `flask_start_port + 2`)
- **Root tier**: `{project_name}_root.py` on port 5004 (or `flask_start_port + 3`)

Each instance:
- Runs as its corresponding Unix user (`{project_name}_{tier}`)
- Serves content with tier-appropriate permissions
- Has its own log file: `/srv/{project_name}/logs/flask_{project_name}_{tier}.log`
- Listens on `127.0.0.1` (localhost only, proxied by NGINX)
- Connects to database using tier-specific credentials

## Technical Details: Flask Application Architecture

The Flask application (`hh/deploy/flask/app.py`) handles HTTP requests and routes them to the Gateway system.

**Tier Detection**:
- Extracts tier from script name: `{project_name}_{tier}.py` → `tier`
- Falls back to environment variable or defaults to empty string

**Configuration**:
- **Project root**: `/srv/{project_name}`
- **Site directory**: `/srv/{project_name}/site`
- **Log file**: `/srv/{project_name}/logs/flask_{project_name}_{tier}.log`
- **Secret key**: Environment variable or default
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

2. **`/img/<path:image_path>`** - Image page display:
   - Only accepts numeric image IDs (strict validation)
   - Routes to `http_client.py` with `show-image --id {id}` command
   - Returns JSON or HTML based on response content

3. **`/img/<int:image_id>/download`** - Image download:
   - Downloads full-size image file
   - Uses download backend via `download_client.py`
   - Serves image file with `Content-Disposition` header

4. **`/file/<int:file_id>`** - File page display:
   - Shows file information page
   - Routes to `http_client.py` with `show-file --id {file_id}` command

5. **`/file/<int:file_id>/download`** - File download:
   - Downloads file
   - Uses download backend via `download_client.py`
   - All file downloads go through this route for gated access

6. **`/audio/<int:audio_id>`** - Audio page display:
   - Shows audio information page
   - Routes to `http_client.py` with `show-audio --id {audio_id}` command

7. **`/audio/<int:audio_id>/stream`** - Audio streaming:
   - Streams audio file for playback in browser
   - Uses download backend via `download_client.py`
   - Supports HTTP range requests for seeking (via Flask's `send_file()` with `conditional=True`)

8. **`/video/<int:video_id>`** - Video page display:
   - Shows video information page
   - Routes to `http_client.py` with `show-video --id {video_id}` command

9. **`/video/<int:video_id>/stream`** - Video streaming:
   - Streams video file for playback in browser
   - Uses download backend via `download_client.py`
   - Supports HTTP range requests for seeking

10. **`/` and `/<path:path>`** - Dynamic page routing:
    - Always routes to `show-page` command
    - **Numeric paths**: Treated as page ID (e.g., `/123` → `show-page --id 123`)
    - **Non-numeric paths**: Treated as page name (e.g., `/Bob/Sally` → `show-page --name Bob/Sally`)
    - Empty path defaults to page ID 1 (homepage)
    - Routes to `http_client.py` via subprocess

11. **`/upload-file`** - File upload handler:
    - Accepts multipart/form-data POST requests
    - Saves files to `/tmp` with UUID names
    - Returns JSON with temp file paths and metadata
    - Used by MCP tools that need file uploads

**Gateway Integration**:
- All requests routed via subprocess to `http_client.py` or `mcp_client.py`
- Uses semaphore for concurrency control (prevents too many simultaneous Gateway calls)
- 10-second timeout per request
- Passes tier via `USER_TIER` environment variable
- Connects to database using tier-specific credentials

## Technical Details: MCP Client

The MCP client (`hh/deploy/flask/mcp_client.py`) is the entry point for MCP requests from Flask.

**MCP Protocol Support**:
- **Protocol Version**: `2024-11-05`
- **Methods**: `initialize`, `tools/list`, `tools/call`, `prompts/list`, `resources/list`, `notifications/initialized`

**Process Flow**:
1. **Read JSON-RPC Request**: Reads from stdin (POST body from Flask), validates JSON-RPC 2.0 structure
2. **Handle Protocol Methods**:
   - **`initialize`**: Returns server capabilities and info
   - **`tools/list`**: Returns tier-filtered tool list via `MCPWhitelist.list_tools(tier)`
   - **`tools/call`**: Validates tool access via `MCPWhitelist.validate_tool()`, routes to Gateway
   - **`prompts/list`**: Returns empty list (not implemented)
   - **`resources/list`**: Returns empty list (not implemented)
3. **Tool Execution**: Validates tool name and arguments for tier, builds argv array `[tool_name, --arg1, value1, ...]`, dispatches to Gateway with "mcp" backend, formats response as JSON-RPC 2.0

**Tier Detection**: Gets tier from `USER_TIER` environment variable (set by Flask app), validates against `HENHOUSE_TIERS`, defaults to 'guest' if invalid.

## Technical Details: HTTP Client

The HTTP client (`hh/deploy/flask/http_client.py`) is the entry point for HTTP backend requests from Flask.

**Process Flow**:
1. **Parse Arguments**: Gets argv from `sys.argv[1:]` (passed by Flask)
2. **Dispatch to Gateway**: Calls `gateway.dispatch(argv, "http")`
3. **Return Result**: Prints output to stdout (captured by Flask), returns exit code (0 for success, 1 for errors)

Used by Flask app for `show-page` and `show-image` commands via HTTP backend.

## Technical Details: Flask Daemon Management

**Flask Start Process** (`flask-start`):
1. **Remove Existing Logrotate Config**: Removes any existing logrotate configuration (cleanup from previous runs)
2. **Start Daemons for Each Tier**: For each tier, calls `start_flask_daemon(project_name, tier, port)`:
   - Verifies app file exists (`{project_name}_{tier}.py`)
   - Verifies Unix user exists (created during installation)
   - Stops any existing processes (acts like restart)
   - Starts daemon using `sudo -u {user} bash -c "cd /srv/{project_name} && nohup python3 {app_path} < /dev/null &> /dev/null &"`
   - Waits 1 second, then verifies process is running via `ps aux`
3. **Configure Logrotate**: Creates `/etc/logrotate.d/{project_name}-flask` with hourly rotation, 24 rotations, compression enabled, copytruncate method, then restarts logrotate service

**Flask Stop Process** (`flask-stop`):
1. **Stop Daemons for Each Tier**: For each tier, calls `stop_flask_daemon(project_name, tier)`:
   - Uses `ps aux` to find processes running `{project_name}_{tier}.py`
   - Extracts PIDs from process list
   - Sends SIGTERM to each PID for graceful shutdown
2. **Remove Logrotate Config**: Removes logrotate configuration if any daemons were stopped or all were not running, then restarts logrotate service

**Flask Status Process** (`flask-status`):
1. **Check Each Tier**: For each tier, calls `get_flask_daemon_status(project_name, tier, port)`:
   - Verifies app file exists (returns "not_deployed" if missing)
   - Uses `ps aux` to find running processes
   - Extracts all PIDs for this tier
   - Returns "running" with PIDs, "stopped", "not_deployed", or "error"
2. **Summary**: Counts running, stopped, not_deployed, and error states, returns detailed status for each tier plus summary

## Technical Details: Process Management

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

**Restart Behavior**: The `flask-start` command stops any existing processes before starting new ones, effectively acting as a restart. This ensures clean process management without requiring separate stop/start commands.

## Technical Details: Logging System

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
- **Management**: Logrotate config is created during `flask-start` and removed during `flask-stop` (if daemons were stopped)

## Technical Details: Concurrency Control

**Gateway Semaphore**:
- Limits concurrent Gateway calls per Flask instance
- Default: 4 concurrent requests (`GATEWAY_MAX_CONCURRENCY`)
- Prevents resource exhaustion from too many simultaneous requests
- 10-second timeout for semaphore acquisition

**Request Timeout**:
- 10-second timeout for subprocess calls to Gateway
- Prevents hung requests from blocking Flask app

## Technical Details: Deployment Integration

Flask applications are deployed during the main `deploy` command:

1. **Template Processing**: `app.py` is copied and modified for each tier:
   - Port number replaced with tier-specific port
   - Log file path replaced with tier-specific path

2. **File Creation**: Creates `{project_name}_{tier}.py` in `/srv/{project_name}/`

3. **Service Start**: `deploy` command calls `run_flask_start()` after deployment completes

## Maintenance Daemon

The maintenance daemon:
- Runs background jobs for cache refresh
- Processes maintenance tasks
- Handles automated maintenance operations
- Logs to: `/srv/{project_name}/logs/{project_name}_maintenance.log`

## Technical Details: Maintenance Daemon Architecture

The maintenance daemon system consists of two distinct components:

- **`hh/deploy/maintenance/`**: Daemon management commands (start, stop, status) - stays in project folder, only accessible by human users or root tier
- **`hh/deploy/maint/`**: Maintenance tools and utilities - gets deployed to `/srv/{project_name}`, accessible by all agent tiers

**Key Distinction**:
- **maintenance/**: Administrative commands for managing the daemon itself (start/stop/status) - privileged access only
- **maint/**: Operational tools that the daemon uses (cache refresh, job queue, orphan checks) - deployed and accessible to all tiers

**Maintenance Worker** (`hh/deploy/maintenance/worker.py`):
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
   - Pending jobs from `maintenance_jobs` table (by job_type) - stored in main database
   - Stale page cache refreshes - detected via cache database
   - Stale image cache refreshes - detected via cache database
   - Stale file cache refreshes - detected via cache database
3. **Execute Tasks**: Runs each task via `maintenance_client.py`
4. **Handle Responses**: Updates job status for job queue items, logs results for cache refreshes
5. **Sleep**: Adaptive delay based on work status

**Logging**:
- Location: `/srv/{project_name}/logs/maintenance_{project_name}.log` (deployed) or `{project_root}/logs/maintenance_{project_name}.log` (local dev)
- Level: Configurable via `MAINTENANCE_LOG_LEVEL` environment variable (default: DEBUG)
- Output: Both stderr (terminal) and log file
- Heartbeat: Logs status every 15 minutes when idle

**Process Management**:
- **Deployed**: Runs as `{project_name}_root` user, script at `/srv/{project_name}/{project_name}_maintenance.py`
- **Local Dev**: Runs as current user, script at `{project_root}/hh/deploy/maintenance/worker.py`
- **Discovery**: Uses `maintenance_client.py` path resolution (deployed vs. local)

## Technical Details: Maintenance Tools

The maintenance daemon uses tools from the `maint/` folder, which are deployed to `/srv/{project_name}/hh/deploy/maint/` and accessible by all agent tiers:

### Cache Refresh Tools

Three tools for refreshing stale caches:
- **`page-cache-refresh`**: Refreshes stale page caches (fetches one stale page ID from cache database, rebuilds cache via `get_page(id).show_page()`, updates `cache_built_at` timestamp)
- **`image-cache-refresh`**: Refreshes stale image caches (fetches one stale image ID, rebuilds cache via `get_image(id).show_image()`, updates timestamp)
- **`file-cache-refresh`**: Refreshes stale file caches (fetches one stale file ID, rebuilds cache via `get_file(id).get_usage_data()`, updates timestamp)

All cache refresh tools query the cache database to find stale items (where `last_modified > cache_built_at` or `cache_built_at IS NULL`).

### Job Queue Management

**`maintenance-jobs-status`**: Checks what maintenance work needs to be done:
- Counts stale pages, images, and files from cache database
- Gets pending jobs by type from `maintenance_jobs` table (main database)
- Counts error jobs
- Returns `has_work` flag and work type counts

**`update-maintenance-job`**: Updates job status in the job queue:
- Accepts: `job_id`, `status`, `progress` (JSON string), `error_message`
- Updates job in `maintenance_jobs` table (main database)
- Job status flow: `pending` → `running` → `done` or `error`

**Job Queue Functions** (`job_queue.py`):
- **`claim_next_maintenance_job(job_type)`**: Claims next pending job with optimistic locking, updates status to 'running'
- **`update_maintenance_job(job_id, status, progress, error_message)`**: Updates job status, progress, and timestamps

### Orphan Checks

**`orphan-check`**: Checks for orphaned database records (broken foreign key relationships):
- Orphan pages (missing parent pages)
- Orphan link sources/targets (missing pages)
- Orphan image pages/targets (missing pages/images)
- Orphan image group pages/images (missing pages/images)
- Orphan file group pages/files (missing pages/files)

All checks query the main database and return counts and ID lists.

### Maintenance Tool Registration Pattern

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

## Troubleshooting

### Daemons Not Running

**Problem**: Flask or maintenance daemons show as not running

**Solutions**:
1. Check daemon status: `{hen_script_name} flask-status` and `{hen_script_name} maintenance-status`
2. Check log files for errors:
   - Flask: `/srv/{project_name}/logs/flask_{project_name}_{tier}.log`
   - Maintenance: `/srv/{project_name}/logs/{project_name}_maintenance.log`
3. Verify database is accessible (see Chapter 7)
4. Manually start daemons: `sudo {hen_script_name} flask-start` and `sudo {hen_script_name} maintenance-start`

### Port Conflicts

**Problem**: Flask daemons fail to start due to port conflicts

**Solutions**:
1. Check what's using the ports: `sudo netstat -tlnp | grep :5001`
2. Verify `flask_start_port` in install config doesn't conflict with other installations
3. Check for other Flask processes: `ps aux | grep flask`

### Permission Errors

**Problem**: Daemons fail with permission errors

**Solutions**:
1. Verify tier users exist: `id {project_name}_guest`
2. Check file permissions in `/srv/{project_name}`
3. Verify database credentials are correct
4. Check log files for specific permission errors

## Log Files

Daemon log files are located in `/srv/{project_name}/logs/`:

- **Flask logs**: `flask_{project_name}_{tier}.log` (one per tier)
- **Maintenance log**: `{project_name}_maintenance.log`

Logs are rotated automatically by logrotate (hourly, 24 rotations, compressed).

## Technical Appendices

### Appendix A: Maintenance Jobs System Architecture

#### Database Schema
**Table**: `maintenance_jobs`

Key fields:
- `id`: Primary key
- `job_type`: Type of maintenance operation (maps to command names)
- `status`: Current status (`pending`, `running`, `done`, `error`)
- `priority`: Execution priority (lower numbers = higher priority)
- `progress_json`: JSON progress data
- `error_message`: Error details for failed jobs
- `attempts`: Number of execution attempts
- `created_at`, `updated_at`, `completed_at`: Timestamps

#### Job Lifecycle
1. **Creation**: Jobs created by external systems or maintenance tools
2. **Claiming**: Worker claims job by executing corresponding maintenance command
3. **Processing**: Tool processes work and returns job_id in response
4. **Status Updates**: Worker updates job status based on response:
   - **Success + Done**: Mark as `done`
   - **Success + More Work**: Mark as `pending` with progress update
   - **Error**: Mark as `error` with debug information
5. **Completion**: Final status recorded with completion timestamp

#### Job Status Management
**Function**: `update_maintenance_job(job_id, status, progress, error_message)`

Provides comprehensive job status updates:
- **Status Changes**: Update job status (`pending`, `running`, `done`, `error`)
- **Progress Tracking**: JSON progress data with custom fields
- **Error Handling**: Truncated error messages (10KB limit)
- **Attempt Counting**: Automatic increment of attempt counter
- **Completion Tracking**: Automatic timestamp updates for final states

### Appendix B: Maintenance Backend Response Handler

**Class**: `ResponseMaintenance` in `hh/gateway/response/response_maintenance.py`

#### Response Format
**Success Response**:
```json
{
  "status": "ok",
  "data": {
    "operation": "rebuild_page_cache",
    "page_id": 123,
    "processed": true,
    "pages_remaining": 5
  },
  "debug": {...}
}
```

**Error Response**:
```json
{
  "status": "error",
  "data": null,
  "errors": [
    {"type": "action", "content": "Error message"}
  ],
  "debug": {...}
}
```

#### Backend Architecture Flow
```
maintenance_client.py (or daemon subprocess)
    ↓
Gateway.dispatch(argv, "maintenance")
    ↓
Action Handler (uses success_payload() wrapper)
    ↓
Maintenance Backend Wrapper (auto-generated via exec())
    - Unwraps MCP envelope from action_response
    - Extracts flat data from content[0]["text"]
    - Replaces wrapped response with flat data
    ↓
ResponseMaintenance.get_output()
    - Formats as JSON: {"status": "ok", "data": {...}, "errors": {...}, "debug": {...}}
    ↓
JSON Response (for daemon) or Parser Backend (for CLI)
```

**Key Features**:
- **JSON Output Format**: Structured JSON with `status`, `data`, `errors`, and `debug` fields
- **Error Handling**: Error responses formatted consistently
- **Debug Integration**: Debug output included when available
- **Envelope Unwrapping**: Maintenance backend extracts flat data from MCP protocol envelopes since maintenance is internal-only

### Appendix C: Maintenance Tools Registry System

#### Tool Registration Pattern
Every maintenance tool requires triple registration for full functionality:

1. **Action registration** (business logic): `@register_action("tool_name")` + `@register_command("tool_name")`
2. **Parser backend registration** (for command-line testing): `@register_parser("tool_name")`
3. **Maintenance registry** (triggers wrapper generation): `register_maintenance_tool("tool_name")` call at bottom of file

#### Auto-Generated Wrappers
The registry automatically generates wrapper functions using `exec()` that unwrap the MCP envelope from action responses:

**Process**:
1. **Scanning**: `_scan_for_maintenance_tools()` searches codebase for `register_maintenance_tool("tool_name")` calls
2. **Collection**: Builds set of all registered tool names from scanned files
3. **Generation**: Uses `exec()` to dynamically generate wrapper functions with `@register_maintenance` decorators
4. **Envelope Stripping**: Each generated wrapper extracts flat data from `action_response["content"][0]["text"]` and replaces the wrapped response
5. **Registration**: Wrappers automatically registered in `maintenances` dictionary for Gateway discovery

#### Response Format Unwrapping
Maintenance operations are internal-only and never sent to external systems, so the MCP protocol envelope is automatically unwrapped:

**Action Handler Flow**:
1. Action uses `success_payload(data)` which creates MCP-style wrapper with `{"content": [{"type": "text", "text": dict(data)}]}`
2. Maintenance backend wrapper automatically unwraps this envelope using `_maintenance_wrapper_template()`, extracting flat data from `action_response["content"][0]["text"]` and replacing the wrapped response
3. Parser backend receives unwrapped flat data directly for CLI testing

### Appendix D: Maintenance Client Entry Point

**File**: `hh/deploy/maint/maintenance_client.py`

The maintenance client is a simple entry point script that bridges command-line arguments to the Gateway system:

- **Simple Interface**: Takes command-line arguments and passes them to Gateway
- **Backend Specification**: Calls `gateway.dispatch(argv, "maintenance")` - this is the key detail
- **Output Handling**: Prints response output and returns appropriate exit codes
- **Encoding Support**: Handles UTF-8 encoding for cross-platform compatibility

**Example Usage**:
```bash
# Via maintenance backend (for daemon)
python3 maintenance_client.py maintenance-jobs-status

# Via parser backend (for command-line testing)
hen maintenance-jobs-status
```

Both routes execute the same action handler, but use different backend handlers for output formatting.

### Appendix E: Cross-Platform Support Details

#### Path Management
- **Project Root Detection**: Walks up directory tree to find `hh/` directory
- **Environment Detection**: Automatic deployed vs. local development mode detection
- **Log Path Resolution**: Environment-appropriate log file paths
- **Script Path Resolution**: Automatic maintenance_client.py discovery

#### Deployment Modes

**Local Development Mode**:
- **Worker Path**: `{project_root}/hh/deploy/maintenance/worker.py`
- **Client Path**: `{project_root}/hh/deploy/maint/maintenance_client.py`
- **Log Path**: `{project_root}/logs/maintenance_{project}.log`
- **User**: Current user
- **Privileges**: No special requirements

**Deployed Mode**:
- **Worker Path**: `/srv/{project}/{project}_maintenance.py`
- **Client Path**: `/srv/{project}/maintenance_client.py`
- **Log Path**: `/srv/{project}/logs/maintenance_{project}.log`
- **User**: `{project}_root`
- **Privileges**: Requires sudo for daemon management

#### Process Management
- **Windows Compatibility**: `CREATE_NO_WINDOW` flag prevents console windows
- **Unix Compatibility**: Standard subprocess execution with proper signal handling
- **Environment Variables**: Proper `PYTHONPATH` management for module imports
- **User Management**: Automatic user switching in deployed environments

### Appendix F: Future Enhancements

#### Job Queue Enhancements
**Planned Improvements**:
- **Priority Processing**: Implement priority-based job queue processing
- **Job Dependencies**: Support for job dependency chains
- **Retry Logic**: Configurable retry policies for failed jobs
- **Job Scheduling**: Time-based job scheduling capabilities
- **Monitoring**: Enhanced job queue monitoring and alerting

#### Performance Optimizations
**Planned Enhancements**:
- **Batch Processing**: Optional batch processing for cache refresh operations
- **Parallel Execution**: Multi-threaded processing for independent operations
- **Resource Management**: Memory and CPU usage optimization
- **Monitoring**: Performance metrics and monitoring integration

#### Logging Abstraction
**Cross-Cutting Enhancement**:
- **Environment Detection**: Automatic SRV vs. local development detection
- **Path Management**: Unified log path resolution for all maintenance components
- **Configuration**: Centralized logging configuration for maintenance and daemon systems
- **Integration**: Seamless integration with existing Gateway debug/logging systems

### Appendix G: Integration with Other Systems

#### With Gateway
- Maintenance registered as backend type in Gateway system
- All maintenance commands route through standard Gateway dispatch
- Uses Gateway connection patterns for database access
- Integrates with Gateway error reporting and debug systems

#### With Registry
- Maintenance tools use standard `@register_action` and `@register_command` patterns
- Auto-generated wrappers registered in `maintenances` dictionary
- Tool discovery through decorator scanning and caching
- Backend handler registration follows standard registry patterns

#### With Database Connection
- Uses standard Gateway connection patterns (`gateway.conn`)
- Transaction management through Gateway commit process
- Database operations use `read()`, `create()`, `update()`, `delete()` methods
- Cache database operations through `read_cache()`, `create_cache()`, `update_cache()`

#### With Error System
- Integrates with centralized error_store system
- Uses `report_error()` for action-level errors
- Error propagation through Gateway error handling
- Consistent error reporting patterns across all maintenance tools

#### With Debug System
- Full integration with Gateway debug system
- Uses `trace_in()`, `trace_out()`, `log()`, `debug()`, `warn()` functions
- Debug filtering and output control available
- Maintenance-specific debug output formatting

## Next Steps

After daemon management is complete, your Henhouse installation is fully operational:

1. **Web Interface**: Access your site at `https://yourdomain.com`
2. **MCP Setup**: Configure MCP wrapper in Cursor (see Development Tools in README)
3. **Customization**: Add your own MCP commands in the `ext/` folder

