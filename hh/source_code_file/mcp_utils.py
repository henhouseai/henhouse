"""
MCP Tool Registrations for Source Code File Operations

Registers source code file-related MCP tools with appropriate tier access:
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.mcp_whitelist import register_mcp_tool

# Write operations - available to admin and root tiers only
# Note: modify_path and modify_language are registered in hh/page/mcp_utils.py

# App actions - tiers 7, 8 (admin app, root app)
@register_mcp_tool(
    tool_name='source_code_file_dummy_page_crud',
    description='Source Code File Dummy - Test app action for page_crud group',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the source code file page'}
        },
        'required': ['page_id']
    },
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='page_crud',
    app_action_label='Source Code File Dummy (Page CRUD)'
)
@register_mcp_tool(
    tool_name='source_code_file_dummy_extra',
    description='Source Code File Dummy - Test app action for extra group',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the source code file page'}
        },
        'required': ['page_id']
    },
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='extra',
    app_action_label='Source Code File Dummy (Extra)'
)
@register_mcp_tool(
    tool_name='source_code_file_dummy_extra_two',
    description='Source Code File Dummy - Test app action for extra_two group',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the source code file page'}
        },
        'required': ['page_id']
    },
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='extra_two',
    app_action_label='Source Code File Dummy (Extra Two)'
)
def _source_code_file_tools_registration():
    """Registration placeholder for all source code file-related MCP tools."""
    pass

