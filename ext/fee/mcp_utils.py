"""
MCP Tool Registrations for Fee Operations

Registers fee-related MCP tools with appropriate tier access:
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.mcp_whitelist import register_mcp_tool

@register_mcp_tool(
    tool_name='modify_fee_info',
    description='Modify fee information (fee amount and date). Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the fee page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'fee': {'type': 'number', 'description': 'The new fee amount (will be normalized to 2 decimal places)'},
            'date': {'type': 'string', 'description': 'The new date for the fee (format: YYYY-MM-DD, optional)'}
        },
        'required': ['page_id', 'fee']
    },
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='fee',
    app_action_label='Edit Fee'
)
def _fee_tools_registration():
    """Registration placeholder for all fee-related MCP tools."""
    pass

