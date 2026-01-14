"""
MCP Tool Registrations for ExpenseCategory Operations

Registers expense category-related MCP tools with appropriate tier access:
- Write operations: admin and root only [3, 4]
- App actions: admin app and root app only [7, 8]
"""

from hh.gateway.registry.tool_whitelist import register_tool

def _expense_category_tools_registration():
    """Registration placeholder for all expense category-related MCP tools."""
    pass

