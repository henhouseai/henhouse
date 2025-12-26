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
    app_action_label='Status'
)
@register_mcp_tool(
    tool_name='modify_work_meta',
    description='Generalized tool for managing work page metadata. Supports multiple actions: add (add key-value pairs or append log entry), remove (remove keys), set (set/update key-value pairs), set_all (replace entire field). Works with protected namespaces (log, files_touched, deviations) and user-defined meta bucket. For remove action, provide keys (JSON array string). For other actions, provide data (JSON object string). Field defaults to "meta" but can be "log", "files_touched", "deviations", or "meta". When field is "log", the add action appends a log entry with automatic timestamp. Note: For files_touched field, keys should be full file paths and values should be descriptions of what was done to each file.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the work page'},
            'action': {
                'type': 'string',
                'enum': ['add', 'remove', 'set', 'set_all'],
                'description': 'The action to perform: add (add key-value pairs or append log entry, errors if key exists), remove (remove keys), set (set/update key-value pairs), set_all (replace entire field). When field is "log", add action appends a log entry with automatic timestamp.'
            },
            'field': {
                'type': 'string',
                'enum': ['log', 'files_touched', 'deviations', 'meta'],
                'description': 'The field to operate on. Defaults to "meta". When field is "log", use add action to append log entries.'
            },
            'data': {
                'type': 'string',
                'description': 'JSON object string containing key-value pairs. Required for add, set, and set_all actions. For add action with field="log", contains log entry fields. For add/set/set_all with other fields, contains key-value pairs to add/update. For files_touched field: keys are full file paths, values are descriptions of what was done to each file (e.g., \'{"hh/work/work_page.py": "Updated _load_work_metadata() method"}\').'
            },
            'keys': {
                'type': 'string',
                'description': 'JSON array string containing keys to remove. Required for remove action.'
            }
        },
        'required': ['page_id', 'action']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='metadata',
    description='App action for editing general metadata (meta field) on work pages. Calls modify_work_meta internally.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the work page'}
        },
        'required': ['page_id']
    },
    tiers=[7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='work',
    app_action_label='Metadata'
)
@register_mcp_tool(
    tool_name='files_touched',
    description='App action for editing files_touched field on work pages. Calls modify_work_meta internally.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the work page'}
        },
        'required': ['page_id']
    },
    tiers=[7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='work',
    app_action_label='Files Touched'
)
@register_mcp_tool(
    tool_name='deviations',
    description='App action for editing deviations field on work pages. Calls modify_work_meta internally.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the work page'}
        },
        'required': ['page_id']
    },
    tiers=[7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='work',
    app_action_label='Deviations'
)
@register_mcp_tool(
    tool_name='log_entry',
    description='App action for adding log entries to work pages. Calls modify_work_meta internally.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the work page'}
        },
        'required': ['page_id']
    },
    tiers=[7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='work',
    app_action_label='Log Entry'
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
    app_action_label='Sort'
)
def _work_tools_registration():
    """Registration placeholder for all work page-related MCP tools."""
    pass

