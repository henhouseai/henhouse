"""
MCP Tool Registrations for Sale Operations

Registers sale-related MCP tools with appropriate tier access:
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.tool_whitelist import register_tool

@register_tool(
    tool_name='modify_sale_info',
    description='Modify sale date, receipt number, and sale type information. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the sale page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'date': {'type': 'string', 'description': 'The new date for the sale (format: YYYY-MM-DD)'},
            'receiptNum': {'type': 'string', 'description': 'The new receipt number (optional, can be null)'},
            'saleType': {'type': 'string', 'description': 'The new sale type (must be one of: retail, wholesale, consignment, royalty, service, advance, account, refund, other, capital-gain, gift, sublet, employment, asset sale)'}
        },
        'required': ['page_id', 'date', 'saleType']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    role_whitelist=['general', 'worker'],
    app_action_group='sale',
    app_action_label='Edit Sale Info'
)
@register_tool(
    tool_name='modify_customer_info',
    description='Modify customer information (name, address, city, state, postal code, country). Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the sale page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'customerName': {'type': 'string', 'description': 'The customer name (optional, can be null)'},
            'address': {'type': 'string', 'description': 'The address (optional, can be null)'},
            'city': {'type': 'string', 'description': 'The city (optional, can be null)'},
            'state': {'type': 'string', 'description': 'The state (optional, can be null)'},
            'postalCode': {'type': 'string', 'description': 'The postal code (optional, can be null)'},
            'country': {'type': 'string', 'description': 'The country (optional, can be null)'}
        },
        'required': ['page_id']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    role_whitelist=['general', 'worker'],
    app_action_group='sale',
    app_action_label='Edit Customer Info'
)
@register_tool(
    tool_name='modify_sale_cost_breakdown',
    description='Modify sale cost breakdown (total, tax, shipping). Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the sale page to modify'},
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
    role_whitelist=['general', 'worker'],
    app_action_group='sale',
    app_action_label='Edit Cost Breakdown'
)
def _sale_tools_registration():
    """Registration placeholder for all sale-related MCP tools."""
    pass

