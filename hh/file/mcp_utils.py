"""
MCP Tool Registrations for File Operations

Registers file-related MCP tools with appropriate tier access:
- Read operations: all tiers [1, 2, 3, 4]
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.mcp_whitelist import register_mcp_tool

@register_mcp_tool(
    tool_name='upload_files',
    description='Upload one or more files to a page from temp files. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page to upload the file(s) to'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id'},
            '_files': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Array of file paths to upload (handled by multipart/form-data)'}
        },
        'required': ['page_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='copy_files',
    description='Copy multiple files from a source page to a target page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'source_page': {'type': 'integer', 'description': 'The ID of the source page containing the files'},
            's_page': {'type': 'integer', 'description': 'Alternative parameter name for source_page'},
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to copy files to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'source_rank': {'type': 'string', 'description': 'Optional comma-separated list of ranks to copy (if omitted, copies all files)'},
            's_rank': {'type': 'string', 'description': 'Short form of source_rank'},
            'target_rank': {'type': 'integer', 'description': 'Optional starting rank position for copied files'},
            't_rank': {'type': 'integer', 'description': 'Short form of target_rank'}
        },
        'required': ['source_page', 'target_page']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='move_files',
    description='Move multiple files from a source page to a target page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'source_page': {'type': 'integer', 'description': 'The ID of the source page containing the files'},
            's_page': {'type': 'integer', 'description': 'Alternative parameter name for source_page'},
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to move files to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'source_rank': {'type': 'string', 'description': 'Optional comma-separated list of ranks to move (if omitted, moves all files)'},
            's_rank': {'type': 'string', 'description': 'Short form of source_rank'},
            'target_rank': {'type': 'integer', 'description': 'Optional starting rank position for moved files'},
            't_rank': {'type': 'integer', 'description': 'Short form of target_rank'}
        },
        'required': ['source_page', 'target_page']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='remove_file',
    description='Remove a file from a page. Can remove a specific instance by rank or all instances. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page containing the file'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id'},
            'file_id': {'type': 'integer', 'description': 'The ID of the file to remove'},
            'rank': {'type': 'integer', 'description': 'Optional rank of the specific file instance to remove (if omitted, removes all instances)'}
        },
        'required': ['page_id', 'file_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='delete'
)
@register_mcp_tool(
    tool_name='set_file_rank',
    description='Change the rank/position of a file within a page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page containing the file'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id'},
            'file_id': {'type': 'integer', 'description': 'The ID of the file to reorder'},
            'target_rank': {'type': 'integer', 'description': 'The new rank position for the file'},
            't_rank': {'type': 'integer', 'description': 'Short form of target_rank parameter'},
            'source_rank': {'type': 'integer', 'description': 'Optional current rank of the file'},
            's_rank': {'type': 'integer', 'description': 'Short form of source_rank parameter'}
        },
        'required': ['page_id', 'file_id', 'target_rank']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='set_file_visibility',
    description='Set the visibility of a file. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'file_id': {'type': 'integer', 'description': 'The ID of the file to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for file_id (use either file_id or id)'},
            'visibility': {'type': 'integer', 'description': 'The new visibility value for the file'}
        },
        'required': ['file_id', 'visibility']
    },
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='files',
    app_action_label='Visibility'
)
@register_mcp_tool(
    tool_name='upload_files_app',
    description='Upload files to a page. App action only - no MCP call.',
    inputSchema={
        'type': 'object',
        'properties': {},
        'required': []
    },
    tiers=[7, 8],  # App action only
    requires_approval=False,
    crud_type='read',
    app_action_group='files',
    app_action_label='Upload'
)
def _file_tools_registration():
    """Registration placeholder for all file-related MCP tools."""
    pass

