# Henhouse Debug System Architecture

This document covers the comprehensive debug system that provides sophisticated debugging capabilities, error handling, and system introspection through multiple specialized debug modules and filtering mechanisms.

## Table of Contents

1. [Error System](#1-error-system)
2. [Debug Safe](#2-debug-safe)
3. [Debug Table](#3-debug-table)
4. [Debug Trace](#4-debug-trace)
5. [Debug Filters](#5-debug-filters)
6. [Debug MCP](#6-debug-mcp)

## Agent Quick Reference

- **Debug Activation**: Use CLI flags to lift additional levels: `-trace` enables level 1–2 (trace_in/trace_out), `-log` adds level 3 (log), `-debug` adds level 4 (debug); level 5 (warn) always records
- **Filter Control**: Use `-white`, `-gray`, `-black` flags for precise output control
- **Output Limits**: Use `-debug-limit` to control message volume
- **Error Rendering**: Error system provides structured error display with field configurations
- **Debug Modules**: Debug Safe (base), Debug Table (tabular), Debug Trace (call stack analysis), Debug MCP (JSON output)
- **Filtering System**: Three-tier filtering (whitelist/graylist/blacklist) with combination counting
- **MCP Debug**: All debug flags work in MCP requests; debug output returned as JSON in response content

## Agent Training Notes

### Debug System Integration
- **Debug Levels**: Levels map to CLI toggles; raise levels by combining `-trace`, `-log`, `-debug` (level 5 warn messages are always captured)
- **Filter Management**: Use `set_debug_whitelist()`, `set_debug_graylist()`, `set_debug_blacklist()` for filter control
- **Safe Mode**: Use `safe_mode()` context manager to prevent recursive debug rendering
- **Error Handling**: Use `render_error_details()` for structured error display with field configurations
- **Debug Backends**: Switch between debug backends using `set_debug_backend(system)`

### Debug Module Usage
- **Debug Safe**: Base debug functionality with filtering and color management
- **Debug Table**: Tabular debug output with field configurations and safe mode
- **Debug Trace**: Call stack analysis with tree building and nesting validation
- **Error System**: Structured error rendering with backend-specific error parsers

### Filter System Control
- **Whitelist**: Control which folders/modules are included (`-white "*gateway*"`)
- **Graylist**: Control which files are included (`-gray "cache.py"`)
- **Blacklist**: Control which functions are excluded (`-black "dispatch,get_arg"`)
- **Debug Limits**: Control message volume per combination (`-debug-limit 10`)

### Common Debug Patterns
- **Start Safe**: Always begin with `-debug-limit 1` to avoid information overload
- **Focus Gradually**: Use filters to narrow down to specific areas of interest
- **Combine Filters**: Use multiple filter types together for precise control
- **File Analysis**: Pipe debug output to files for detailed analysis with grep/awk

---

## 1. Error System

**File**: `hh/gateway/error/error.py`

The comprehensive error handling and rendering system that provides structured error display with field configurations and backend-specific error parsers.

The error system serves as the central error management and display system for the Henhouse architecture. It provides structured error rendering with color-coded field configurations, supports multiple error types, and integrates with the render system to produce formatted error output. The system handles error collection, categorization, and display through specialized field configurations and backend-specific error parsers.

### Global Module

#### owned by:
- global scope : *Module-level error handling and rendering*

#### owns:
- error rendering functions : *Error display and formatting functions*
- error field configurations : *Error display field definitions*
- error parsers : *Backend-specific error parsers*

#### data managed:
- error field configurations (created dynamically) : *FieldConfig instances created per-render in render_error_details() at line 41*
- error rendering state (local copy) : *Error rendering process state*

#### calls:
- **render_error_details()** : *Renders detailed error information for specific error types*
- **parser_error()** : *Parser backend error handler*
- **http_error()** : *HTTP backend error handler*
- **mcp_error()** : *MCP backend error handler*
- **maintenance_error()** : *Maintenance backend error handler*
- **render_header_block()** : *Renders error section header*
- **render_block()** : *Renders error information tables*
- **finalize_output()** : *Finalizes error output*
- **get_gateway()** : *Gets gateway instance for error access*

#### called by:
- gateway (error handling) : *Gateway calls error parsers*
- backend systems (error rendering) : *Backend systems use error rendering*

#### retrieves from:
- gateway (error data) : *Gets error data from gateway response*
- render system (table rendering) : *Gets table rendering functionality*
- config system (labels, icons) : *Gets error display configuration*
- debug system (colors) : *Gets color definitions for error display*

#### provides to:
- gateway (error output) : *Provides formatted error output*
- backend systems (error rendering) : *Provides error rendering functionality*

#### configuration dependencies:
- label.ini : *Error label definitions*
- icon.ini : *Error icon definitions*

#### error handling:
- **warn()** : *Logs warnings for error rendering issues*

#### cross-references:
- **[Render System](../render.md#1-render-system)**: *Uses render system for table formatting*
- **[Config System](../render.md#9-config-system)**: *Uses config system for labels and icons*

---

## 2. Debug Safe

**File**: `hh/gateway/debug/debug_safe.py`

The foundational debug rendering system that provides the base functionality for processing and displaying debug information with filtering, color management, and safe rendering capabilities.

Debug Safe serves as the base class for all debug rendering systems, providing the core filtering, color management, and safe rendering capabilities that other debug modules build upon. It manages debug entries with filtering state tracking, handles color assignment for visual separation, and provides safe mode context to prevent recursive debug rendering issues.

### DebugEntry Class

#### owned by:
- debug systems : *Created by debug data stores*

#### owns:
- index, timestamp, level, message : *Debug entry data*
- function_name, filename, folder : *Caller information*
- filter flags : *Filtering state tracking*

#### data managed:
- entry data (source of truth) : *Debug entry information*
- filter state (source of truth) : *Filtering pass/fail flags*
- count data (source of truth) : *Folder/file/function counts*

#### calls:
- none : *Data container class*

#### called by:
- Debug class (entry creation) : *Debug creates entry instances*

#### retrieves from:
- debug data stores : *Gets debug entry data*

#### provides to:
- Debug class (entry data) : *Provides entry data for rendering*

### Debug Class

#### owned by:
- global scope : *Global debug instance*

#### owns:
- _shared_store : *Reference to shared debug store*
- color mappings : *Module, filename, function color assignments*
- filtered_data : *Processed debug entries*

#### data managed:
- filtered_data (source of truth) : *Processed and filtered debug entries*
- color assignments (source of truth) : *Module, filename, function color mapping*

#### calls:
- **get_arg_overrides()** : *Gets filter settings from shared store*
- **get_module_color(), get_filename_color(), get_function_color()** : *Gets color assignments*
- **render_table_hook()** : *Hook for table rendering*
- **process_extra_data()** : *Processes additional data*
- **render_extra_data()** : *Renders additional data*
- **render()** : *Main rendering method*

#### called by:
- debug_registry (debug rendering) : *Debug registry calls render*
- gateway (debug output) : *Gateway gets debug output*

#### retrieves from:
- shared debug store : *Gets captured debug data*
- debug_filters : *Gets filtering functionality*

#### provides to:
- debug_registry (rendered output) : *Provides formatted debug output*

### Global Module

#### owned by:
- global scope : *Module-level utilities and singleton*

#### owns:
- DOCUMENT_ROOT : *Project root path*
- COLORS, COLOR_NAMES : *Color definitions*
- _debug : *Global debug instance*

#### data managed:
- DOCUMENT_ROOT (source of truth) : *Project root path*
- color definitions (source of truth) : *Color codes and names*

#### calls:
- **detect_document_root()** : *Detects project root directory*
- **trim_document_root()** : *Trims project root from paths*
- **get_debug()** : *Gets global debug instance*

#### called by:
- debug_registry (debug instance access) : *Gets debug instance*
- debug systems : *Uses color and path utilities*

#### retrieves from:
- file system (path detection) : *Gets project root path*

#### provides to:
- debug systems : *Provides color definitions and path utilities*
- debug_registry : *Provides debug instance*

#### cross-references:
- **[Debug Filters](#5-debug-filters)**: *Uses debug filters for filtering functionality*

---

## 3. Debug Table

**File**: `hh/gateway/debug/debug_table.py`

The tabular debug rendering system that formats debug information as structured tables with sophisticated visual styling and safe mode context management.

Debug Table extends the base Debug functionality to provide structured table output, making debug information more readable and organized while maintaining the filtering and color capabilities of the base system. It handles safe mode context to prevent recursive debug rendering during table construction and supports deep debug integration.

Safe mode captures every trace/log/debug message emitted while the table is rendered. The tabular output is returned immediately, and when the `--deep-debug` CLI flag is present, the captured safe-mode stream is appended so agents can inspect the raw render-time chatter without triggering recursive table builds.

### DebugTable Class

#### owned by:
- global scope : *Global debug table instance*

#### owns:
- filtered_data : *Processed debug entries*

#### data managed:
- table field configurations (created dynamically) : *FieldConfig instances created per-render in _render_table_from_entries() at lines 90 and 125*
- filtered_data (source of truth) : *Processed debug entries for table rendering*

#### calls:
- **render_table_hook()** : *Main table rendering method*
- **process_extra_data()** : *Processes additional data*
- **render_extra_data()** : *Renders additional data*
- **_render_table_from_entries()** : *Renders table from debug entries*
- **safe_mode()** : *Uses safe mode for nested debug rendering*

#### called by:
- debug_registry (debug rendering) : *Debug registry calls render*
- gateway (debug output) : *Gateway gets debug output*

#### retrieves from:
- debug_safe (base functionality) : *Gets base debug functionality*
- render system (table formatting) : *Gets table rendering*
- gateway (deep-debug flag) : *Gets deep debug configuration*

#### provides to:
- debug_registry (rendered output) : *Provides formatted table output*

### Global Module

#### owned by:
- global scope : *Module-level configuration and singleton*

#### owns:
- _debug : *Global debug table instance*

#### data managed:
- none : *Pure singleton pattern (field configs created dynamically in _render_table_from_entries())*

#### calls:
- **get_debug()** : *Gets global debug table instance*

#### called by:
- debug_registry (debug instance access) : *Gets debug table instance*

#### retrieves from:
- none : *Static configuration*

#### provides to:
- debug systems : *Provides table field configuration*
- debug_registry : *Provides debug table instance*

#### cross-references:
- **[Debug Safe](#2-debug-safe)**: *Extends debug safe for base functionality*
- **[Render System](../render.md#1-render-system)**: *Uses render system for table formatting*

---

## 4. Debug Trace

**File**: `hh/gateway/debug/debug_trace.py`

The call stack tracing system that builds and renders hierarchical call stack trees from debug trace data with nesting validation and call statistics.

Debug Trace extends Debug Table to provide specialized call stack analysis, making it possible to visualize the execution flow and identify performance bottlenecks or call patterns in complex debugging scenarios. It builds hierarchical tree structures from trace_in/trace_out entries and provides detailed call stack analysis.

### DebugTrace Class

#### owned by:
- global scope : *Global debug trace instance*

#### owns:
- trace_structure : *Call stack tree structure*
- filtered_data : *Processed debug entries*

#### data managed:
- trace_structure (source of truth) : *Call stack tree representation*
- filtered_data (source of truth) : *Processed debug entries for trace rendering*

#### calls:
- **process_extra_data()** : *Builds call stack tree from trace entries*
- **render_extra_data()** : *Renders trace table output*
- **render_trace_table()** : *Renders call stack tree as formatted table*

#### called by:
- debug_registry (debug rendering) : *Debug registry calls render*
- gateway (debug output) : *Gateway gets debug output*

#### retrieves from:
- debug_table (base functionality) : *Gets base debug table functionality*
- render system (meta table formatting) : *Gets meta table rendering*

#### provides to:
- debug_registry (rendered output) : *Provides formatted trace output*

### Global Module

#### owned by:
- global scope : *Module-level singleton*

#### owns:
- _debug_trace : *Global debug trace instance*

#### data managed:
- none : *Pure singleton pattern*

#### calls:
- **get_debug()** : *Gets global debug trace instance*

#### called by:
- debug_registry (debug instance access) : *Gets debug trace instance*

#### retrieves from:
- none : *Static singleton*

#### provides to:
- debug_registry : *Provides debug trace instance*

#### cross-references:
- **[Debug Table](#3-debug-table)**: *Extends debug table for base functionality*
- **[Render System](../render.md#1-render-system)**: *Uses render system for meta table formatting*

---

## 5. Debug Filters

**File**: `hh/gateway/debug/debug_filters.py`

The filtering system that provides precise control over debug output by implementing three-tier filtering rules with combination counting and pattern matching.

The debug filters enable developers to see exactly the debug information they need without being overwhelmed by irrelevant output. It implements whitelist, graylist, and blacklist filtering with wildcard pattern matching and combination counting to prevent spam while providing precise control over debug output.

### FilterMixin Class

#### owned by:
- debug systems : *Used by debug data stores and rendering systems*

#### owns:
- whitelist, graylist, blacklist : *Filter pattern lists*
- summary_limit : *Output limit per combination*
- combination tracking : *Seen and total combination counts*

#### data managed:
- filter patterns (source of truth) : *Whitelist, graylist, blacklist patterns*
- combination counts (source of truth) : *Seen and total combination tracking*

#### calls:
- **is_whitelisted()** : *Checks if module matches whitelist patterns*
- **is_graylisted()** : *Checks if filename matches graylist patterns*
- **is_blacklisted()** : *Checks if function matches blacklist patterns*
- **should_show_message()** : *Determines if message should be shown based on limits*
- **set_whitelist(), set_graylist(), set_blacklist()** : *Sets filter patterns*
- **set_summary_limit()** : *Sets output limit per combination*
- **clear_combinations()** : *Clears combination tracking*

#### called by:
- debug systems (filtering) : *Debug systems use filtering functionality*

#### retrieves from:
- filter patterns : *Gets filter pattern data*

#### provides to:
- debug systems (filtering) : *Provides filtering functionality*

#### configuration dependencies:
- none : *Pure filtering logic*

#### error handling:
- **pattern matching errors** : *Handles invalid pattern matching gracefully*

#### cross-references:
- **[Debug Safe](#2-debug-safe)**: *Used by debug safe for filtering*

---

## 6. Debug MCP

**File**: `hh/gateway/debug/debug_mcp.py`

The MCP-specific debug rendering system that outputs debug information as structured JSON for inclusion in MCP JSON-RPC responses.

Debug MCP extends Debug Safe to provide JSON-formatted debug output specifically designed for MCP (Model Context Protocol) responses. It uses shortened keys and normalized timestamps to minimize response size while maintaining full debug information. The debug output is automatically included in MCP responses as a separate content item when debug flags are present in the request.

### DebugMCP Class

#### owned by:
- global scope : *Global debug MCP instance*

#### owns:
- filtered_data : *Processed debug entries*
- color mappings : *Module, filename, function color assignments (inherited)*

#### data managed:
- filtered_data (source of truth) : *Processed and filtered debug entries*
- JSON output structure (source of truth) : *Structured debug entries with shortened keys*

#### calls:
- **render()** : *Main rendering method - returns JSON dict structure*
- **get_arg_overrides()** : *Gets filter settings from shared store*
- **is_whitelisted(), is_graylisted(), is_blacklisted()** : *Filter checking methods*
- **should_show_message()** : *Limit checking per function combination*

#### called by:
- gateway (debug output for MCP) : *Gateway gets debug output for MCP responses*
- response_mcp (response formatting) : *MCP response handler includes debug output*

#### retrieves from:
- shared debug store : *Gets captured debug data*
- debug_filters : *Gets filtering functionality*
- debug_safe : *Gets base debug functionality*

#### provides to:
- response_mcp (JSON debug output) : *Provides structured JSON debug data*

### MCP Debug Output Format

Debug MCP outputs a compact JSON structure with shortened keys:

```json
{
  "entries": [
    {
      "L": "log",           // level (trace_in, trace_out, log, debug, warn)
      "F": "/hh/gateway/",  // folder (module path)
      "I": "gateway.py",    // file (filename)
      "U": "dispatch",       // function (function name)
      "M": "Message text",   // message (debug message)
      "T": 0.123             // timestamp (delta in seconds, millisecond precision)
    }
  ]
}
```

**Key Features**:
- **Shortened Keys**: Single-character keys (L, F, I, U, M, T) to minimize JSON size
- **Normalized Timestamps**: First entry is 0.0, subsequent entries are deltas in seconds with millisecond precision
- **Structured Data**: All debug information preserved in machine-readable format
- **Filtering Support**: All standard debug filters (whitelist, graylist, blacklist, debug-limit) work with MCP requests

### MCP Debug Integration

When making MCP requests, agents can include any debug flags in the request arguments:

**Available Debug Flags for MCP Requests**:
- `debug=1` : Enable debug level messages (level 4)
- `log=1` : Enable log level messages (level 3)
- `trace=1` : Enable trace level messages (levels 1-2)
- `debug-limit=N` : Limit messages per function combination (default: unlimited)
- `gray="filename.py"` : Filter by filename (comma-separated list supported)
- `white="*pattern*"` : Filter by folder/module pattern (comma-separated list supported)
- `black="function_name"` : Exclude functions by name (comma-separated list supported)

**Example MCP Request with Debug Flags**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "get_page",
    "arguments": {
      "id": 1,
      "debug": 1,
      "log": 1,
      "debug-limit": 3,
      "gray": "response.py,gateway.py"
    }
  }
}
```

**Response Structure**:
The debug output is included in the MCP response as a separate content item:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "<main response data as JSON string>"
      },
      {
        "type": "text",
        "text": "{\"entries\":[{\"L\":\"log\",\"F\":\"/hh/gateway/\",\"I\":\"gateway.py\",\"U\":\"dispatch\",\"M\":\"Message\",\"T\":0.0}]}"
      }
    ]
  }
}
```

### Global Module

#### owned by:
- global scope : *Module-level singleton*

#### owns:
- _debug : *Global debug MCP instance*

#### data managed:
- none : *Pure singleton pattern*

#### calls:
- **get_debug()** : *Gets global debug MCP instance*

#### called by:
- debug_registry (debug instance access) : *Gets debug MCP instance*
- gateway (MCP debug configuration) : *Gets debug MCP for MCP backend*

#### retrieves from:
- none : *Static singleton*

#### provides to:
- debug_registry : *Provides debug MCP instance*
- gateway : *Provides debug MCP for MCP backend*

#### cross-references:
- **[Debug Safe](#2-debug-safe)**: *Extends debug safe for base functionality*
- **[Response MCP](../mcp.md#mcp-response-handler)**: *Debug output included in MCP responses*

---

## Debug System Use Guide

This section provides comprehensive guidance for using the Henhouse debug system effectively, with practical examples and best practices for system investigation and troubleshooting.

### Debug Activation Levels

The debug system supports multiple activation levels that can be combined:

**CLI Usage**:
```bash
# Basic log messages only
python3 hh.py command-name -log

# Log + debug messages
python3 hh.py command-name -log -debug

# Log + debug + trace messages (comprehensive)
python3 hh.py command-name -log -debug -trace
```

**MCP Request Usage**:
All debug flags can be included in MCP request arguments:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "get_page",
    "arguments": {
      "id": 1,
      "log": 1,
      "debug": 1,
      "trace": 1
    }
  }
}
```

### Filter System Control

The debug system uses three types of filters for precise output control:

#### Whitelist Filter (`-white`)
Controls which **folders/modules** are included using wildcard patterns:

```bash
# Show only gateway-related modules
python3 hh.py command-list -log -white "*gateway*"

# Show only render system modules
python3 hh.py command-list -log -white "*render*"

# Show multiple module patterns
python3 hh.py command-list -log -white "*gateway*,*render*"
```

#### Graylist Filter (`-gray`)
Controls which **files** are included using pattern matching:

**CLI Usage**:
```bash
# Show only cache.py messages
python3 hh.py command-list -log -gray "cache.py"

# Show multiple files
python3 hh.py command-list -log -gray "cache.py,request.py"

# Show files with pattern matching
python3 hh.py command-list -log -gray "*debug*"
```

**MCP Request Usage**:
```json
{
  "params": {
    "name": "get_page",
    "arguments": {
      "id": 1,
      "log": 1,
      "gray": "response.py,gateway.py"
    }
  }
}
```

#### Blacklist Filter (`-black`)
Excludes **functions** that match specified patterns:

```bash
# Hide noisy functions
python3 hh.py command-list -log -black "dispatch,get_arg,is_no"

# Hide functions with pattern matching
python3 hh.py command-list -log -black "*_init*,*_setup*"
```

### Debug Limit Control

Use `-debug-limit` to control message volume per function combination:

**CLI Usage**:
```bash
# Start safe with minimal output
python3 hh.py command-list -log -debug-limit 1

# Increase detail gradually
python3 hh.py command-list -log -debug-limit 10

# Comprehensive analysis (use carefully)
python3 hh.py command-list -log -debug-limit 50

# Unlimited output (use with caution)
python3 hh.py command-list -log -debug-limit 0
```

**MCP Request Usage**:
```json
{
  "params": {
    "name": "get_page",
    "arguments": {
      "id": 1,
      "log": 1,
      "debug-limit": 3
    }
  }
}
```

### Strategic Debugging Workflow

#### Step 1: Start Safe
Always begin with minimal output to avoid information overload:

```bash
python3 hh.py command-name -log -debug-limit 1
```

#### Step 2: Focus on Specific Areas
Use filters to narrow down to areas of interest:

```bash
# Focus on cache operations
python3 hh.py command-list -log -gray "cache.py" -debug-limit 1

# Focus on request processing
python3 hh.py command-list -log -gray "request.py" -debug-limit 1

# Focus on render system
python3 hh.py command-list -log -white "*render*" -debug-limit 1
```

#### Step 3: Eliminate Noise
Use blacklisting to hide irrelevant functions:

```bash
# Hide common noisy functions
python3 hh.py command-list -log -gray "cache.py" -debug-limit 10 -black "dispatch,get_arg,is_no"

# Focus on specific function
python3 hh.py command-list -log -gray "cache.py" -debug-limit 50 -black "discover_base_registrations,check_command_exists"
```

#### Step 4: Increase Detail
Once you've identified the right area, increase detail:

```bash
# See detailed cache operations
python3 hh.py command-list -log -gray "cache.py" -debug-limit 20 -black "dispatch,get_arg"
```

### Common Debug Patterns

#### Investigating Cache Operations
```bash
# Basic cache investigation
python3 hh.py command-list -log -gray "cache.py" -debug-limit 5

# Detailed cache analysis
python3 hh.py command-list -log -gray "cache.py" -debug-limit 20 -black "dispatch,get_arg,is_no"
```

#### Understanding Request Processing
```bash
# Request flow analysis
python3 hh.py command-list -log -gray "request.py" -debug-limit 10

# Gateway operations
python3 hh.py command-list -log -white "*gateway*" -debug-limit 5
```

#### Studying Rendering Pipeline
```bash
# Render system analysis
python3 hh.py command-list -log -white "*render*" -debug-limit 10

# Table rendering focus
python3 hh.py command-list -log -gray "table.py" -debug-limit 15
```

#### Registry System Investigation
```bash
# Registry operations
python3 hh.py command-list -log -gray "registry.py" -debug-limit 10

# Backend discovery
python3 hh.py command-list -log -gray "backend.py" -debug-limit 5
```

### Advanced Debug Techniques

#### Combining Multiple Filters
```bash
# Show render operations but hide specific functions
python3 hh.py command-list -log -white "*render*" -black "finalize_output,break_section" -debug-limit 20

# Focus on specific file with noise reduction
python3 hh.py command-list -log -gray "cache.py" -black "dispatch,get_arg,is_no,add_output" -debug-limit 15
```

#### Function-Specific Investigation
To study a specific function in detail:

1. Identify the function from broader debug output
2. Use blacklisting to hide everything else
3. Increase debug-limit to see many instances

```bash
# Example: Study discover_backend_specific_registrations
python3 hh.py command-list -log -gray "cache.py" -debug-limit 50 -black "discover_base_registrations,check_command_exists,check_backend_exists"
```

#### Debug Output Analysis
For detailed analysis, pipe debug output to files:

```bash
# Capture debug output to file
python3 hh.py command-list -log -debug-limit 100 > /tmp/debug_output.txt 2>&1

# Search for specific patterns
grep "discover_backend_specific_registrations" /tmp/debug_output.txt
grep "cache.py" /tmp/debug_output.txt | head -10
grep -c "dispatch" /tmp/debug_output.txt
```

### Debug Output Interpretation

#### Debug Levels
- **Level 1-2**: `trace_in()`, `trace_out()` - Function entry/exit
- **Level 3**: `log()` - General operational messages
- **Level 4**: `debug()` - Detailed debugging information
- **Level 5**: `warn()` - Warning messages and errors

#### Key Information in Output
- **folder**: Module folder path (trimmed from document root)
- **file**: Specific filename
- **function**: Function name that generated the message
- **message**: The actual debug message content
- **color coding**: Visual separation by module, file, and function

#### Understanding Call Patterns
- Look for repeated function calls to understand system flow
- Trace function entry/exit pairs to understand call hierarchy
- Watch for error patterns and warning messages
- Monitor performance by observing call frequency

### Best Practices

1. **Start Small**: Always begin with `-debug-limit 1` to avoid information overload
2. **Be Specific**: Use gray filters to focus on specific files or modules
3. **Silence Noise**: Use black filters to hide irrelevant functions
4. **Increase Gradually**: Only increase debug-limit when you know what you're looking for
5. **Combine Filters**: Use multiple filter types together for precise control
6. **Study Patterns**: Look for repeated function calls to understand system flow
7. **Use File Analysis**: Pipe output to files for detailed analysis with grep/awk
8. **Focus on Errors**: Pay attention to warning and error messages
9. **Trace Call Flow**: Use trace_in/trace_out to understand execution paths
10. **Validate Understanding**: Use debug output to verify your understanding of system behavior

### Troubleshooting Common Issues

#### Too Much Output
```bash
# Reduce output with limits and filters
python3 hh.py command-name -log -debug-limit 1 -black "noisy_function"
```

#### Missing Information
```bash
# Increase limits and check filters
python3 hh.py command-name -log -debug-limit 10 -white "*target_module*"
```

#### Performance Impact
```bash
# Use minimal debug for performance testing
python3 hh.py command-name -log -debug-limit 1 -gray "specific_file.py"
```

### MCP Debug Usage

When making MCP requests, agents can include debug flags directly in the request arguments. The debug output will be returned as a separate content item in the JSON-RPC response.

**Example: Focused Debug Output**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "get_page",
    "arguments": {
      "id": 1,
      "debug": 1,
      "log": 1,
      "debug-limit": 3,
      "gray": "response.py,gateway.py"
    }
  }
}
```

**Response includes debug output**:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "<main response data>"
      },
      {
        "type": "text",
        "text": "{\"entries\":[{\"L\":\"log\",\"F\":\"/hh/gateway/\",\"I\":\"gateway.py\",\"U\":\"dispatch\",\"M\":\"Message\",\"T\":0.0}]}"
      }
    ]
  }
}
```

**Best Practices for MCP Debug**:
1. Always start with `debug-limit=1` to avoid overwhelming responses
2. Use `gray` filter to focus on specific files of interest
3. Combine multiple filters for precise control
4. Parse the debug content item separately from main response data
5. Use normalized timestamps (T field) to understand execution timing

This debug system provides powerful capabilities for understanding and troubleshooting the Henhouse system while maintaining control over output volume and focus.
