"""
MCP Tool Registrations for Document Operations

Registers document-related MCP tools with appropriate tier access:
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.tool_whitelist import register_tool

@register_tool(
    tool_name='modify_document_info',
    description='Modify document metadata fields (output_filename, output_format). Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the document page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'output_filename': {'type': 'string', 'description': 'The target filename for generated output (e.g., "README.md")'},
            'output_format': {'type': 'string', 'description': 'The output format ("markdown", "html", or "json")'}
        },
        'required': ['page_id']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    role_whitelist=['worker']
)
@register_tool(
    tool_name='document_combo',
    app_action_tiers=[3, 4],
    app_action_group='document',
    app_action_label='Edit Document'
)
def _document_tools_registration():
    """Registration placeholder for all document-related MCP tools."""
    pass