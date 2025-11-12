# Henhouse Gateway System Architecture

This document covers the core gateway and parsing infrastructure of the Henhouse system, including the entry point, central orchestration, debugging, response management, and command-line parsing pipeline.

## Table of Contents

1. [Entry Point (hh.py)](#1-entry-point-hhpy)
2. [Gateway](#2-gateway)
3. [Debug Registry](#3-debug-registry)
4. [Debug Filters](#4-debug-filters)
5. [Response](#5-response)
6. [Request](#6-request)
7. [Grammar Parser](#7-grammar-parser)
8. [Tokenizer](#8-tokenizer)
9. [Parser](#9-parser)
10. [Semantics](#10-semantics)

## Agent Quick Reference

- **Entry Point**: `hh.py` → `get_gateway()` → `dispatch()`
- **Core Dispatch Flow**: arguments → grammar → registry → cache → modules → handlers → response
- **Key Objects**: Request, Response, CommandRegistry, Gateway
- **Parsing Pipeline**: Grammar Parser → Tokenizer → Parser → Semantics
- **Error System**: Coordinated error types through gateway get collected and handled by Response
- **Debug System**: always-on warning system can be toggled into deeper modes like -debug -log -trace 
- **Debug System Control**: White/gray/black lists + limit features allow fine tune control over exactly what modules and messages show up

## Agent Training Notes

### Gateway Integration Points
- **Gateway Access**: Use `get_gateway()` to access system state and arguments
- **Argument Retrieval**: `gateway.get_arg(name)` for string/integer arguments
- **Flag Checking**: `gateway.is_no(flag)` for no-flag states
- **Response Setting**: `gateway.set_action_response(json_data)` for action results
- **Error Reporting**: Use specific error methods (request_error, action_error, etc.)

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

## 1. Entry Point (hh.py)

**File**: `hh.py`

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
- response : *Output buffer and error management*
- registry : *Command and backend handler discovery*
- action_handler : *Business logic execution function*
- backend_handler : *Presentation logic execution function*
- error_handler : *Error processing function*
- debug_system : *Debug system identifier*
- debug_module : *Debug module instance*
- get_debug_func : *Debug function factory*

#### data managed:
- command (source of truth) : *Current command being executed*
- backend (source of truth) : *Current backend being used*
- debug_system (source of truth) : *Debug system configuration*
- debug_module (source of truth) : *Debug module instance*
- get_debug_func (source of truth) : *Debug function factory*
- error state (coordinates across all layers) : *Centralized error coordination*

#### calls:
- **dispatch()** : *Main execution flow through action and backend*
- **_initialize()** : *Sets up all subsystems in proper order*
- **_initialize_debug_module()** : *Configures debugging based on request flags*
- **_initialize_command()** : *Extracts command from parsed request*
- **_initialize_action()** : *Loads and validates action handler*
- **_initialize_backend()** : *Loads and validates backend handler*
- **_configure_debug_module()** : *Applies debug filter overrides*
- **_apply_debug_filter_overrides()** : *Applies debug filter overrides from request*
- **Request(raw_argv)** : *Creates request parser instance*
- **CommandRegistry(command, backend)** : *Discovers and loads handlers*
- **action_handler()** : *Executes business logic*
- **backend_handler()** : *Executes presentation logic*
- **error_handler()** : *Executes error handling logic*
- **flush_debug()** : *Outputs debug information*
- **set_action_response()** : *Stores action results*
- **get_action_response()** : *Retrieves action results*
- **has_action_response()** : *Checks if action completed*
- **add_backend_response()** : *Adds formatted output*
- **get_arg()** : *Provides argument access to components*
- **is_no()** : *Checks no-flag states*
- **capture()** : *Captures debug messages*
- **get_debug_safe_mode()** : *Checks if in safe debug mode*
- **switch_to_safe_debug()** : *Switches to safe debug mode*
- **restore_debug_system()** : *Restores original debug system*
- **error()** : *Checks error state*
- **request_error()** : *Reports request-level errors*
- **registry_error()** : *Reports registry-level errors*
- **action_error()** : *Reports action-level errors*
- **backend_error()** : *Reports backend-level errors*
- **debug_error()** : *Reports debug-level errors*
- **connection_error()** : *Reports connection-level errors*
- **json_error()** : *Reports JSON-level errors*
- **syntax_error()** : *Reports syntax-level errors*

#### called by:
- hh.py (dispatch) : *Main entry point calls dispatch method*
- get_gateway() (singleton access) : *Singleton factory creates instance*
- actions (get_gateway()) : *Actions access gateway for argument access*
- backends (get_gateway()) : *Backends access gateway for response data*
- debug system : *Debug system calls gateway methods*

#### retrieves from:
- request (parsed arguments) : *Gets command and argument data*
- registry (handlers, error handlers) : *Gets action and backend handlers*
- response (output and errors) : *Gets response data and error state*

#### provides to:
- actions (gateway instance, argument access) : *Provides gateway and argument access*
- backends (gateway instance, action response) : *Provides gateway and action results*
- response (error reporting methods) : *Provides error reporting interface*
- hh.py (final output) : *Provides final formatted output*

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
- hh.py (get_gateway) : *Main entry point gets gateway instance*
- debug system (debug functions) : *Debug system uses global debug functions*
- actions (debug functions) : *Actions use global debug functions*

#### retrieves from:
- debug_registry (debug function implementations) : *Gets debug function implementations*

#### provides to:
- hh.py (get_gateway function) : *Provides gateway access function*
- debug system (debug functions) : *Provides global debug functions*
- actions (debug functions) : *Provides global debug functions*

### configuration dependencies:
- debug system configuration : *Debug flags and module paths from debug system*

### error handling:
- **Centralized Error Coordination**: Manages 8 distinct error types across all system layers
- **Error State Tracking**: Maintains error state for request, registry, action, backend, debug, connection, JSON, and syntax errors
- **Error Propagation**: Provides consistent error reporting interface to all components

### agent training notes:
- **Singleton Pattern**: Always use `get_gateway()`, never instantiate directly
- **Critical Methods**:
  - `get_arg(name)`: Access command arguments
  - `is_no(flag)`: Check if flags are disabled
  - `set_action_response(data)`: Store action results as JSON
  - `error_*()`: Report errors by category
- **Execution Flow**: dispatch() → _initialize_*() → action_handler() → backend_handler()
- **State Management**: Gateway holds all system state - request, response, handlers

### cross-references:
- **[Entry Point](#1-entry-point-hhpy)**: Receives raw arguments and backend specification
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

The output assembly and error coordination system that collects, manages, and formats all response data from the system. It:

- **Buffers Output**: Collects formatted output from backend handlers
- **Stores Action Results**: Holds JSON data from successful action execution
- **Manages Error Collections**: Maintains separate error lists for each system layer (request, registry, action, backend, debug, connection, JSON, syntax)
- **Assembles Final Output**: Combines backend output with error information and debug data
- **Provides Error Checking**: Offers unified error state checking across all layers

The response system ensures that all output and error information is properly collected and formatted before being returned to the user.

### Response Class

#### owned by:
- gateway : *Created and managed by gateway instance*

#### owns:
- output_buffer : *List of output strings*
- action_response : *Action execution results*
- error lists : *Various error type collections*

#### data managed:
- output_buffer (source of truth) : *Final formatted output*
- action_response (source of truth) : *Action execution results*
- request_errors (source of truth) : *Request parsing errors*
- registry_errors (source of truth) : *Registry resolution errors*
- action_errors (source of truth) : *Action execution errors*
- backend_errors (source of truth) : *Backend execution errors*
- debug_errors (source of truth) : *Debug system errors*
- connection_errors (source of truth) : *Database connection errors*
- json_errors (source of truth) : *JSON processing errors*
- syntax_errors (source of truth) : *Syntax parsing errors*

#### calls:
- **add_output()** : *Adds formatted output to buffer*
- **has_action_response()** : *Checks if action response exists*
- **set_action_response()** : *Stores action execution results*
- **get_action_response()** : *Retrieves action execution results*
- **add_request_error()** : *Adds request parsing errors*
- **add_registry_error()** : *Adds registry resolution errors*
- **add_action_error()** : *Adds action execution errors*
- **add_backend_error()** : *Adds backend execution errors*
- **add_debug_error()** : *Adds debug system errors*
- **add_connection_error()** : *Adds database connection errors*
- **add_json_error()** : *Adds JSON processing errors*
- **add_syntax_error()** : *Adds syntax parsing errors*
- **error()** : *Checks if any errors exist*
- **get_errors()** : *Retrieves all error data*
- **get_output()** : *Assembles final output string*

#### called by:
- gateway (output and error management) : *Gateway manages response state*
- actions (set_action_response) : *Actions store their results*
- backends (add_backend_response) : *Backends add formatted output*

#### retrieves from:
- gateway (error reporting) : *Gets error data from gateway*
- actions (response data) : *Gets action execution results*
- backends (formatted output) : *Gets formatted output from backends*

#### provides to:
- gateway (get_output, error checking) : *Provides final output and error state*
- hh.py (final output) : *Provides final formatted output*

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
- none : *Response system uses no external configuration*

### error handling:
- **Error Collection**: Maintains 8 separate error lists for different system layers
- **Error Assembly**: Combines error information with backend output for final response
- **Error State Checking**: Provides unified error state checking across all layers

### agent training notes:
- **Response Lifecycle**: output_buffer → action_response → error collections → final assembly
- **Error Categories**: 8 distinct error types - request, registry, action, backend, debug, connection, JSON, syntax
- **Integration Points**: Actions call set_action_response(), backends call add_output(), gateway manages state

### cross-references:
- **[Gateway](#2-gateway)**: Manages response state and coordinates output/error management
- **[Entry Point](#1-entry-point-hhpy)**: Receives final assembled output for stdout printing

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
- **parse_request()** : *Grammar parser for command line arguments*
- **add_synthetic_arg()** : *Adds programmatically generated arguments*
- **is_no()** : *Checks if flag is disabled via no-flags or no-groups*
- **get_arg()** : *Retrieves argument value by name*
- **has_command()** : *Checks if command exists*
- **get_command()** : *Retrieves command name*

#### called by:
- gateway (argument access) : *Gateway accesses parsed arguments*
- actions (via gateway.get_arg) : *Actions access arguments through gateway*

#### retrieves from:
- grammar_parser (parsed command structure) : *Gets parsed command line data*

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
- **build_request()** : *Builds Request object from parsed structure*
- **Request()** : *Creates Request instance*

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
- **4-Stage Flow**: tokenize() → parse() → build_request() → Request()
- **Integration Point**: Called by Request during initialization

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
