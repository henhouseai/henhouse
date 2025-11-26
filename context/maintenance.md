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

The Henhouse maintenance system provides automated background task processing through a sophisticated daemon architecture. The system handles:

- **Cache Management**: Automatic detection and refresh of stale page, image, and file caches
- **Job Queue Processing**: Database-backed job queue with priority-based execution
- **Daemon Orchestration**: Cross-platform daemon management with privilege detection
- **Tool Registry**: Automatic discovery and registration of maintenance tools
- **Error Recovery**: Comprehensive error handling with retry logic and status tracking

### Architecture Flow

```
Maintenance Worker Daemon
    ↓
Polls maintenance-jobs-status
    ↓
Builds Work Docket (Priority Order):
1. Pending Jobs (from maintenance_jobs table)
2. Stale Cache Refreshes (pages, images, files)
    ↓
Executes via maintenance_client.py
    ↓
Gateway.dispatch(argv, "maintenance")
    ↓
Maintenance Tool (Action Handler)
    ↓
Job Status Updates (if job queue item)
```

### Key Integration Points

- **Gateway Backend**: Maintenance registered as backend type in `hh/gateway/registry/backend.py`
- **Tool Discovery**: Auto-generated wrappers in `hh/gateway/registry/maintenance.py`
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

## 4. Maintenance Tools Registry

**File**: `hh/gateway/registry/maintenance.py`

The maintenance tools registry provides automatic discovery and wrapper generation for maintenance commands.

### Tool Registration Pattern

Every maintenance tool requires dual registration:

```python
# Action registration (business logic)
@register_action("tool_name")
@register_command("tool_name")
def tool_name_action() -> bool:
    # Business logic implementation
    data = {"result": "success"}
    gateway.response.set_action_response(success_payload(data))
    return True

# Backend registration (output formatting)
@register_parser("tool_name")
def tool_name_parser() -> bool:
    # Parser gets unwrapped flat data directly from maintenance backend
    source_data = get_data(gateway.response.get_action_response())
    # Render output using source_data
    pass

# Maintenance registry (discovery)
register_maintenance_tool("tool_name")
```

### Auto-Generated Wrappers

The registry automatically generates wrapper functions using `exec()` that unwrap the MCP envelope:

```python
@register_maintenance('tool_name')
def tool_name() -> bool:
    gateway = get_gateway()
    if not gateway.response.has_action_response():
        report_error("backend", "No action response available")
        return False
    
    # Extract flat data from MCP-wrapped action_response
    action_response = gateway.response.get_action_response()
    if "content" in action_response and action_response["content"]:
        content_item = action_response["content"][0]
        if content_item.get("type") == "text" and "text" in content_item:
            flat_data = content_item["text"]
            # Replace the MCP-wrapped response with flat data
            gateway.response.set_action_response(flat_data)
    return True
```

### Tool Discovery Process

1. **Scanning**: `_scan_for_maintenance_tools()` searches for `register_maintenance_tool` calls
2. **Collection**: Builds set of all registered tool names
3. **Generation**: Uses `exec()` to create wrapper functions with `@register_maintenance` decorators
4. **Registration**: Wrappers automatically registered in `maintenances` dictionary

### Backend Integration

Maintenance tools integrate with the Gateway backend system:

- **Backend Type**: `maintenance` registered alongside `parser`, `http`, `mcp`
- **Handler Dictionary**: `maintenances` contains all registered maintenance handlers
- **Response Processing**: Wrappers verify action response exists and unwrap MCP envelope
- **Envelope Unwrapping**: Maintenance backend extracts flat data from `success_payload()` MCP wrapper since maintenance is internal-only

### Response Format Unwrapping

The maintenance backend implements a clever envelope unwrapping mechanism since maintenance operations are purely internal:

**Action Handler Flow**:
1. Action uses `success_payload(data)` which creates MCP-style wrapper:
   ```python
   {
       "content": [
           {
               "type": "text", 
               "text": dict(data)  # The actual data
           }
       ]
   }
   ```

2. Maintenance backend wrapper automatically unwraps this envelope:
   ```python
   # Extract flat data from MCP-wrapped action_response
   action_response = gateway.response.get_action_response()
   flat_data = action_response["content"][0]["text"]
   # Replace wrapped response with flat data
   gateway.response.set_action_response(flat_data)
   ```

3. Parser backend receives unwrapped flat data directly:
   ```python
   # No need for get_data() extraction - data is already flat
   source_data = get_data(gateway.response.get_action_response())
   ```

This eliminates the external protocol envelope overhead since maintenance commands never leave the system boundary.

---

## 5. Daemon Management

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

## 6. Cache Refresh System

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

## 7. Cross-Platform Support

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

## 8. Future Enhancements

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
