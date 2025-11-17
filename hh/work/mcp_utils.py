"""
MCP Tool Registrations for Work Page Operations

Registers work page-related MCP tools with appropriate tier access:
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.mcp_whitelist import register_mcp_tool

# Write operations - available to admin and root tiers only
@register_mcp_tool(
    tool_name='modify_work_status',
    description='Modify the status of a work page (work docket, ask, task, or step).',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the work page'},
            'status': {
                'type': 'string',
                'enum': ['todo', 'doing', 'review', 'done'],
                'description': 'The new status for the work page'
            }
        },
        'required': ['page_id', 'status']
    },
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='work',
    app_action_label='Modify Work Status'
)
@register_mcp_tool(
    tool_name='modify_work_meta',
    description='Modify the meta field of a work page (work docket, ask, task, or step).',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the work page'},
            'meta': {
                'type': 'string',
                'description': 'The new meta JSON string for the work page'
            }
        },
        'required': ['page_id', 'meta']
    },
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='work',
    app_action_label='Modify Work Meta'
)
@register_mcp_tool(
    tool_name='modify_work_sort_order',
    description='Modify the sort_order of a work page (work docket, ask, task, or step).',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the work page'},
            'sort_order': {
                'type': 'integer',
                'description': 'The new sort_order for the work page'
            }
        },
        'required': ['page_id', 'sort_order']
    },
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='work',
    app_action_label='Modify Work Sort Order'
)
def _work_tools_registration():
    """Registration placeholder for all work page-related MCP tools."""
    pass

