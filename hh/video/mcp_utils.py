"""
MCP Tool Registrations for Video Operations

Registers video-related MCP tools with appropriate tier access:
- Read operations: all tiers [1, 2, 3, 4]
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.mcp_whitelist import register_mcp_tool

# Read operations - available to all tiers
@register_mcp_tool(
    tool_name='show_video',
    description='Show video details by ID. Returns complete video data including usage, instances, and metadata.',
    inputSchema={
        'type': 'object',
        'properties': {
            'id': {'type': 'integer', 'description': 'The ID of the video to show'},
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
    tool_name='upload_video',
    description='Upload one or more video files to a page from temp files. Requires admin/panel tier access with database write permissions. Pass files using the _files parameter (e.g., _files=["path/to/file1.mp4", "path/to/file2.mov"]). The system automatically handles file upload via multipart/form-data. Processes files sequentially and stops on any error.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page to upload the video file(s) to'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id'},
            'caption': {'type': 'string', 'description': 'Optional caption for all video files (defaults to original filename for each file)'},
            '_files': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Array of file paths to upload. The system handles the file upload automatically.'}
        },
        'required': ['page_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='modify_video_caption',
    description='Modify the caption of a video file. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'video_id': {'type': 'integer', 'description': 'The ID of the video to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for video_id (use either video_id or id)'},
            'caption': {'type': 'string', 'description': 'The new caption text for the video'},
            'clear': {'type': 'boolean', 'description': 'If true, clears the caption (sets to empty string). Use this instead of providing an empty caption string.'}
        },
        'required': ['video_id', 'caption']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='set_video_visibility',
    description='Set the visibility of a video file. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'video_id': {'type': 'integer', 'description': 'The ID of the video to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for video_id (use either video_id or id)'},
            'visibility': {'type': 'integer', 'description': 'The new visibility value for the video'}
        },
        'required': ['video_id', 'visibility']
    },
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='video',
    app_action_label='Visibility'
)
def _video_tools_registration():
    """Registration placeholder for all video-related MCP tools."""
    pass
