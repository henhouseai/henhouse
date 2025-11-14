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
    tool_name='show_image',
    description='Show image details by ID. Returns complete image data including usage, instances, and metadata.',
    inputSchema={
        'type': 'object',
        'properties': {
            'id': {'type': 'integer', 'description': 'The ID of the image to show'},
            'json': {'type': 'boolean', 'description': 'If true, returns JSON format output (optional)'}
        },
        'required': ['id']
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
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
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
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
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
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
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
    tiers=[3, 4],
    requires_approval=False,
    crud_type='delete'
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
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
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
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='add_image',
    description='Add a single image to a page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'target_page': {'type': 'integer', 'description': 'The ID of the page to add the image to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'file': {'type': 'string', 'description': 'Path to the image file to add'},
            'caption': {'type': 'string', 'description': 'Caption for the image (optional, defaults to filename without extension)'}
        },
        'required': ['target_page', 'file']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='add_images',
    description='Add multiple images from a folder to a page. Scans folder for valid image files and adds them all. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'target_page': {'type': 'integer', 'description': 'The ID of the page to add images to'},
            't_page': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for target_page'},
            'folder': {'type': 'string', 'description': 'Path to the folder containing image files to add'},
            'caption': {'type': 'string', 'description': 'Caption to use for all images (optional, defaults to individual filenames)'}
        },
        'required': ['target_page', 'folder']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
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
    tool_name='modify_caption',
    description='Modify the caption of an image. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'image_id': {'type': 'integer', 'description': 'The ID of the image to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for image_id (use either image_id or id)'},
            'caption': {'type': 'string', 'description': 'The new caption text for the image'},
            'clear': {'type': 'boolean', 'description': 'If true, clears the caption (sets to empty string). Use this instead of providing an empty caption string.'}
        },
        'required': ['image_id', 'caption']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='modify_path',
    description='Modify the file path of a source code file page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the source code file page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'path': {'type': 'string', 'description': 'The new file path for the source code file'}
        },
        'required': ['page_id', 'path']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='modify_language',
    description='Modify the programming language of a source code file page. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the source code file page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'language': {'type': 'string', 'description': 'The new programming language for the source code file (e.g., \'python\', \'javascript\', \'markdown\')'}
        },
        'required': ['page_id', 'language']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
# App actions - tiers 7, 8 (admin app, root app)
@register_mcp_tool(
    tool_name='page_dummy_1',
    description='Page Dummy 1 - Test app action for page_crud group',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page'}
        },
        'required': ['page_id']
    },
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='page_crud',
    app_action_label='Page Dummy 1'
)
@register_mcp_tool(
    tool_name='page_dummy_2',
    description='Page Dummy 2 - Test app action for page_crud group',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page'}
        },
        'required': ['page_id']
    },
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='page_crud',
    app_action_label='Page Dummy 2'
)
@register_mcp_tool(
    tool_name='extra_dummy',
    description='Extra Dummy - Test app action for extra group',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page'}
        },
        'required': ['page_id']
    },
    tiers=[7, 8],
    requires_approval=False,
    crud_type='read',
    app_action_group='extra',
    app_action_label='Extra Dummy'
)
def _page_tools_registration():
    """Registration placeholder for all page-related MCP tools."""
    pass

