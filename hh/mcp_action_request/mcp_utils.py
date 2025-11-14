"""
MCP Tool Registrations for MCP Action Request Operations

Registers MCP action request-related MCP tools with appropriate tier access:
- Write operations: admin and root only [3, 4]
"""

from hh.gateway.registry.mcp_whitelist import register_mcp_tool

# Write operations - available to admin and root tiers only
@register_mcp_tool(
    tool_name='modify_mcp_action_request',
    description='Modify an MCP action request. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the MCP action request page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'tool_name': {'type': 'string', 'description': 'The tool name for the MCP action request'},
            'arguments': {'type': 'string', 'description': 'JSON string for the arguments'},
            'extraction_spec': {'type': 'string', 'description': 'JSON string for the extraction spec'},
            'status': {'type': 'string', 'description': 'Status of the MCP action request'},
            'result': {'type': 'string', 'description': 'JSON string for the result'},
            'is_create': {'type': 'boolean', 'description': 'Whether this is a create operation'},
            'is_read': {'type': 'boolean', 'description': 'Whether this is a read operation'},
            'is_update': {'type': 'boolean', 'description': 'Whether this is an update operation'},
            'is_delete': {'type': 'boolean', 'description': 'Whether this is a delete operation'}
        },
        'required': ['page_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
# App actions - tiers 7, 8 (admin app, root app)
@register_mcp_tool(
    tool_name='mcp_action_request_dummy',
    description='MCP Action Request Dummy - Test app action for mcp_action_request group',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the MCP action request page'}
        },
        'required': ['page_id']
    },
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='mcp_action_request',
    app_action_label='MCP Action Request Dummy'
)
def _mcp_action_request_tools_registration():
    """Registration placeholder for all MCP action request-related MCP tools."""
    pass

