"""
MCP Tool Registrations for Statement Operations

Registers statement-related MCP tools with appropriate tier access:
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.tool_whitelist import register_tool

@register_tool(
    tool_name='modify_statement_info',
    description='Modify statement period and balance information (start date, end date, opening balance, closing balance). Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the statement page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'startDate': {'type': 'string', 'description': 'The new start date for the statement (format: YYYY-MM-DD)'},
            'endDate': {'type': 'string', 'description': 'The new end date for the statement (format: YYYY-MM-DD)'},
            'openingBalance': {'type': 'number', 'description': 'The new opening balance (will be normalized to 2 decimal places)'},
            'closingBalance': {'type': 'number', 'description': 'The new closing balance (will be normalized to 2 decimal places)'}
        },
        'required': ['page_id', 'startDate', 'endDate', 'openingBalance', 'closingBalance']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    requires_approval=False,
    crud_type='update',
    app_action_group='statement',
    app_action_label='Edit Statement Info'
)
@register_tool(
    tool_name='modify_finance_info',
    description='Modify finance information (interest earned and finance charge). Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the statement page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'interestEarned': {'type': 'number', 'description': 'The new interest earned amount (will be normalized to 2 decimal places)'},
            'financeCharge': {'type': 'number', 'description': 'The new finance charge amount (will be normalized to 2 decimal places)'}
        },
        'required': ['page_id', 'interestEarned', 'financeCharge']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    requires_approval=False,
    crud_type='update',
    app_action_group='statement',
    app_action_label='Edit Finance Info'
)
def _statement_tools_registration():
    """Registration placeholder for all statement-related MCP tools."""
    pass

