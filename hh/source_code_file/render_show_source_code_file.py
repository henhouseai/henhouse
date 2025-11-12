from __future__ import annotations
from hh.gateway.registry.registry import register_parser, register_http
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.page.render_show_page import show_page

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

@register_http('modify_path')
@register_parser('modify_path')
@register_http('modify_language')
@register_parser('modify_language')
def show_source_code_file() -> bool:
    return show_page()

