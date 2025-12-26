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
    description='Generalized tool for managing work page metadata. Supports multiple actions: add_log (append log entry), add (add key-value pairs), remove (remove keys), set (set/update key-value pairs), set_all (replace entire field). Works with protected namespaces (log, files_touched, deviations) and user-defined meta bucket. For remove action, provide keys (JSON array string). For other actions, provide data (JSON object string). Field defaults to "meta" but can be "log", "files_touched", "deviations", or "meta".',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the work page'},
            'action': {
                'type': 'string',
                'enum': ['add_log', 'add', 'remove', 'set', 'set_all'],
                'description': 'The action to perform: add_log (append log entry), add (add key-value pairs, errors if key exists), remove (remove keys), set (set/update key-value pairs), set_all (replace entire field)'
            },
            'field': {
                'type': 'string',
                'enum': ['log', 'files_touched', 'deviations', 'meta'],
                'description': 'The field to operate on. Defaults to "meta". Note: "log" field only supports "add_log" action.'
            },
            'data': {
                'type': 'string',
                'description': 'JSON object string containing key-value pairs. Required for add_log, add, set, and set_all actions. For add_log, contains log entry fields. For add/set/set_all, contains key-value pairs to add/update.'
            },
            'keys': {
                'type': 'string',
                'description': 'JSON array string containing keys to remove. Required for remove action.'
            }
        },
        'required': ['page_id', 'action']
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

