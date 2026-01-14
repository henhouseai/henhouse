"""
MCP Tool Registrations for Transfer Operations

Registers transfer-related MCP tools with appropriate tier access:
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.tool_whitelist import register_tool

@register_tool(
    tool_name='modify_transfer_info',
    description='Modify transfer information (date, amount, modifier, fee). If modifier is non-zero, amount is adjusted by modifier. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the transfer page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'date': {'type': 'string', 'description': 'The new date for the transfer (format: YYYY-MM-DD, optional)'},
            'amount': {'type': 'number', 'description': 'The new transfer amount (will be normalized to 2 decimal places)'},
            'modifier': {'type': 'number', 'description': 'Amount modifier - if non-zero, amount is adjusted by this value (will be normalized to 2 decimal places, optional, defaults to 0)'},
            'fee': {'type': 'number', 'description': 'The new transfer fee (will be normalized to 2 decimal places)'}
        },
        'required': ['page_id', 'amount', 'fee']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    requires_approval=False,
    crud_type='update',
    app_action_group='transfer',
    app_action_label='Edit Transfer Info'
)
@register_tool(
    tool_name='modify_target_info',
    description='Modify the transfer target page ID. The target must be a statement, sale, or invoice. Pass null to clear the transfer target. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the transfer page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'transfer_to': {'type': 'string', 'description': 'The ID of the target page (statement, sale, or invoice) as a string. Pass empty string to clear the target.'}
        },
        'required': ['page_id', 'transfer_to']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    requires_approval=False,
    crud_type='update',
    app_action_group='transfer',
    app_action_label='Edit Transfer Target'
)
def _transfer_tools_registration():
    """Registration placeholder for all transfer-related MCP tools."""
    pass

