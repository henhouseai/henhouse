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
@register_tool(
    tool_name='add_file',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='add_files',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='upload_files',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_file',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_files',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='move_file',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='move_files',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='remove_file',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='set_file_rank',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_files_app',
    app_action_tiers=[3, 4],
    app_action_group='files',
    app_action_label='Copy'
)
@register_tool(
    tool_name='move_files_app',
    app_action_tiers=[3, 4],
    app_action_group='files',
    app_action_label='Move'
)
@register_tool(
    tool_name='delete_files_app',
    app_action_tiers=[3, 4],
    app_action_group='files',
    app_action_label='Delete'
)
@register_tool(
    tool_name='sort_files_app',
    app_action_tiers=[3, 4],
    app_action_group='files',
    app_action_label='Sort'
)
@register_tool(
    tool_name='upload_files_app',
    app_action_tiers=[3, 4],
    app_action_group='files',
    app_action_label='Upload'
)
def _file_tools_registration():
    """Registration placeholder for all file-related MCP tools."""
    pass

