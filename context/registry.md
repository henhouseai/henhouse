# Henhouse Registry System Architecture

This document covers the command registry, caching, backend configuration, action modules, and database connection systems that form the core execution layer of the Henhouse system.

## Table of Contents

1. [Command Registry](#1-command-registry)
2. [Cache](#2-cache)
3. [Backend](#3-backend)
4. [Generic Action Module](#4-generic-action-module)
5. [Connection Decorators](#5-connection-decorators)
6. [Connection](#6-connection)
7. [Generic Backend Module](#7-generic-backend-module)

## Agent Quick Reference

- **Registry Usage**: `CommandRegistry("command", "backend")` → `registry.get_action_handler()` for dynamic loading
- **Cache Access**: `discover_base_registrations()` provides command/backend discovery from JSON cache
- **Backend Types**: `['action', 'parser', 'mcp', 'http', 'maintenance']` with automatic decorator generation
- **Action Pattern**: `@register_action` + `@register_command` + `gateway.set_action_response(data)`
- **DB Decorators**: `@db_read` (read-only) / `@db_write` (with retry) for safe database operations
- **Error Flow**: Registry validation → gateway reporting → response coordination

## Agent Training Notes

### Registry System Integration
- **Registry Creation**: `CommandRegistry("command", "backend")` → validates command/backend existence and loads handler data
- **Handler Access**: Use `registry.get_action_handler()` and `registry.get_backend_handler()` for dynamic function loading
- **Cache Integration**: Registry works with JSON cache files to avoid repeated filesystem scans and module imports
- **Error Handling**: Registry errors become `registry_error()` calls in gateway response system

### Cache System Usage
- **Cache Discovery**: `discover_base_registrations()` provides command/backend lists from JSON cache
- **Command Variations**: System handles kebab-case ↔ snake_case conversion automatically (e.g., `command-list` ↔ `command_list`)
- **Cache Miss Handling**: Automatic regeneration when cache is stale or missing
- **Performance**: Avoids repeated filesystem scans by storing discovery results in `CACHE_DIR/cache/`

### Backend Type Management
- **Five Backend Types**: `['action', 'parser', 'mcp', 'http', 'maintenance']` with automatic decorator generation
- **Decorator Pattern**: Each type gets `@register_{type}` decorator (e.g., `@register_action`, `@register_parser`)
- **Handler Dictionaries**: Each type has corresponding dict (`actions`, `parsers`, `mcps`, `https`, `maintenances`)
- **Dynamic Registration**: Backend decorators automatically populate handler dictionaries during module import

### Action Module Development
- **Dual Registration**: Every action needs both `@register_action("name")` and `@register_command("name")` decorators
- **Gateway Integration**:
  - `get_gateway()` for system access
  - `gateway.get_arg(name)` for command arguments
  - `gateway.set_action_response(json_data)` for results
  - `report_error("action", message)` for error reporting (import from `hh.gateway.error.error_store`)
- **Response Structure**: Use `success_payload(data)` for standardized JSON response format
- **Database Access**: Use `@db_read` (queries) or `@db_write` (modifications) decorators for safe database operations

### Connection Decorator Patterns
- **Read Operations**: `@db_read` decorator - no retry, no transaction, for SELECT queries
- **Write Operations**: `@db_write` decorator - with retry logic, automatic transactions, for INSERT/UPDATE/DELETE
- **Error Classification**: Automatic error categorization with retry decisions based on error type
- **Configuration**: Retry counts, delays, and transaction modes come from config system
- **Agent Validation**: Use `agent_validation=True` with `agent_id` and `badge_ts` parameters for secure access

### Backend Handler Development
- **Backend Registration**: Typically register for both CLI and web access by applying both `@register_parser("command")` and `@register_http("command")` decorators to the same function
- **Gateway Integration**:
  - `gateway.get_action_response()` for action results
  - `gateway.add_backend_response(formatted_output)` for final output
  - `report_error("backend", message)` for error reporting (import from `hh.gateway.error.error_store`)
- **Render System**: Use `render_header_block()`, `render_block()`, `finalize_output()` for formatting
- **Output Assembly**: Backend handlers format action response data into user-facing output

### Common Integration Patterns
- **Command Discovery**: Use `check_command_exists(command)` and `check_backend_exists(backend)` for validation
- **Handler Loading**: `registry.load_action_module()` and `registry.load_backend_module()` for dynamic loading
- **Error Propagation**: Registry errors → gateway error methods → response system error collections
- **Cache Management**: Cache files stored in `hh/gateway/registry/cache/` with automatic regeneration


## 1. Command Registry

**File**: `hh/gateway/registry/registry.py`

The command registry is a sophisticated data holder and accessor class that manages command and backend information with dynamic handler loading and validation. It's created by the gateway during initialization and handles the complex process of matching commands to their appropriate handlers.

The registry doesn't do discovery or scanning itself - that's handled by the cache system. Instead, it takes pre-discovered information from the cache and provides a clean interface for the gateway to access action handlers, backend handlers, and error handlers. It manages dynamic module loading, validation, and error handling for handler resolution.

The registry uses a sophisticated two-part data structure: it stores both action handler information (from the "action" backend cache) and backend handler information (from the specific backend cache) for the current command, allowing the gateway to access both types of handlers through a unified interface.

### CommandRegistry Class

#### owned by:
- gateway : *Created and managed by gateway instance*

#### owns:
- command, backend : *Command and backend identifiers*
- matched_backend : *Selected backend handler with validation*
- backend_registration, action_cache_data, backend_cache_data, error_cache_data : *Handler cache data with validation state*
- handler loading state : *Dynamic module loading and validation tracking*

#### data managed:
- command (local copy) : *Command name being processed*
- backend (local copy) : *Backend type being used*
- matched_backend (local copy) : *Selected backend handler reference*
- backend_registration (local copy) : *Backend cache data for current command*
- action_cache_data (local copy) : *Action handler cache data for current command*
- backend_cache_data (local copy) : *Backend handler cache data for current command*
- error_cache_data (local copy) : *Error handler cache data for current backend*
- handler loading state (local copy) : *Tracks which handlers have been loaded and validated*

#### calls:
- **select_backend()** : *Finds and validates backend handler from backends dict*
- **select_command()** : *Finds and validates action handler from action cache*
- **select_error_handler()** : *Finds and validates error handler from backend cache*
- **has_command(), has_backend(), has_action_handler(), has_backend_handler()** : *Validates handler availability*
- **has_action_args(), has_error_handler()** : *Checks additional handler properties*
- **get_action_handler(), get_backend_handler(), get_error_handler()** : *Dynamically loads and validates handler functions*
- **get_action_args()** : *Gets action argument list from cache data*
- **load_action_module(), load_backend_module()** : *Loads and validates handler modules*

#### called by:
- gateway (handler resolution) : *Gateway resolves action and backend handlers*

#### retrieves from:
- cache (check_command_exists, check_backend_exists, check_command_in_backend) : *Gets handler existence and cache data*
- backends dict (select_backend) : *Gets backend handler references*
- importlib (get_action_handler, get_backend_handler) : *Dynamically loads handler modules with validation*

#### provides to:
- gateway (handler access methods) : *Provides validated handler access methods*

#### configuration dependencies:
- BACKEND_TYPES : *Supported backend type definitions from backend configuration*

#### error handling:
- **Handler Loading Validation**: Validates handler modules during dynamic loading with detailed error reporting
- **Cache Miss Handling**: Manages missing handler registrations with graceful degradation
- **Module Import Errors**: Handles import failures during discovery with retry logic
- **Handler Function Validation**: Ensures loaded handlers have required methods and signatures

#### agent training notes:
- **Dynamic Handler Loading**: Registry provides `get_*_handler()` methods for runtime module loading
- **Cache Integration**: Works with sophisticated cache system for performance optimization
- **Backend Selection**: Matches commands to appropriate backend types with validation
- **Error Propagation**: Registry errors become registry-level errors in response system
- **Handler Validation**: Validates handler availability before providing access methods

#### cross-references:
- **[Cache](#2-cache)**: Provides cached handler data for registry operations
- **[Backend](#3-backend)**: Uses backend type definitions for handler discovery
- **[Gateway](#2-gateway)**: Created by and provides handlers to gateway

---

## 2. Cache

**File**: `hh/gateway/registry/cache.py`

The sophisticated caching and discovery system that provides performance optimization by avoiding repeated file system scans and module imports. It:

- **Caches Discovery Results**: Stores discovered command and backend registrations in JSON files to avoid repeated scanning
- **Handles Command Variations**: Supports multiple naming conventions (kebab-case, snake-case) for command matching
- **Manages Cache Misses**: Automatically regenerates cache when needed and handles fallback scenarios
- **Coordinates Discovery**: Orchestrates the scanning of decorators and importing of modules across the codebase

The cache system is triggered by CommandRegistry during handler resolution and provides the foundation for efficient command and backend discovery throughout the system.

### Global Module

#### owned by:
- global scope : *Module-level caching and discovery*

#### owns:
- CACHE_DIR : *Cache directory path*
- cache files : *JSON cache files for registrations*
- filesystem scanning : *Module and decorator discovery logic*
- module importing : *Dynamic module loading for registration*

#### data managed:
- base registrations (source of truth) : *Cached base command and backend lists*
- backend-specific registrations (source of truth) : *Cached handler registrations*
- module validation state : *Tracks which cached modules are still valid*

#### calls:
- **discover_base_registrations()** : *Discovers and caches base command and backend registrations*
- **discover_all_backends(), discover_all_commands()** : *Gets all registered backends/commands from cache*
- **discover_backend_specific_registrations()** : *Discovers and caches handlers for specific backend type*
- **discover_all_backend_handlers()** : *Discovers all backend handlers across all backend types*
- **check_command_exists(), check_backend_exists()** : *Checks handler existence using cached data*
- **check_command_in_backend()** : *Checks command availability in backend with name variation support*
- **_scan_for_decorator()** : *Scans filesystem for decorator usage patterns*
- **_import_modules()** : *Imports modules containing decorators to trigger registration*
- **_validate_cached_module_path()** : *Validates cached module paths are still importable*

#### called by:
- CommandRegistry (handler discovery) : *Registry discovers available handlers*

#### retrieves from:
- file system (module scanning) : *Scans for decorator usage patterns across codebase*
- registry (registered handlers) : *Gets registered handler data after module import*
- BACKEND_TYPES (backend configuration) : *Gets supported backend types for discovery*
- filesystem (JSON cache files) : *Reads and writes cached discovery results*

#### provides to:
- CommandRegistry (handler information) : *Provides discovered handler data and cache management*
- file system (JSON cache files) : *Writes cached discovery results to disk*

#### configuration dependencies:
- CACHE_DIR : *Cache directory path configuration (relative to module)*
- BACKEND_TYPES : *Backend type definitions for discovery scoping*

#### error handling:
- **Cache Misses**: Automatically regenerates cache when stale or missing
- **File System Errors**: Handles scan failures and permission issues with graceful fallback
- **Module Import Errors**: Manages import failures during discovery with detailed logging
- **JSON Serialization**: Handles cache file read/write errors with validation

#### agent training notes:
- **Performance Optimization**: Avoids repeated filesystem scans through intelligent JSON caching
- **Name Variation Support**: Handles kebab-case ↔ snake_case command matching automatically
- **Automatic Regeneration**: Cache rebuilds automatically when source files change
- **Discovery Coordination**: Orchestrates decorator scanning across entire codebase
- **Validation System**: Validates cached module paths are still importable before use

#### cross-references:
- **[Command Registry](#1-command-registry)**: Consumes cached handler data for performance
- **[Backend](#3-backend)**: Uses backend types to scope discovery operations

---

## 3. Backend

**File**: `hh/gateway/registry/backend.py`

The centralized backend configuration system that defines the supported backend types and their associated metadata. It:

- **Defines Backend Types**: Establishes the canonical list of supported backend types (action, parser, mcp, http, maintenance)
- **Maps Decorators**: Associates each backend type with its corresponding registration decorator name
- **Maps Dictionaries**: Associates each backend type with its corresponding handler dictionary name
- **Provides Descriptions**: Offers human-readable descriptions for each backend type

The backend configuration is used during module initialization and by registry/cache systems for backend discovery, handler registration, and decorator generation.

### Global Module

#### owned by:
- global scope : *Module-level backend configuration*

#### owns:
- BACKEND_TYPES : *List of supported backend types*
- BACKEND_DESCRIPTIONS : *Backend type descriptions*
- BACKEND_DECORATORS : *Decorator names for each backend type*
- BACKEND_DICTS : *Dictionary names for each backend type*

#### data managed:
- backend configuration (source of truth) : *Backend type definitions and mappings*

#### calls:
- none : *Pure configuration data*

#### called by:
- registry (backend handling) : *Registry uses backend configuration*
- cache (backend discovery) : *Cache uses backend configuration*

#### retrieves from:
- none : *Static configuration*

#### provides to:
- registry (backend types) : *Provides backend type definitions*
- cache (backend discovery) : *Provides backend discovery configuration*

#### configuration dependencies:
- none : *Self-contained configuration definitions*

#### error handling:
- **Configuration Validation**: Ensures all backend types have required mappings
- **Type Consistency**: Validates decorator and dictionary name consistency

#### agent training notes:
- **Backend Types**: Five main types - action (business logic), parser (CLI parsing), mcp (Model Context Protocol), http (web server), maintenance (maintenance backend handlers)
- **Decorator Mapping**: Each type has specific registration decorator pattern
- **Dictionary Mapping**: Each type has corresponding handler dictionary name
- **Discovery Foundation**: Provides basis for registry/cache discovery operations

#### cross-references:
- **[Command Registry](#1-command-registry)**: Uses backend type definitions for handler discovery
- **[Cache](#2-cache)**: Uses backend configuration to scope discovery operations

---

## 4. Generic Action Module

**File**: `hh/gateway/registry/utils.py` (example: `command_list` function)

The business logic execution layer that implements the core functionality of commands. It:

- **Implements Business Logic**: Contains the actual command functionality and data processing
- **Uses Dual Registration**: Registers with both `@register_action` and `@register_command` decorators
- **Returns Structured Data**: Provides JSON response data via `gateway.set_action_response()`
- **Handles Errors**: Reports action-level errors through the gateway error system
- **Accesses Gateway**: Uses `get_gateway()` to access command arguments and system state
- **Database Integration**: Uses sophisticated decorators for safe database access with retry logic

Action modules are executed by the gateway after command resolution and provide the core business logic that backends then format for presentation.

### Example Implementation (command_list)

```python
@register_action("command_list")
@register_command("command_list")
def command_list() -> bool:
    # Reads from JSON cache files
    # Loads command registry data
    # Returns structured command list data
    # Uses gateway.set_action_response() for results
```

### Global Module

#### owned by:
- registry (via decorators) : *Registered via @register_action and @register_command decorators*

#### owns:
- action functions : *Business logic functions with dual registration*
- gateway access : *Access to gateway instance for system integration*
- database operations : *Safe database access through decorators*

#### data managed:
- business logic state (local copy) : *Action-specific state and data*
- action response data (via gateway) : *Structured JSON response data set via gateway*
- error state (via gateway) : *Action-level error reporting through gateway*

#### calls:
- **get_gateway()** : *Gets gateway instance for system access*
- **gateway.get_arg()** : *Retrieves command line arguments*
- **gateway.is_no()** : *Checks no-flag states*
- **gateway.set_action_response()** : *Sets structured JSON response data*
- **report_error("action", message)** : *Reports action-level errors*
- **success_payload()** : *Creates standardized JSON response structure*
- **@db_read/@db_write decorators** : *Database access decorators with retry logic*
- **r_query()** : *Executes SELECT queries with parameter binding*
- **u_query()** : *Executes UPDATE queries with parameter binding*
- **c_query()** : *Executes INSERT queries with parameter binding*
- **d_query()** : *Executes DELETE queries with parameter binding*
- **ensure_iso_timestamps()** : *Converts timestamps to ISO format*
- **debug functions** : *Debug logging and tracing*

#### called by:
- gateway (action_handler()) : *Gateway executes action handler*

#### retrieves from:
- gateway (arguments, database access) : *Gets arguments and database connections*
- database (via connection decorators) : *Gets data from database with retry logic*
- cache system (discovered data) : *Gets cached command/backend information*
- registry (handler information) : *Gets registered handler data*

#### provides to:
- gateway (action response data) : *Provides structured JSON response data*
- backend modules (via gateway) : *Provides data for backend formatting*

#### configuration dependencies:
- none : *Business logic is typically configuration-agnostic*

#### error handling:
- **Action-Level Errors**: Reports business logic failures through gateway error system
- **Database Errors**: Propagated from connection decorators with retry context and classification
- **Argument Validation**: Validates command arguments before processing
- **Response Structure**: Ensures proper JSON response structure

#### agent training notes:
- **Dual Registration Pattern**: Every action needs both `@register_action` and `@register_command` decorators
- **Gateway Integration**:
  - `get_gateway()` for system access
  - `gateway.get_arg(name)` for arguments
  - `gateway.set_action_response(json_data)` for results
  - `report_error("action", message)` for error reporting
- **Database Access**: Use `@db_read`/`@db_write` decorators for safe database operations with automatic retry
- **Response Structure**: Return JSON-serializable data structures via success_payload()

#### cross-references:
- **[Command Registry](#1-command-registry)**: Provides registered action handlers
- **[Connection Decorators](#5-connection-decorators)**: Used for database access patterns
- **[Connection](#6-connection)**: Provides underlying database connectivity

---

## 5. Connection Decorators

**File**: `hh/gateway/connection/decorators.py`

The sophisticated database access abstraction layer that provides decorators for safe database operations. It:

- **Provides Database Decorators**: Offers `@db_read` and `@db_write` decorators for database operations
- **Manages Connection Lifecycle**: Handles connection creation, transaction management, and cleanup
- **Implements Error Handling**: Provides sophisticated error classification and retry logic with exponential backoff
- **Supports Agent Validation**: Validates agent identity for secure database access
- **Handles Configuration**: Uses config system for retry counts, delays, and transaction modes

Connection decorators are used by action modules to safely access the database with automatic error handling and retry logic.

### Global Module

#### owned by:
- global scope : *Module-level decorator functions*

#### owns:
- @db_read decorator : *Database read operation decorator*
- @db_write decorator : *Database write operation decorator*
- with_connection function : *Core connection management decorator*
- error classification functions : *Error handling and retry logic*
- config defaults : *Configuration management*

#### data managed:
- error classification rules (source of truth) : *Error code mapping and retry logic*
- configuration defaults (local copy) : *Retry counts, delays, transaction modes*
- connection state (local copy) : *Connection lifecycle management*

#### calls:
- **@db_read()** : *Decorator for database read operations (no retry)*
- **@db_write()** : *Decorator for database write operations (with retry)*
- **with_connection()** : *Core connection management decorator with retry logic*
- **classify_exception()** : *Classifies database exceptions for retry decisions*
- **should_retry()** : *Determines if operation should be retried*
- **get_config_defaults()** : *Gets configuration defaults*

#### called by:
- action modules (via decorators) : *Actions use decorators for database access*

#### retrieves from:
- connection module : *Gets connection management functionality*
- config system : *Gets configuration defaults*
- gateway : *Gets gateway instance for error reporting*

#### provides to:
- action modules (database access) : *Provides database access to actions*
- gateway (error reporting) : *Reports connection errors through gateway*

#### configuration dependencies:
- retry configuration : *Retry counts, delays, backoff strategies from config*
- connection configuration : *Connection pool settings, timeouts*

#### error handling:
- **Sophisticated Retry Logic**: Exponential backoff with configurable retry limits and intelligent error classification
- **Error Classification**: Categorizes database exceptions for appropriate retry decisions
- **Agent Validation**: Ensures secure database access through identity verification
- **Connection Lifecycle**: Manages connection creation, usage, and cleanup with proper error handling
- **Transaction Management**: Automatic rollback on failures

#### agent training notes:
- **Decorator Pattern**: Use `@db_read` for queries (no retry), `@db_write` for modifications (with retry)
- **Automatic Features**:
  - Connection management and cleanup
  - Retry logic with exponential backoff
  - Agent identity validation
  - Error classification and reporting
- **Configuration Driven**: Retry counts, delays, and strategies come from config system
- **Error Propagation**: Database errors become connection-level errors in response system

#### cross-references:
- **[Connection](#6-connection)**: Provides the underlying database connection functionality
- **[Generic Action Module](#4-generic-action-module)**: Primary consumer of database decorators

---

## 6. Connection

**File**: `hh/gateway/connection/connection.py`

The database connection and query execution layer that provides low-level database access functionality. It:

- **Manages Database Connections**: Handles connection creation, configuration loading, and connection lifecycle
- **Executes Database Queries**: Provides query execution with parameter binding and result processing
- **Handles Data Types**: Manages TypedDict structures for database rows and JSON responses
- **Supports Agent Validation**: Validates agent identity for secure database access
- **Provides JSON Utilities**: Offers JSON serialization, timestamp conversion, and response formatting

The connection module is used by connection decorators to provide the underlying database access functionality with proper error handling and data type management.

### Global Module

#### owned by:
- global scope : *Module-level database connection management*

#### owns:
- connection functions : *Database connection and query execution functions*
- TypedDict classes : *DatabaseRow and JsonResponse data structures*
- DSN configuration : *Database connection configuration*
- utility functions : *JSON and timestamp utility functions*

#### data managed:
- DSN data (source of truth) : *Database connection configuration*
- TypedDict definitions (source of truth) : *Data structure definitions*
- connection state (local copy) : *Active database connections*

#### calls:
- **load_dsn()** : *Loads database configuration from config file*
- **get_connection()** : *Creates database connections with cursor configuration*
- **r_query()** : *Executes SELECT queries with parameter binding*
- **u_query()** : *Executes UPDATE queries with parameter binding*
- **c_query()** : *Executes INSERT queries with parameter binding*
- **d_query()** : *Executes DELETE queries with parameter binding*
- **validate_agent_identity()** : *Validates agent identity for secure access*
- **json_success()/json_error()** : *Creates JSON response structures*
- **iso_now()** : *Gets current timestamp in ISO format*
- **ensure_iso_timestamps()** : *Converts timestamps to ISO format*
- **pymysql.connect()** : *Creates database connections*

#### called by:
- action modules (via decorators) : *Actions access database through decorators*

#### retrieves from:
- config files (DSN data) : *Gets database connection configuration from ~/.henhouse.cnf*
- pymysql (database operations) : *Gets database functionality*
- datetime (timestamp functions) : *Gets timestamp functionality*

#### provides to:
- connection decorators (database access) : *Provides database connections and query execution*
- action modules (via decorators) : *Provides database access through decorators*

#### configuration dependencies:
- DSN configuration : *Database connection settings from ~/.henhouse.cnf*
- connection pool settings : *Connection pool size, timeout configurations*

#### error handling:
- **Connection Management**: Handles connection failures and recovery
- **Query Execution**: Parameter binding validation and SQL injection prevention
- **Agent Validation**: Secure identity verification before database access
- **Timestamp Handling**: ISO format conversion and validation

#### agent training notes:
- **Configuration Location**: Database settings loaded from ~/.henhouse.cnf
- **Connection Management**: Automatic connection lifecycle management
- **Security Features**:
  - Agent identity validation
  - Parameter binding for SQL injection prevention
  - Secure connection handling
- **Data Types**: Provides TypedDict structures for type-safe database operations
- **JSON Utilities**: Built-in JSON serialization and timestamp formatting

#### cross-references:
- **[Connection Decorators](#5-connection-decorators)**: Uses connection module for underlying database access
- **[Generic Action Module](#4-generic-action-module)**: Indirectly uses connection functionality through decorators

---

## 7. Generic Backend Module

**File**: `hh/gateway/registry/render_command_list.py` (example: `command_list` function)

The backend handler layer that processes action response data through different backend types. It:

- **Handles Multiple Backend Types**: Supports various backend handler types for different processing needs
- **Uses Backend Registration**: Registers with backend-specific decorators for different handler types
- **Processes Response Data**: Works with action response data through backend-specific logic
- **Provides Backend-Specific Output**: Each backend type produces different output formats

Backend modules are executed by the gateway after action completion and provide backend-specific processing and output.

### Example Implementation (render_command_list)

```python
@register_http('command_list')
@register_parser('command_list')
def command_list() -> bool:
    # Gets action response data from gateway
    # Renders command list using render system (formats as CLI tables or HTML based on backend type)
    # Adds formatted output to gateway response
    # Uses field configurations for table formatting
```

### Global Module

#### owned by:
- registry (via decorators) : *Registered via backend-specific decorators*

#### owns:
- backend functions : *Presentation logic functions*
- gateway access : *Access to gateway instance*

#### data managed:
- formatted output (local copy) : *Backend-specific output formatting*
- backend response data (via gateway) : *Response data set via gateway*

#### calls:
- **get_gateway()** : *Gets gateway instance for argument access*
- **gateway.get_arg()** : *Retrieves command line arguments*
- **gateway.is_no()** : *Checks no-flag states*
- **gateway.has_action_response()** : *Checks if action response exists*
- **gateway.get_action_response()** : *Gets action response data*
- **gateway.add_backend_response()** : *Adds formatted output*
- **report_error("backend", message)** : *Reports backend-level errors (import from `hh.gateway.error.error_store`)*
- **render functions** : *Rendering system calls*
- **debug functions** : *Debug logging and tracing*

#### called by:
- gateway (backend_handler()) : *Gateway executes backend handler*

#### retrieves from:
- gateway (action response data) : *Gets action execution results*
- render system (formatting functions) : *Gets rendering functionality*

#### provides to:
- gateway (formatted output) : *Provides formatted output*

#### configuration dependencies:
- none : *Backend logic is typically configuration-agnostic*

#### error handling:
- **Backend-Level Errors**: Reports presentation logic failures through gateway
- **Render System Errors**: Propagated from rendering system with formatting context
- **Response Processing**: Handles malformed or missing action response data

#### agent training notes:
- **Backend Registration**: Uses backend-specific decorators matching the backend types (typically both `@register_parser` and `@register_http` on the same function for CLI and web support)
- **Gateway Integration**:
  - `get_gateway()` for system access
  - `gateway.get_action_response()` for action results
  - `gateway.add_backend_response()` for formatted output
  - `report_error("backend", message)` for error reporting (import from `hh.gateway.error.error_store`)
- **Render System Usage**: Leverages render functions for output formatting
- **Output Production**: Each backend type produces different output formats

#### cross-references:
- **[Command Registry](#1-command-registry)**: Provides registered backend handlers
- **[Generic Action Module](#4-generic-action-module)**: Processes action response data for presentation
