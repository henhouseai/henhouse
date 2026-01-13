"""
MCP Tool Registrations for Account Operations

Registers account-related MCP tools with appropriate tier access:
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.tool_whitelist import register_tool

@register_tool(
    tool_name='modify_account_type',
    description='Modify the account type of an account page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the account page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'type': {'type': 'string', 'description': 'The new account type (e.g., \'cash\', \'checking\', \'savings\')'}
        },
        'required': ['page_id', 'type']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    requires_approval=False,
    crud_type='update',
    app_action_group='account',
    app_action_label='Edit Account Type'
)
def _account_tools_registration():
    """Registration placeholder for all account-related MCP tools."""
    pass

