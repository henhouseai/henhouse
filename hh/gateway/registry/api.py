"""
Auto-generated API Wrapper Functions
This module dynamically generates boilerplate wrapper functions with @register_api decorators
based on the API tools from the tool registry.

The exec block contains @register_api decorators that will be discovered by the registry system
when this module is imported.
"""
from __future__ import annotations
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.gateway.registry.registry import register_api
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.registry.tool_whitelist import _global_tool_registry
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
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
def _api_wrapper_template(tool_name: str) -> bool:
    """Boilerplate API wrapper - passes through action_response."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway or response available")
        return trace_out(False)
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        return trace_out(False)
    # action_response is already set, ResponseAPI.get_output() will handle serialization
    log(f"API backend {tool_name} confirmed action_response available")
    return trace_out(True)

# Dynamically generate wrapper functions with @register_api decorators using exec
# This exec block will be discovered by the registry system when this module is imported
# Get all tools that have api_tiers defined
_wrapper_code = ""
all_tools: set[str] = set()

# Scan _global_tool_registry for tools with api_tiers
for tool_name, tool_config in _global_tool_registry.items():
    api_tier_levels = tool_config.get('api_tiers', [])
    if api_tier_levels:
        all_tools.add(tool_name)

for tool_name in all_tools:
    # Convert tool_name to valid Python function name (replace hyphens with underscores)
    func_name = tool_name.replace('-', '_')
    _wrapper_code += f"""
@register_api('{tool_name}')
def {func_name}() -> bool:
    \"\"\"API wrapper for {tool_name}.\"\"\"
    return _api_wrapper_template('{tool_name}')
"""

exec(_wrapper_code)

