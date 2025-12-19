"""
MCP Tool Registrations for File Operations

Registers file-related MCP tools with appropriate tier access:
- Read operations: all tiers [1, 2, 3, 4]
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.mcp_whitelist import register_mcp_tool

@register_mcp_tool(
    tool_name='modify_file_description',
    description='Modify the description of a file. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'file_id': {'type': 'integer', 'description': 'The ID of the file to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for file_id (use either file_id or id)'},
            'description': {'type': 'string', 'description': 'The new description text for the file'},
            'clear': {'type': 'boolean', 'description': 'If true, clears the description (sets to empty string). Use this instead of providing an empty description string.'}
        },
        'required': ['file_id', 'description']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='set_file_visibility',
    description='Set the visibility of a file. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'file_id': {'type': 'integer', 'description': 'The ID of the file to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for file_id (use either file_id or id)'},
            'visibility': {'type': 'integer', 'description': 'The new visibility value for the file'}
        },
        'required': ['file_id', 'visibility']
    },
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='files',
    app_action_label='Visibility'
)
def _file_tools_registration():
    """Registration placeholder for all file-related MCP tools."""
    pass

