"""
MCP Tool Registrations for Video Operations

Registers video-related MCP tools with appropriate tier access:
- Read operations: all tiers [1, 2, 3, 4]
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.tool_whitelist import register_tool

@register_tool(
    tool_name='show_video',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='upload_video',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='modify_video_caption',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='set_video_visibility',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_video',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_videos',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='move_video',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='move_videos',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='remove_video',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='set_video_rank',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='upload_video_app',
    app_action_tiers=[3, 4],
    app_action_group='video',
    app_action_label='Upload'
)
@register_tool(
    tool_name='copy_video_app',
    app_action_tiers=[3, 4],
    app_action_group='video',
    app_action_label='Copy'
)
@register_tool(
    tool_name='move_video_app',
    app_action_tiers=[3, 4],
    app_action_group='video',
    app_action_label='Move'
)
@register_tool(
    tool_name='delete_video_app',
    app_action_tiers=[3, 4],
    app_action_group='video',
    app_action_label='Delete'
)
@register_tool(
    tool_name='sort_video_app',
    app_action_tiers=[3, 4],
    app_action_group='video',
    app_action_label='Sort'
)
@register_tool(
    tool_name='get_video_group',
    api_tiers=[1, 2, 3, 4]
)
def _video_tools_registration():
    """Registration placeholder for all video-related MCP tools."""
    pass
