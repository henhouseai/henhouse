"""
MCP Tool Registrations for MCP Request Operations

Registers MCP request-related MCP tools with appropriate tier access:
- Write operations: admin and root only [3, 4]
"""

from hh.gateway.registry.mcp_whitelist import register_mcp_tool

# Write operations - available to admin and root tiers only
@register_mcp_tool(
    tool_name='modify_mcp_request',
    description='Modify an MCP request. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the MCP request page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'input_request': {'type': 'string', 'description': 'JSON string for the input request'},
            'output_response': {'type': 'string', 'description': 'JSON string for the output response'},
            'create_request': {'type': 'integer', 'description': 'Create request count'},
            'read_request': {'type': 'integer', 'description': 'Read request count'},
            'update_request': {'type': 'integer', 'description': 'Update request count'},
            'delete_request': {'type': 'integer', 'description': 'Delete request count'},
            'create_executed': {'type': 'integer', 'description': 'Create executed count'},
            'read_executed': {'type': 'integer', 'description': 'Read executed count'},
            'update_executed': {'type': 'integer', 'description': 'Update executed count'},
            'delete_executed': {'type': 'integer', 'description': 'Delete executed count'},
            'status': {'type': 'string', 'description': 'Status of the MCP request'}
        },
        'required': ['page_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
# App actions - tiers 7, 8 (admin app, root app)
@register_mcp_tool(
    tool_name='mcp_request_dummy',
    description='MCP Request Dummy - Test app action for mcp_request group',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the MCP request page'}
        },
        'required': ['page_id']
    },
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='mcp_request',
    app_action_label='MCP Request Dummy'
)
def _mcp_request_tools_registration():
    """Registration placeholder for all MCP request-related MCP tools."""
    pass

