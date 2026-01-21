"""
MCP Tool Registrations for File Operations

Registers file-related MCP tools with appropriate tier access:
- Read operations: all tiers [1, 2, 3, 4]
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.tool_whitelist import register_tool

@register_tool(
    tool_name='modify_file_description',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='set_file_visibility',
    api_tiers=[3, 4]
)
def _file_tools_registration():
    """Registration placeholder for all file-related MCP tools."""
    pass

