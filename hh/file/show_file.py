from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.file.file_registry import get_file

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

@register_action('show_file')
@register_command('show_file')
def show_file() -> bool:
    trace_in()
    gateway = get_gateway()
    file_id_arg = gateway.get_arg('id')
    if not file_id_arg:
        warn("No file ID provided")
        report_error("action", "File ID is required")
    file_id: int = 0
    if not is_error():
        try:
            file_id = int(file_id_arg)
        except ValueError:
            warn(f"Invalid file ID: {file_id_arg}")
            report_error("action", "File ID must be a number")
    file = None
    if not is_error():
        log(f"Loading file {file_id}")
        file = get_file(file_id=file_id)
        if not file:
            warn(f"File {file_id} not found")
            report_error("action", f"File {file_id} not found")
    if not is_error() and file is not None:
        # Get complete file display data using the unified show_file method
        response_data = file.show_file()
        gateway.response.set_action_response(success_payload(response_data))
        file_name = file.file_name if file.file_name is not None else "Unknown"
        log(f"Successfully loaded file {file_id}: {file_name}")
    trace_out()
    return not is_error()
