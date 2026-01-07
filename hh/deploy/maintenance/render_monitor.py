"""Monitor command parser backend - no-op since process gets replaced."""

from hh.gateway.registry.registry import register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
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


@register_parser("monitor")
def monitor() -> bool:
    """Monitor parser backend - this should never be called since os.execvp() replaces the process."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in monitor parser")
        trace_out()
        return False

    # This parser should never execute because the monitor action uses os.execvp()
    # to replace the current process with the monitor.sh script. If we get here,
    # something went wrong with the process replacement.
    warn("Monitor parser executed - this should not happen (process replacement failed)")
    report_error("backend", "Monitor parser executed unexpectedly - process replacement may have failed")

    # Add minimal output in case something went wrong
    gateway.response.add_output("Monitor session launch failed - check error logs\n")
    trace_out()
    return False