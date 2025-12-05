"""
MCP Tool Registrations for Image Operations

Registers image-related MCP tools with appropriate tier access:
- Read operations: all tiers [1, 2, 3, 4]
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.mcp_whitelist import register_mcp_tool

# Read operations - available to all tiers
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
# Write operations - available to admin and root tiers only
@register_mcp_tool(
    tool_name='upload_images',
    description='Upload one or more images to a page from temp files. Requires admin/panel tier access with database write permissions. Pass files using the _files parameter (e.g., _files=["path/to/file1.jpg", "path/to/file2.jpg"]). The system automatically handles file upload via multipart/form-data. Processes files sequentially and stops on any error.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page to upload the image(s) to'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id'},
            'caption': {'type': 'string', 'description': 'Optional caption for all images (defaults to original filename for each image)'},
            '_files': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Array of file paths to upload. The system handles the file upload automatically.'}
        },
        'required': ['page_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
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
    tool_name='set_image_visibility',
    description='Set the visibility of an image. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'image_id': {'type': 'integer', 'description': 'The ID of the image to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for image_id (use either image_id or id)'},
            'visibility': {'type': 'integer', 'description': 'The new visibility value for the image'}
        },
        'required': ['image_id', 'visibility']
    },
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='images',
    app_action_label='Visibility'
)
def _image_tools_registration():
    """Registration placeholder for all image-related MCP tools."""
    pass

