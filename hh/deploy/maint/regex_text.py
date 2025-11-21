from __future__ import annotations

from typing import Optional

from hh.gateway.gateway import get_gateway
from hh.gateway.registry.maintenance import register_maintenance_tool
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.response.json_standard import success_payload
from hh.page.page_registry import get_page
from hh.gateway.error.error_store import report_error, is_error
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


@register_command("regex_text")
@register_action("regex_text")
def regex_text() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("request", "No gateway available")
        trace_out()
        return False

    page_id_arg = gateway.get_arg("page_id")
    page_id: Optional[int] = None
    if page_id_arg:
        try:
            page_id = int(page_id_arg)
            if page_id <= 0:
                report_error("request", f"Invalid page_id: {page_id} (must be > 0)")
                page_id = None
        except (ValueError, TypeError):
            report_error("request", f"Invalid page_id: {page_id_arg}")
            page_id = None

    resolution_id_arg = gateway.get_arg("resolution_id")
    resolution_id: Optional[int] = None
    if not resolution_id_arg:
        report_error("request", "Missing required argument: resolution_id")
    else:
        try:
            resolution_id = int(resolution_id_arg)
            if resolution_id <= 0:
                report_error("request", f"Invalid resolution_id: {resolution_id} (must be > 0)")
                resolution_id = None
        except (ValueError, TypeError):
            report_error("request", f"Invalid resolution_id: {resolution_id_arg}")
            resolution_id = None
    
    old_name = gateway.get_arg("old_name")
    new_name = gateway.get_arg("new_name")
    
    if not old_name or not new_name:
        report_error("request", "Both old_name and new_name are required")

    if resolution_id_arg and resolution_id is None:
        # error already recorded
        pass

    if is_error():
        trace_out()
        return False

    log(
        f"Loading resolution page {resolution_id} for maintenance rename "
        f"(source page={page_id}, {old_name} -> {new_name})"
    )
    page_obj = get_page(page_id=resolution_id)
    if not page_obj:
        warn(f"Page {resolution_id} could not be loaded")
        report_error("registry", f"Page {resolution_id} could not be loaded")
        trace_out()
        return False

    log(f"Processing maintenance rename for resolution page {resolution_id}")
    result = page_obj.regex_text(
        old_name=old_name,
        new_name=new_name,
    )

    gateway.response.set_action_response(
        success_payload(
            {
                "operation": "regex_text",
                "page_id": page_id,
                "resolution_id": resolution_id,
                "old_name": old_name,
                "new_name": new_name,
                "result": result,
            }
        )
    )
    log(
        f"Maintenance rename for resolution page {resolution_id} completed: "
        f"processed={result.get('processed')}, modified={result.get('modified')}"
    )
    trace_out()
    return not is_error()


register_maintenance_tool("regex_text")

