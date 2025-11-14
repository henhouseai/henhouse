"""
MCP Tool Registrations for Registry Listers

Registers the six lister tools (command_list, action_list, backend_list, 
http_list, parser_list, mcp_list) as MCP tools available to all tiers.
These are read-only tools that list available registry items.
"""

from hh.gateway.registry.mcp_whitelist import register_mcp_tool

# All lister tools use the same simple schema and are available to all tiers
_LISTER_SCHEMA = {
    'type': 'object',
    'properties': {},
    'required': []
}

# Register all lister tools using a single placeholder function
# tiers=[1, 2, 3, 4] means all tiers (1=guest, 2=verified, 3=admin, 4=root)
@register_mcp_tool(
    tool_name='command_list',
    description='List available commands',
    inputSchema=_LISTER_SCHEMA,
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
    tool_name='action_list',
    description='List available action handlers',
    inputSchema=_LISTER_SCHEMA,
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
    tool_name='backend_list',
    description='List available backend handlers',
    inputSchema=_LISTER_SCHEMA,
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
    tool_name='http_list',
    description='List available HTTP backends',
    inputSchema=_LISTER_SCHEMA,
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
    tool_name='parser_list',
    description='List available parser backends',
    inputSchema=_LISTER_SCHEMA,
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
    tool_name='mcp_list',
    description='List available MCP backends',
    inputSchema=_LISTER_SCHEMA,
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
def _lister_tools_registration():
    """Registration placeholder for all lister MCP tools."""
    pass
