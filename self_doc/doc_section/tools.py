"""
MCP Tool Registrations for Doc Section Operations

Registers doc section-related MCP tools with appropriate tier access:
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.tool_whitelist import register_tool

@register_tool(
    tool_name='modify_doc_section_info',
    description='Modify doc section metadata fields (section_level, sort_order, section_type). Requires admin/panel tier access with database write permissions.',
    inputSchema={
        'type': 'object',
        'properties': {
            'page_id': {'type': 'integer', 'description': 'The ID of the doc section page to modify'},
            'id': {'type': 'integer', 'description': 'Alternative parameter name for page_id (use either page_id or id)'},
            'section_level': {'type': 'integer', 'description': 'Header level for this section (1-6, default 2 for ##)'},
            'sort_order': {'type': 'integer', 'description': 'Ordering within the document (numeric)'},
            'section_type': {'type': 'string', 'description': 'Type of section ("heading", "content", "code", "list", "table")'}
        },
        'required': ['page_id']
    },
    mcp_tiers=[3, 4],
    api_tiers=[3, 4],
    role_whitelist=['worker']
)
@register_tool(
    tool_name='doc_section_combo',
    app_action_tiers=[3, 4],
    app_action_group='doc_section',
    app_action_label='Edit Doc Section'
)
def _doc_section_tools_registration():
    """Registration placeholder for all doc section-related MCP tools."""
    pass