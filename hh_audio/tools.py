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
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='upload_audio',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='modify_audio_caption',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='set_audio_visibility',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_audio',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_audios',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='move_audio',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='move_audios',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='remove_audio',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='set_audio_rank',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='upload_audio_app',
    app_action_tiers=[3, 4],
    app_action_group='audio',
    app_action_label='Upload'
)
@register_tool(
    tool_name='copy_audio_app',
    app_action_tiers=[3, 4],
    app_action_group='audio',
    app_action_label='Copy'
)
@register_tool(
    tool_name='move_audio_app',
    app_action_tiers=[3, 4],
    app_action_group='audio',
    app_action_label='Move'
)
@register_tool(
    tool_name='delete_audio_app',
    app_action_tiers=[3, 4],
    app_action_group='audio',
    app_action_label='Delete'
)
@register_tool(
    tool_name='sort_audio_app',
    app_action_tiers=[3, 4],
    app_action_group='audio',
    app_action_label='Sort'
)
@register_tool(
    tool_name='get_audio_group',
    api_tiers=[1, 2, 3, 4]
)
def _audio_tools_registration():
    """Registration placeholder for all audio-related MCP tools."""
    pass
