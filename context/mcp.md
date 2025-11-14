# Henhouse MCP System Architecture

This document covers the Henhouse-specific implementation of the MCP (Model Context Protocol) integration system. It explains how MCP integrates with the Gateway architecture and how to navigate and modify the codebase.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Key Files](#2-key-files)
3. [Integration with Gateway](#3-integration-with-gateway)
4. [Configuration](#4-configuration)
5. [Modifying the System](#5-modifying-the-system)

## Agent Quick Reference

- **MCP Backend**: Registered as backend type in Gateway alongside `parser`, `http`, `action`
- **Tool Whitelist**: Decorator-based system with tier-specific caches - tools registered via `@register_mcp_tool` decorators in module-specific `mcp_utils.py` files
- **Response Format**: `success_payload()` creates `{"content": [{"type": "text", "text": {...dict...}}]}`, ResponseMCP serializes inner dict to JSON string
- **Config File**: `~/.{project_name}.cnf` (same format/location as database config)
- **HTTP Endpoint**: `https://panel.{domain}/mcp` (subdomain access)
- **Redeployment**: Whitelist changes auto-discovered on cache miss; cache files in `hh/gateway/registry/cache/mcp-whitelist-{tier}.json`

## Agent Training Notes

### Gateway Integration
- MCP tools route through standard Gateway dispatch: `gateway.dispatch(argv, "mcp")`
- Arguments converted from MCP format to `--key value` command-line format
- Action handlers execute normally, set `action_response` via `success_payload()`
- MCP backend handlers are auto-generated wrappers that verify `action_response` exists

### Response Flow
- Action sets `action_response` = `{"content": [{"type": "text", "text": {...dict...}}]}`
- `ResponseMCP.get_output()` serializes `content[0]["text"]` dict to JSON string
- Wraps in JSON-RPC 2.0 format with `request_id` from `set_request_id()`

### Configuration
- Config file: `~/.{project_name}.cnf` in home directory
- Auto-detects project name by finding `hh/` directory in parent path
- Uses `[client]` section with `user`, `password`, `host` fields
- Same format as database configuration for unified credential management

---

## 1. System Overview

The MCP system integrates with Gateway as a backend type. Tool execution flows through the standard Gateway dispatch mechanism, with MCP-specific response formatting.

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
- Validates tool name against tier-specific whitelist via `MCPWhitelist.get_tool(tier, tool_name)`
- Validates arguments against tool's `inputSchema` via `MCPWhitelist.validate_tool(tier, tool_name, args)`
- Builds `argv` array: `[tool_name, --arg1, value1, ...]`
- Calls `gateway.dispatch(argv, "mcp")`
- Sets `request_id` via `gateway.response.set_request_id()`
- Tier determined from `USER_TIER` environment variable (set by Flask app)

### MCP Wrapper Script
**File**: `mcp_wrapper.py` (project root)

Bridges stdio MCP to HTTP endpoint:
- Reads JSON-RPC from stdin (newline-delimited)
- Auto-detects project name by finding `hh/` directory
- Loads config from `~/.{project_name}.cnf`
- POSTs to `https://{host}/mcp` with Basic Auth
- Outputs JSON-RPC responses to stdout
- Runs in loop handling multiple requests

### MCP Registry
**File**: `hh/gateway/registry/mcp.py`

Auto-generates backend handler wrappers:
- Loads tier-specific whitelists from `MCPWhitelist._load_tier_whitelist(tier)` for all tiers
- Collects all unique tool names across all tier whitelists
- Uses `exec()` to generate wrapper functions with `@register_mcp('tool_name')` decorators
- Wrappers verify `action_response` exists and return success
- Functions registered in global `mcps` dictionary for registry discovery

### MCP Response Handler
**File**: `hh/gateway/response/response_mcp.py`

Formats Gateway responses as JSON-RPC 2.0:
- Extends base `Response` class
- `get_output()` serializes `action_response["content"][0]["text"]` dict to JSON string
- Wraps in JSON-RPC 2.0 format with `request_id`
- Formats Gateway errors as JSON-RPC error responses

### MCP Tools Whitelist System
**Core File**: `hh/gateway/registry/mcp_whitelist.py`

Decorator-based lazy-loading whitelist system:
- Tools registered via `@register_mcp_tool` decorators in module-specific `mcp_utils.py` files
- Registration files located in: `hh/gateway/registry/mcp_utils.py`, `hh/page/mcp_utils.py`, `hh/agents/mcp_utils.py`, `hh/mcp_request/mcp_utils.py`, `hh/mcp_action_request/mcp_utils.py`
- Tier-specific whitelists: Each tier (guest, verified, admin, root) has separate cache file
- Cache files: `hh/gateway/registry/cache/mcp-whitelist-{tier}.json`
- Lazy loading: Cache files loaded on demand; rebuilt on cache miss by scanning decorators
- Used by `mcp_client.py` for validation and `tools/list` via `MCPWhitelist` class
- Used by `mcp.py` for auto-generating wrappers

**Decorator Parameters**:
- `tool_name`: Name of the MCP tool
- `description`: Tool description
- `inputSchema`: JSON Schema for tool arguments
- `tiers`: List of tier levels `[1, 2, 3, 4]` (1=guest, 2=verified, 3=admin, 4=root). Default: all tiers
- `requires_approval`: Whether tool requires approval queue (for future transaction system)
- `crud_type`: Operation type ('create', 'read', 'update', 'delete')
- `display_color`: Optional color for approval interface (for future transaction system)

---

## 3. Integration with Gateway

### Backend Registration

MCP is registered as a backend type in `hh/gateway/registry/backend.py`:
- Backend type: `"mcp"`
- Decorator: `@register_mcp`
- Dictionary: `mcps`

### Command Execution Flow

1. **MCP Client** receives tool call, validates against tier-specific whitelist
2. **Argument Conversion**: MCP arguments → `--key value` format
3. **Gateway Dispatch**: `gateway.dispatch([tool_name, --arg1, val1, ...], "mcp")`
4. **Action Handler**: Standard Gateway action executes, sets `action_response` via `success_payload()`
5. **MCP Backend Handler**: Auto-generated wrapper verifies `action_response` exists
6. **ResponseMCP**: Formats `action_response` as JSON-RPC 2.0

### Response Data Structure

Actions use `success_payload(data)` which creates:
```python
{
    "content": [
        {
            "type": "text",
            "text": dict(data)  # The actual data dict
        }
    ]
}
```

`ResponseMCP.get_output()` then:
1. Takes `action_response["content"][0]["text"]` (dict)
2. Serializes to JSON string: `json.dumps(content[0]["text"])`
3. Wraps in JSON-RPC 2.0 format with `request_id`

### Error Integration

Gateway errors collected through standard error system, formatted by ResponseMCP:
- Error collection from `is_error()` and `get_errors()`
- First error used as message
- All errors included in `data.errors` array
- JSON-RPC error codes mapped from Gateway error types

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

### Project Name Detection

Both `mcp_wrapper.py` and database connection use same detection:
1. Start from script/module location
2. Walk up directory tree looking for `hh/` directory
3. Use parent directory name as project name
4. Load config from `~/.{project_name}.cnf`

### HTTP Endpoint

**URL**: `https://{host}/mcp` (typically `https://panel.{domain}/mcp`)

**Access**: Subdomain `panel.{domain}` routes to Flask server

**Authentication**: Basic Auth using `user` and `password` from config

**Method**: POST with JSON-RPC 2.0 request body

---

## 5. Modifying the System

### Adding a Tool to Whitelist

1. **Create or Edit Registration File**: Add `@register_mcp_tool` decorator to appropriate `mcp_utils.py` file:
   - `hh/gateway/registry/mcp_utils.py` - For registry lister tools
   - `hh/page/mcp_utils.py` - For page-related tools
   - `hh/agents/mcp_utils.py` - For agent-related tools
   - `hh/mcp_request/mcp_utils.py` - For MCP request tools
   - `hh/mcp_action_request/mcp_utils.py` - For MCP action request tools
   - Or create new `mcp_utils.py` in appropriate module folder

2. **Register Tool**: Use decorator on a placeholder function:
   ```python
   from hh.gateway.registry.mcp_whitelist import register_mcp_tool

   @register_mcp_tool(
       tool_name='new_tool',
       description='Tool description',
       inputSchema={
           'type': 'object',
           'properties': {
               'arg1': {
                   'type': 'string',
                   'description': 'Argument description'
               }
           },
           'required': ['arg1']
       },
       tiers=[1, 2, 3, 4],  # Or specific tiers like [3, 4] for admin/root only
       requires_approval=False,
       crud_type='read'
   )
   def _tool_registration():
       """Registration placeholder for new_tool."""
       pass
   ```

3. **Prerequisites**: Tool must have action handler with `@register_action` and `@register_command` decorators

4. **Cache Rebuild**: 
   - Cache files auto-rebuild on next cache miss (when tool is requested but not in cache)
   - Or manually clear cache to force rebuild: Delete `hh/gateway/registry/cache/mcp-whitelist-*.json` files
   - No Flask server restart needed (cache files are checked on each request)
   - MCP registry auto-generates wrapper on next import (no code changes needed)

### Tool Requirements

For a tool to work through MCP:
- Must be registered with `@register_mcp_tool` decorator in an `mcp_utils.py` file
- Must be available for the requesting tier (tier levels: 1=guest, 2=verified, 3=admin, 4=root)
- Must have action handler registered with `@register_action` and `@register_command`
- Must use `success_payload()` for response data (creates proper structure)
- Should follow standard Gateway patterns (error handling, tracing)

### Schema Validation

The `inputSchema` in whitelist is used by `MCPWhitelist.validate_tool()` for validation:
- Validates tool exists for the requesting tier
- Validates required fields are present
- Validates field types (string, integer, boolean, array, object)
- Allows extra fields (Gateway handles additional validation)
- Returns detailed error messages for failures

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
- Uses `success_payload()` structure from `json_standard.py`
- `get_data()` extracts from `content[0].text` (MCP format)

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
