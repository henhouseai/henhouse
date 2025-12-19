"""
Backend Types Configuration

BACKEND_TYPES is the source of truth for all backend types in the system.
When adding a new backend type, you must update it in multiple places:

1. Add to BACKEND_TYPES list below
2. Add description to BACKEND_DESCRIPTIONS
3. Add decorator name to BACKEND_DECORATORS
4. Add dict name to BACKEND_DICTS
5. Add explicit decorator definition in hh/gateway/registry/registry.py
   (replace exec() with: register_newtype = create_backend_decorator('newtype'))
6. If it's a delivery backend, add to BACKEND_RESPONSE_MODULES

The system uses BACKEND_TYPES to:
- Generate dataclasses (ActionInfo, ParserInfo, etc.) via exec() in registry.py
- Generate dictionaries (actions, parsers, etc.) via exec() in registry.py
- Generate decorator functions (register_action, etc.) - NOW EXPLICIT in registry.py
- Generate list actions and parsers via exec() in utils.py
- Build backend_handlers structure in registry.py
- Pre-populate backends dict in registry.py
"""

BACKEND_TYPES = ['action', 'parser', 'mcp', 'http', 'maintenance', 'download']

BACKEND_DESCRIPTIONS = {
    'action': 'Action handlers that process business logic',
    'parser': 'Parser handlers that format output for display', 
    'mcp': 'MCP (Model Context Protocol) handlers',
    'http': 'HTTP handlers for web/HTML output',
    'maintenance': 'Maintenance backend handlers',
    'download': 'Download backend handlers'
}

BACKEND_DECORATORS = {
    'action': 'register_action',
    'parser': 'register_parser',
    'mcp': 'register_mcp',
    'http': 'register_http',
    'maintenance': 'register_maintenance',
    'download': 'register_download'
}

BACKEND_DICTS = {
    'action': 'actions',
    'parser': 'parsers',
    'mcp': 'mcps',
    'http': 'https',
    'maintenance': 'maintenances',
    'download': 'downloads'
}

# Note: there is intentionally no entry for 'action' here.
# Actions are not delivery backends—they are the first phase of every Gateway request,
# so they do not need (nor should they have) a dedicated Response handler.
BACKEND_RESPONSE_MODULES = {
    'http': 'hh.gateway.response.response_http.ResponseHTTP',
    'parser': 'hh.gateway.response.response_parser.ResponseParser',
    'mcp': 'hh.gateway.response.response_mcp.ResponseMCP',
    'maintenance': 'hh.gateway.response.response_maintenance.ResponseMaintenance',
    'download': 'hh.gateway.response.response_download.ResponseDownload',
}
