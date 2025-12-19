# Henhouse Gateway System Architecture

This document covers the core gateway and parsing infrastructure of the Henhouse system. The Gateway is the **central orchestrator** that manages request lifecycle, coordinates all subsystems, and provides unified access to system state. It ensures all components interact through a single, well-defined interface.

## Table of Contents

1. [Entry Point](#1-entry-point)
2. [Gateway](#2-gateway)
3. [Debug System](#3-debug-system)
4. [Response](#4-response)
5. [Request](#5-request)
6. [Parsing Pipeline](#6-parsing-pipeline)
7. [Connection](#7-connection)
8. [FileSystem](#8-filesystem)

## Agent Quick Reference

- **Entry Point**: `hen.py` → `get_gateway()` → `dispatch()`
- **Core Dispatch Flow**: arguments → grammar → registry → cache → modules → handlers → response
- **Key Objects**: Request, Response, CommandRegistry, Gateway
- **Parsing Pipeline**: Grammar Parser → Tokenizer → Parser → Semantics
- **Error System**: Centralized error store (`error_store.py`) with `report_error()` and `is_error()` functions, 12 error types
- **Debug System**: Always-on warning system, toggleable with `-debug`, `-log`, `-trace` flags
- **Debug Control**: White/gray/black lists + limit features for precise output control

## Agent Training Notes

### Gateway Integration Points
- **Gateway Access**: Use `get_gateway()` to access system state and arguments
- **Argument Retrieval**: `gateway.get_arg(name)` for string/integer arguments
- **Flag Checking**: `gateway.is_no(flag)` for no-flag states
- **Response Setting**: `gateway.response.set_action_response(json_data)` for action results
- **Error Reporting**: Use `report_error(error_type, content)` from `error_store` module
- **Error Checking**: Use `is_error()` from `error_store` module to check error state

### Parsing Pipeline Understanding
- **4-Stage Process**: Raw args → tokens → parsed grammar → Request object
- **Grammar Parser**: Orchestrates the entire parsing workflow
- **Tokenizer**: Handles quote detection and token classification
- **Parser**: Builds structured grammar from tokens
- **Semantics**: Constructs final Request with proper data types

### Debug System Control
- **Default white-list**: `*` (all modules allowed)
- **Default gray-list**: empty
- **Default black-list**: empty
- **Default debug-limit**: 10 messages per unique method combination
- **Default verbosity**: Always show warnings
- **Flags**: `-debug` (debug + warnings), `-log` (log + debug + warnings), `-trace` (full trace analysis)
- **Filter Overrides**: `-white`, `-gray`, `-black`, `-debug-limit` flags for fine control
- **Disable**: `--no_debug` flag prevents debug system from loading

---

## 1. Entry Point

**File**: `hen.py`

The main entry point that bridges the command line to the Henhouse system. It captures raw command-line arguments, creates the singleton gateway instance, dispatches the request, and outputs the final formatted response.

**Key Pattern**: parse → gateway → print → exit

See `main()` function in `hen.py` for implementation.

---

## 2. Gateway

**File**: `hh/gateway/gateway.py`

The central orchestrator and state manager for the entire Henhouse system. It manages request lifecycle, coordinates execution, handles errors, manages debugging, and provides consistent APIs for all subsystems.

### Gateway Class

**Singleton Pattern**: Use `init_gateway(raw_argv, backend)` to create and initialize, then `get_gateway()` to access. Never instantiate directly.

**Initialization**: Gateway is initialized via `init_gateway(raw_argv, backend)` which:
- Creates the Gateway singleton instance
- Calls `Gateway.__init__(raw_argv, backend)` which performs all initialization
- Guarantees that `request`, `response`, `conn`, and `files` are non-None after initialization completes

**Core State Management**:
- `request`: Parsed command-line arguments and flags (guaranteed non-None after init)
- `response`: Output buffer and response management (guaranteed non-None after init)
- `registry`: Command and backend handler discovery
- `conn`: Database connection instance (Connection, MySQLConnection, or RootConnection) (guaranteed non-None after init)
- `files`: FileSystem instance for file operations (guaranteed non-None after init)
- `os`: ProcessManager instance for cross-platform process management
- `action_handler`: Business logic execution function
- `backend_handler`: Presentation logic execution function
- `error_handler`: Error processing function
- `debug_system`, `debug_module`, `get_debug_func`: Debug system components
- `_user_tier_level`: User tier level (0=unknown, 1=guest, 2=verified, 3=admin, 4=root)

### Execution Flow

1. **Entry Point**: `init_gateway(raw_argv, backend)` creates and initializes Gateway
2. **Initialization** (in `Gateway.__init__()`):
   - `_initialize()`: Sets up all subsystems in proper order
     - `_initialize_debug_module()`: Configures debugging based on request flags
     - `_initialize_command()`: Extracts command from parsed request (with defaults for http/parser backends)
     - `_initialize_connection()`: Initializes database connection and returns user tier level
     - `_initialize_response()`: Initializes backend-specific Response subclass
     - `_initialize_action()`: Loads and validates action handler
     - `_initialize_backend()`: Loads and validates backend handler
     - `_configure_debug_module()`: Applies debug filter overrides
3. **Dispatch** (in `dispatch()`):
   - `action_handler()`: Executes business logic
   - `backend_handler()`: Executes presentation logic
   - `_process_errors()`: Processes errors and runs error handler if available
   - `_commit()`: Commits file operations, refreshes caches, and commits database transactions
   - `flush_debug()`: Outputs debug information

### Critical Methods

- `get_arg(name)`: Access command arguments (via `gateway.request`, guaranteed non-None)
- `is_no(flag)`: Check if flags are disabled (via `gateway.request`, guaranteed non-None)
- `is_set(name)`: Check if argument is set (via `gateway.request`, guaranteed non-None)
- `gateway.response.set_action_response(data)`: Actions store results via response (guaranteed non-None)
- `gateway.response.add_output(text)`: Backends add output via response (guaranteed non-None)
- `report_error(type, content)`: Report errors via error_store module
- `is_error()`: Check error state via error_store module

**Note:** After Gateway initialization, `gateway.request`, `gateway.response`, `gateway.conn`, and `gateway.files` are guaranteed to be non-None. No null checks are needed when accessing these attributes in action handlers, backend handlers, or parser functions.

### Connection Management

Gateway initializes Connection/MySQLConnection/RootConnection based on request args:
- **Connection**: Standard connection using config file DSN
- **RootConnection**: Uses root credentials from command-line arguments
- **MySQLConnection**: Connects to MySQL system database (database=None)

Connection initialization returns user tier level detected from DSN username pattern: `{project_name}_{tier}`

### Commit Process

`_commit()` handles coordinated commit/rollback:
1. File operations (via `files.commit()`)
2. Cache refresh (page/image/file caches via `refresh_stale_*_caches()`)
3. Database transactions (via `conn.commit()`)

All operations rollback on errors. Dry-run mode automatically rolls back instead of committing.

### Default Commands

- HTTP backend: Defaults to `show_page` with `id=1`
- Parser backend: Defaults to `help`

See `Gateway.dispatch()` and `Gateway._initialize()` in `hh/gateway/gateway.py` for implementation.

---

## 3. Debug System

The debug system provides always-on warning capture with optional deeper modes. It uses a centralized data store with sophisticated filtering capabilities.

### Debug Registry

**File**: `hh/gateway/registry/debug.py`

**Purpose**: Centralized debug data collection and management

**Key Features**:
- Captures trace, log, debug, and warning messages from all modules
- Thread-safe access via locks
- Automatic color assignment to modules, files, and functions
- Whitelist, graylist, and blacklist filtering
- Entry indexing and combination counting for output management

**Global Debug Functions**: Use `trace_in()`, `trace_out()`, `log()`, `debug()`, `warn()` - never direct print statements.

**Safe Mode**: Use `safe_mode()` context manager when rendering debug data to prevent recursive debug rendering. The system uses thread-local storage to track safe mode depth and prevent infinite loops.

See `SharedDebugDataStore` class and global debug functions in `hh/gateway/registry/debug.py`.

### Debug Filters

**File**: `hh/gateway/debug/debug_filters.py`

**Purpose**: Three-tier filtering system for precise debug output control

**Filter Hierarchy**:
1. **Whitelist** (modules): Includes only modules matching patterns
2. **Graylist** (files): Includes only files matching patterns
3. **Blacklist** (functions): Excludes functions matching patterns

**Output Limits**: Controls how many debug entries are shown per module/file/function combination.

**Usage Examples**:
- `-log -gray re* -black is_no -debug-limit 0`: Log mode, gray filter for files starting with "re", black filter for "is_no" function, unlimited output
- `-debug-limit 1`: Quick peek (1 message per combination)
- `-debug-limit 20`: Deep dive (20 messages per combination)

See the filter class in `hh/gateway/debug/debug_filters.py` for implementation.

### Error System

**File**: `hh/gateway/error/error_store.py`

**Purpose**: Centralized error reporting and state management

**Error Types**: 12 distinct error types - request, registry, action, backend, debug, connection, JSON, syntax, link_resolution, cache_refresh, dependency, deployment

**Key Functions**:
- `report_error(error_type, content)`: Report errors
- `is_error()`: Check error state

Gateway uses `is_error()` throughout execution to check error state and `_process_errors()` runs error handler if available when errors are detected.

---

## 4. Response

**File**: `hh/gateway/response/response.py`

The output assembly system that collects, manages, and formats all response data from the system.

### Response Class

**Purpose**: Buffers output, stores action results, manages seed data, header links, and content sections

**Key Fields**:
- `output_buffer`: List of formatted output strings
- `action_response`: Action execution results (dict)
- `error_output`: Error output (dict, set by error handlers)
- `debug_output`: Debug output (dict, set by flush_debug)
- `seed_data`: Arbitrary client seed payload (dict)
- `header_css_links`, `header_js_links`: Custom CSS/JS links for HTML
- `title`, `path`, `page_text`: HTML layout fields
- `upper_content`, `lower_content`: HTML content sections
- `user_tier_level`: User tier level (0=unknown, 1=guest, 2=verified, 3=admin, 4=root)

**Key Methods**:
- `add_output(text)`: Backends add formatted output
- `set_action_response(data)`: Actions store execution results
- `get_action_response()`: Retrieve action results
- `set_seed_data()` / `add_seed_data()`: Manage client seed payload
- `add_css_link()` / `add_js_link()`: Add header links
- `set_content_wrapper_header()`: Sets content wrapper header
- `set_path()`, `set_page_text()`, `set_upper_content()`, `set_lower_content()`: HTML layout
- `set_user_tier_level()` / `get_user_tier_level()`: User tier management
- `get_output()`: Assembles final output string

**User Tier Sources**: User tier level can be set from:
- Connection initialization (detected from DSN username pattern)
- `USER_TIER` environment variable (if set)
- Explicitly via `set_user_tier_level()`

**Backend-Specific Subclasses**: Gateway initializes backend-specific Response subclass:
- `ResponseHTTP`: HTML output for web interface
- `ResponseParser`: CLI table output for parser backend
- `ResponseMCP`: JSON output for MCP backend
- `ResponseMaintenance`: JSON output for maintenance backend

**Note**: Error handling is managed separately by the centralized error_store system, not by Response.

See `Response` class and backend-specific subclasses in `hh/gateway/response/response.py`.

---

## 5. Request

**File**: `hh/gateway/request/request.py`

The command-line argument parsing and validation system that converts raw input into structured, typed data.

### Request Class

**Purpose**: Parses arguments, categorizes data, handles flag groups, manages commands

**Key Fields**:
- `raw_argv`: Original command line arguments
- `command`: Parsed command name
- `string_args`: String argument values (dict)
- `int_args`: Integer argument values (dict)
- `flag_args`: Boolean flag arguments (dict)
- `no_flags`: Disabled flag list (set)
- `extra_commands`: Additional command names (list)
- `extra_command_defaults`: Default values for extra commands (dict)

**Key Methods**:
- `parse_request()`: Grammar parser for command line arguments (called during __init__)
- `add_synthetic_arg()`: Adds programmatically generated arguments
- `is_no(flag)`: Checks if flag is disabled via no-flags or no-groups
- `is_set(name)`: Checks if argument is set
- `get_arg(name)`: Retrieves argument value by name
- `has_command()`: Checks if command exists
- `get_command()`: Retrieves command name

**Access Pattern**: Use `gateway.get_arg(name)` and `gateway.is_no(flag)` - never access Request directly.

**Flag Groups**: `NO_GROUPS` defines which flags work together (e.g., header-related flags). When a flag in a group is disabled with `--no-flag`, all flags in that group are disabled.

See `Request` class in `hh/gateway/request/request.py` for implementation.

---

## 6. Parsing Pipeline

The parsing pipeline transforms raw command-line input into a structured Request object through four sequential stages.

### Grammar Parser

**File**: `hh/gateway/request/grammar_parser.py`

**Purpose**: Orchestrates the entire parsing workflow

**Flow**: `tokenize()` → `parse()` → `Request()` → `build_request()`

**Implementation Note**: `parse_request()` creates a Request instance, then calls `build_request()` to populate it. `Request.__init__()` also calls `parse_request()` internally, creating a circular dependency that's handled by checking if parsing succeeded.

See `parse_request()` function in `hh/gateway/request/grammar_parser.py`.

### Tokenizer

**File**: `hh/gateway/request/tokenizer.py`

**Purpose**: Breaks down raw command-line strings into categorized tokens

**Key Features**:
- Detects quote styles (single/double quotes)
- Classifies token types (commands, flags, values)
- Handles special cases like negative numbers

See `tokenize()` function in `hh/gateway/request/tokenizer.py`.

### Parser

**File**: `hh/gateway/request/parser.py`

**Purpose**: Builds structured grammar representation from tokens

**Key Features**:
- Organizes tokens into parsed commands, flags, no-flags, and values
- Uses `ParserState` enum to track parsing progress
- Creates `ParsedCommand`, `ParsedFlag`, `ParsedValue` objects

See `parse()` function in `hh/gateway/request/parser.py`.

### Semantics

**File**: `hh/gateway/request/semantics.py`

**Purpose**: Constructs final Request object from parsed grammar

**Key Features**:
- Populates argument collections (string_args, int_args, flag_args, no_flags)
- Applies default values where appropriate
- Creates structured data model for system consumption

See `build_request()` function in `hh/gateway/request/semantics.py`.

---

## 7. Connection

**File**: `hh/gateway/connection/conn.py`

The database connection manager that provides unified access to main, cache, and history databases.

### Connection Class

**Purpose**: Manages multiple databases, detects user tier, supports transactions, provides CRUD operations

**Key Features**:
- **Multiple Databases**: Handles connections to main, cache, and history databases
- **User Tier Detection**: Automatically detects user tier level from DSN username pattern: `{project_name}_{tier}`
- **Transactions**: Manages transactions across all databases with commit/rollback
- **CRUD Operations**: Offers read, create, update, delete methods for each database
- **Dry Run**: Supports dry-run mode that rolls back instead of committing

**Key Methods**:
- `initialize()`: Opens connections to all databases, returns user tier level
- `close()`: Closes all database connections
- `commit()`: Commits all active transactions (rolls back if dry_run)
- `rollback()`: Rolls back all active transactions
- `read()`, `create()`, `update()`, `delete()`: Main database operations
- `read_cache()`, `create_cache()`, `update_cache()`: Cache database operations
- `read_history()`, `create_history()`, `update_history()`: History database operations (not yet implemented)

**Access Pattern**: Use `gateway.conn.read()`, `gateway.conn.create()`, etc. - never access Connection directly.

**Transaction Management**: Transactions start automatically on first write operation. Commit/rollback handled by `gateway._commit()`.

**Error Handling**: Connection errors are classified and attached to exceptions via `_classify_and_attach_error()` method, providing structured error information for debugging.

**Connection Subclasses**:
- **RootConnection** (`hh/gateway/connection/root_connection.py`): Uses root credentials for main database
- **MySQLConnection** (`hh/gateway/connection/mysql_connection.py`): Connects to MySQL system database (database=None)

**Configuration**: DSN loaded from `~/.{project_name}.cnf` files. Project name detected via `detect_project_context()`.

See `Connection` class and subclasses in `hh/gateway/connection/conn.py`.

---

## 8. FileSystem

**File**: `hh/gateway/system/file_system.py`

The file system operation manager that provides abstraction for filesystem operations with rollback support.

### FileSystem Class

**Purpose**: Schedules operations, supports rollback, handles OS differences, provides file access

**Key Features**:
- **Scheduled Operations**: Queues file move and delete operations for batch execution
- **Rollback Support**: Provides rollback capability for completed file operations
- **Operation Status Tracking**: Tracks operation status (scheduled, completed, failed, rolled_back, rollback_failed) for each file operation
- **OS Handling**: Detects and handles Windows, macOS, Linux/Ubuntu differences
- **File Access**: Offers file reading, writing, existence checking, and metadata operations
- **Dry Run**: Supports dry-run mode that skips file operation execution

**Key Methods**:
- `schedule_move()`: Schedules file move operation for commit
- `schedule_delete()`: Schedules file delete operation (soft delete to /tmp) for commit
- `commit()`: Executes all scheduled file operations
- `rollback()`: Rolls back all completed file operations
- `has_operations()`: Checks if there are scheduled operations
- `file_exists()`, `directory_exists()`: Existence checks
- `get_file_size()`: Gets file size in bytes
- `create_directory()`: Creates directory with optional permissions
- `read_file()`, `read_file_text()`: File reading
- `write_file()`, `write_file_text()`: File writing (immediate execution)
- `join_path()`, `normalize_path()`: Path manipulation
- `get_parent_directory()`, `get_filename()`: Path utilities

**Access Pattern**: Use `gateway.files.schedule_move()`, `gateway.files.read_file()`, etc. - never access FileSystem directly.

**Scheduled vs Immediate**: 
- `schedule_move()`/`schedule_delete()` queue operations for `commit()`
- `write_file()`/`write_file_text()` execute immediately

**Delete Operations**: `schedule_delete()` performs soft delete by moving files to `/tmp` with timestamped names.

**Commit Coordination**: File operations are committed before database transactions in `gateway._commit()`. Rollback processes operations in reverse order (LIFO).

**Error Handling**: File existence checks and reads return None/False on errors instead of raising exceptions. Errors reported via `error_store.report_error()`. Operation status is tracked for each file operation, allowing rollback of completed operations in reverse order (LIFO).

**Future Support**: Placeholder for remote file handler integration.

See `FileSystem` class in `hh/gateway/system/file_system.py` for implementation.

---

## Integration with Other Systems

### With Page System (see page.md)
- Gateway provides `gateway.conn` for database access
- Gateway coordinates cache refresh during commit via `refresh_stale_page_caches()`, `refresh_stale_image_caches()`, `refresh_stale_file_caches()`
- Actions use `gateway.response.set_action_response()` for results

### With Registry (see registry.md)
- Gateway uses CommandRegistry for handler discovery
- Actions use `@register_action` decorator
- Backends use `@register_parser`/`@register_http`/`@register_mcp` decorators

### With Render System (see render.md)
- Backends use render functions to format data
- Response system provides structured data for rendering

### With MCP Backend (see mcp.md)
- Gateway initializes ResponseMCP for JSON output
- MCP tools use gateway for argument access and response management

---

This document focuses specifically on the gateway and parsing infrastructure. For business logic modules (Page, Image, File), see the respective documentation files.

