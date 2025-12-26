

# Henhouse MCP System Architecture

This document covers the Henhouse-specific implementation of the MCP (Model Context Protocol) integration system. It explains how MCP integrates with the Gateway architecture and how to navigate and modify the codebase.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Key Files](#2-key-files)
3. [Integration with Gateway](#3-integration-with-gateway)
4. [Configuration](#4-configuration)
5. [Modifying the System](#5-modifying-the-system)

## Agent Quick Reference

- **MCP Backend**: Registered as backend type in Gateway alongside `parser`, `http`, `maintenance` (not `action` - actions are not backends)
- **Tool Whitelist**: Decorator-based system with tier-specific caches - tools registered via `@register_mcp_tool` decorators in module-specific `mcp_utils.py` files
- **Response Format**: `success_payload()` creates `{"content": [{"type": "text", "text": {...dict...}}]}`, ResponseMCP serializes `content[0]["text"]` dict to JSON string in JSON-RPC 2.0 format
- **Config File**: `~/.{project_name}.cnf` (same format/location as database config)
- **HTTP Endpoint**: `https://{host}/mcp` (host from config file, typically `https://panel.{domain}/mcp`)
- **Redeployment**: Whitelist changes auto-discovered on cache miss; cache files in `hh/gateway/registry/cache/mcp-whitelist-{tier}.json`

## Agent Training Notes

### Gateway Integration
- MCP tools route through standard Gateway dispatch: `gateway.dispatch(argv, "mcp")`
- Arguments converted from MCP format: `{"key": "value"}` → `["tool_name", "--key", "value"]` command-line format
- Action handlers execute normally, set `action_response` via `gateway.response.set_action_response(success_payload(data))`
- MCP backend handlers are auto-generated wrappers that verify `action_response` exists via `gateway.response.has_action_response()`

### Response Flow
- Action sets `action_response` = `success_payload(data)` which creates `{"content": [{"type": "text", "text": {...dict...}}]}`
- `ResponseMCP.get_output()` takes `action_response["content"][0]["text"]` (dict)
- Serializes dict to JSON string: `json.dumps(content[0]["text"])`
- Wraps in JSON-RPC 2.0 format with `request_id` from `set_request_id()`
- Includes debug output in `content` array if available

### Configuration
- Config file: `~/.{project_name}.cnf` in home directory
- Auto-detects project name by finding `hh/` directory in parent path
- Uses `[client]` section with `user`, `password`, `host` fields
- Same format as database configuration for unified credential management

---

## 1. System Overview

The MCP system integrates with Gateway as a backend type. Tool execution flows through the standard Gateway dispatch mechanism, with MCP-specific response formatting. The HTTP backend uses the MCP backend for all API operations - there is no separate API backend. This unified approach treats MCP protocol as a standardized API format, with the HTTP interface making MCP requests via Fetch API. This design enables all CRUD operations to route through the same interface, whether performed by humans (via web UI) or agents (via MCP protocol), allowing for future collaboration scenarios where both can work simultaneously.

### Architecture Flow

```
MCP Client (stdio/HTTP)
    ↓
mcp_wrapper.py [if using stdio - bridges to HTTP]
    ↓
HTTP POST to panel.{domain}/mcp
    ↓
hh/deploy/flask/mcp_client.py
    ↓
Gateway.dispatch(argv, "mcp")
    ↓
Action Handler (standard Gateway action)
    ↓
MCP Backend Handler (auto-generated wrapper from hh/gateway/registry/mcp.py)
    ↓
ResponseMCP.get_output() (hh/gateway/response/response_mcp.py)
    ↓
JSON-RPC 2.0 Response
```

### Key Integration Points

- **Backend Type**: MCP registered in `hh/gateway/registry/backend.py` as one of four backend types
- **Registry Discovery**: Auto-generated wrappers discovered through standard registry system
- **Response Formatting**: Extends base `Response` class, formats specifically for MCP
- **Error Handling**: Gateway errors formatted as JSON-RPC errors through ResponseMCP

---

## 2. Key Files

### MCP Client Entry Point
**File**: `hh/deploy/flask/mcp_client.py`

Handles MCP protocol methods and routes to Gateway:
- Implements MCP protocol methods: `initialize`, `tools/list`, `prompts/list`, `resources/list`, `tools/call`, `notifications/initialized`
- Protocol version: `"2024-11-05"` (MCP_PROTOCOL_VERSION constant)
- Server info: Returns `{"name": "Henhouse MCP Server", "version": "1.0.0"}` in initialize response
- Server capabilities: Tools, prompts, resources support `listChanged`; resources support `subscribe`; logging supported
- Tier determined from `USER_TIER` environment variable (defaults to 'guest' if not set or invalid)
- For `tools/call`: Validates tool name and arguments via `MCPWhitelist.validate_tool(tier, tool_name, args)`
- Builds `argv` array: `[tool_name, --arg1, value1, ...]` (also accepts query string params from sys.argv[1:])
- Sets `request_id` via `gateway.response.set_request_id()` before dispatch
- Calls `gateway.dispatch(argv, "mcp")`
- Parses response as JSON-RPC or wraps plain text in MCP format

### MCP Wrapper Script
**File**: `mcp_wrapper.py` (project root)

**Cursor IDE Configuration:**

To use the MCP wrapper with Cursor IDE, add the following to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "{project_name}-root": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_wrapper.py"]
    }
  }
}
```

Replace `/absolute/path/to/mcp_wrapper.py` with the full path to `mcp_wrapper.py` in your project directory. On Windows, use forward slashes or escaped backslashes (e.g., `"C:\\Users\\username\\project\\mcp_wrapper.py"` or `"C:/Users/username/project/mcp_wrapper.py"`).

**File Upload Support:**

The wrapper supports automatic file uploads. Include files in MCP tool calls using:
- `_files` parameter: Array of file paths (e.g., `["image1.jpg", "audio.mp3", "video.mp4"]`)
- `file_paths` parameter: Alternative parameter name (same format)

Files are automatically attached to HTTP requests as multipart/form-data. Supported file types include images, audio, video, and documents. File paths can be relative (to project root) or absolute (must be within project directory). The wrapper validates file paths to prevent path traversal attacks.

Bridges stdio MCP to HTTP endpoint:
- Reads JSON-RPC from stdin (newline-delimited, one request per line)
- Auto-detects project name by finding `hh/` directory starting from script location
- Loads config from `~/.{project_name}.cnf` (requires user, password, host fields)
- Handles file attachments: extracts `_files` or `file_paths` from params, validates paths, sends as multipart/form-data
- POSTs to `https://{host}/mcp` with Basic Auth (uses JSON for regular requests, multipart for file uploads)
- Outputs JSON-RPC responses to stdout
- Runs in infinite loop handling multiple requests until EOF
- Handles 204 No Content responses (for notifications)

### MCP Registry
**File**: `hh/gateway/registry/mcp.py`

Auto-generates backend handler wrappers:
- Loads tier-specific whitelists from `MCPWhitelist._load_tier_whitelist(tier)` for all tiers in HENHOUSE_TIERS
- Collects all unique tool names across all tier whitelists
- Uses `exec()` to generate wrapper functions with `@register_mcp('tool_name')` decorators
- Wrapper template (`_mcp_wrapper_template`) verifies `gateway.response.has_action_response()` exists
- Wrappers return `True` on success, `False` on failure (reports error via `report_error("backend", ...)`)
- Functions registered in global `mcps` dictionary (via `register_mcp` decorator) for registry discovery
- Tool names converted to valid Python function names (hyphens replaced with underscores)

### MCP Response Handler
**File**: `hh/gateway/response/response_mcp.py`

Formats Gateway responses as JSON-RPC 2.0:
- Extends base `Response` class
- Stores `request_id` via `set_request_id()` method
- `get_output()` handles two cases:
  - **Error case**: If `error_output` exists with "errors" key, formats as JSON-RPC error response with error code -32603, includes debug output in error data if available
  - **Success case**: Takes `action_response["content"][0]["text"]` (dict), serializes to JSON string, wraps in JSON-RPC 2.0 result format
- Includes debug output in `content` array if `debug_output` has entries
- Post-processes to stringify `content[0]["text"]` field if it's a dict (for MCP format compatibility)

### MCP Tools Whitelist System
**Core File**: `hh/gateway/registry/mcp_whitelist.py`

Decorator-based lazy-loading whitelist system:
- Tools registered via `@register_mcp_tool` decorators in module-specific `mcp_utils.py` files
- Registration files located in: `hh/gateway/registry/mcp_utils.py`, `hh/page/mcp_utils.py`, `hh/agents/mcp_utils.py`, `hh/mcp_request/mcp_utils.py`, `hh/mcp_action_request/mcp_utils.py`, `hh/image/mcp_utils.py`, `hh/work/mcp_utils.py`, `hh/source_code_file/mcp_utils.py`
- Global registry: `_global_tool_registry` dictionary populated by decorators at import time
- Tier-specific whitelists: Each tier (guest, verified, admin, root) has separate cache file
- Cache files: `hh/gateway/registry/cache/mcp-whitelist-{tier}.json`
- Lazy loading: Cache files loaded on demand; rebuilt on cache miss by scanning all decorators and rebuilding all tier whitelists at once
- Scanning: `_scan_for_mcp_tools()` recursively searches `hh/` directory for files containing `@register_mcp_tool`
- Used by `mcp_client.py` for validation and `tools/list` via `MCPWhitelist` class
- Used by `mcp.py` for auto-generating wrappers

### Application Actions System

Application actions are a custom add-on layer built on top of the MCP whitelist system, designed for the TypeScript/HTTP interfaces. They use tier levels 5-8 (mapped from user tier levels 1-4: 1→5, 2→6, 3→7, 4→8).

**Three Types of Tool Registration**:
1. **MCP-only tools** (tiers 1-4): Available as MCP tools for agents/external clients, not shown in web UI
2. **App-action-only tools** (tiers 5-8 only): Available as clickable links in web UI, not available as MCP tools (typically aggregate operations that modify multiple things at once)
3. **Dual-purpose tools** (tiers 1-4 AND 5-8, e.g., `[3, 4, 7, 8]`): Available as both MCP tools AND app actions - can be called via MCP protocol or clicked in web UI

**Common Tier Patterns**:
- **`[3, 4, 7, 8]` (dual-purpose, admin/root only)**: Common pattern for CRUD operations that require restricted access. These tools are available to admin (tier 3) and root (tier 4) users via MCP, and also appear as app actions in the web UI for the same user tiers. Examples include `modify_name`, `modify_text`, `add_page`, `delete_page` - operations that mutate data and shouldn't be accessible to guest or verified users.
- **`[7, 8]` (app-action-only, admin/root only)**: Common pattern for aggregate operations that modify multiple things at once through a single UI interaction. These have no direct MCP counterpart because they're designed specifically for the web interface workflow, but they are built from individual MCP tools. The TypeScript client includes optimization logic (traveling salesman-like) to minimize MCP calls by selecting the best combination of setters to mutate required data with minimum API calls. Examples include `combo`, `copy_images_app`, `move_images_app` - complex operations that combine multiple steps into one user action.

**App Action Access**:
- Accessed via `MCPWhitelist.get_app_actions(user_tier_level)` - maps user tier level (1-4) to app action tier level (5-8)
- Returns actions with `id`, `tool_name`, `description`, `label`, `group`, `requires_fields`
- Included in `get_page` response `available_actions` field when backend is "mcp" (for TypeScript client)
- Also used by HTTP backend for server-rendered action links
- Tools with tier levels 5-8 are filtered out of MCP whitelists (not shown in `tools/list`)

**Decorator Parameters**:
- `tool_name`: Name of the MCP tool
- `description`: Tool description
- `inputSchema`: JSON Schema for tool arguments
- `tiers`: List of tier levels. Can include:
  - `[1, 2, 3, 4]` for MCP tools (1=guest, 2=verified, 3=admin, 4=root)
  - `[5, 6, 7, 8]` for app actions only (mapped from user tiers 1-4)
  - `[3, 4, 7, 8]` for dual-purpose tools (admin/root only - both MCP and app action)
  - `[7, 8]` for app-action-only tools (admin/root only - no MCP counterpart)
  - Default: `None` (all MCP tiers `[1, 2, 3, 4]`)
- `requires_approval`: Whether tool requires approval queue (for future transaction system)
- `crud_type`: Operation type ('create', 'read', 'update', 'delete', 'mixed')
- `display_color`: Optional color for approval interface (for future transaction system)
- `app_action_group`: Optional group name for app actions (tiers 5-8) - used for organizing actions in web UI
- `app_action_label`: Optional label for app actions (defaults to tool_name) - displayed in web UI

---

## 3. Integration with Gateway

### Backend Registration

MCP is registered as a backend type in `hh/gateway/registry/backend.py`:
- Backend type: `"mcp"`
- Decorator: `@register_mcp`
- Dictionary: `mcps`

### Command Execution Flow

1. **MCP Client** receives tool call via `tools/call` method, gets tier from `USER_TIER` env var (defaults to 'guest')
2. **Validation**: Validates tool exists and arguments match schema via `MCPWhitelist.validate_tool(tier, tool_name, args)`
3. **Argument Conversion**: MCP arguments `{"key": "value"}` → `["tool_name", "--key", "value"]` format (also accepts query params from sys.argv[1:])
4. **Request ID**: Sets request ID via `gateway.response.set_request_id(request_id)` before dispatch
5. **Gateway Dispatch**: `gateway.dispatch(argv, "mcp")`
6. **Action Handler**: Standard Gateway action executes, sets `action_response` via `gateway.response.set_action_response(success_payload(data))`
7. **MCP Backend Handler**: Auto-generated wrapper verifies `gateway.response.has_action_response()` exists
8. **ResponseMCP**: Formats `action_response` as JSON-RPC 2.0, includes debug output if available

### Response Data Structure

Actions use `success_payload(data)` from `hh/gateway/response/json_standard.py` which creates a structure with `{"content": [{"type": "text", "text": dict(data)}]}`.

`ResponseMCP.get_output()` (see `hh/gateway/response/response_mcp.py` - `ResponseMCP.get_output()` method) then:
1. Makes deep copy of `action_response` to avoid modifying original
2. Takes `action_response["content"][0]["text"]` (dict)
3. Serializes entire response to JSON: `json.dumps(jsonrpc_response, indent=2, default=str)`
4. Post-processes: If `content[0]["text"]` is a dict, stringifies it: `json.dumps(content[0]["text"])`
5. Wraps in JSON-RPC 2.0 format with `request_id` in `id` field
6. Includes debug output in `content` array if `debug_output` has entries

### Error Integration

Gateway errors collected through standard error system, formatted by ResponseMCP:
- Error detection: Checks if `error_output` exists with "errors" key
- Error response: Uses JSON-RPC error code -32603 (Internal error)
- Error message: Generic message like "N error(s) detected" based on error count
- Error data: All errors included in `error.data.errors` array
- Debug output: Included in `error.data.content` array if available
- Request ID: Included in error response `id` field

---

## 4. Configuration

### Config File Location

**Path**: `~/.{project_name}.cnf` (e.g., `~/.henhouse.cnf`)

**Format**: Same INI format as database configuration:
```ini
[client]
user = username
password = password
host = panel.domain.com
```

**Required Fields**: `user`, `password`, and `host` are all required. Missing fields cause configuration error.

### Project Name Detection

Both `mcp_wrapper.py` and database connection use same detection:
1. Start from script/module location
2. Walk up directory tree looking for `hh/` directory
3. Use parent directory name as project name
4. Load config from `~/.{project_name}.cnf`

### HTTP Endpoint

**URL**: `https://{host}/mcp` (host from config file, typically `https://panel.{domain}/mcp`)

**Access**: Host from config file routes to Flask server

**Authentication**: Basic Auth using `user` and `password` from config (Base64 encoded)

**Method**: POST with JSON-RPC 2.0 request body (JSON) or multipart/form-data (for file uploads)

**File Uploads**: `mcp_wrapper.py` extracts `_files` or `file_paths` from params, validates paths, sends as multipart/form-data with files attached

---

## 5. Modifying the System

### Adding a Tool to Whitelist

1. **Create or Edit Registration File**: Add `@register_mcp_tool` decorator to appropriate `mcp_utils.py` file:
   - `hh/gateway/registry/mcp_utils.py` - For registry lister tools
   - `hh/page/mcp_utils.py` - For page-related tools
   - `hh/agents/mcp_utils.py` - For agent-related tools
   - `hh/mcp_request/mcp_utils.py` - For MCP request tools
   - `hh/mcp_action_request/mcp_utils.py` - For MCP action request tools
   - `hh/image/mcp_utils.py` - For image-related tools
   - `hh/work/mcp_utils.py` - For work-related tools
   - `hh/source_code_file/mcp_utils.py` - For source code file tools
   - Or create new `mcp_utils.py` in appropriate module folder (will be auto-discovered by scanner)

2. **Register Tool**: Use `@register_mcp_tool` decorator on a placeholder function. See `hh/gateway/registry/mcp_whitelist.py` - `register_mcp_tool()` function for the decorator definition, and see existing `mcp_utils.py` files (e.g., `hh/page/mcp_utils.py`, `hh/gateway/registry/mcp_utils.py`) for registration examples.

3. **Prerequisites**: Tool must have action handler with `@register_action` and `@register_command` decorators

4. **Cache Rebuild**: 
   - Cache files auto-rebuild on cache miss (when tool is requested but not in cache for any tier)
   - Rebuild process: Scans all `mcp_utils.py` files, imports modules, rebuilds ALL tier whitelists at once
   - Or manually clear cache to force rebuild: Delete `hh/gateway/registry/cache/mcp-whitelist-*.json` files
   - No Flask server restart needed (cache files are checked on each request, in-memory cache persists)
   - MCP registry auto-generates wrapper on next import (no code changes needed, uses exec() to create functions)

### Tool Requirements

For a tool to work through MCP:
- Must be registered with `@register_mcp_tool` decorator in an `mcp_utils.py` file
- Must be available for the requesting tier (tier levels: 1=guest, 2=verified, 3=admin, 4=root)
- Must have action handler registered with `@register_action` and `@register_command`
- Must use `success_payload()` for response data (creates proper structure)
- Should follow standard Gateway patterns (error handling, tracing)

### How `mcp_utils.py` modules get imported (and when the registry is populated)

- There are two import paths:
  - **Whitelist rebuild path**: On cache miss/force rebuild, `mcp_whitelist._scan_for_mcp_tools()` finds every file with `@register_mcp_tool` under `hh/`, then `_import_modules()` imports them. Each decorator call populates `_global_tool_registry`. MCP-tier tools (1-4) are written into tier caches; app-action-only tools (5-8) stay only in the in-memory registry.
  - **Page-load path**: When a page is loaded (HTTP or MCP backend), `hh/page/page_registry.py::_load_mcp_utils_for_page_class` walks the page class MRO and `importlib.import_module("{base}.mcp_utils")` for each class. That import also runs decorators and fills `_global_tool_registry`. This is how app actions get into memory for `get_page`/`show_page` responses, even though they are not stored in the tier caches.
- `get_app_actions(user_tier_level)` reads `_global_tool_registry` (not the tier caches) and filters for app-action tier levels (5-8, mapped from user tier +4). Page classes attach these to `available_actions` for MCP responses.

### Schema Validation

The `inputSchema` in whitelist is used by `MCPWhitelist.validate_tool()` for validation:
- Validates tool exists for the requesting tier (calls `get_tool()` which may trigger rebuild)
- Validates required fields are present (checks `schema.get('required', [])`)
- Validates field types (string, integer, boolean, array, object) with automatic type coercion:
  - String numbers coerced to integers for integer fields
  - Negative numbers handled correctly
- Allows extra fields (fields not in schema are ignored, Gateway handles additional validation)
- Returns tuple `(bool, str)` - `(False, error_message)` on failure, `(True, "")` on success

### Testing Changes

After adding to whitelist and redeploying:
1. Tool should appear in `tools/list` response
2. Argument validation should work per schema
3. Tool execution should route through Gateway normally
4. Response should be properly formatted as JSON-RPC 2.0

---

## Integration with Other Systems

### With Gateway (see gateway.md)
- MCP is a backend type, uses standard `gateway.dispatch()` flow
- Arguments parsed by Gateway's grammar parser
- Errors collected through Gateway error system

### With Registry (see registry.md)
- MCP handlers discovered through standard registry discovery
- Auto-generated wrappers registered in `mcps` dictionary
- Uses same command/backend matching as other backends

### With Response System (see gateway.md)
- `ResponseMCP` extends base `Response` class
- Uses `success_payload()` structure from `json_standard.py` (`hh/gateway/response/json_standard.py`)
- `get_data()` function in `json_standard.py` extracts from `content[0].text` (MCP format) with fallback to old `dat` field
- ResponseMCP includes debug output in `content` array if available

### With HTTP Backend
- HTTP backend uses MCP backend for all API operations - no separate API backend exists
- TypeScript client makes Fetch API calls that route through MCP protocol
- Server-rendered HTTP pages can include app action links that trigger MCP tool calls
- App actions retrieved via `MCPWhitelist.get_app_actions()` are included in `get_page` responses for TypeScript client consumption
- Unified interface: All CRUD work goes through the same MCP interface whether humans (via TypeScript client) or agents (via MCP protocol) are performing the work, enabling future collaboration where both can work simultaneously

### With Database Connection
- Shares same config file format and location
- Uses same project name detection logic
- Unified credential management approach

---

## Example: Adding This File to the System

This documentation file itself was added to the Henhouse system using three sequential MCP tool calls, demonstrating the system in action:

1. **Create the page**: Used `add_page` with `target_page=535` (the "context" page) and `class="source_code_file"` with no name:
   - Response returned page `id=545`

2. **Set the file path**: Used `modify_path` with `page_id=545` (from step 1) and `path="context/mcp.md"`:
   - Response confirmed the path was set and auto-generated the name "mcp.md" from the path

3. **Set the language**: Used `modify_language` with `page_id=545` (from step 1) and `language="markdown"`:
   - Response confirmed the language was set and loaded the file content

4. **Verify the content**: Used `show_page` with `id=545` to verify the file content was loaded:
   - Initial check showed older deployed version (file was edited locally but not yet deployed)
   - After deployment, subsequent check showed updated content including this example section

This process illustrates how MCP tools can be chained together, with later operations depending on the response data (page ID) from earlier operations. **Important note**: When editing files locally, the changes only appear in the system after deployment. The database operations (add_page, modify_path, modify_language) work with the deployed file content, not local edits. Local file changes must be deployed to the server before they become available through the page system.

---

This document focuses on Henhouse-specific MCP implementation details. For general MCP protocol information, see MCP specification. For Gateway, Registry, and Response system details, see respective documentation files.
