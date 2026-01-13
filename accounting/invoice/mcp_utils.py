"""
MCP Tool Registrations for Invoice Operations

Registers invoice-related MCP tools with appropriate tier access:
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.tool_whitelist import register_tool

@register_tool(
    tool_name='modify_invoice_info',
    description='Modify invoice date and reference information. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the invoice page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'date': {'type': 'string', 'description': 'The new date for the invoice (format: YYYY-MM-DD)'},
            'reference': {'type': 'string', 'description': 'The new reference for the invoice (optional, can be null)'}
        },
        'required': ['page_id', 'date']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    requires_approval=False,
    crud_type='update',
    app_action_group='invoice',
    app_action_label='Edit Invoice Info'
)
@register_tool(
    tool_name='modify_invoice_cost_breakdown',
    description='Modify invoice cost breakdown (total, tax, shipping). Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the invoice page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'total': {'type': 'number', 'description': 'The new total amount (will be normalized to 2 decimal places)'},
            'tax': {'type': 'number', 'description': 'The new tax amount (will be normalized to 2 decimal places)'},
            'shipping': {'type': 'number', 'description': 'The new shipping amount (will be normalized to 2 decimal places)'}
        },
        'required': ['page_id', 'total', 'tax', 'shipping']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    requires_approval=False,
    crud_type='update',
    app_action_group='invoice',
    app_action_label='Edit Cost Breakdown'
)
def _invoice_tools_registration():
    """Registration placeholder for all invoice-related MCP tools."""
    pass

