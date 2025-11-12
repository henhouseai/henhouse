BACKEND_TYPES = ['action', 'parser', 'mcp', 'http']

BACKEND_DESCRIPTIONS = {
    'action': 'Action handlers that process business logic',
    'parser': 'Parser handlers that format output for display', 
    'mcp': 'MCP (Model Context Protocol) handlers',
    'http': 'HTTP handlers for web/HTML output'
}

BACKEND_DECORATORS = {
    'action': 'register_action',
    'parser': 'register_parser',
    'mcp': 'register_mcp',
    'http': 'register_http'
}

BACKEND_DICTS = {
    'action': 'actions',
    'parser': 'parsers',
    'mcp': 'mcps',
    'http': 'https'
}
