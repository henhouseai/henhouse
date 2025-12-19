"""
MCP Tool Registrations for Page Operations

Registers page-related MCP tools with appropriate tier access:
- Read operations: all tiers [1, 2, 3, 4]
- Write operations: admin and root only [3, 4]
"""

from hh.gateway.registry.mcp_whitelist import register_mcp_tool

# Read operations - available to all tiers
@register_mcp_tool(
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
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
    tool_name='show_page',
    description='Show page with full details by ID, name, or link. Returns complete page data including hierarchy and content.',
    inputSchema={
        'type': 'object',
        'properties': {
            'id': {'type': 'integer', 'description': 'The ID of the page to show'},
            'name': {'type': 'string', 'description': 'The name/link of the page to show (alternative to id)'},
            'link': {'type': 'string', 'description': 'The link of the page to show (alternative to id or name)'}
        },
        'required': []
    },
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
    tool_name='get_app_actions',
    description='Get available app actions for the current user tier level. Returns list of app actions that can be triggered from the web interface.',
    inputSchema={
        'type': 'object',
        'properties': {},
        'required': []
    },
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
    tool_name='count_pages',
    description='Count the total number of pages and images in the database.',
    inputSchema={
        'type': 'object',
        'properties': {},
        'required': []
    },
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
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
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
    tool_name='get_add_page_class_info',
    description='Get allowed child page classes for a parent page. Returns list of page classes that can be created as children, including whether they allow null names, duplicate names, and auto-link names.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the parent page'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'}
        },
        'required': ['page_id']
    },
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
    tool_name='help',
    description='Get help documentation for a topic and optional section. Returns help content in JSON format.',
    inputSchema={
        'type': 'object',
        'properties': {
            'topic': {'type': 'string', 'description': 'The help topic to retrieve (defaults to \'help\' if not provided)'},
            'section': {'type': 'string', 'description': 'Optional specific section within the topic'}
        },
        'required': []
    },
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
# Write operations - admin and root only
@register_mcp_tool(
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
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='pages',
    app_action_label='Edit Name'
)
@register_mcp_tool(
    tool_name='modify_text',
    description='Modify the text content of a page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'text': {'type': 'string', 'description': 'The new text content for the page'}
        },
        'required': ['page_id', 'text']
    },
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='pages',
    app_action_label='Edit Text'
)
@register_mcp_tool(
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
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type='create',
    app_action_group='pages',
    app_action_label='Add Page'
)
@register_mcp_tool(
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
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type='delete',
    app_action_group='pages',
    app_action_label='Delete Page'
)
@register_mcp_tool(
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
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='pages',
    app_action_label='Move Page'
)
@register_mcp_tool(
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
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type='create',
    app_action_group='pages',
    app_action_label='Copy Page'
)
@register_mcp_tool(
    tool_name='combo',
    description='Test form with name and text editable, plus read-only fields displayed. App action only - no MCP call.',
    inputSchema={
        'type': 'object',
        'properties': {},
        'required': []
    },
    tiers=[7, 8],  # App action only - no MCP tiers
    requires_approval=False,
    crud_type='read',  # Mark as read since it's not a real MCP tool
    app_action_group='pages',
    app_action_label='Combo'
)
@register_mcp_tool(
    tool_name='copy_image',
    description='Copy a single image to a target page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to copy the image to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'image_id': {'type': 'integer', 'description': 'The ID of the image to copy'},
            'rank': {'type': 'integer', 'description': 'Optional rank position for the copied image'}
        },
        'required': ['target_page', 'image_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='copy_images',
    description='Copy multiple images to a target page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to copy images to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'image_id': {'type': 'string', 'description': 'Comma-separated list of image IDs to copy'},
            'rank': {'type': 'integer', 'description': 'Optional starting rank position for the copied images'}
        },
        'required': ['target_page', 'image_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='move_image',
    description='Move a single image from a source page to a target page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'source_page': {'type': 'integer', 'description': 'The ID of the source page containing the image'},
            's_page': {'type': 'integer', 'description': 'Alternative parameter name for source_page'},
            'image_id': {'type': 'integer', 'description': 'The ID of the image to move'},
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to move the image to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'source_rank': {'type': 'integer', 'description': 'Optional rank of the image in the source page (auto-detected if not specified and only one instance exists)'},
            's_rank': {'type': 'integer', 'description': 'Short form of source_rank parameter'},
            'target_rank': {'type': 'integer', 'description': 'Optional rank position for the image in the target page'},
            't_rank': {'type': 'integer', 'description': 'Short form of target_rank parameter'}
        },
        'required': ['source_page', 'image_id', 'target_page']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='move_images',
    description='Move multiple images from a source page to a target page. Can move all images or specific ones by rank. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'source_page': {'type': 'integer', 'description': 'The ID of the source page containing the images'},
            's_page': {'type': 'integer', 'description': 'Alternative parameter name for source_page'},
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to move images to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'source_rank': {'type': 'string', 'description': 'Optional comma-separated list of ranks to move (if not specified, moves all images)'},
            's_rank': {'type': 'string', 'description': 'Short form of source_rank parameter'},
            'target_rank': {'type': 'integer', 'description': 'Optional starting rank position for moved images in the target page'},
            't_rank': {'type': 'integer', 'description': 'Short form of target_rank parameter'}
        },
        'required': ['source_page', 'target_page']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='remove_image',
    description='Remove an image from a page. Can remove a specific instance by rank or all instances. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page containing the image'},
            'image_id': {'type': 'integer', 'description': 'The ID of the image to remove'},
            'rank': {'type': 'integer', 'description': 'Optional rank of the specific image instance to remove (if not specified, removes all instances)'}
        },
        'required': ['page_id', 'image_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='delete'
)
@register_mcp_tool(
    tool_name='set_image_rank',
    description='Change the rank/position of an image within a page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page containing the image'},
            'image_id': {'type': 'integer', 'description': 'The ID of the image to reorder'},
            'target_rank': {'type': 'integer', 'description': 'The new rank position for the image'},
            't_rank': {'type': 'integer', 'description': 'Short form of target_rank parameter'},
            'source_rank': {'type': 'integer', 'description': 'Optional current rank of the image (auto-detected if not specified and only one instance exists)'},
            's_rank': {'type': 'integer', 'description': 'Short form of source_rank parameter'}
        },
        'required': ['page_id', 'image_id', 'target_rank']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='copy_images_app',
    description='Copy images to a target page. App action only - no MCP call.',
    inputSchema={
        'type': 'object',
        'properties': {},
        'required': []
    },
    tiers=[7, 8],  # App action only - no MCP tiers
    requires_approval=False,
    crud_type='read',  # Mark as read since it's not a real MCP tool
    app_action_group='images',
    app_action_label='Copy'
)
@register_mcp_tool(
    tool_name='move_images_app',
    description='Move images from a source page to a target page. App action only - no MCP call.',
    inputSchema={
        'type': 'object',
        'properties': {},
        'required': []
    },
    tiers=[7, 8],  # App action only - no MCP tiers
    requires_approval=False,
    crud_type='read',  # Mark as read since it's not a real MCP tool
    app_action_group='images',
    app_action_label='Move'
)
@register_mcp_tool(
    tool_name='delete_images_app',
    description='Delete images from a page. App action only - no MCP call.',
    inputSchema={
        'type': 'object',
        'properties': {},
        'required': []
    },
    tiers=[7, 8],  # App action only - no MCP tiers
    requires_approval=False,
    crud_type='read',  # Mark as read since it's not a real MCP tool
    app_action_group='images',
    app_action_label='Delete'
)
@register_mcp_tool(
    tool_name='sort_images_app',
    description='Sort/reorder images on a page. App action only - no MCP call.',
    inputSchema={
        'type': 'object',
        'properties': {},
        'required': []
    },
    tiers=[7, 8],  # App action only - no MCP tiers
    requires_approval=False,
    crud_type='read',  # Mark as read since it's not a real MCP tool
    app_action_group='images',
    app_action_label='Sort'
)
@register_mcp_tool(
    tool_name='Upload',
    description='Upload images to a page. App action only - no MCP call.',
    inputSchema={
        'type': 'object',
        'properties': {},
        'required': []
    },
    tiers=[7, 8],  # App action only - no MCP tiers
    requires_approval=False,
    crud_type='read',  # Mark as read since it's not a real MCP tool
    app_action_group='images',
    app_action_label='Upload'
)
@register_mcp_tool(
    tool_name='add_file',
    description='Add a single file to a page from a file path. The file will be processed, renamed, and stored in the proper directory structure with hash value. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to add the file to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'file': {'type': 'string', 'description': 'The file path to add'},
            'description': {'type': 'string', 'description': 'Optional description/caption for the file (defaults to filename if not provided)'},
            'caption': {'type': 'string', 'description': 'Alternative parameter name for description'}
        },
        'required': ['target_page', 'file']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='add_files',
    description='Add multiple files to a page from a folder. Files will be processed, renamed, and stored in the proper directory structure with hash values. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to add files to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'folder': {'type': 'string', 'description': 'The folder path containing files to add'},
            'description': {'type': 'string', 'description': 'Optional description/caption for all files (defaults to filename if not provided)'},
            'caption': {'type': 'string', 'description': 'Alternative parameter name for description'}
        },
        'required': ['target_page', 'folder']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
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
    tool_name='copy_file',
    description='Copy a single file to a target page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to copy the file to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'file_id': {'type': 'integer', 'description': 'The ID of the file to copy'},
            'rank': {'type': 'integer', 'description': 'Optional rank position for the copied file'}
        },
        'required': ['target_page', 'file_id']
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
    tool_name='move_file',
    description='Move a single file from a source page to a target page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'source_page': {'type': 'integer', 'description': 'The ID of the source page containing the file'},
            's_page': {'type': 'integer', 'description': 'Alternative parameter name for source_page'},
            'file_id': {'type': 'integer', 'description': 'The ID of the file to move'},
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to move the file to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'source_rank': {'type': 'integer', 'description': 'Optional rank of the file in the source page (auto-detected if not specified and only one instance exists)'},
            's_rank': {'type': 'integer', 'description': 'Short form of source_rank parameter'},
            'target_rank': {'type': 'integer', 'description': 'Optional rank position for the file in the target page'},
            't_rank': {'type': 'integer', 'description': 'Short form of target_rank parameter'}
        },
        'required': ['source_page', 'file_id', 'target_page']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
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
    tool_name='copy_files_app',
    description='Copy files to a target page. App action only - no MCP call.',
    inputSchema={'type': 'object', 'properties': {}, 'required': []},
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='files',
    app_action_label='Copy'
)
@register_mcp_tool(
    tool_name='move_files_app',
    description='Move files from a source page to a target page. App action only - no MCP call.',
    inputSchema={'type': 'object', 'properties': {}, 'required': []},
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='files',
    app_action_label='Move'
)
@register_mcp_tool(
    tool_name='delete_files_app',
    description='Delete files from a page. App action only - no MCP call.',
    inputSchema={'type': 'object', 'properties': {}, 'required': []},
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='files',
    app_action_label='Delete'
)
@register_mcp_tool(
    tool_name='sort_files_app',
    description='Sort/reorder files on a page. App action only - no MCP call.',
    inputSchema={'type': 'object', 'properties': {}, 'required': []},
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='files',
    app_action_label='Sort'
)
@register_mcp_tool(
    tool_name='copy_audio',
    description='Copy a single audio file to a target page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to copy the audio to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'audio_id': {'type': 'integer', 'description': 'The ID of the audio to copy'},
            'rank': {'type': 'integer', 'description': 'Optional rank position for the copied audio'}
        },
        'required': ['target_page', 'audio_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='copy_audios',
    description='Copy multiple audio files to a target page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to copy audio to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'audio_id': {'type': 'string', 'description': 'Comma-separated list of audio IDs to copy'},
            'rank': {'type': 'integer', 'description': 'Optional starting rank position for the copied audio'}
        },
        'required': ['target_page', 'audio_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='move_audio',
    description='Move a single audio file from a source page to a target page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'source_page': {'type': 'integer', 'description': 'The ID of the source page containing the audio'},
            's_page': {'type': 'integer', 'description': 'Alternative parameter name for source_page'},
            'audio_id': {'type': 'integer', 'description': 'The ID of the audio to move'},
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to move the audio to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'source_rank': {'type': 'integer', 'description': 'Optional rank of the audio in the source page (auto-detected if not specified and only one instance exists)'},
            's_rank': {'type': 'integer', 'description': 'Short form of source_rank parameter'},
            'target_rank': {'type': 'integer', 'description': 'Optional rank position for the audio in the target page'},
            't_rank': {'type': 'integer', 'description': 'Short form of target_rank parameter'}
        },
        'required': ['source_page', 'audio_id', 'target_page']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='move_audios',
    description='Move multiple audio files from a source page to a target page. Can move all audio or specific ones by rank. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'source_page': {'type': 'integer', 'description': 'The ID of the source page containing the audio'},
            's_page': {'type': 'integer', 'description': 'Alternative parameter name for source_page'},
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to move audio to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'source_rank': {'type': 'string', 'description': 'Optional comma-separated list of ranks to move (if not specified, moves all audio)'},
            's_rank': {'type': 'string', 'description': 'Short form of source_rank parameter'},
            'target_rank': {'type': 'integer', 'description': 'Optional starting rank position for moved audio in the target page'},
            't_rank': {'type': 'integer', 'description': 'Short form of target_rank parameter'}
        },
        'required': ['source_page', 'target_page']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='remove_audio',
    description='Remove an audio file from a page. Can remove a specific instance by rank or all instances. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page containing the audio file'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id'},
            'audio_id': {'type': 'integer', 'description': 'The ID of the audio file to remove'},
            'rank': {'type': 'integer', 'description': 'Optional rank of the specific audio file instance to remove (if omitted, removes all instances)'}
        },
        'required': ['page_id', 'audio_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='delete'
)
@register_mcp_tool(
    tool_name='set_audio_rank',
    description='Change the rank/position of an audio file within a page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page containing the audio file'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id'},
            'audio_id': {'type': 'integer', 'description': 'The ID of the audio file to reorder'},
            'target_rank': {'type': 'integer', 'description': 'The new rank position for the audio file'},
            't_rank': {'type': 'integer', 'description': 'Short form of target_rank parameter'},
            'source_rank': {'type': 'integer', 'description': 'Optional current rank of the audio file'},
            's_rank': {'type': 'integer', 'description': 'Short form of source_rank parameter'}
        },
        'required': ['page_id', 'audio_id', 'target_rank']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='copy_video',
    description='Copy a single video file to a target page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to copy the video to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'video_id': {'type': 'integer', 'description': 'The ID of the video to copy'},
            'rank': {'type': 'integer', 'description': 'Optional rank position for the copied video'}
        },
        'required': ['target_page', 'video_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='copy_videos',
    description='Copy multiple video files to a target page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to copy videos to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'video_id': {'type': 'string', 'description': 'Comma-separated list of video IDs to copy'},
            'rank': {'type': 'integer', 'description': 'Optional starting rank position for the copied videos'}
        },
        'required': ['target_page', 'video_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='move_video',
    description='Move a single video file from a source page to a target page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'source_page': {'type': 'integer', 'description': 'The ID of the source page containing the video'},
            's_page': {'type': 'integer', 'description': 'Alternative parameter name for source_page'},
            'video_id': {'type': 'integer', 'description': 'The ID of the video to move'},
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to move the video to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'source_rank': {'type': 'integer', 'description': 'Optional rank of the video in the source page (auto-detected if not specified and only one instance exists)'},
            's_rank': {'type': 'integer', 'description': 'Short form of source_rank parameter'},
            'target_rank': {'type': 'integer', 'description': 'Optional rank position for the video in the target page'},
            't_rank': {'type': 'integer', 'description': 'Short form of target_rank parameter'}
        },
        'required': ['source_page', 'video_id', 'target_page']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='move_videos',
    description='Move multiple video files from a source page to a target page. Can move all videos or specific ones by rank. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'source_page': {'type': 'integer', 'description': 'The ID of the source page containing the videos'},
            's_page': {'type': 'integer', 'description': 'Alternative parameter name for source_page'},
            'target_page': {'type': 'integer', 'description': 'The ID of the target page to move videos to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'source_rank': {'type': 'string', 'description': 'Optional comma-separated list of ranks to move (if not specified, moves all videos)'},
            's_rank': {'type': 'string', 'description': 'Short form of source_rank parameter'},
            'target_rank': {'type': 'integer', 'description': 'Optional starting rank position for moved videos in the target page'},
            't_rank': {'type': 'integer', 'description': 'Short form of target_rank parameter'}
        },
        'required': ['source_page', 'target_page']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='remove_video',
    description='Remove a video file from a page. Can remove a specific instance by rank or all instances. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page containing the video file'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id'},
            'video_id': {'type': 'integer', 'description': 'The ID of the video file to remove'},
            'rank': {'type': 'integer', 'description': 'Optional rank of the specific video file instance to remove (if omitted, removes all instances)'}
        },
        'required': ['page_id', 'video_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='delete'
)
@register_mcp_tool(
    tool_name='set_video_rank',
    description='Change the rank/position of a video file within a page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page containing the video file'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id'},
            'video_id': {'type': 'integer', 'description': 'The ID of the video file to reorder'},
            'target_rank': {'type': 'integer', 'description': 'The new rank position for the video file'},
            't_rank': {'type': 'integer', 'description': 'Short form of target_rank parameter'},
            'source_rank': {'type': 'integer', 'description': 'Optional current rank of the video file'},
            's_rank': {'type': 'integer', 'description': 'Short form of source_rank parameter'}
        },
        'required': ['page_id', 'video_id', 'target_rank']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='upload_files_app',
    description='Upload files to a page. App action only - no MCP call.',
    inputSchema={'type': 'object', 'properties': {}, 'required': []},
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='files',
    app_action_label='Upload'
)
@register_mcp_tool(
    tool_name='upload_audio_app',
    description='Upload audio files to a page. App action only - no MCP call.',
    inputSchema={'type': 'object', 'properties': {}, 'required': []},
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='audio',
    app_action_label='Upload'
)
@register_mcp_tool(
    tool_name='upload_video_app',
    description='Upload video files to a page. App action only - no MCP call.',
    inputSchema={'type': 'object', 'properties': {}, 'required': []},
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='video',
    app_action_label='Upload'
)
@register_mcp_tool(
    tool_name='copy_audio_app',
    description='Copy audio files to a target page. App action only - no MCP call.',
    inputSchema={'type': 'object', 'properties': {}, 'required': []},
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='audio',
    app_action_label='Copy'
)
@register_mcp_tool(
    tool_name='move_audio_app',
    description='Move audio files from a source page to a target page. App action only - no MCP call.',
    inputSchema={'type': 'object', 'properties': {}, 'required': []},
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='audio',
    app_action_label='Move'
)
@register_mcp_tool(
    tool_name='delete_audio_app',
    description='Delete audio files from a page. App action only - no MCP call.',
    inputSchema={'type': 'object', 'properties': {}, 'required': []},
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='audio',
    app_action_label='Delete'
)
@register_mcp_tool(
    tool_name='sort_audio_app',
    description='Sort/reorder audio files on a page. App action only - no MCP call.',
    inputSchema={'type': 'object', 'properties': {}, 'required': []},
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='audio',
    app_action_label='Sort'
)
@register_mcp_tool(
    tool_name='copy_video_app',
    description='Copy video files to a target page. App action only - no MCP call.',
    inputSchema={'type': 'object', 'properties': {}, 'required': []},
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='video',
    app_action_label='Copy'
)
@register_mcp_tool(
    tool_name='move_video_app',
    description='Move video files from a source page to a target page. App action only - no MCP call.',
    inputSchema={'type': 'object', 'properties': {}, 'required': []},
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='video',
    app_action_label='Move'
)
@register_mcp_tool(
    tool_name='delete_video_app',
    description='Delete video files from a page. App action only - no MCP call.',
    inputSchema={'type': 'object', 'properties': {}, 'required': []},
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='video',
    app_action_label='Delete'
)
@register_mcp_tool(
    tool_name='sort_video_app',
    description='Sort/reorder video files on a page. App action only - no MCP call.',
    inputSchema={'type': 'object', 'properties': {}, 'required': []},
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='video',
    app_action_label='Sort'
)
@register_mcp_tool(
    tool_name='get_browser',
    description='Get browser HTML for page selection overlay. Returns structured HTML sections with metadata for browser overlay.',
    inputSchema={
        'type': 'object',
        'properties': {
            'id': {'type': 'integer', 'description': 'The ID of the page to display in browser'},
            'name': {'type': 'string', 'description': 'The name/link of the page to display (alternative to id)'},
            'link': {'type': 'string', 'description': 'The link of the page to display (alternative to id or name)'}
        },
        'required': []
    },
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
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
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
    tool_name='set_page_visibility',
    description='Set the visibility of a page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'visibility': {'type': 'integer', 'description': 'The new visibility value for the page'}
        },
        'required': ['page_id', 'visibility']
    },
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='pages',
    app_action_label='Visibility'
)
@register_mcp_tool(
    tool_name='set_page_display_style',
    description='Set the display style of a page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'display_style': {'type': 'integer', 'description': 'The new display style value for the page'},
            'displayStyle': {'type': 'integer', 'description': 'Alternative parameter name for display_style'}
        },
        'required': ['page_id', 'display_style']
    },
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='pages',
    app_action_label='Display Style'
)
@register_mcp_tool(
    tool_name='get_image_group',
    description='Get JSON data for all images in a page\'s image group. Returns image metadata including instances for use in image viewer.',
    inputSchema={
        'type': 'object',
        'properties': {
            'id': {'type': 'integer', 'description': 'The ID of the page to get images from'},
            'page_id': {'type': 'integer', 'description': 'Alternative parameter name for id'}
        },
        'required': ['id']
    },
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
    tool_name='get_audio_group',
    description='Get JSON data for all audio files in a page\'s audio group. Returns audio metadata including instances for use in audio viewer.',
    inputSchema={
        'type': 'object',
        'properties': {
            'id': {'type': 'integer', 'description': 'The ID of the page to get audio files from'},
            'page_id': {'type': 'integer', 'description': 'Alternative parameter name for id'}
        },
        'required': ['id']
    },
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
@register_mcp_tool(
    tool_name='get_video_group',
    description='Get JSON data for all video files in a page\'s video group. Returns video metadata including instances for use in video viewer.',
    inputSchema={
        'type': 'object',
        'properties': {
            'id': {'type': 'integer', 'description': 'The ID of the page to get video files from'},
            'page_id': {'type': 'integer', 'description': 'Alternative parameter name for id'}
        },
        'required': ['id']
    },
    tiers=[1, 2, 3, 4],
    requires_approval=False,
    crud_type='read'
)
def _page_tools_registration():
    """Registration placeholder for all page-related MCP tools."""
    pass

