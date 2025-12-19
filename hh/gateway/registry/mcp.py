"""
Auto-generated MCP Wrapper Functions
This module dynamically generates boilerplate wrapper functions with @register_mcp decorators
based on the MCP_TOOLS_WHITELIST.

The exec block contains @register_mcp decorators that will be discovered by the registry system
when this module is imported.
"""
from __future__ import annotations
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.gateway.registry.registry import register_mcp
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.registry.mcp_whitelist import MCPWhitelist
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)

# Boilerplate wrapper function template
def _mcp_wrapper_template(tool_name: str) -> bool:
    """Boilerplate MCP wrapper - passes through action_response."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway or response available")
        trace_out()
        return False
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False
    # action_response is already set, ResponseMCP.get_output() will handle serialization
    log(f"MCP backend {tool_name} confirmed action_response available")
    trace_out()
    return True

# Dynamically generate wrapper functions with @register_mcp decorators using exec
# This exec block will be discovered by the registry system when this module is imported
# Get all tools from all tiers to generate wrappers
_wrapper_code = ""
all_tools: set[str] = set()
for tier in HENHOUSE_TIERS:
    try:
        tier_whitelist = MCPWhitelist._load_tier_whitelist(tier)
        all_tools.update(tier_whitelist.keys())
    except Exception as e:
        warn(f"Error loading {tier} whitelist for wrapper generation: {e}")

for tool_name in all_tools:
    # Convert tool_name to valid Python function name (replace hyphens with underscores)
    func_name = tool_name.replace('-', '_')
    _wrapper_code += f"""
@register_mcp('{tool_name}')
def {func_name}() -> bool:
    \"\"\"MCP wrapper for {tool_name}.\"\"\"
    return _mcp_wrapper_template('{tool_name}')
"""

exec(_wrapper_code)


