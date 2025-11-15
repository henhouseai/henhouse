from __future__ import annotations
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_mcp_request_validation_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


class McpRequestValidationMixin:
    
    @classmethod
    def allow_null_names(cls) -> bool:
        """MCP requests allow null names."""
        return True
    
    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """MCP requests allow duplicate names."""
        return True
    
    @classmethod
    def auto_link_name(cls) -> bool:
        """MCP requests do not auto-link names."""
        return False
    
    def allow_class_inside(self, target_class: str) -> bool:
        """MCP requests can contain pages or mcp_action_request."""
        return target_class in ('page', 'mcp_action_request')
    
    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """MCP requests can only be inside pages."""
        return parent_class == 'page'

