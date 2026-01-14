"""
MCP Tool Registrations for MCP Action Request Operations

Registers MCP action request-related MCP tools with appropriate tier access:
- Write operations: admin and root only [3, 4]
"""

from hh.gateway.registry.tool_whitelist import register_tool

@register_tool(
    tool_name='modify_mcp_action_request',
    api_tiers=[3]
)
@register_tool(
    tool_name='mcp_action_request_dummy'
)
def _mcp_action_request_tools_registration():
    """Registration placeholder for all MCP action request-related MCP tools."""
    pass

