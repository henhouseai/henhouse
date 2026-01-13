"""
MCP Tool Registrations for FiscalPeriod Operations

Registers fiscal period-related MCP tools with appropriate tier access:
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.tool_whitelist import register_tool

@register_tool(
    tool_name='modify_fiscal_period_info',
    description='Modify the date range of a fiscal period page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the fiscal period page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'startDate': {'type': 'string', 'description': 'The new start date for the fiscal period (format: YYYY-MM-DD)'},
            'endDate': {'type': 'string', 'description': 'The new end date for the fiscal period (format: YYYY-MM-DD)'}
        },
        'required': ['page_id', 'startDate', 'endDate']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    requires_approval=False,
    crud_type='update',
    app_action_group='fiscalPeriod',
    app_action_label='Edit Fiscal Period'
)
def _fiscal_period_tools_registration():
    """Registration placeholder for all fiscal period-related MCP tools."""
    pass

