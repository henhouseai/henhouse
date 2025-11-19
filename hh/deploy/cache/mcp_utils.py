"""
MCP Tool registrations for cache maintenance actions.
"""

from hh.gateway.registry.mcp_whitelist import register_mcp_tool


@register_mcp_tool(
    tool_name="rebuild_cache",
    description="Rebuild cached pages and images from the relational database. Supports optional limits and entity filters.",
    inputSchema={
        "type": "object",
        "properties": {
            "pages": {
                "type": "boolean",
                "description": "Set true to rebuild pages (default true)",
            },
            "images": {
                "type": "boolean",
                "description": "Set true to rebuild images (default true)",
            },
            "limit": {
                "type": "integer",
                "description": "Max records per entity to process (default 25, max 250)",
            },
        },
        "required": [],
    },
    tiers=[3, 4, 7, 8],
    requires_approval=False,
    crud_type="update",
    app_action_group="cache",
    app_action_label="Rebuild Cache",
)

