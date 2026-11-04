"""
MCP Tool Registrations for Image Operations

Registers image-related MCP tools with appropriate tier access:
- Read operations: all tiers [1, 2, 3, 4]
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.tool_whitelist import register_tool

@register_tool(
    tool_name='show_image',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='upload_images',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='modify_image_caption',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='set_image_visibility',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_image',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_images',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='move_image',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='move_images',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='remove_image',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='set_image_rank',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_images_app',
    app_action_tiers=[3, 4],
    app_action_group='images',
    app_action_label='Copy'
)
@register_tool(
    tool_name='move_images_app',
    app_action_tiers=[3, 4],
    app_action_group='images',
    app_action_label='Move'
)
@register_tool(
    tool_name='delete_images_app',
    app_action_tiers=[3, 4],
    app_action_group='images',
    app_action_label='Delete'
)
@register_tool(
    tool_name='sort_images_app',
    app_action_tiers=[3, 4],
    app_action_group='images',
    app_action_label='Sort'
)
@register_tool(
    tool_name='Upload',
    app_action_tiers=[3, 4],
    app_action_group='images',
    app_action_label='Upload'
)
@register_tool(
    tool_name='get_image_group',
    api_tiers=[1, 2, 3, 4]
)
def _image_tools_registration():
    """Registration placeholder for all image-related MCP tools."""
    pass

