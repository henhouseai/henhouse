"""
Backend handler for migrate_legacy_work command.
"""

from __future__ import annotations
from hh.gateway.registry.registry import register_parser, register_http
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

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


@register_parser('migrate_legacy_work')
@register_http('migrate_legacy_work')
def render_migrate_legacy_work() -> bool:
    """Render migrate_legacy_work output."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False
    json_data = gateway.response.get_action_response()
    try:
        # For parser backend, just print the summary text
        if json_data and isinstance(json_data, dict) and 'summary' in json_data:
            gateway.response.add_output(json_data['summary'])
            log("Parser execution completed successfully")
        else:
            warn("No summary in action response")
            report_error("backend", "No summary in action response")
            trace_out()
            return False
        trace_out()
        return True
    except Exception as e:
        warn("Parser execution raised an exception")
        report_error("backend", f"Parser execution raised an exception: {e}")
        trace_out()
        return False
