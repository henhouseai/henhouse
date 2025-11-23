from __future__ import annotations

from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.gateway.error.error_store import is_error
from hh.page.page import Page
from hh.page.page_class_registry import register_page_class
from hh.mcp_action_request.mcp_action_request_content import (
    McpActionRequestContentMixin,
)
from hh.mcp_action_request.mcp_action_request_validation import (
    McpActionRequestValidationMixin,
)


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


@register_page_class('mcp_action')
class McpActionRequest(McpActionRequestValidationMixin, McpActionRequestContentMixin, Page):
    def __init__(self, id: int):
        # Call parent constructor (Page handles gateway, DB load, cache hydration, and automatically extracts metadata fields as attributes)
        super().__init__(id)

