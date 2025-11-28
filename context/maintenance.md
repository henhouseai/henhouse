# Henhouse Maintenance System Architecture

This document covers the comprehensive maintenance system that handles automated background tasks, cache management, and daemon orchestration in the Henhouse system.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Maintenance Worker Daemon](#2-maintenance-worker-daemon)
3. [Maintenance Jobs System](#3-maintenance-jobs-system)
4. [Maintenance Tools Registry](#4-maintenance-tools-registry)
5. [Daemon Management](#5-daemon-management)
6. [Cache Refresh System](#6-cache-refresh-system)
7. [Cross-Platform Support](#7-cross-platform-support)
8. [Future Enhancements](#8-future-enhancements)

## Agent Quick Reference

- **Maintenance Worker**: Single monolithic daemon (`worker.py`) that processes job queue and stale cache items
- **Job Queue**: Database-backed queue (`maintenance_jobs` table) with priority-based processing
- **Cache System**: Automatic detection and refresh of stale pages, images, and files
- **Tool Registration**: `@register_maintenance_tool` decorator for maintenance command discovery
- **Daemon Control**: Cross-platform start/stop/status commands with privilege detection
- **Gateway Integration**: All maintenance commands route through standard Gateway dispatch with "maintenance" backend
- **Logging System**: Dual logging (stderr + file) with environment-based path detection

## Agent Training Notes

### System Integration
- **Gateway Backend**: Maintenance is registered as backend type alongside parser, http, mcp
- **Command Routing**: All maintenance tools accessible via `maintenance_client.py` → Gateway dispatch
- **Database Access**: Uses standard Gateway connection patterns with transaction management
- **Error Handling**: Integrates with centralized error_store system for consistent error reporting
- **Debug System**: Full debug/trace/log integration with filtering capabilities

### Maintenance Worker Patterns
- **Work Detection**: Polls `maintenance-jobs-status` command to detect available work
- **Priority System**: Job queue items processed before stale cache refreshes
- **Heartbeat Logging**: 15-minute status reports when idle, immediate logging when work available
- **Error Recovery**: Automatic retry with `-log` flag on errors, job status updates
- **Graceful Shutdown**: Signal handling for clean daemon termination

### Tool Development
- **Dual Registration**: Maintenance tools need both `@register_action` + `@register_command` and `@register_maintenance_tool`
- **Response Format**: Use `success_payload()` for standardized JSON responses (maintenance backend automatically unwraps the MCP envelope)
- **Job Integration**: Tools can claim jobs from queue via job_id in response
- **Progress Tracking**: Job status updates via `update-maintenance-job` command

---

## 1. System Overview

The Henhouse maintenance system provides automated background task processing through a Gateway backend type. The system handles:

- **Cache Management**: Automatic detection and refresh of stale page, image, and file caches
- **Job Queue Processing**: Database-backed job queue with priority-based execution
- **Backend Architecture**: Custom ResponseMaintenance class with JSON output format
- **Tool Registry**: Automatic discovery and registration of maintenance tools via decorator scanning
- **Dual Interface**: Tools accessible via maintenance backend (for daemon) and parser backend (for command-line testing)

### Backend Architecture Flow

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

**Key Entry Point**: `maintenance_client.py` is a simple script that calls `gateway.dispatch(argv, "maintenance")`, allowing any client (daemon or command-line) to execute maintenance tools through the Gateway system.

### Key Integration Points

- **Gateway Backend**: Maintenance registered as backend type in `hh/gateway/registry/backend.py`
- **Entry Point**: `maintenance_client.py` calls `gateway.dispatch(argv, "maintenance")` - this is the key detail that allows daemon or command-line execution
- **Tool Discovery**: Auto-generated wrappers in `hh/gateway/registry/maintenance.py` via `exec()` function
- **Response Format**: `ResponseMaintenance` class outputs JSON format with status, data, errors, and debug fields
- **Dual Interface**: All maintenance tools also have parser backend handlers, allowing command-line testing (e.g., `hen maintenance-jobs-status`)
- **Database Integration**: Uses standard Gateway connection patterns with transaction management
- **Error System**: Integrates with centralized error_store for consistent error reporting

---

## 2. Maintenance Worker Daemon

**File**: `hh/deploy/maintenance/worker.py`

The maintenance worker is a single monolithic daemon that monitors work availability and processes tasks in priority order. It provides:

- **Continuous Monitoring**: Polls for work every 5 seconds (configurable via `--delay`)
- **Priority Processing**: Job queue items processed before stale cache refreshes
- **Intelligent Logging**: Heartbeat logs every 15 minutes when idle, immediate logging when work available
- **Error Recovery**: Automatic retry with debug logging on failures
- **Graceful Shutdown**: Signal handling for clean termination

### Worker Class Architecture

#### MaintenanceWorker Process Flow

1. **Initialization**: Configure logging, set up signal handlers, detect project context
2. **Work Detection**: Poll `maintenance-jobs-status` command for available work
3. **Docket Building**: Create prioritized list of commands to execute
4. **Task Execution**: Run commands via `maintenance_client.py` subprocess calls
5. **Status Management**: Update job statuses and handle error recovery
6. **Cycle Management**: Sleep intervals based on work availability (0.5s if work, full delay if idle)

#### Key Methods

- **`run_cycle()`**: Main work detection and execution cycle
- **`build_work_docket()`**: Creates prioritized task list from status data
- **`handle_job_response()`**: Processes job queue responses and updates status
- **`run_maintenance_command()`**: Executes maintenance commands via subprocess

### Logging System

The worker implements a sophisticated dual-logging system:

- **Stderr Output**: Real-time console output for monitoring
- **File Logging**: Persistent logs with environment-based path detection
  - **Deployed**: `/srv/{project}/logs/maintenance_{project}.log`
  - **Local Dev**: `{project_root}/logs/maintenance_{project}.log`
- **Log Levels**: Configurable via `MAINTENANCE_LOG_LEVEL` environment variable
- **Heartbeat Pattern**: Reduces log noise by only logging when work is available or every 15 minutes

### Work Priority System

The worker processes work in strict priority order:

1. **Pending Jobs** (from `maintenance_jobs` table)
   - Sorted by priority (future enhancement)
   - Require job status updates via `update-maintenance-job`
   - Support progress tracking and error recovery

2. **Stale Cache Refreshes** (direct cache operations)
   - Page cache refresh (`page-cache-refresh`)
   - Image cache refresh (`image-cache-refresh`)
   - File cache refresh (`file-cache-refresh`)
   - No job status tracking required

### Cross-Platform Support

The worker provides full cross-platform compatibility:

- **Windows**: Uses `CREATE_NO_WINDOW` flag to prevent console windows
- **Unix/Linux**: Standard subprocess execution
- **Path Detection**: Automatic project root and maintenance_client.py discovery
- **Environment Variables**: Proper `PYTHONPATH` management for module imports

---

## 3. Maintenance Jobs System

The maintenance jobs system provides a database-backed queue for complex, trackable maintenance operations.

### Database Schema

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

### Job Lifecycle

1. **Creation**: Jobs created by external systems or maintenance tools
2. **Claiming**: Worker claims job by executing corresponding maintenance command
3. **Processing**: Tool processes work and returns job_id in response
4. **Status Updates**: Worker updates job status based on response:
   - **Success + Done**: Mark as `done`
   - **Success + More Work**: Mark as `pending` with progress update
   - **Error**: Mark as `error` with debug information
5. **Completion**: Final status recorded with completion timestamp

### Job Status Management

**File**: `hh/deploy/maint/update_maintenance_job.py`

Provides comprehensive job status updates:

- **Status Changes**: Update job status (`pending`, `running`, `done`, `error`)
- **Progress Tracking**: JSON progress data with custom fields
- **Error Handling**: Truncated error messages (10KB limit)
- **Attempt Counting**: Automatic increment of attempt counter
- **Completion Tracking**: Automatic timestamp updates for final states

### Job Queue Integration

Tools integrate with the job queue by:

1. **Claiming Jobs**: Return `job_id` in response when work is claimed
2. **Progress Reporting**: Include progress data in response
3. **Completion Signaling**: Set `done: true` when no more work available
4. **Error Reporting**: Return error information for failed operations

---

## 4. Maintenance Backend Response Handler

**File**: `hh/gateway/response/response_maintenance.py`

The maintenance backend uses a custom response handler that outputs JSON format suitable for machine consumption.

### ResponseMaintenance Class

The `ResponseMaintenance` class extends the base `Response` class and provides:

- **JSON Output Format**: Structured JSON with `status`, `data`, `errors`, and `debug` fields
- **Error Handling**: Error responses formatted as `{"status": "error", "data": null, "errors": [...]}`
- **Debug Integration**: Debug output included in response when available
- **Success Format**: `{"status": "ok", "data": {...}}` with optional debug field (all systems handle success + debug)

### Response Format

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

Note: The `debug` field is optional and included when debug output is available. All systems are designed to handle success responses with or without debug data.

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

This format is optimized for daemon consumption while remaining human-readable for command-line testing.

---

## 5. Maintenance Tools Registry

**File**: `hh/gateway/registry/maintenance.py`

The maintenance tools registry provides automatic discovery and wrapper generation for maintenance commands.

### Tool Registration Pattern

Every maintenance tool requires triple registration for full functionality:

1. **Action registration** (business logic): `@register_action("tool_name")` + `@register_command("tool_name")`
2. **Parser backend registration** (for command-line testing): `@register_parser("tool_name")`
3. **Maintenance registry** (triggers wrapper generation): `register_maintenance_tool("tool_name")` call at bottom of file

See `hh/deploy/maint/maintenance_jobs_status.py` for a complete example of the triple registration pattern.

The `register_maintenance_tool()` call at the bottom of each file is scanned by the registry, which then uses `exec()` to generate wrapper functions. These wrappers automatically unwrap the MCP envelope from responses, extracting the flat data for internal use.

**Dual Interface Support**: Tools can be executed via:
- **Maintenance backend**: `maintenance_client.py tool_name` → JSON output for daemon consumption
- **Parser backend**: `hen tool_name` → Formatted table output for command-line testing

Both routes use the same action handler but different backend handlers for output formatting.

### Auto-Generated Wrappers

The registry automatically generates wrapper functions using `exec()` that unwrap the MCP envelope from action responses. Actions use `success_payload(data)` (see `hh/gateway/response/json_standard.py`) which wraps data in MCP format with `{"content": [{"type": "text", "text": {...actual data...}}]}`.

The generated wrapper functions use the `_maintenance_wrapper_template()` function (see `hh/gateway/registry/maintenance.py` - `_maintenance_wrapper_template()` function) to extract flat data from the envelope. The template function:
- Verifies `gateway.response.has_action_response()` exists
- Extracts flat data from `action_response["content"][0]["text"]`
- Replaces the wrapped response with flat data

Since maintenance operations are internal-only and never sent to external systems, the MCP protocol envelope is automatically unwrapped, leaving clean flat data for ResponseMaintenance to format as JSON.

### Tool Discovery Process

1. **Scanning**: `_scan_for_maintenance_tools()` searches codebase for `register_maintenance_tool("tool_name")` calls
2. **Collection**: Builds set of all registered tool names from scanned files
3. **Generation**: Uses `exec()` to dynamically generate wrapper functions with `@register_maintenance` decorators
4. **Envelope Stripping**: Each generated wrapper extracts flat data from `action_response["content"][0]["text"]` and replaces the wrapped response
5. **Registration**: Wrappers automatically registered in `maintenances` dictionary for Gateway discovery

### Backend Integration

Maintenance tools integrate with the Gateway backend system:

- **Backend Type**: `maintenance` registered alongside `parser`, `http`, `mcp`
- **Handler Dictionary**: `maintenances` contains all registered maintenance handlers (auto-generated via `exec()`)
- **Response Processing**: Wrappers verify action response exists and unwrap MCP envelope
- **Envelope Unwrapping**: Maintenance backend extracts flat data from `success_payload()` MCP wrapper since maintenance is internal-only
- **Simple Decorator**: `register_maintenance_tool("tool_name")` call at bottom of each tool file triggers discovery

**Similarity to MCP Backend**: The maintenance backend follows a similar pattern to the MCP backend but is simpler because:
- Single purpose: Always internal-only usage
- No tier-based whitelisting needed (always runs as root tier user)
- Simpler wrapper generation (no tool validation or tier checking)
- Direct envelope unwrapping (no protocol overhead needed)

### Response Format Unwrapping

The maintenance backend implements a clever envelope unwrapping mechanism since maintenance operations are purely internal:

**Action Handler Flow**:
1. Action uses `success_payload(data)` (see `hh/gateway/response/json_standard.py`) which creates MCP-style wrapper with `{"content": [{"type": "text", "text": dict(data)}]}`

2. Maintenance backend wrapper automatically unwraps this envelope using `_maintenance_wrapper_template()` (see `hh/gateway/registry/maintenance.py` - `_maintenance_wrapper_template()` function), which extracts flat data from `action_response["content"][0]["text"]` and replaces the wrapped response

3. Parser backend receives unwrapped flat data directly (see `hh/deploy/maint/maintenance_jobs_status.py` for parser backend implementation)

This eliminates the external protocol envelope overhead since maintenance commands never leave the system boundary.

---

## 6. Maintenance Client Entry Point

**File**: `hh/deploy/maint/maintenance_client.py`

The maintenance client is a simple entry point script that bridges command-line arguments to the Gateway system:

- **Simple Interface**: Takes command-line arguments and passes them to Gateway
- **Backend Specification**: Calls `gateway.dispatch(argv, "maintenance")` - this is the key detail
- **Output Handling**: Prints response output and returns appropriate exit codes
- **Encoding Support**: Handles UTF-8 encoding for cross-platform compatibility

This script enables:
- **Daemon Execution**: Worker daemon calls this script via subprocess to execute maintenance tools
- **Command-Line Testing**: Developers can test maintenance tools directly from command line
- **Unified Interface**: All maintenance operations route through the same Gateway dispatch mechanism

**Example Usage**:
```bash
# Via maintenance backend (for daemon)
python3 maintenance_client.py maintenance-jobs-status

# Via parser backend (for command-line testing)
hen maintenance-jobs-status
```

Both routes execute the same action handler, but use different backend handlers for output formatting.

---

## 7. Daemon Management

The system provides comprehensive cross-platform daemon management through three core commands.

### Maintenance Start

**File**: `hh/deploy/maintenance/maintenance_start.py`

Starts the maintenance daemon with full environment detection:

- **Privilege Detection**: Requires sudo on deployed systems
- **Process Management**: Stops existing processes before starting new ones
- **User Management**: Runs as `{project}_root` user in deployed mode
- **Path Resolution**: Automatic worker script and log file path detection
- **Verification**: Post-start process verification with PID tracking

### Maintenance Stop

**File**: `hh/deploy/maintenance/maintenance_stop.py`

Stops running maintenance daemons:

- **Process Discovery**: Finds running maintenance processes by name filter
- **Graceful Termination**: Uses process manager for clean shutdown
- **Multi-Process Support**: Handles multiple running instances
- **Status Reporting**: Returns list of stopped PIDs

### Maintenance Status

**File**: `hh/deploy/maintenance/maintenance_status.py`

Reports current daemon status:

- **Process Detection**: Checks for running maintenance processes
- **Path Verification**: Confirms worker script exists
- **Deployment Detection**: Reports deployed vs. local development mode
- **PID Tracking**: Lists all running process IDs

### Process Manager Integration

All daemon management commands integrate with the Gateway's process manager (`gateway.os`):

- **Cross-Platform**: Unified interface for Windows/Unix process management
- **Privilege Detection**: Automatic sudo requirement detection
- **Background Processes**: Proper daemon startup with log file redirection
- **Process Filtering**: Name-based process discovery and management

---

## 8. Cache Refresh System

The maintenance system provides automatic cache refresh for three core data types.

### Page Cache Refresh

**File**: `hh/deploy/maint/page_cache_refresh.py`

Refreshes stale page caches using the page registry system:

- **Staleness Detection**: `last_modified > cache_built_at OR cache_built_at IS NULL`
- **Single Page Processing**: Processes one page per execution for granular control
- **Page Registry Integration**: Uses `get_page()` and `show_page()` for cache rebuild
- **Error Handling**: Comprehensive error reporting with page class and name context
- **Progress Tracking**: Returns remaining page count for queue management

#### Key Methods

- **`fetch_stale_page_id()`**: Gets next stale page ID in modification order
- **`count_stale_pages()`**: Returns total stale page count
- **`rebuild_page()`**: Rebuilds cache for single page with error handling

### Image Cache Refresh

**File**: `hh/deploy/maint/image_cache_refresh.py`

Similar pattern to page cache refresh but for image data:

- **Staleness Detection**: `COALESCE(last_modified, uploaded) > cache_built_at OR cache_built_at IS NULL`
- **Image Registry Integration**: Uses image system for cache rebuild
- **Instance Management**: Handles multi-size image instance caching

### File Cache Refresh

**File**: `hh/deploy/maint/file_cache_refresh.py`

Handles file attachment cache refresh:

- **File System Integration**: Works with file attachment system
- **Upload Timestamp Handling**: Uses upload time when modification time unavailable
- **Metadata Caching**: Refreshes file metadata and association caches

### Cache Architecture Integration

All cache refresh tools integrate with the broader Henhouse cache architecture:

- **Two-Tier Caching**: Hot cache (in-memory) + cache database (persistent)
- **Gateway Commit Integration**: Cache refresh triggered during Gateway commit process
- **Staleness Detection**: Database-driven staleness detection with timestamp comparison
- **Atomic Updates**: Cache updates happen within database transactions

---

## 9. Cross-Platform Support

The maintenance system provides comprehensive cross-platform compatibility across Windows, macOS, and Linux.

### Path Management

- **Project Root Detection**: Walks up directory tree to find `hh/` directory
- **Environment Detection**: Automatic deployed vs. local development mode detection
- **Log Path Resolution**: Environment-appropriate log file paths
- **Script Path Resolution**: Automatic maintenance_client.py discovery

### Process Management

- **Windows Compatibility**: `CREATE_NO_WINDOW` flag prevents console windows
- **Unix Compatibility**: Standard subprocess execution with proper signal handling
- **Environment Variables**: Proper `PYTHONPATH` management for module imports
- **User Management**: Automatic user switching in deployed environments

### Deployment Modes

#### Local Development Mode
- **Worker Path**: `{project_root}/hh/deploy/maintenance/worker.py`
- **Client Path**: `{project_root}/hh/deploy/maint/maintenance_client.py`
- **Log Path**: `{project_root}/logs/maintenance_{project}.log`
- **User**: Current user
- **Privileges**: No special requirements

#### Deployed Mode
- **Worker Path**: `/srv/{project}/{project}_maintenance.py`
- **Client Path**: `/srv/{project}/maintenance_client.py`
- **Log Path**: `/srv/{project}/logs/maintenance_{project}.log`
- **User**: `{project}_root`
- **Privileges**: Requires sudo for daemon management

### Process Manager Integration

The system integrates with Gateway's process manager for unified process handling:

- **Process Discovery**: Name-based filtering for maintenance processes
- **Background Execution**: Proper daemon startup with log redirection
- **Signal Handling**: Graceful shutdown via SIGTERM/SIGINT
- **PID Tracking**: Process ID management for status reporting

---

## 10. Future Enhancements

Several enhancements are planned to extend the maintenance system capabilities:

### Job Queue Enhancements

**Planned Improvements**:
- **Priority Processing**: Implement priority-based job queue processing
- **Job Dependencies**: Support for job dependency chains
- **Retry Logic**: Configurable retry policies for failed jobs
- **Job Scheduling**: Time-based job scheduling capabilities
- **Monitoring**: Enhanced job queue monitoring and alerting

### Performance Optimizations

**Planned Enhancements**:
- **Batch Processing**: Optional batch processing for cache refresh operations
- **Parallel Execution**: Multi-threaded processing for independent operations
- **Resource Management**: Memory and CPU usage optimization
- **Monitoring**: Performance metrics and monitoring integration

### Logging Abstraction

**Cross-Cutting Enhancement**:
- **Environment Detection**: Automatic SRV vs. local development detection
- **Path Management**: Unified log path resolution for all maintenance components
- **Configuration**: Centralized logging configuration for maintenance and daemon systems
- **Integration**: Seamless integration with existing Gateway debug/logging systems

**Note**: For daemon management and auto-scaling capabilities, see `daemon_manager.md` which covers the comprehensive daemon orchestration system.

---

## Integration with Other Systems

### With Gateway (see gateway.md)
- Maintenance registered as backend type in Gateway system
- All maintenance commands route through standard Gateway dispatch
- Uses Gateway connection patterns for database access
- Integrates with Gateway error reporting and debug systems

### With Registry (see registry.md)
- Maintenance tools use standard `@register_action` and `@register_command` patterns
- Auto-generated wrappers registered in `maintenances` dictionary
- Tool discovery through decorator scanning and caching
- Backend handler registration follows standard registry patterns

### With Database Connection
- Uses standard Gateway connection patterns (`gateway.conn`)
- Transaction management through Gateway commit process
- Database operations use `read()`, `create()`, `update()`, `delete()` methods
- Cache database operations through `read_cache()`, `create_cache()`, `update_cache()`

### With Error System (see patterns.md)
- Integrates with centralized error_store system
- Uses `report_error()` for action-level errors
- Error propagation through Gateway error handling
- Consistent error reporting patterns across all maintenance tools

### With Debug System (see debug.md)
- Full integration with Gateway debug system
- Uses `trace_in()`, `trace_out()`, `log()`, `debug()`, `warn()` functions
- Debug filtering and output control available
- Maintenance-specific debug output formatting

---

This maintenance system provides a robust, scalable foundation for automated background task processing while maintaining full integration with the broader Henhouse architecture. The current implementation provides comprehensive job queue management, cache refresh automation, and cross-platform daemon orchestration.
