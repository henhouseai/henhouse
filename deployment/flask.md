# Flask Application Management

The Flask application management system handles tier-based Flask daemon lifecycle, process management, logging, and HTTP/MCP request routing.

## Prerequisites

Before using Flask application management, you must have:
- Installation system completed (see `installation.md`) - tier users must exist
- File deployment completed (see `file-deployment.md`) - Flask application files must be deployed
- Database deployment completed (see `database.md`) - database must be accessible
- Sudo/root privileges for starting/stopping daemons

The Flask application management system depends on the installation system because each Flask instance runs as its corresponding tier user (`{project_name}_{tier}`), using credentials and permissions established during installation.

## Flask Architecture

Henhouse deploys multiple Flask application instances, one per user tier:

- **Guest tier**: `{project_name}_guest.py` on port 5001
- **Verified tier**: `{project_name}_verified.py` on port 5002
- **Admin tier**: `{project_name}_admin.py` on port 5003
- **Root tier**: `{project_name}_root.py` on port 5004

Each instance:
- Runs as its corresponding Unix user (`{project_name}_{tier}`) created by installation system (see `installation.md`)
- Serves content with tier-appropriate permissions
- Has its own log file: `/srv/{project_name}/logs/flask_{project_name}_{tier}.log`
- Listens on `127.0.0.1` (localhost only, proxied by NGINX)
- Connects to database using tier-specific credentials (see `database.md`)

The Flask applications are deployed by the file deployment system (see `file-deployment.md`) and are proxied by the HTTP/NGINX deployment system (see `http-nginx.md`).

## Flask Application Start

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
   - **Check user exists**: Verifies Unix user exists (created by installation system - see `installation.md`)
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

## Flask Application Stop

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

## Flask Application Status

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

## Flask Application (`app.py`)

**File**: `hh/deploy/flask/app.py`

The main Flask application handles HTTP requests and routes them to the Gateway system.

**Tier Detection**:
- Extracts tier from script name: `{project_name}_{tier}.py` → `tier`
- Falls back to environment variable or defaults to empty string

**Configuration**:
- **Project root**: `/srv/{project_name}`
- **Site directory**: `/srv/{project_name}/site` (deployed by file deployment system - see `file-deployment.md`)
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
- Connects to database using tier-specific credentials (see `database.md`)

**Error Handling**:
- JSON-RPC 2.0 error responses for MCP requests
- HTML error pages for HTTP requests
- Fallback response shows tier and project configuration if Gateway fails

**See also**: `hh/deploy/flask/app.py` - Main Flask application

## MCP Client

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
- Validates against `HENHOUSE_TIERS` (from configuration system - see `configuration.md`)
- Defaults to 'guest' if invalid

**See also**: `hh/deploy/flask/mcp_client.py` - MCP client entry point

## HTTP Client

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

## Process Management

**Background Process Execution**:
- Flask daemons run as background processes using `nohup`
- Input/output redirected to `/dev/null` (Flask handles its own logging)
- Processes run as tier-specific Unix users via `sudo -u {user}` (users created by installation system - see `installation.md`)
- Working directory: `/srv/{project_name}`

**Process Discovery**:
- Uses `ps aux` to find running processes
- Searches for `{project_name}_{tier}.py` in process command line
- Extracts PIDs from process list (second column)

**Signal Handling**:
- Uses SIGTERM for graceful shutdown (via `gateway.os.kill_process(pid, force=False)`)
- Processes should handle SIGTERM to clean up and exit

## Logging System

**Log Files**:
- Location: `/srv/{project_name}/logs/flask_{project_name}_{tier}.log`
- Format: `%(asctime)s %(levelname)s %(message)s`
- Level: INFO
- Flask's built-in logging system writes directly to log files
- Log directory created by file deployment system (see `file-deployment.md`)

**Logrotate**:
- Configuration: `/etc/logrotate.d/{project_name}-flask`
- Rotation: Hourly
- Retention: 24 rotations (24 hours)
- Compression: Enabled with delaycompress
- Method: copytruncate (allows continuous logging without file handle issues)

## Concurrency Control

**Gateway Semaphore**:
- Limits concurrent Gateway calls per Flask instance
- Default: 4 concurrent requests (`GATEWAY_MAX_CONCURRENCY`)
- Prevents resource exhaustion from too many simultaneous requests
- 10-second timeout for semaphore acquisition

**Request Timeout**:
- 10-second timeout for subprocess calls to Gateway
- Prevents hung requests from blocking Flask app

## Deployment Integration

Flask applications are deployed during the main `deploy` command (see `file-deployment.md`):

1. **Template Processing**: `app.py` is copied and modified for each tier:
   - Port number replaced with tier-specific port
   - Log file path replaced with tier-specific path

2. **File Creation**: Creates `{project_name}_{tier}.py` in `/srv/{project_name}/`

3. **Service Start**: `deploy` command calls `run_flask_start()` after deployment completes

## Integration with Other Systems

The Flask application management system integrates with:

1. **Installation System** (`installation.md`): Each Flask instance runs as its corresponding tier user, using credentials and permissions established during installation.

2. **Database Deployment** (`database.md`): Each Flask instance connects to the database using its tier user's credentials, enforcing tier-based permissions at the database level.

3. **File Deployment** (`file-deployment.md`): Creates Flask application files and starts Flask daemons after deployment.

4. **HTTP/NGINX Deployment** (`http-nginx.md`): Flask applications are proxied by NGINX. NGINX routes requests to the appropriate Flask instance based on subdomain and tier.

5. **Maintenance Daemon** (`maintenance.md`): Flask applications and maintenance daemon run independently but share the same codebase and database.

6. **Configuration System** (`configuration.md`): Uses `HENHOUSE_TIERS` to determine which Flask instances to create and manage.

7. **Site Assets Deployment** (`site-assets.md`): Serves static files from `/srv/{project_name}/site/` deployed by the file deployment system.

## Deployment Workflow

Flask applications are automatically managed during deployment:

**During File Deployment**:
- Flask application files are created
- Flask daemons are stopped before deployment
- Flask daemons are started after deployment

**Manual Management**:
```bash
sudo hen flask-start    # Start all Flask daemons
sudo hen flask-stop     # Stop all Flask daemons
hen flask-status        # Check status of all Flask daemons
```

See `workflows.md` for complete deployment workflow documentation.

