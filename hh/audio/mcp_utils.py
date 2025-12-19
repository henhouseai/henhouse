"""
MCP Tool Registrations for Audio Operations

Registers audio-related MCP tools with appropriate tier access:
- Read operations: all tiers [1, 2, 3, 4]
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.mcp_whitelist import register_mcp_tool

# Read operations - available to all tiers
@register_mcp_tool(
    tool_name='show_audio',
    description='Show audio details by ID. Returns complete audio data including usage, instances, and metadata.',
    inputSchema={
        'type': 'object',
        'properties': {
            'id': {'type': 'integer', 'description': 'The ID of the audio to show'},
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
    tool_name='upload_audio',
    description='Upload one or more audio files to a page from temp files. Requires admin/panel tier access with database write permissions. Pass files using the _files parameter (e.g., _files=["path/to/file1.mp3", "path/to/file2.wav"]). The system automatically handles file upload via multipart/form-data. Processes files sequentially and stops on any error.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the page to upload the audio file(s) to'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id'},
            'caption': {'type': 'string', 'description': 'Optional caption for all audio files (defaults to original filename for each file)'},
            '_files': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Array of file paths to upload. The system handles the file upload automatically.'}
        },
        'required': ['page_id']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='create'
)
@register_mcp_tool(
    tool_name='modify_audio_caption',
    description='Modify the caption of an audio file. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'audio_id': {'type': 'integer', 'description': 'The ID of the audio to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for audio_id (use either audio_id or id)'},
            'caption': {'type': 'string', 'description': 'The new caption text for the audio'},
            'clear': {'type': 'boolean', 'description': 'If true, clears the caption (sets to empty string). Use this instead of providing an empty caption string.'}
        },
        'required': ['audio_id', 'caption']
    },
    tiers=[3, 4],
    requires_approval=False,
    crud_type='update'
)
@register_mcp_tool(
    tool_name='set_audio_visibility',
    description='Set the visibility of an audio file. Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'audio_id': {'type': 'integer', 'description': 'The ID of the audio to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for audio_id (use either audio_id or id)'},
            'visibility': {'type': 'integer', 'description': 'The new visibility value for the audio'}
        },
        'required': ['audio_id', 'visibility']
    },
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type='update',
    app_action_group='audio',
    app_action_label='Visibility'
)
def _audio_tools_registration():
    """Registration placeholder for all audio-related MCP tools."""
    pass
