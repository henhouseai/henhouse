"""Backend List - Lists all registered backend types"""
from __future__ import annotations
from typing import Dict, Any
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.registry import register_command, register_action, register_parser, BACKEND_TYPES
from hh.gateway.gateway import get_gateway
from hh.gateway.error.error_store import report_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.render.render import render_header_block, finalize_output
from hh.render.config.config import break_section
from hh.gateway.response.json_standard import get_data
from hh.gateway.registry.utils import CommandListData, render_section

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

@register_action("backend_list")
@register_command("backend_list")
def backend_list() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        return trace_out(False)
    try:
        current_backend = gateway.backend
        backend_list_items = list(BACKEND_TYPES)
        log(f"Listing {len(backend_list_items)} registered backends")
        data: Dict[str, Any] = {
            "type": "backend_list",
            "count": len(backend_list_items),
            "backends": []
        }
        backends_list = data["backends"]
        assert isinstance(backends_list, list), "backends should be a list"
        for backend_name in sorted(backend_list_items):
            is_loaded = backend_name == current_backend
            backends_list.append({
                "name": backend_name,
                "module_path": f"hh.gateway.registry.{backend_name}",
                "is_loaded": is_loaded
            })
        backends_list = data.get('backends', [])
        backends_count = len(backends_list) if isinstance(backends_list, list) else 0
        log(f"Successfully created backend list with {backends_count} backends (current: {current_backend})")
        gateway.response.set_action_response(success_payload(data))
        return trace_out(True)
    except Exception as e:
        warn("Backend list failed.")
        report_error("action", f"Failed to list backends: {str(e)}")
        return trace_out(False)

@register_parser('backend_list')
def parse_backend_list() -> bool:
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
    json_data = gateway.response.get_action_response()
    try:
        lines = []
        lines.append(render_header_block('l_backend_list_header'))
        source_data = get_data(json_data) if json_data is not None else {}
        # Type cast to CommandListData for type checker
        command_list_data: CommandListData = source_data  # type: ignore[assignment]
        if not render_section(command_list_data, lines):
            warn("Failed to render backends section")
            report_error("backend", "Failed to render backends section")
            trace_out()
            return False
        break_section(lines)
        result = finalize_output(lines)
        if len(result) == 0:
            warn("Backend response is empty")
        gateway.response.add_output(result)
        log(f"Parser execution completed successfully with {len(result)} lines.")
        trace_out()
        return True
    except Exception as e:
        warn("Parser execution raised an exception.")
        report_error("backend", f"Parser execution raised an exception: {e}")
        trace_out()
        return False
