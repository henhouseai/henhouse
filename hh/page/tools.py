"""
MCP Tool Registrations for Page Operations

Registers page-related MCP tools with appropriate tier access:
- Read operations: all tiers [1, 2, 3, 4]
- Write operations: admin and root only [3, 4]
"""

from hh.gateway.registry.tool_whitelist import register_tool

# Read operations - available to all tiers
@register_tool(
    tool_name='get_page',
    description='Get page data by ID, name, or link. Returns JSON-friendly page data including children, images, and metadata.',
    inputSchema={
        'type': 'object',
        'properties': {
            'id': {'type': 'integer', 'description': 'The ID of the page to retrieve'},
            'name': {'type': 'string', 'description': 'The name/link of the page to retrieve (alternative to id)'},
            'link': {'type': 'string', 'description': 'The link of the page to retrieve (alternative to id or name)'}
        },
        'required': []
    },
    mcp_tiers=[1, 2, 3, 4],
    api_tiers=[1, 2, 3, 4],
    role_whitelist=['general', 'worker'],
    requires_approval=False,
    crud_type='read'
)
@register_tool(
    tool_name='show_page',
    api_tiers=[1, 2, 3, 4]
)
@register_tool(
    tool_name='get_app_actions',
    api_tiers=[1, 2, 3, 4]
)
@register_tool(
    tool_name='get_text',
    description='Get processed/parsed text for a page. Returns HTTP-rendered text processed through TextProcessor with final_decorator=\'http\'.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page to get processed text for'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'}
        },
        'required': ['page_id']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    role_whitelist=['general', 'worker'],
    requires_approval=False,
    crud_type='read'
)
@register_tool(
    tool_name='get_add_page_class_info',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='help',
    api_tiers=[3, 4]
)
# Write operations - admin and root only
@register_tool(
    tool_name='modify_name',
    description='Modify the name of a page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'name': {'type': 'string', 'description': 'The new name for the page. Can be empty string or null if the page class allows null names.'}
        },
        'required': ['page_id']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    role_whitelist=['worker'],
    requires_approval=False,
    crud_type='update',
    app_action_group='pages',
    app_action_label='Edit Name'
)
@register_tool(
    tool_name='modify_text',
    description='''Modify the text content of a page with flexible editing modes. Requires admin/panel tier access with database write permissions.

Editing Modes:
- "replace_all" (default): Complete replacement of page text with the provided text
- "prepend": Insert text at the beginning of existing content
- "append": Insert text at the end of existing content
- "replace": Replace a specific string with the provided text (exactly 1 match required)

For "replace" mode, you must provide old_string - the exact string to find and replace. This mode requires the old_string to appear exactly once in the content; it will fail if the string is not found or appears multiple times.

All modes validate the final combined content through TextProcessor before saving.''',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'text': {'type': 'string', 'description': 'The text content. For replace_all: the complete new content. For prepend/append: the text to insert. For replace: the replacement string.'},
            'new_string': {'type': 'string', 'description': 'Alias for text parameter. Allows agents to use new_string when they see old_string in the documentation.'},
            'mode': {'type': 'string', 'description': 'Editing mode: "replace_all" (default), "prepend", "append", or "replace"', 'enum': ['replace_all', 'prepend', 'append', 'replace']},
            'old_string': {'type': 'string', 'description': 'The exact string to find and replace (required when mode="replace"). Must appear exactly once in the content.'},
            'return_full_page': {'type': 'boolean', 'description': 'If true, returns full page object via show_page(). Use for HTTP/TypeScript clients that need complete page data for UI updates. Default: false.'},
            'return_full_text': {'type': 'boolean', 'description': 'If true, returns just the updated page text content. Use when you need the actual text but not the full page object. Default: false.'}
        },
        'required': ['page_id']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    role_whitelist=['worker'],
    requires_approval=False,
    crud_type='update',
    app_action_group='pages',
    app_action_label='Edit Text'
)
@register_tool(
    tool_name='add_page',
    description='Create a new page under a target parent page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'target_page': {'type': 'integer', 'description': 'The ID of the parent page under which to create the new page'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'name': {'type': 'string', 'description': 'The name for the new page. Required for page classes that don\'t allow null names.'},
            'class': {'type': 'string', 'description': 'The page class type (defaults to \'page\' if not specified)'}
        },
        'required': ['target_page']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    role_whitelist=['worker'],
    requires_approval=False,
    crud_type='create',
    app_action_group='pages',
    app_action_label='Add Page'
)
@register_tool(
    tool_name='delete_page',
    description='Delete a page and all its children. Requires admin/panel tier access with database write permissions. The confirm parameter must be set to true to proceed with deletion.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page to delete'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id'},
            'confirm': {'type': 'boolean', 'description': 'Confirmation flag required for page deletion. Must be set to true to proceed.'}
        },
        'required': ['page_id', 'confirm']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    role_whitelist=['worker'],
    requires_approval=False,
    crud_type='delete',
    app_action_group='pages',
    app_action_label='Delete Page'
)
@register_tool(
    tool_name='move_page',
    description='Move a page to a different parent page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'source_page': {'type': 'integer', 'description': 'The ID of the page to move'},
            's_page': {'type': 'integer', 'description': 'Alternative parameter name for source_page'},
            'target_page': {'type': 'integer', 'description': 'The ID of the new parent page'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'}
        },
        'required': ['source_page', 'target_page']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    role_whitelist=['worker'],
    requires_approval=False,
    crud_type='update',
    app_action_group='pages',
    app_action_label='Move Page'
)
@register_tool(
    tool_name='copy_page',
    description='Copy a page (and optionally its children recursively) to a target parent page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'source_page': {'type': 'integer', 'description': 'The ID of the page to copy'},
            's_page': {'type': 'integer', 'description': 'Alternative parameter name for source_page'},
            'target_page': {'type': 'integer', 'description': 'The ID of the target parent page where the copy will be created'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'recursive': {'type': 'boolean', 'description': 'Whether to recursively copy all child pages (default: false)'},
            'r': {'type': 'boolean', 'description': 'Short form of recursive parameter'},
            'recursive-depth': {'type': 'integer', 'description': 'Maximum depth for recursive copy (optional)'},
            'rd': {'type': 'integer', 'description': 'Short form of recursive-depth parameter'}
        },
        'required': ['source_page', 'target_page']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    role_whitelist=['worker'],
    requires_approval=False,
    crud_type='create',
    app_action_group='pages',
    app_action_label='Copy Page'
)
@register_tool(
    tool_name='combo',
    app_action_tiers=[3, 4],
    app_action_group='pages',
    app_action_label='Combo'
)
@register_tool(
    tool_name='copy_image',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_images',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='move_image',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='move_images',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='remove_image',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='set_image_rank',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_images_app',
    app_action_tiers=[3, 4],
    app_action_group='images',
    app_action_label='Copy'
)
@register_tool(
    tool_name='move_images_app',
    app_action_tiers=[3, 4],
    app_action_group='images',
    app_action_label='Move'
)
@register_tool(
    tool_name='delete_images_app',
    app_action_tiers=[3, 4],
    app_action_group='images',
    app_action_label='Delete'
)
@register_tool(
    tool_name='sort_images_app',
    app_action_tiers=[3, 4],
    app_action_group='images',
    app_action_label='Sort'
)
@register_tool(
    tool_name='Upload',
    app_action_tiers=[3, 4],
    app_action_group='images',
    app_action_label='Upload'
)
@register_tool(
    tool_name='add_file',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='add_files',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='upload_files',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_file',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_files',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='move_file',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='move_files',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='remove_file',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='set_file_rank',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_files_app',
    app_action_tiers=[3, 4],
    app_action_group='files',
    app_action_label='Copy'
)
@register_tool(
    tool_name='move_files_app',
    app_action_tiers=[3, 4],
    app_action_group='files',
    app_action_label='Move'
)
@register_tool(
    tool_name='delete_files_app',
    app_action_tiers=[3, 4],
    app_action_group='files',
    app_action_label='Delete'
)
@register_tool(
    tool_name='sort_files_app',
    app_action_tiers=[3, 4],
    app_action_group='files',
    app_action_label='Sort'
)
@register_tool(
    tool_name='copy_audio',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_audios',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='move_audio',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='move_audios',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='remove_audio',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='set_audio_rank',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_video',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='copy_videos',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='move_video',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='move_videos',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='remove_video',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='set_video_rank',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='upload_files_app',
    app_action_tiers=[3, 4],
    app_action_group='files',
    app_action_label='Upload'
)
@register_tool(
    tool_name='upload_audio_app',
    app_action_tiers=[3, 4],
    app_action_group='audio',
    app_action_label='Upload'
)
@register_tool(
    tool_name='upload_video_app',
    app_action_tiers=[3, 4],
    app_action_group='video',
    app_action_label='Upload'
)
@register_tool(
    tool_name='copy_audio_app',
    app_action_tiers=[3, 4],
    app_action_group='audio',
    app_action_label='Copy'
)
@register_tool(
    tool_name='move_audio_app',
    app_action_tiers=[3, 4],
    app_action_group='audio',
    app_action_label='Move'
)
@register_tool(
    tool_name='delete_audio_app',
    app_action_tiers=[3, 4],
    app_action_group='audio',
    app_action_label='Delete'
)
@register_tool(
    tool_name='sort_audio_app',
    app_action_tiers=[3, 4],
    app_action_group='audio',
    app_action_label='Sort'
)
@register_tool(
    tool_name='copy_video_app',
    app_action_tiers=[3, 4],
    app_action_group='video',
    app_action_label='Copy'
)
@register_tool(
    tool_name='move_video_app',
    app_action_tiers=[3, 4],
    app_action_group='video',
    app_action_label='Move'
)
@register_tool(
    tool_name='delete_video_app',
    app_action_tiers=[3, 4],
    app_action_group='video',
    app_action_label='Delete'
)
@register_tool(
    tool_name='sort_video_app',
    app_action_tiers=[3, 4],
    app_action_group='video',
    app_action_label='Sort'
)
@register_tool(
    tool_name='get_browser',
    api_tiers=[3, 4]
)
@register_tool(
    tool_name='get_page_section',
    description='Get HTML snippet for a specific page section (images, children, files) in the requested view mode (table or tile).',
    inputSchema={
        'type': 'object',
        'properties': {
            'id': {'type': 'integer', 'description': 'Page ID'},
            'section': {'type': 'string', 'description': 'Section name: images, children, or files', 'enum': ['images', 'children', 'files']},
            'view_type': {'type': 'string', 'description': 'View mode: table, tile, or auto (defaults based on backend)', 'enum': ['table', 'tile', 'auto']},
            'class_name': {'type': 'string', 'description': 'For children sections, filter by specific class (optional)'}
        },
        'required': ['id', 'section']
    },
    mcp_tiers=[1, 2, 3, 4],
    api_tiers=[1, 2, 3, 4],
    role_whitelist=['general', 'worker'],
    requires_approval=False,
    crud_type='read'
)
@register_tool(
    tool_name='check_links',
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    app_action_group='pages',
    app_action_label='Check Links'
)
@register_tool(
    tool_name='set_page_visibility',
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    app_action_group='pages',
    app_action_label='Visibility'
)
@register_tool(
    tool_name='set_page_display_style',
    api_tiers=[3, 4],
    app_action_tiers=[3, 4],
    app_action_group='pages',
    app_action_label='Display Style'
)
@register_tool(
    tool_name='get_image_group',
    api_tiers=[1, 2, 3, 4]
)
@register_tool(
    tool_name='get_audio_group',
    api_tiers=[1, 2, 3, 4]
)
@register_tool(
    tool_name='get_video_group',
    api_tiers=[1, 2, 3, 4]
)
def _page_tools_registration():
    """Registration placeholder for all page-related MCP tools."""
    pass

