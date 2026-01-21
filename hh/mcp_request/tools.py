"""
MCP Tool Registrations for MCP Request Operations

Registers MCP request-related MCP tools with appropriate tier access:
- Write operations: admin and root only [3, 4]
"""

from hh.gateway.registry.tool_whitelist import register_tool

@register_tool(
    tool_name='modify_mcp_request',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='mcp_request_dummy'
)
def _mcp_request_tools_registration():
    """Registration placeholder for all MCP request-related MCP tools."""
    pass

