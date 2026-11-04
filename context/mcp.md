

# Henhouse MCP/API System Architecture

This document covers the Henhouse implementation of separate MCP and API backends with dedicated whitelists. It explains how MCP (for agents) and API (for web UI) integrate with the Gateway architecture and how to navigate and modify the codebase.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Key Files](#2-key-files)
3. [Integration with Gateway](#3-integration-with-gateway)
4. [Configuration](#4-configuration)
5. [Modifying the System](#5-modifying-the-system)

## Agent Quick Reference

- **MCP Backend**: Agent API backend with minimal responses - registered as backend type alongside `parser`, `http`, `maintenance`, `api`
- **API Backend**: Web UI API backend with fuller responses - separate from MCP with dedicated whitelists
- **Tool Whitelist**: Three-field system (`mcp_tiers`, `api_tiers`, `app_action_tiers`) with 8 cold cache files (4 MCP + 4 API); app actions use hot cache only
- **Role-Based Filtering**: MCP tools support optional `role_whitelist` parameter for additional role-based access control on top of tier permissions
- **Multi-Role Support**: Agents can specify multiple roles (e.g., "worker,auditor") with automatic "general" role inheritance; ANY role match grants access
- **Response Format**: MCP returns minimal JSON-RPC 2.0, API returns fuller responses with state data
- **Config File**: `~/.{project_name}.cnf` (same format/location as database config)
- **HTTP Endpoints**: `/mcp` (agents) and `/api` (web UI) on same host
- **Redeployment**: Whitelist changes auto-discovered on cache miss; separate cache files for MCP and API

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

Henhouse implements **separate MCP and API backends** with dedicated whitelists to distinguish between agent calls and web UI API calls. This separation allows for different response optimization strategies and security models.

### Architecture Flow

**MCP Backend** (Agents - Minimal Responses):
```
Agent → mcp_wrapper.py → /mcp endpoint → MCPWhitelist → Gateway.dispatch(backend="mcp") → ResponseMCP
```

**API Backend** (Web UI - Fuller Responses):
```
TypeScript Fetch → /api endpoint → APIWhitelist → Gateway.dispatch(backend="api") → ResponseAPI
```

**App Actions** (Web UI Buttons):
```
Page Load → get_app_actions() → AppActionWhitelist → available_actions in get_page response
```

### Key Integration Points

- **Backend Types**: MCP and API registered separately in `hh/gateway/registry/backend.py` as distinct backend types
- **Registry Discovery**: Auto-generated wrappers discovered through standard registry system for both backends
- **Response Formatting**: ResponseMCP (minimal) and ResponseAPI (full) extend base `Response` class
- **Error Handling**: Gateway errors formatted appropriately for each backend type
- **Security**: Separate whitelists allow different permissions for agents vs. human users

---

## 2. Key Files

### MCP Client Entry Point
**File**: `hh/deploy/flask/mcp_client.py`

Handles MCP protocol methods for agent calls:
- Implements MCP protocol methods: `initialize`, `tools/list`, `prompts/list`, `resources/list`, `tools/call`, `notifications/initialized`
- Protocol version: `"2024-11-05"` (MCP_PROTOCOL_VERSION constant)
- Server info: Returns `{"name": "Henhouse MCP Server", "version": "1.0.0"}` in initialize response
- Server capabilities: Tools, prompts, resources support `listChanged`; resources support `subscribe`; logging supported
- Tier determined from `USER_TIER` environment variable (defaults to 'guest' if not set or invalid)
- **Role Handling**:
  - `tools/list` accepts optional `role` parameter (comma-separated string, e.g., "worker,auditor")
  - Always includes "general" role by default: `roles = ['general'] + additional_roles`
  - Filters tools by role_whitelist using set intersection (ANY role match grants access)
  - Empty role_whitelist hides tool from all roles
- For `tools/call`: Validates tool name and arguments via `MCPWhitelist.validate_tool(tier, tool_name, args)`
- Builds `argv` array: `[tool_name, --arg1, value1, ...]` (also accepts query string params from sys.argv[1:])
- Sets `request_id` via `gateway.response.set_request_id()` before dispatch
- Calls `gateway.dispatch(argv, "mcp")` - dispatches to MCP backend
- Returns minimal JSON-RPC 2.0 responses to conserve agent context

### API Client Entry Point
**File**: `hh/deploy/flask/api_client.py`

Handles API calls from TypeScript web UI:
- Processes Fetch API requests from web UI components
- Validates against `api-whitelist-{tier}.json` files (simple tool name lists, no schema validation)
- No MCP protocol methods (`tools/list`, etc.) - just tool execution
- No role filtering (API uses tier-based access only)
- Returns fuller responses with state data for web UI consumption
- Builds `argv` array and calls `gateway.dispatch(argv, "api")` - dispatches to API backend

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

For role-based filtering, add role arguments:
```json
{
  "mcpServers": {
    "{project_name}-worker": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_wrapper.py", "worker"]
    },
    "{project_name}-auditor": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_wrapper.py", "worker", "auditor"]
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
- **Role Support**: Accepts optional positional arguments for agent roles (e.g., `python mcp_wrapper.py worker auditor`)
  - Multiple role arguments comma-joined into single "role" parameter
  - Sent to mcp_client.py which adds "general" role by default
  - Tools filtered by role_whitelist on top of tier permissions
- Handles file attachments: extracts `_files` or `file_paths` from params, validates paths, sends as multipart/form-data
- POSTs to `https://{host}/mcp` with Basic Auth (uses JSON for regular requests, multipart for file uploads)
- Outputs JSON-RPC responses to stdout
- Runs in infinite loop handling multiple requests until EOF
- Handles 204 No Content responses (for notifications)

### Tool Whitelist Registry
**File**: `hh/gateway/registry/tool_whitelist.py`

Manages three-field tool registration system with role-based filtering:
- `@register_tool()` decorator with `mcp_tiers`, `api_tiers`, `app_action_tiers`, `role_whitelist` parameters
- Global registry `_global_tool_registry` populated by decorators at import time
- Generates 8 separate cold cache files during regeneration:
  - 4 MCP whitelists (`mcp-whitelist-1.json` through `mcp-whitelist-4.json`)
  - 4 API whitelists (`api-whitelist-1.json` through `api-whitelist-4.json`)
  - App actions use hot cache only (no cold cache files)
- Lazy loading with cache rebuild on miss by scanning all `tools.py` files
- **Role-Based Access Control**:
  - `role_whitelist` parameter filters MCP tools by agent role (on top of tier permissions)
  - Empty role_whitelist = tool hidden from all roles
  - Multi-role support: Agent can specify multiple roles, ANY role match grants access
  - Role inheritance: "general" role always included by default
  - Example roles: "general" (all agents), "worker" (CRUD operations), "auditor" (read-only auditing)

### MCP Response Handler
**File**: `hh/gateway/response/response_mcp.py`

Formats Gateway responses as minimal JSON-RPC 2.0 for agents:
- Extends base `Response` class
- Stores `request_id` via `set_request_id()` method
- Returns minimal responses to conserve agent context windows
- `get_output()` handles two cases:
  - **Error case**: JSON-RPC error response with error code -32603, includes debug output in error data
  - **Success case**: Serializes `action_response["content"][0]["text"]` to JSON string, wraps in JSON-RPC 2.0 result format
- Includes debug output in `content` array if `debug_output` has entries

### API Response Handler
**File**: `hh/gateway/response/response_api.py`

Formats Gateway responses with fuller data for web UI:
- Extends base `Response` class
- Returns comprehensive responses with state data for web UI consumption
- Does not use JSON-RPC 2.0 format (direct JSON responses)
- Includes complete action results and metadata needed by TypeScript components

### MCP Tools Whitelist System
**Core File**: `hh/gateway/registry/mcp_whitelist.py`

Decorator-based lazy-loading whitelist system:
- Tools registered via `@register_mcp_tool` decorators in module-specific `tools.py` files
- Registration files located in: `hh/gateway/registry/tools.py`, `hh/page/tools.py`, `hh/agents/tools.py`, `hh/mcp_request/tools.py`, `hh/mcp_action_request/tools.py`, `hh/image/tools.py`, `hh/work/tools.py`, `hh/source_code_file/tools.py`
- Global registry: `_global_tool_registry` dictionary populated by decorators at import time
- Tier-specific whitelists: Each tier (guest, verified, admin, root) has separate cache file
- Cache files: `hh/gateway/registry/cache/mcp-whitelist-{tier}.json`
- Lazy loading: Cache files loaded on demand; rebuilt on cache miss by scanning all decorators and rebuilding all tier whitelists at once
- Scanning: `_scan_for_mcp_tools()` recursively searches both `hh/` and `ext/` directories for files containing `@register_mcp_tool`
- Used by `mcp_client.py` for validation and `tools/list` via `MCPWhitelist` class
- Used by `mcp.py` for auto-generating wrappers

### Application Actions System

Application actions provide clickable action links in the web UI. They read from dedicated `app-action-whitelist-{tier}.json` files instead of mixing with MCP whitelists.

**Three Types of Tool Registration**:
1. **MCP-only tools** (`mcp_tiers=[1,2,3,4]`): Available as MCP tools for agents/external clients, not shown in web UI
2. **API-only tools** (`api_tiers=[1,2,3,4]`): Available to web UI via `/api` endpoint, not as MCP tools
3. **App-action-only tools** (`app_action_tiers=[3,4]`): Available as clickable links in web UI, separate from MCP/API
4. **Dual-purpose tools** (`mcp_tiers=[3,4], api_tiers=[3,4], app_action_tiers=[3,4]`): Available everywhere

**Common Patterns**:
- **`mcp_tiers=[3,4], api_tiers=[3,4], app_action_tiers=[3,4]`**: CRUD operations available everywhere (admin/root only)
- **`app_action_tiers=[3,4]`**: Complex aggregate operations that appear as single buttons in web UI but are built from multiple API calls
- **`mcp_tiers=[1,2,3,4]`**: Read operations available to all agent tiers

**App Action Access**:
- Accessed via `get_app_actions(user_tier_level)` which maps user tiers (1-4) to app action tiers
- Returns actions with `id`, `tool_name`, `description`, `label`, `group`, `requires_fields`
- Included in `get_page` response `available_actions` field for TypeScript client
- Used by HTTP backend for server-rendered action links

**Decorator Parameters**:
- `tool_name`: Name of the tool
- `description`: Tool description (required for MCP tools)
- `inputSchema`: JSON Schema for tool arguments (required for MCP tools)
- `mcp_tiers`: List of MCP tier levels (1-4) for agent access via `/mcp`
- `api_tiers`: List of API tier levels (1-4) for web UI access via `/api`
- `app_action_tiers`: List of app action tier levels (1-4) for web UI buttons
- `role_whitelist`: List of MCP role names for additional agent role filtering (MCP only)
  - Empty list = tool hidden from all roles
  - Example: `["general"]` = available to all agents
  - Example: `["worker"]` = only available to agents with "worker" role
  - Example: `["worker", "auditor"]` = available to agents with "worker" OR "auditor" role
  - Role check uses set intersection: agent's roles vs. tool's role_whitelist, ANY match grants access
- `app_action_group`: Group name for organizing actions in web UI
- `app_action_label`: Display label for app actions (defaults to tool_name)

---

## 3. Integration with Gateway

### Backend Registration

MCP and API are registered as separate backend types in `hh/gateway/registry/backend.py`:
- Backend types: `"mcp"` and `"api"`
- Decorators: `@register_mcp` and `@register_api`
- Dictionaries: `mcps` and `apis`

### MCP Command Execution Flow

1. **MCP Client** receives tool call via `tools/call` method, gets tier from `USER_TIER` env var (defaults to 'guest')
2. **Role Extraction**: Extracts role parameter from request params (e.g., `role="worker,auditor"`), builds role list starting with "general"
3. **Validation**: Validates tool exists and arguments match schema via `MCPWhitelist.validate_tool(tier, tool_name, args)`
   - Checks tier permission (mcp_tiers)
   - Checks role permission (role_whitelist) - uses set intersection, ANY role match grants access
4. **Argument Conversion**: MCP arguments `{"key": "value"}` → `["tool_name", "--key", "value"]` format
5. **Request ID**: Sets request ID via `gateway.response.set_request_id(request_id)` before dispatch
6. **Gateway Dispatch**: `gateway.dispatch(argv, "mcp")` - routes to MCP backend
7. **Action Handler**: Standard Gateway action executes, sets `action_response`
8. **MCP Backend Handler**: Auto-generated wrapper verifies response exists
9. **ResponseMCP**: Formats minimal JSON-RPC 2.0 response for agents

### API Command Execution Flow

1. **TypeScript Client** makes Fetch API call to `/api` endpoint
2. **Validation**: Validates tool exists for user tier via `APIWhitelist.validate_tool(tier, tool_name, args)`
3. **Argument Conversion**: API arguments `{"key": "value"}` → `["tool_name", "--key", "value"]` format
4. **Gateway Dispatch**: `gateway.dispatch(argv, "api")` - routes to API backend
5. **Action Handler**: Standard Gateway action executes, sets `action_response`
6. **API Backend Handler**: Auto-generated wrapper verifies response exists
7. **ResponseAPI**: Formats fuller JSON response with state data for web UI

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

1. **Create or Edit Registration File**: Add `@register_tool` decorator to appropriate `tools.py` file:
   - `hh/gateway/registry/tools.py` - For registry lister tools
   - `hh/page/tools.py` - For page-related tools
   - `hh/image/tools.py` - For image-related tools
   - `hh/work/tools.py` - For work-related tools
   - `hh/source_code_file/tools.py` - For source code file tools
   - Or create new `tools.py` in appropriate module folder (will be auto-discovered by scanner)

2. **Register Tool**: Use `@register_tool` decorator with appropriate tier and role parameters:

```python
@register_tool(
    tool_name='modify_name',
    description='Modify the name of a page',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer'},
            'name': {'type': 'string'}
        },
        'required': ['page_id', 'name']
    },
    mcp_tiers=[3, 4],          # Admin/root via MCP
    api_tiers=[3, 4],          # Admin/root via API
    app_action_tiers=[3, 4],   # Admin/root as app action
    role_whitelist=['worker'], # Only agents with "worker" role
    crud_type='update'
)
```

**Role Whitelist Examples**:
```python
# Available to all agents (any role)
role_whitelist=['general']

# Available to worker agents only
role_whitelist=['worker']

# Available to worker OR auditor agents (ANY role match)
role_whitelist=['worker', 'auditor']

# Hidden from all agents (empty list)
role_whitelist=[]
```

3. **Prerequisites**: Tool must have action handler with `@register_action` and `@register_command` decorators

4. **Cache Rebuild**:
   - Cache files auto-rebuild on cache miss (when tool is requested but not in cache)
   - Rebuild process: Scans all `tools.py` files, imports modules, rebuilds ALL whitelist files at once (8 total: 4 MCP + 4 API)
   - Or manually clear cache to force rebuild: Delete `hh/gateway/registry/cache/*-whitelist-*.json` files
   - No Flask server restart needed (cache files are checked on each request, in-memory cache persists)
   - Note: App actions use hot cache only (no cold cache files)

### Tool Requirements

For a tool to work through MCP or API:
- Must be registered with `@register_tool` decorator in a `tools.py` file
- Must specify appropriate tier permissions (`mcp_tiers`, `api_tiers`, `app_action_tiers`)
- Must have action handler registered with `@register_action` and `@register_command`
- MCP tools must include `description` and `inputSchema` parameters
- Should follow standard Gateway patterns (error handling, tracing)

### How `tools.py` modules get imported (and when the registry is populated)

- **Whitelist rebuild path**: On cache miss/force rebuild, `tool_whitelist._scan_for_mcp_tools()` finds every file with `@register_tool` under both `hh/` and `ext/`, then imports them. Each decorator call populates `_global_tool_registry`. Tools are then distributed into 8 separate cold cache files (4 MCP, 4 API). App actions use hot cache only.
- **Page-load path**: When a page is loaded, `hh/page/page_registry.py::_load_tools_for_page_class` walks the page class MRO and imports tools modules. This populates `_global_tool_registry` for app action access.
- `get_app_actions(user_tier_level)` uses hot cache (freshly imported tools modules) and filters for appropriate user tiers.

### Schema Validation

The `inputSchema` parameter is used for MCP tool validation:
- MCP tools require `inputSchema` and validate arguments against it
- API tools can omit `inputSchema` (less strict validation)
- Validates tool exists for the requesting tier and backend type
- Validates required fields are present (checks `schema.get('required', [])`)
- Validates field types with automatic type coercion
- Allows extra fields (Gateway handles additional validation)
- Returns tuple `(bool, str)` - `(False, error_message)` on failure, `(True, "")` on success

### Testing Changes

After adding to whitelist and redeploying:
1. **MCP tools**: Should appear in `tools/list` response at `/mcp` endpoint
2. **API tools**: Should be callable via `/api` endpoint
3. **App actions**: Should appear in `available_actions` field of `get_page` responses
4. Argument validation should work per schema (MCP) or be more permissive (API)
5. Tool execution should route through Gateway normally
6. Responses should be formatted appropriately (JSON-RPC 2.0 for MCP, direct JSON for API)

---

## Role-Based Access Control for MCP Tools

### Overview

MCP tools support role-based filtering **in addition to** tier-based permissions. This two-layer system allows fine-grained control over agent tool access:

1. **Tier Layer**: `mcp_tiers` controls which user tiers (1-4) can access the tool
2. **Role Layer**: `role_whitelist` controls which agent roles can see/use the tool

Both checks must pass for a tool to be available to an agent.

### Role Inheritance Pattern

Agents can have multiple roles with automatic inheritance:
- **"general" role**: Always included by default, cannot be removed
- **Additional roles**: Specified when launching agent (e.g., "worker", "auditor")
- **ANY match**: Tool available if ANY agent role matches ANY tool role_whitelist entry

Example:
```bash
# Agent with "worker" and "auditor" roles
python mcp_wrapper.py worker auditor

# Roles list becomes: ["general", "worker", "auditor"]
# Agent sees tools with role_whitelist containing ANY of: "general", "worker", "auditor"
```

### Common Role Patterns

**General Tools** (available to all agents):
```python
role_whitelist=['general']
```
Examples: `get_page`, `get_text`, `get_page_section`

**Worker Tools** (CRUD operations):
```python
role_whitelist=['worker']
```
Examples: `modify_text`, `add_page`, `delete_page`, `modify_work_status`

**Auditor Tools** (read-only inspection):
```python
role_whitelist=['auditor']
```
Examples: Accounting module tools for read-only financial auditing

**Multi-Role Tools** (available to multiple specialized roles):
```python
role_whitelist=['worker', 'auditor']
```
Either worker OR auditor agents can use this tool

**Hidden Tools** (not available via MCP):
```python
role_whitelist=[]
```
Tool exists for API/app-action use but hidden from all MCP agents

### Role Filtering Logic

From `tool_whitelist.py`:
```python
def list_tools(tier: str, roles: List[str]) -> List[Dict]:
    # Roles defaults to ['general'] if not provided
    roles_set = set(roles)

    for tool in tier_tools:
        tool_roles = set(tool.get('role_whitelist', []))

        # If role_whitelist empty, tool hidden
        if not tool_roles:
            continue

        # If ANY agent role in tool's role_whitelist, include tool
        if roles_set & tool_roles:  # Set intersection
            filtered_tools.append(tool)
```

### Multi-Role Agent Example

An agent running as "worker" and "auditor":
```bash
python mcp_wrapper.py worker auditor
```

Gets access to:
- All tools with `role_whitelist=['general']` (inheritance)
- All tools with `role_whitelist=['worker']` (explicit)
- All tools with `role_whitelist=['auditor']` (explicit)
- All tools with `role_whitelist=['worker', 'auditor']` (ANY match)

Does NOT get access to:
- Tools with `role_whitelist=[]` (hidden)
- Tools with `role_whitelist=['other_role']` (no match)

### MCP Wrapper Role Configuration

Configure different agents in `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "henhouse-general": {
      "command": "python",
      "args": ["/path/to/mcp_wrapper.py"]
    },
    "henhouse-worker": {
      "command": "python",
      "args": ["/path/to/mcp_wrapper.py", "worker"]
    },
    "henhouse-auditor": {
      "command": "python",
      "args": ["/path/to/mcp_wrapper.py", "worker", "auditor"]
    }
  }
}
```

Each connection gets different tool lists based on roles.

---

## Known Issues and Fixes

### Work Page Status Bug (Fixed 2026-01-25)

**Issue**: Work page status field not returned in API responses, causing TypeScript overlay to show wrong status and reject updates.

**Root Cause**: `hh_page/data_operations.py` was calling standalone `get_page_data(page)` function instead of `page.get_page_data()` method, bypassing WorkPage's override that adds work-specific fields (status, sort_order, meta, etc.).

**Impact**:
- TypeScript overlay showed 'todo' for all work pages regardless of actual status
- Status change submissions rejected as "not change needed"
- Only affected API/HTTP interface, MCP unaffected

**Fix**: Changed three locations in `data_operations.py` to call `page.get_page_data()` method:
- Line 51: `assemble_page_data()` function
- Line 324: `get_children_data()` function
- Line 386: `show_page()` function

This ensures derived class overrides (like WorkPage) are properly invoked and custom fields are included in API responses.

**Deployment**: Requires `sudo hen deploy` to take effect on server.

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
- HTTP backend uses API backend for programmatic operations via `/api` endpoint
- TypeScript client makes Fetch API calls that route through API backend (not MCP)
- Server-rendered HTTP pages include app action links from app-action whitelists
- App actions retrieved via `get_app_actions()` are included in `get_page` responses
- Separation allows different response formats: fuller responses for web UI, minimal for agents

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

This document focuses on Henhouse-specific MCP and API implementation details. For general MCP protocol information, see MCP specification. For Gateway, Registry, and Response system details, see respective documentation files.
