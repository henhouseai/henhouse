# Henhouse Gateway System Architecture

This document covers the core gateway and parsing infrastructure of the Henhouse system, including the entry point, central orchestration, debugging, response management, and command-line parsing pipeline.

## Table of Contents

1. [Entry Point (hen.py)](#1-entry-point-henpy)
2. [Gateway](#2-gateway)
3. [Debug Registry](#3-debug-registry)
4. [Debug Filters](#4-debug-filters)
5. [Response](#5-response)
6. [Request](#6-request)
7. [Grammar Parser](#7-grammar-parser)
8. [Tokenizer](#8-tokenizer)
9. [Parser](#9-parser)
10. [Semantics](#10-semantics)
11. [Connection](#11-connection)
12. [FileSystem](#12-filesystem)

## Agent Quick Reference

- **Entry Point**: `hen.py` → `get_gateway()` → `dispatch()`
- **Core Dispatch Flow**: arguments → grammar → registry → cache → modules → handlers → response
- **Key Objects**: Request, Response, CommandRegistry, Gateway
- **Parsing Pipeline**: Grammar Parser → Tokenizer → Parser → Semantics
- **Error System**: Centralized error store (error_store.py) with report_error() and is_error() functions, 10 error types
- **Debug System**: always-on warning system can be toggled into deeper modes like -debug -log -trace 
- **Debug System Control**: White/gray/black lists + limit features allow fine tune control over exactly what modules and messages show up

## Agent Training Notes

### Gateway Integration Points
- **Gateway Access**: Use `get_gateway()` to access system state and arguments
- **Argument Retrieval**: `gateway.get_arg(name)` for string/integer arguments
- **Flag Checking**: `gateway.is_no(flag)` for no-flag states
- **Response Setting**: `gateway.response.set_action_response(json_data)` for action results
- **Error Reporting**: Use `report_error(error_type, content)` from error_store module

### Parsing Pipeline Understanding
- **4-Stage Process**: Raw args → tokens → parsed grammar → Request object
- **Grammar Parser**: Orchestrates the entire parsing workflow
- **Tokenizer**: Handles quote detection and token classification
- **Parser**: Builds structured grammar from tokens
- **Semantics**: Constructs final Request with proper data types

### Debug System Control
- **Default white-list**: is set to * meaning all modules in all folders are allowed to report output
- **Default gray-list**: is empty
- **Default black-list** is empty
- **Default debug-limit**: is set to 10 messages shown before further output from any unique method is suppressed
- **Default verbosity**: is to always show warnings
- **Adding -debug flag**: will show debug messages + warnings
- **Adding -log flag**: will show log messages + debug messages + warnings
- **Adding -trace flag**: will show additional trace-route analysis of the entire execution tree
- **Overriding the -white flag**: lets you limit the folders that a module must match, like for example:  -white /hh/render/table/,/hh/gateway*,*help*
- **Overriding the -gray flag**: lets you hone in on specific filenames, like for example: -gray gate*,re* will get you gateway, request, response, registry, and render which are all handy top level groups.
- **Overriding the -black flag**: lets you omit any specific functions/methods that would spam the output, like for example: -black is_no
- **Overriding the -debug_limit flag**: lets you limit how many times any specifc combo of folder + file + function gets output globally, like for example set to 1-3 for quick peek or 20-30 for deep dive, or 0 for unlimited output
- **Advanced Usage Example**: -log -gray re* -black is_no -debug-limit 0
- **Disbling the Whole System**: is possible using the --no_debug flag anywhere in teh command-line will prevent any debug systems from loading and will noop all reporting methods.

---

## 1. Entry Point (hen.py)

**File**: `hen.py`

The main entry point that bridges the command line to the Henhouse system. It:

- **Captures Input**: Gets raw command-line arguments from sys.argv
- **Creates Gateway**: Instantiates the singleton gateway instance
- **Dispatches Request**: Hands control to the gateway with "parser" backend
- **Outputs Result**: Prints the final formatted response to stdout
- **Exits Cleanly**: Returns appropriate exit code to the system

The script follows a simple pattern: parse → gateway → print → exit, keeping the entry point minimal and focused.

### owned by:
- global : *Main entry point script*

### owns:
- gateway (via get_gateway()) : *Gateway instance access*
- main() function : *Main execution function*

### data managed:
- command line arguments (raw_argv) : *Raw command line input*
- exit code (return value) : *Process exit status*

### calls:
- **get_gateway()** : *Gets singleton gateway instance*
- **gateway.dispatch(argv, "parser")** : *Dispatches request to gateway*
- **print()** : *Outputs final result*
- **SystemExit()** : *Exits with return code*

### called by:
- system (entry point) : *Command line execution*
- SystemExit (if __name__ == "__main__") : *Direct script execution*

### retrieves from:
- sys.argv (command line arguments) : *Gets raw command line input*

### provides to:
- gateway (raw arguments and backend type) : *Provides command line data*
- system (exit code) : *Provides process exit status*

### configuration dependencies:
- none : *No external configuration required*

### error handling:
- **System Exit**: Uses SystemExit for clean process termination
- **Exception Propagation**: Allows unhandled exceptions to propagate for debugging

### agent training notes:
- **Entry Pattern**: Always starts with `if __name__ == "__main__"` check
- **Gateway Access**: Use `get_gateway()` function, not direct instantiation
- **Minimal Interface**: Entry point should remain simple - no business logic here

### cross-references:
- **[Gateway](#2-gateway)**: Receives raw arguments and backend specification
- **[Request](#6-request)**: Arguments become structured Request object
- **[Response](#5-response)**: Final output comes from Response system

---

## 2. Gateway

**File**: `hh/gateway/gateway.py`

The central orchestrator and state manager for the entire Henhouse system. It:

- **Manages State**: Holds the current request, response, registry, and handlers
- **Coordinates Execution**: Orchestrates the action-backend execution sequence
- **Handles Errors**: Provides unified error reporting across all layers
- **Manages Debugging**: Controls debug output and tracing
- **Provides Interfaces**: Offers consistent APIs for all subsystems

The gateway pattern ensures that all components interact through a single, well-defined interface rather than directly with each other.

### Gateway Class

#### owned by:
- global (singleton pattern) : *Managed by module-level singleton pattern*

#### owns:
- request : *Parsed command-line arguments and flags*
- response : *Output buffer and response management*
- registry : *Command and backend handler discovery*
- conn : *Database connection instance (Connection, MySQLConnection, or RootConnection)*
- files : *FileSystem instance for file operations*
- os : *ProcessManager instance for cross-platform process management*
- action_handler : *Business logic execution function*
- backend_handler : *Presentation logic execution function*
- error_handler : *Error processing function*
- debug_system : *Debug system identifier*
- debug_module : *Debug module instance*
- get_debug_func : *Debug function factory*
- _user_tier_level : *User tier level (0=unknown, 1=guest, 2=verified, 3=admin, 4=root)*

#### data managed:
- command (source of truth) : *Current command being executed*
- backend (source of truth) : *Current backend being used*
- debug_system (source of truth) : *Debug system configuration*
- debug_module (source of truth) : *Debug module instance*
- get_debug_func (source of truth) : *Debug function factory*
- _user_tier_level (source of truth) : *User tier level from connection initialization*

#### calls:
- **dispatch()** : *Main execution flow through action and backend*
- **_initialize()** : *Sets up all subsystems in proper order*
- **_initialize_debug_module()** : *Configures debugging based on request flags*
- **_initialize_command()** : *Extracts command from parsed request (with defaults for http/parser backends)*
- **_initialize_connection()** : *Initializes database connection (Connection, MySQLConnection, or RootConnection) and returns user tier level*
- **_initialize_response()** : *Initializes backend-specific Response subclass*
- **_initialize_action()** : *Loads and validates action handler*
- **_initialize_backend()** : *Loads and validates backend handler*
- **_configure_debug_module()** : *Applies debug filter overrides*
- **_apply_debug_filter_overrides()** : *Applies debug filter overrides from request*
- **_process_errors()** : *Processes errors and runs error handler if available*
- **_commit()** : *Commits file operations, refreshes caches, and commits database transactions*
- **Request(raw_argv)** : *Creates request parser instance*
- **CommandRegistry(command, backend)** : *Discovers and loads handlers*
- **Connection() / MySQLConnection() / RootConnection()** : *Creates database connection*
- **FileSystem()** : *Creates file system handler*
- **ProcessManager()** : *Creates process management handler*
- **action_handler()** : *Executes business logic*
- **backend_handler()** : *Executes presentation logic*
- **error_handler()** : *Executes error handling logic*
- **registry.load_action_module()** : *Loads action module*
- **registry.load_backend_module()** : *Loads backend module*
- **flush_debug()** : *Outputs debug information*
- **get_arg()** : *Provides argument access to components*
- **is_no()** : *Checks no-flag states*
- **is_set()** : *Checks if argument is set*
- **capture()** : *Captures debug messages*
- **get_debug_safe_mode()** : *Checks if in safe debug mode*
- **switch_to_safe_debug()** : *Switches to safe debug mode*
- **restore_debug_system()** : *Restores original debug system*
- **report_error()** : *Reports errors via centralized error store*
- **is_error()** : *Checks error state via centralized error store*

#### called by:
- hen.py (dispatch) : *Main entry point calls dispatch method*
- get_gateway() (singleton access) : *Singleton factory creates instance*
- actions (get_gateway()) : *Actions access gateway for argument access*
- backends (get_gateway()) : *Backends access gateway for response data*
- debug system : *Debug system calls gateway methods*

#### retrieves from:
- request (parsed arguments) : *Gets command and argument data*
- registry (handlers, error handlers) : *Gets action and backend handlers*
- response (output) : *Gets response data*
- error_store (error state) : *Gets error state via is_error()*

#### provides to:
- actions (gateway instance, argument access, response) : *Provides gateway, argument access, and response for set_action_response()*
- backends (gateway instance, action response, response) : *Provides gateway, action results, and response for add_output()*
- hen.py (final output) : *Provides final formatted output*

### Global Module

#### owned by:
- global scope : *Module-level global variables and functions*

#### owns:
- gateway (singleton instance) : *Single gateway instance for the application*
- trace_in, trace_out, log, debug, warn (debug functions) : *Global debug function references*

#### data managed:
- gateway (source of truth) : *Singleton gateway instance*
- debug functions (source of truth) : *Global debug function implementations*

#### calls:
- **_initialize_debug()** : *Initializes debug functions on module load*
- **Gateway()** : *Creates singleton gateway instance*
- **get_trace_in(), get_trace_out(), get_log(), get_debug(), get_warn()** : *Gets debug function implementations*

#### called by:
- hen.py (get_gateway) : *Main entry point gets gateway instance*
- debug system (debug functions) : *Debug system uses global debug functions*
- actions (debug functions) : *Actions use global debug functions*

#### retrieves from:
- debug_registry (debug function implementations) : *Gets debug function implementations*

#### provides to:
- hen.py (get_gateway function) : *Provides gateway access function*
- debug system (debug functions) : *Provides global debug functions*
- actions (debug functions) : *Provides global debug functions*

### configuration dependencies:
- debug system configuration : *Debug flags and module paths from debug system*

### error handling:
- **Centralized Error Store**: Uses error_store module with report_error() and is_error() functions
- **Error Types**: 12 distinct error types - request, registry, action, backend, debug, connection, JSON, syntax, link_resolution, cache_refresh, dependency, deployment
- **Error Processing**: _process_errors() method runs error handler if available when errors are detected
- **Error State Checking**: Uses is_error() from error_store to check error state throughout execution

### agent training notes:
- **Singleton Pattern**: Always use `get_gateway()`, never instantiate directly
- **Critical Methods**:
  - `get_arg(name)`: Access command arguments
  - `is_no(flag)`: Check if flags are disabled
  - `is_set(name)`: Check if argument is set
  - `gateway.response.set_action_response(data)`: Actions store results via response
  - `gateway.response.add_output(text)`: Backends add output via response
  - `report_error(type, content)`: Report errors via error_store module
  - `is_error()`: Check error state via error_store module
- **Execution Flow**: dispatch() → _initialize() → _initialize_*() → load modules → action_handler() → backend_handler() → _process_errors() → _commit() → flush_debug()
- **State Management**: Gateway holds all system state - request, response, registry, conn, files, handlers
- **Connection Management**: Gateway initializes Connection/MySQLConnection/RootConnection based on request args, returns user tier level
- **File System**: Gateway initializes FileSystem for file operations
- **Commit Process**: _commit() handles file operations, cache refresh (image/file/page), and database transactions with rollback on errors
- **Default Commands**: HTTP backend defaults to show_page with id=1, parser backend defaults to help

### cross-references:
- **[Entry Point](#1-entry-point-henpy)**: Receives raw arguments and backend specification
- **[Error Store](#error-store)**: Uses centralized error reporting system
- **[Debug Registry](#3-debug-registry)**: Provides debug function implementations
- **[Debug Filters](#4-debug-filters)**: Applies debug filter overrides
- **[Response](#5-response)**: Coordinates output and error management
- **[Request](#6-request)**: Gets parsed arguments and command data

---

## 3. Debug Registry

**File**: `hh/gateway/registry/debug.py`

The centralized debug data collection and management system that captures, stores, and filters debug information across the entire application. It:

- **Captures Debug Data**: Collects trace, log, debug, and warning messages from all modules
- **Manages Threading**: Uses locks to ensure thread-safe access to shared debug data
- **Assigns Colors**: Automatically assigns unique colors to modules, files, and functions for visual separation
- **Applies Filtering**: Implements whitelist, graylist, and blacklist filtering to control debug output
- **Tracks State**: Maintains entry indexing and combination counting for output management

The debug registry enables sophisticated debugging with precise control over what information appears, when it appears, and how it's formatted.

### SharedDebugDataStore Class

#### owned by:
- global scope : *Global debug data store instance*

#### owns:
- captured_data : *List of debug entries*
- _lock : *Thread synchronization lock*
- _module_colors, _filename_colors, _function_colors : *Color assignment tracking*
- _next_index : *Entry index counter*

#### data managed:
- captured_data (source of truth) : *All captured debug entries*
- color assignments (source of truth) : *Module, filename, and function color mapping*
- entry indexing (source of truth) : *Sequential entry numbering*

#### calls:
- **capture()** : *Captures debug entry with caller information*
- **clear_processed_data()** : *Clears all captured data and resets state*
- **set_whitelist(), set_graylist(), set_blacklist()** : *Applies filtering rules*
- **set_summary_limit()** : *Sets output limit for debug entries*

#### called by:
- trace_in, trace_out, log, debug, warn : *Global debug functions*
- debug filtering functions : *Filter management*

#### retrieves from:
- inspect (caller frame information) : *Gets calling function and file details*
- time (timestamp) : *Gets current timestamp for entries*

#### provides to:
- debug rendering functions : *Provides filtered debug data*
- safe mode context : *Provides debug data for safe mode*

### Global Module

#### owned by:
- global scope : *Module-level debug system management*

#### owns:
- _shared_debug_store : *Global debug data store*
- _debug_init_functions : *Registered debug initialization functions*
- _initialized_functions : *Set of initialized function IDs*
- _tls : *Thread-local storage for safe mode*

#### data managed:
- debug flags (source of truth) : *Global trace/log/debug enablement flags*
- debug module path (source of truth) : *Current debug backend module path*
- safe mode state (source of truth) : *Thread-local safe mode depth*

#### calls:
- **register_debug_init()** : *Registers debug initialization functions*
- **initialize_debug_modules()** : *Initializes all registered debug modules*
- **set_debug_backend()** : *Sets the debug backend module*
- **resolve_get_debug_for()** : *Resolves debug function for specific system*
- **set_trace_flags()** : *Sets global trace/log/debug flags*
- **get_trace_in(), get_trace_out(), get_log(), get_debug(), get_warn()** : *Gets debug function implementations*
- **safe_mode()** : *Context manager for safe debug mode*
- **trace_in(), trace_out(), log(), debug(), warn()** : *Global debug capture functions*

#### called by:
- gateway (debug initialization and management) : *Gateway uses debug system*
- all modules (debug functions) : *All modules use global debug functions*
- debug backends (debug function resolution) : *Debug backends get function implementations*

#### retrieves from:
- importlib (module loading) : *Loads debug backend modules*
- threading (thread-local storage) : *Manages thread-local safe mode state*
- debug_safe (safe debug implementation) : *Gets safe debug functionality*

#### provides to:
- gateway (debug function implementations) : *Provides debug functions to gateway*
- all modules (global debug functions) : *Provides trace/log/debug/warn functions*
- debug backends (debug function resolution) : *Provides debug function resolution*

### configuration dependencies:
- debug backend modules : *Debug rendering backends loaded via importlib*

### error handling:
- **Thread Safety**: Uses locks to prevent race conditions in debug data collection
- **Safe Mode Context**: Provides context manager to prevent recursive debug rendering
- **Initialization Tracking**: Tracks which debug functions have been initialized to prevent duplicate setup

### agent training notes:
- **Global Debug Functions**: Use trace_in(), trace_out(), log(), debug(), warn() - never direct print statements
- **Thread Safety**: System handles concurrent debug calls automatically via locks
- **Color Assignment**: Automatic color coding by module/file/function for visual separation
- **Safe Mode**: Use safe_mode() context manager when rendering debug data to prevent recursion

### cross-references:
- **[Gateway](#2-gateway)**: Receives debug function implementations and manages debug state
- **[Debug Filters](#4-debug-filters)**: Applies filtering rules to captured debug data

---

## 4. Debug Filters

**File**: `hh/gateway/debug/debug_filters.py`

The filtering system that provides precise control over debug output by implementing three-tier filtering rules. It:

- **Applies Whitelist Rules**: Includes only modules that match specified patterns
- **Applies Graylist Rules**: Includes only files that match specified patterns
- **Applies Blacklist Rules**: Excludes functions that match specified patterns
- **Manages Output Limits**: Controls how many debug entries are shown per combination
- **Tracks Combinations**: Monitors module/file/function combinations to prevent spam

The debug filters enable developers to see exactly the debug information they need without being overwhelmed by irrelevant output.

### FilterMixin Class

#### owned by:
- debug systems : *Used by debug data stores and rendering systems*

#### owns:
- whitelist, graylist, blacklist : *Filter rule lists*
- summary_limit : *Output limit configuration*
- _seen_combinations, _total_combinations : *Combination tracking dictionaries*

#### data managed:
- filter rules (source of truth) : *Whitelist, graylist, and blacklist patterns*
- summary limits (source of truth) : *Output limit for debug entries*
- combination counts (source of truth) : *Tracked combination statistics*

#### calls:
- **is_whitelisted()** : *Checks if module matches whitelist patterns*
- **is_graylisted()** : *Checks if filename matches graylist patterns*
- **is_blacklisted()** : *Checks if function matches blacklist patterns*
- **should_show_message()** : *Determines if message should be shown based on limits*
- **set_whitelist(), set_graylist(), set_blacklist()** : *Sets filter rule lists*
- **set_summary_limit()** : *Sets output limit for debug entries*
- **clear_combinations()** : *Clears combination tracking data*

#### called by:
- SharedDebugDataStore : *Debug data filtering*
- debug rendering systems : *Output filtering*

#### retrieves from:
- filter rule lists : *Gets whitelist, graylist, blacklist patterns*

#### provides to:
- debug systems : *Provides filtering logic and rule management*

### Global Module

#### owned by:
- global scope : *Module-level utility functions*

#### owns:
- parse_list_arg function : *List parsing utility*

#### data managed:
- none : *Pure utility functions*

#### calls:
- **parse_list_arg()** : *Parses comma-separated list arguments with quote handling*

#### called by:
- gateway (debug filter overrides) : *Parses debug filter arguments*
- debug systems : *Parses filter configuration*

#### retrieves from:
- input strings : *Gets comma-separated list arguments*

#### provides to:
- gateway (parsed filter lists) : *Provides parsed filter arguments*
- debug systems : *Provides list parsing functionality*

### configuration dependencies:
- none : *Pure filtering logic, no external configuration*

### error handling:
- **Filter Validation**: Validates filter patterns and handles malformed input
- **Combination Tracking**: Manages combination counts to prevent memory issues with excessive tracking

### agent training notes:
- **Strategic Filtering**: Start with `-debug-limit 1`, use gray filters for specific files, black filters for noisy functions
- **Filter Hierarchy**: Whitelist (modules) → Graylist (files) → Blacklist (functions) - processed in order
- **Pattern Matching**: Use wildcards (*, ?) for flexible pattern matching
- **Combination Management**: System tracks module/file/function combinations to prevent spam

### cross-references:
- **[Debug Registry](#3-debug-registry)**: Applies filtering rules to captured debug data
- **[Gateway](#2-gateway)**: Receives parsed filter arguments from command line

---

## 5. Response

**File**: `hh/gateway/response/response.py`

The output assembly system that collects, manages, and formats all response data from the system. It:

- **Buffers Output**: Collects formatted output from backend handlers via add_output()
- **Stores Action Results**: Holds JSON data from successful action execution via set_action_response()
- **Manages Seed Data**: Stores arbitrary client seed payload for HTML/clients
- **Manages Header Links**: Stores custom CSS and JS links for HTML output
- **Manages Content Sections**: Stores page text, path, upper/lower content for HTML layout
- **Assembles Final Output**: Combines backend output with debug data
- **User Tier Management**: Tracks and manages user tier level (0=unknown, 1=guest, 2=verified, 3=admin, 4=root)

The response system ensures that all output information is properly collected and formatted before being returned to the user. Note: Error handling is managed separately by the centralized error_store system, not by Response.

### Response Class

#### owned by:
- gateway : *Created and managed by gateway instance*

#### owns:
- output_buffer : *List of output strings*
- action_response : *Action execution results (dict)*
- error_output : *Error output (dict, set by error handlers)*
- debug_output : *Debug output (dict, set by flush_debug)*
- seed_data : *Arbitrary client seed payload (dict)*
- header_css_links : *Custom CSS links for HTML*
- header_js_links : *Custom JS links for HTML*
- title, path, page_text : *HTML layout fields*
- upper_content, lower_content : *HTML content sections*
- user_tier_level : *User tier level (0=unknown, 1=guest, 2=verified, 3=admin, 4=root)*

#### data managed:
- output_buffer (source of truth) : *Final formatted output*
- action_response (source of truth) : *Action execution results*
- error_output (source of truth) : *Error output from error handlers*
- debug_output (source of truth) : *Debug output from debug system*
- seed_data (source of truth) : *Client seed payload*
- header_css_links, header_js_links (source of truth) : *Header links*
- title, path, page_text (source of truth) : *HTML layout fields*
- upper_content, lower_content (source of truth) : *HTML content sections*
- user_tier_level (source of truth) : *User tier level*

#### calls:
- **add_output()** : *Adds formatted output to buffer*
- **has_action_response()** : *Checks if action response exists*
- **set_action_response()** : *Stores action execution results*
- **get_action_response()** : *Retrieves action execution results*
- **set_seed_data()** : *Sets/replaces seed data*
- **add_seed_data()** : *Merges seed data*
- **get_seed_data()** : *Gets seed data*
- **add_css_link()** : *Adds CSS link to header*
- **add_js_link()** : *Adds JS link to header*
- **get_css_links()** : *Gets CSS links*
- **get_js_links()** : *Gets JS links*
- **set_content_wrapper_header()** : *Sets content wrapper header*
- **set_path()** : *Sets path HTML content*
- **set_page_text()** : *Sets page text HTML content*
- **set_upper_content()** : *Adds content to upper section*
- **set_lower_content()** : *Adds content to lower section*
- **set_user_tier_level()** : *Sets user tier level*
- **get_user_tier_level()** : *Gets user tier level*
- **get_output()** : *Assembles final output string*

#### called by:
- gateway (output management) : *Gateway manages response state and initializes backend-specific Response subclass*
- actions (set_action_response) : *Actions store their results via gateway.response.set_action_response()*
- backends (add_output) : *Backends add formatted output via gateway.response.add_output()*

#### retrieves from:
- gateway (user tier level) : *Gets user tier level from connection initialization*
- actions (response data) : *Gets action execution results via set_action_response()*
- backends (formatted output) : *Gets formatted output via add_output()*
- environment (USER_TIER) : *Gets user tier from environment variable if set*

#### provides to:
- gateway (get_output) : *Provides final output via get_output()*
- hen.py (final output) : *Provides final formatted output*

### Global Module

#### owned by:
- global scope : *Module-level debug initialization*

#### owns:
- trace_in, trace_out, log, debug, warn : *Debug function references*

#### data managed:
- debug functions (source of truth) : *Debug function implementations*

#### calls:
- **_initialize_debug()** : *Initializes debug functions on module load*
- **get_trace_in(), get_trace_out(), get_log(), get_debug(), get_warn()** : *Gets debug function implementations*

#### called by:
- debug_registry (debug initialization) : *Debug system initializes functions*

#### retrieves from:
- debug_registry (debug function implementations) : *Gets debug function implementations*

#### provides to:
- Response class (debug functions) : *Provides debug functions to Response class*

### configuration dependencies:
- BACKEND_RESPONSE_MODULES : *Backend-specific Response subclasses (ResponseHTTP, ResponseParser, ResponseMCP, ResponseMaintenance)*
- HENHOUSE_TIERS : *User tier definitions from user_account_suffixes*

### error handling:
- **No Error Management**: Response does not manage errors - error handling is done by centralized error_store system
- **Error Output**: error_output field can be set by error handlers, but Response does not collect errors itself

### agent training notes:
- **Response Lifecycle**: output_buffer → action_response → debug_output → final assembly
- **Backend-Specific**: Gateway initializes backend-specific Response subclass (ResponseHTTP, ResponseParser, ResponseMCP, ResponseMaintenance)
- **Integration Points**: Actions call gateway.response.set_action_response(), backends call gateway.response.add_output(), gateway manages state
- **User Tier**: Response tracks user tier level, can be set from connection or USER_TIER environment variable
- **Seed Data**: Use set_seed_data() or add_seed_data() for client payload
- **HTML Layout**: Use set_path(), set_page_text(), set_upper_content(), set_lower_content() for HTML layout

### cross-references:
- **[Gateway](#2-gateway)**: Manages response state and coordinates output management, initializes backend-specific Response subclass
- **[Entry Point](#1-entry-point-henpy)**: Receives final assembled output for stdout printing

---

## 6. Request

**File**: `hh/gateway/request/request.py`

The command-line argument parsing and validation system that converts raw input into structured, typed data. It:

- **Parses Arguments**: Uses grammar-based parsing to handle complex command-line syntax
- **Categorizes Data**: Separates arguments into strings, integers, flags, and no-flags
- **Handles Flag Groups**: Supports grouped flags and no-flag overrides (e.g., `--no-headers`)
- **Manages Commands**: Extracts and validates command names with support for extra commands
- **Provides Access**: Offers clean APIs for argument retrieval and flag checking

The request system transforms raw command-line input into a structured, validated data model that the rest of the system can safely consume.

### Request Class

#### owned by:
- gateway : *Created and managed by gateway instance*

#### owns:
- raw_argv : *Original command line arguments*
- command : *Parsed command name*
- argument collections : *Various argument type storage*

#### data managed:
- raw_argv (local copy) : *Original command line input*
- command (source of truth) : *Parsed command name*
- string_args (source of truth) : *String argument values*
- int_args (source of truth) : *Integer argument values*
- flag_args (source of truth) : *Boolean flag arguments*
- no_flags (source of truth) : *Disabled flag list*
- extra_commands (source of truth) : *Additional command names*
- extra_command_defaults (source of truth) : *Default values for extra commands*

#### calls:
- **parse_request()** : *Grammar parser for command line arguments (called during __init__)*
- **add_synthetic_arg()** : *Adds programmatically generated arguments*
- **is_no()** : *Checks if flag is disabled via no-flags or no-groups*
- **is_set()** : *Checks if argument is set*
- **get_arg()** : *Retrieves argument value by name*
- **has_command()** : *Checks if command exists*
- **get_command()** : *Retrieves command name*

#### called by:
- gateway (argument access) : *Gateway accesses parsed arguments*
- actions (via gateway.get_arg) : *Actions access arguments through gateway*

#### retrieves from:
- grammar_parser.parse_request() (parsed command structure) : *Gets parsed command line data during initialization*

#### provides to:
- gateway (get_command, get_arg, is_no) : *Provides command and argument access*
- actions (via gateway) : *Provides argument access to actions*

### Global Module

#### owned by:
- global scope : *Module-level constants and debug initialization*

#### owns:
- NO_GROUPS : *Flag group definitions*
- trace_in, trace_out, log, debug, warn : *Debug function references*

#### data managed:
- NO_GROUPS (source of truth) : *Flag group membership definitions*
- debug functions (source of truth) : *Debug function implementations*

#### calls:
- **_initialize_debug()** : *Initializes debug functions on module load*
- **get_trace_in(), get_trace_out(), get_log(), get_debug(), get_warn()** : *Gets debug function implementations*

#### called by:
- debug_registry (debug initialization) : *Debug system initializes functions*

#### retrieves from:
- debug_registry (debug function implementations) : *Gets debug function implementations*

#### provides to:
- Request class (debug functions) : *Provides debug functions to Request class*
- Request class (NO_GROUPS) : *Provides flag group definitions*

### configuration dependencies:
- NO_GROUPS : *Hardcoded flag group definitions*

### error handling:
- **Argument Validation**: Validates and categorizes command-line arguments
- **Flag Group Processing**: Handles no-flag overrides and flag group logic

### agent training notes:
- **Data Structure**: Request holds raw_argv, command, string_args, int_args, flag_args, no_flags
- **Access Pattern**: Use gateway.get_arg(name) and gateway.is_no(flag) - never access Request directly
- **Flag Groups**: NO_GROUPS defines which flags work together (e.g., header-related flags)

### cross-references:
- **[Grammar Parser](#7-grammar-parser)**: Provides parsed command structure for Request construction
- **[Gateway](#2-gateway)**: Manages Request instance and provides access methods

---

## 7. Grammar Parser

**File**: `hh/gateway/request/grammar_parser.py`

The grammar parser is the orchestrator that coordinates the entire parsing pipeline, managing the flow of data through four sequential processing stages. Each stage has a distinct responsibility in transforming raw command-line input into structured, validated data:

- **Grammar Parser (Stage 1)**: Acts as the main entry point and orchestrator, calling each subsequent stage in sequence and managing the overall parsing workflow from raw arguments to final Request object
- **Tokenizer (Stage 2)**: Breaks down raw command-line strings into categorized tokens, detecting quote styles, classifying token types (commands, flags, values), and handling special cases like negative numbers
- **Parser (Stage 3)**: Builds a structured grammar representation from tokens, organizing them into parsed commands, flags, no-flags, and values according to the command-line grammar rules
- **Semantics (Stage 4)**: Constructs the final Request object from the parsed grammar, populating argument collections, applying defaults, and creating the structured data model that the rest of the system consumes

### Global Module

#### owned by:
- global scope : *Module-level parsing orchestration*

#### owns:
- parse_request function : *Main parsing entry point*
- trace_in, trace_out, log, debug, warn : *Debug function references*

#### data managed:
- none : *Pure orchestration functions*

#### calls:
- **tokenize()** : *Tokenizes command line arguments*
- **parse()** : *Parses tokens into grammar structure*
- **Request()** : *Creates Request instance (which internally calls parse_request again)*
- **build_request()** : *Populates Request object with parsed structure*

#### called by:
- Request (initialization) : *Request calls parse_request during init*

#### retrieves from:
- tokenizer (tokenized arguments) : *Gets tokenized command line*
- parser (parsed grammar) : *Gets parsed grammar structure*
- semantics (request building) : *Gets request building logic*

#### provides to:
- Request (parsed command structure) : *Provides parsed command data*

### configuration dependencies:
- none : *Pure parsing orchestration logic*

### error handling:
- **Pipeline Coordination**: Manages the 4-stage parsing process and handles stage failures
- **Request Construction**: Ensures proper Request object creation from parsed data

### agent training notes:
- **Orchestration Role**: Coordinates the entire parsing pipeline - doesn't do parsing itself
- **4-Stage Flow**: tokenize() → parse() → Request() → build_request()
- **Implementation Note**: parse_request() creates a Request instance, then calls build_request() to populate it. Request.__init__() also calls parse_request() internally, creating a circular dependency that's handled by checking if parsing succeeded
- **Integration Point**: Called by Request during initialization, and also called directly by parse_request()

### cross-references:
- **[Request](#6-request)**: Orchestrates parsing for Request object creation
- **[Tokenizer](#8-tokenizer)**: Calls tokenize() as first stage
- **[Parser](#9-parser)**: Calls parse() as second stage
- **[Semantics](#10-semantics)**: Calls build_request() as final stage

---

## 8. Tokenizer

**File**: `hh/gateway/request/tokenizer.py`

### Global Module

#### owned by:
- global scope : *Module-level tokenization*

#### owns:
- tokenize function : *Main tokenization entry point*
- trace_in, trace_out, log, debug, warn : *Debug function references*

#### data managed:
- none : *Pure tokenization functions*

#### calls:
- **tokenize()** : *Main tokenization function*
- **_detect_quote_style()** : *Detects quote style in arguments*
- **_classify_token_basic()** : *Basic token classification*
- **_classify_tokens()** : *Advanced token classification with context*
- **_is_negative_number()** : *Checks if token is negative number*

#### called by:
- grammar_parser (tokenization) : *Grammar parser calls tokenize*

#### retrieves from:
- token module (Token, TokenKind, QuoteStyle) : *Gets token definitions*

#### provides to:
- grammar_parser (tokenized arguments) : *Provides tokenized command line*

### configuration dependencies:
- token definitions : *Token, TokenKind, QuoteStyle classes*

### error handling:
- **Quote Detection**: Handles various quote styles and malformed quoted strings
- **Token Classification**: Validates token types and handles edge cases like negative numbers

### agent training notes:
- **Quote Handling**: Detects single/double quotes and preserves content within quotes
- **Token Types**: Classifies tokens as commands, flags, values, or special cases
- **Negative Numbers**: Special handling for negative numeric values

### cross-references:
- **[Grammar Parser](#7-grammar-parser)**: Called by grammar parser as first parsing stage
- **[Parser](#9-parser)**: Provides tokenized arguments for grammar parsing

---

## 9. Parser

**File**: `hh/gateway/request/parser.py`

### Global Module

#### owned by:
- global scope : *Module-level grammar parsing*

#### owns:
- parse function : *Main parsing entry point*
- ParserState enum : *Parser state definitions*
- ParsedValue, ParsedCommand, ParsedFlag classes : *Parsed data structures*
- trace_in, trace_out, log, debug, warn : *Debug function references*

#### data managed:
- none : *Pure parsing functions*

#### calls:
- **parse()** : *Main parsing function*
- **_parse_command()** : *Parses command tokens*
- **_parse_flag()** : *Parses flag tokens*
- **_parse_no_flag()** : *Parses no-flag tokens*
- **_parse_value()** : *Parses value tokens*

#### called by:
- grammar_parser (parsing) : *Grammar parser calls parse*

#### retrieves from:
- tokenizer (tokenized arguments) : *Gets tokenized command line*
- token module (Token, TokenKind) : *Gets token definitions*

#### provides to:
- grammar_parser (parsed grammar) : *Provides parsed grammar structure*

### configuration dependencies:
- token definitions : *Token, TokenKind classes for token type checking*

### error handling:
- **Grammar Validation**: Validates command-line grammar structure and syntax
- **State Management**: Tracks parser state through ParserState enum

### agent training notes:
- **Grammar Building**: Converts tokens into structured grammar representation
- **State Tracking**: Uses ParserState to track parsing progress and context
- **Data Structures**: Creates ParsedCommand, ParsedFlag, ParsedValue objects

### cross-references:
- **[Grammar Parser](#7-grammar-parser)**: Called as second parsing stage
- **[Tokenizer](#8-tokenizer)**: Receives tokenized arguments for grammar parsing
- **[Semantics](#10-semantics)**: Provides parsed grammar for Request building

---

## 10. Semantics

**File**: `hh/gateway/request/semantics.py`

### Global Module

#### owned by:
- global scope : *Module-level request building*

#### owns:
- build_request function : *Main request building entry point*
- trace_in, trace_out, log, debug, warn : *Debug function references*

#### data managed:
- none : *Pure request building functions*

#### calls:
- **build_request()** : *Main request building function*
- **_add_default_value()** : *Adds default values to request*

#### called by:
- grammar_parser (request building) : *Grammar parser calls build_request*

#### retrieves from:
- parser (parsed grammar) : *Gets parsed grammar structure*
- Request class : *Gets Request class definition*

#### provides to:
- grammar_parser (built request) : *Provides built Request object*

### configuration dependencies:
- none : *Pure request building logic*

### error handling:
- **Request Construction**: Validates parsed grammar and constructs proper Request object
- **Default Value Application**: Applies default values where appropriate

### agent training notes:
- **Final Assembly**: Takes parsed grammar and creates structured Request object
- **Data Population**: Populates string_args, int_args, flag_args, no_flags collections
- **Default Handling**: Applies default values for missing arguments

### cross-references:
- **[Grammar Parser](#7-grammar-parser)**: Called as final parsing stage
- **[Parser](#9-parser)**: Receives parsed grammar structure for Request building
- **[Request](#6-request)**: Creates final Request object with proper data types

---

## 11. Connection

**File**: `hh/gateway/connection/conn.py`

The database connection manager that provides unified access to main, cache, and history databases. It:

- **Manages Multiple Databases**: Handles connections to main, cache, and history databases
- **Detects User Tier**: Automatically detects user tier level from DSN username
- **Supports Transactions**: Manages transactions across all databases with commit/rollback
- **Provides CRUD Operations**: Offers read, create, update, delete methods for each database
- **Handles Dry Run**: Supports dry-run mode that rolls back instead of committing

The connection system ensures consistent database access patterns and proper transaction management across the entire application.

### Connection Class

#### owned by:
- gateway : *Created and managed by gateway instance*

#### owns:
- main : *Main database connection (pymysql connection)*
- cache : *Cache database connection (pymysql connection, may be same as main)*
- history : *History database connection (pymysql connection, currently None/not implemented)*
- _transaction_started : *Transaction state flag*
- _initialized : *Initialization state flag*
- _dry_run : *Dry run mode flag*

#### data managed:
- main (source of truth) : *Main database connection*
- cache (source of truth) : *Cache database connection*
- history (source of truth) : *History database connection*
- _transaction_started (source of truth) : *Transaction state*
- _initialized (source of truth) : *Initialization state*

#### calls:
- **initialize()** : *Opens connections to all databases, returns user tier level*
- **close()** : *Closes all database connections*
- **commit()** : *Commits all active transactions (rolls back if dry_run)*
- **rollback()** : *Rolls back all active transactions*
- **has_transaction()** : *Checks if transaction is active*
- **is_initialized()** : *Checks if connections are initialized*
- **_start_transaction()** : *Starts transaction on all databases (called automatically)*
- **_get_main_dsn()** : *Gets main database DSN (override in subclasses)*
- **_detect_user_tier_level()** : *Detects user tier from DSN username*
- **read()** : *Execute SELECT on main database*
- **create()** : *Execute INSERT on main database*
- **update()** : *Execute UPDATE on main database*
- **delete()** : *Execute DELETE on main database*
- **read_cache()** : *Execute SELECT on cache database*
- **create_cache()** : *Execute INSERT on cache database*
- **update_cache()** : *Execute UPDATE on cache database*
- **read_history()** : *Execute SELECT on history database*
- **create_history()** : *Execute INSERT on history database*
- **update_history()** : *Execute UPDATE on history database*

#### called by:
- gateway (_initialize_connection) : *Gateway initializes connection during setup*
- actions (database operations) : *Actions use connection for database access*
- gateway (_commit) : *Gateway commits transactions during commit phase*

#### retrieves from:
- config files (~/.{project_name}.cnf) : *Gets DSN configuration*
- detect_project_context() : *Gets project name for DSN loading*
- HENHOUSE_TIERS : *Gets tier definitions for user tier detection*

#### provides to:
- gateway (user tier level) : *Provides user tier level from initialization*
- actions (database access) : *Provides database connection methods*
- gateway (transaction management) : *Provides commit/rollback for transaction management*

### Connection Subclasses

#### RootConnection
**File**: `hh/gateway/connection/root_connection.py`

Connection subclass that uses root credentials for the main database. Overrides `_get_main_dsn()` to use root user and password from command-line arguments.

#### MySQLConnection
**File**: `hh/gateway/connection/mysql_connection.py`

Connection subclass that extends RootConnection to connect to MySQL system database (database=None) instead of project database.

### configuration dependencies:
- DSN configuration files : *~/.{project_name}.cnf files with database connection info*
- project context detection : *Project name detection for DSN loading*
- HENHOUSE_TIERS : *User tier definitions for tier level detection*

### error handling:
- **Connection Initialization**: Handles DSN loading failures and connection errors gracefully
- **Transaction Management**: Automatically starts transactions on first write, manages commit/rollback
- **Error Classification**: Attaches structured error info to exceptions via _classify_and_attach_error()
- **Dry Run Support**: Rolls back instead of committing when dry_run is enabled

### agent training notes:
- **Access Pattern**: Use `gateway.conn.read()`, `gateway.conn.create()`, etc. - never access Connection directly
- **Database Selection**: Main database for primary data, cache database for cache data, history database for history (not yet implemented)
- **Transaction Management**: Transactions start automatically on first write operation, commit/rollback handled by gateway._commit()
- **User Tier Detection**: Tier level detected from DSN username pattern: {project_name}_{tier}
- **Connection Types**: Standard Connection uses config file DSN, RootConnection uses root credentials, MySQLConnection connects to MySQL system
- **Dry Run**: When dry_run flag is set, commit() automatically calls rollback() instead

### cross-references:
- **[Gateway](#2-gateway)**: Initializes connection and uses for transaction management
- **[FileSystem](#12-filesystem)**: Works with FileSystem for coordinated commit/rollback

---

## 12. FileSystem

**File**: `hh/gateway/system/file_system.py`

The file system operation manager that provides abstraction for filesystem operations with rollback support. It:

- **Schedules Operations**: Queues file move and delete operations for batch execution
- **Supports Rollback**: Provides rollback capability for completed file operations
- **Handles OS Differences**: Detects and handles Windows, macOS, Linux/Ubuntu differences
- **Provides File Access**: Offers file reading, writing, existence checking, and metadata operations
- **Handles Dry Run**: Supports dry-run mode that skips file operation execution

The file system ensures consistent file operation patterns and proper coordination with database transactions.

### FileSystem Class

#### owned by:
- gateway : *Created and managed by gateway instance*

#### owns:
- _operations : *List of scheduled file operations*
- _os_type : *Detected operating system type*
- _remote_file_handler : *Placeholder for future remote file handling*
- _dry_run : *Dry run mode flag*

#### data managed:
- _operations (source of truth) : *Scheduled file operations queue*
- _os_type (source of truth) : *Operating system type (windows, macos, linux, ubuntu, unknown)*

#### calls:
- **schedule_move()** : *Schedules file move operation for commit*
- **schedule_delete()** : *Schedules file delete operation (soft delete to /tmp) for commit*
- **commit()** : *Executes all scheduled file operations*
- **rollback()** : *Rolls back all completed file operations*
- **has_operations()** : *Checks if there are scheduled operations*
- **file_exists()** : *Checks if file exists*
- **directory_exists()** : *Checks if directory exists*
- **get_file_size()** : *Gets file size in bytes*
- **create_directory()** : *Creates directory with optional permissions*
- **read_file()** : *Reads file as bytes*
- **read_file_text()** : *Reads file as text*
- **write_file()** : *Writes bytes to file immediately*
- **write_file_text()** : *Writes text to file immediately*
- **join_path()** : *Joins path parts with OS-appropriate separator*
- **normalize_path()** : *Normalizes path (resolves .. and .)*
- **get_parent_directory()** : *Gets parent directory of path*
- **get_filename()** : *Gets filename from path*
- **_detect_os()** : *Detects operating system type*

#### called by:
- gateway (_initialize) : *Gateway initializes FileSystem during setup*
- actions (file operations) : *Actions use FileSystem for file access*
- gateway (_commit) : *Gateway commits file operations during commit phase*

#### retrieves from:
- platform (OS detection) : *Gets operating system information*
- filesystem (file operations) : *Gets file/directory information*

#### provides to:
- gateway (file operations) : *Provides file operation methods*
- actions (file access) : *Provides file reading/writing capabilities*
- gateway (commit coordination) : *Provides commit/rollback for file operations*

### configuration dependencies:
- operating system : *OS type detection for path handling*
- filesystem permissions : *File/directory permissions for operations*

### error handling:
- **Graceful Failures**: File existence checks and reads return None/False on errors instead of raising exceptions
- **Operation Tracking**: Tracks operation status (scheduled, completed, failed, rolled_back, rollback_failed)
- **Error Reporting**: Reports file operation errors via error_store.report_error()
- **Rollback Support**: Can rollback completed operations in reverse order
- **Dry Run Support**: Skips execution when dry_run is enabled

### agent training notes:
- **Access Pattern**: Use `gateway.files.schedule_move()`, `gateway.files.read_file()`, etc. - never access FileSystem directly
- **Scheduled vs Immediate**: schedule_move()/schedule_delete() queue operations for commit(), write_file()/write_file_text() execute immediately
- **Delete Operations**: schedule_delete() performs soft delete by moving files to /tmp with timestamped names
- **OS Handling**: System automatically detects OS and handles path separators and permissions appropriately
- **Commit Coordination**: File operations are committed before database transactions in gateway._commit()
- **Rollback Order**: Rollback processes operations in reverse order (LIFO)
- **Remote File Support**: Placeholder for future remote file handler integration

### cross-references:
- **[Gateway](#2-gateway)**: Initializes FileSystem and coordinates commit/rollback with database transactions
- **[Connection](#11-connection)**: Works with Connection for coordinated commit/rollback
