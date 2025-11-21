BACKEND_TYPES = ['action', 'parser', 'mcp', 'http', 'maintenance']

BACKEND_DESCRIPTIONS = {
    'action': 'Action handlers that process business logic',
    'parser': 'Parser handlers that format output for display', 
    'mcp': 'MCP (Model Context Protocol) handlers',
    'http': 'HTTP handlers for web/HTML output',
    'maintenance': 'Maintenance backend handlers'
}

BACKEND_DECORATORS = {
    'action': 'register_action',
    'parser': 'register_parser',
    'mcp': 'register_mcp',
    'http': 'register_http',
    'maintenance': 'register_maintenance'
}

BACKEND_DICTS = {
    'action': 'actions',
    'parser': 'parsers',
    'mcp': 'mcps',
    'http': 'https',
    'maintenance': 'maintenances'
}

# Note: there is intentionally no entry for 'action' here.
# Actions are not delivery backends—they are the first phase of every Gateway request,
# so they do not need (nor should they have) a dedicated Response handler.
BACKEND_RESPONSE_MODULES = {
    'http': 'hh.gateway.response.response_http.ResponseHTTP',
    'parser': 'hh.gateway.response.response_parser.ResponseParser',
    'mcp': 'hh.gateway.response.response_mcp.ResponseMCP',
    'maintenance': 'hh.gateway.response.response_maintenance.ResponseMaintenance',
}
