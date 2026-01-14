"""
MCP Tool Registrations for Audio Operations

Registers audio-related MCP tools with appropriate tier access:
- Read operations: all tiers [1, 2, 3, 4]
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.tool_whitelist import register_tool

@register_tool(
    tool_name='show_audio',
    api_tiers=[3]
)
@register_tool(
    tool_name='upload_audio',
    api_tiers=[3]
)
@register_tool(
    tool_name='modify_audio_caption',
    api_tiers=[3]
)
@register_tool(
    tool_name='set_audio_visibility',
    api_tiers=[3, 4]
)
def _audio_tools_registration():
    """Registration placeholder for all audio-related MCP tools."""
    pass
