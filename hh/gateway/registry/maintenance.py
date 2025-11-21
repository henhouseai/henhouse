"""Maintenance backend registry utilities."""

from __future__ import annotations

from typing import Set

from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.gateway.registry.registry import register_maintenance
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


def _maintenance_wrapper_template(tool_name: str) -> bool:
    """Shared backend wrapper: ensure action response exists for maintenance backend."""
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.response.has_action_response():
        report_error("backend", "No action response available")
        trace_out()
        return False
    log(f"Maintenance backend '{tool_name}' confirmed action response")
    trace_out()
    return True


_registered_tools: Set[str] = set()


def register_maintenance_tool(tool_name: str) -> None:
    """Register a maintenance backend handler using the shared wrapper."""
    if tool_name in _registered_tools:
        return

    @register_maintenance(tool_name)
    def _wrapper() -> bool:
        return _maintenance_wrapper_template(tool_name)

    _registered_tools.add(tool_name)

