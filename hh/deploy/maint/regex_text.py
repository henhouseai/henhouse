from __future__ import annotations

from typing import Optional

from hh.deploy.maint.job_queue import update_maintenance_job
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
    if not page_id_arg:
        report_error("request", "Missing required argument: page_id")
    else:
        try:
            page_id = int(page_id_arg)
            if page_id <= 0:
                report_error("request", f"Invalid page_id: {page_id} (must be > 0)")
                page_id = None
        except (ValueError, TypeError):
            report_error("request", f"Invalid page_id: {page_id_arg}")
            page_id = None
    
    old_name = gateway.get_arg("old_name")
    new_name = gateway.get_arg("new_name")
    
    last_page_id_arg = gateway.get_arg("last_page_id") or "0"
    try:
        last_page_id = int(last_page_id_arg)
        if last_page_id < 0:
            report_error("request", f"Invalid last_page_id: {last_page_id} (must be >= 0)")
            last_page_id = 0
    except (ValueError, TypeError):
        last_page_id = 0
    
    batch_limit_arg = gateway.get_arg("batch_limit") or "25"
    try:
        batch_limit = int(batch_limit_arg)
        if batch_limit <= 0:
            batch_limit = 25
    except (ValueError, TypeError):
        batch_limit = 25

    if not old_name or not new_name:
        report_error("request", "Both old_name and new_name are required")

    job_id = gateway.get_arg("job_id")

    if is_error():
        trace_out()
        return False

    log(f"Loading page {page_id} for maintenance name change")
    page_obj = get_page(page_id=page_id)
    if not page_obj:
        warn(f"Page {page_id} could not be loaded")
        report_error("registry", f"Page {page_id} could not be loaded")
        trace_out()
        return False

    log(f"Processing name change: {old_name} -> {new_name} (last_page_id={last_page_id}, batch_limit={batch_limit})")
    result = page_obj.maintenance_process_name_change(
        old_name=old_name,
        new_name=new_name,
        last_page_id=last_page_id,
        batch_limit=batch_limit,
    )

    if job_id and (result["processed"] or result["done"]):
        log(f"Updating maintenance job {job_id}: processed={result.get('processed')}, done={result.get('done')}")
        update_maintenance_job(
            job_id=int(job_id),
            status="done" if result["done"] else "running",
            progress=result,
        )

    gateway.response.set_action_response(
        success_payload(
            {
                "operation": "regex_text",
                "page_id": page_id,
                "old_name": old_name,
                "new_name": new_name,
                "result": result,
            }
        )
    )
    log(f"Maintenance name change completed: processed={result.get('processed')}, done={result.get('done')}")
    trace_out()
    return not is_error()


register_maintenance_tool("regex_text")

