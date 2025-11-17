"""
MCP Tool Registrations for Source Code File Operations

Registers source code file-related MCP tools with appropriate tier access:
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.mcp_whitelist import register_mcp_tool

@register_mcp_tool(
    tool_name='modify_path',
    description='Modify the file path of a source code file page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the source code file page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'path': {'type': 'string', 'description': 'The new file path for the source code file'}
        },
        'required': ['page_id', 'path']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='modify_language',
    description='Modify the programming language of a source code file page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the source code file page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'language': {'type': 'string', 'description': 'The new programming language for the source code file (e.g., \'python\', \'javascript\', \'markdown\')'}
        },
        'required': ['page_id', 'language']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='source_code_file_combo',
    description='Edit source code file: text, file path, and language. App action only - no MCP call.',
    inputSchema={
        'type': 'object',
        'properties': {},
        'required': []
    },
    tiers=[7, 8],  # App action only - no MCP tiers
    requires_approval=False,
    crud_type='read',  # Mark as read since it's not a real MCP tool
    app_action_group='source_code',
    app_action_label='Edit Source Code File'
)
def _source_code_file_tools_registration():
    """Registration placeholder for all source code file-related MCP tools."""
    pass

