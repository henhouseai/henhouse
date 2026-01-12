from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload, get_data
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page
from hh.render.render import (
    FieldConfig,
    TableData,
    finalize_output,
    render_block,
    render_header_block,
)
from hh.work.work_page import _format_relative_time

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

@register_action('modify_work_status')
@register_command('modify_work_status')
def modify_work_status() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_set('page_id') and not gateway.is_set('id'):
        warn("No page ID provided")
        report_error("action", "Page ID is required")
    if not is_error():
        if not gateway.is_set('status'):
            warn("No new status provided")
            report_error("action", "New status is required")
    if not is_error():
        page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
        new_status = gateway.get_arg('status')
        # Handle the case where -status is passed as a flag (returns True)
        if new_status is True:
            new_status = ""
        # Validate status enum
        valid_statuses = ['todo', 'doing', 'review', 'done']
        if new_status not in valid_statuses:
            warn(f"Invalid status: {new_status}")
            report_error("action", f"Status must be one of: {', '.join(valid_statuses)}")
        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
    if not is_error():
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
    if not is_error():
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    if not is_error():
        log(f"Modifying page {page_id} status to '{new_status}'")
        if page:
            old_status = getattr(page, 'status', None)  # Capture old status for response
            success = page.modify_work_status(new_status)
            if not success:
                warn("Page status modification failed")
                report_error("action", "Page status modification failed")
            # Build simple status response instead of full page data
            response_data = {
                "page_id": page_id,
                "old_status": old_status,
                "new_status": new_status,
                "success": success,
                "work_sort_order": getattr(page, 'sort_order', None),  # Current sort order
                "work_started_ts": getattr(page, 'started_ts', None),  # When work started
                "work_ended_ts": getattr(page, 'ended_ts', None)  # When work ended
            }
            gateway.response.set_action_response(success_payload(response_data))
            log(f"Successfully modified page {page_id} status from '{old_status}' to '{new_status}'")
    trace_out()
    return not is_error()


@register_parser('modify_work_status')
def parser_modify_work_status() -> bool:
    """
    Dedicated parser for modify_work_status action.
    Shows work status change in a clean, simple format.
    """
    trace_in()
    gateway = get_gateway()

    if not gateway:
        warn("No gateway available")
        report_error("backend", "No gateway available")
        return trace_out(False)

    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        return trace_out(False)

    try:
        json_data = gateway.response.get_action_response()
        source_data = get_data(json_data) if json_data and isinstance(json_data, dict) else {}

        lines = [render_header_block("l_modify_work_status_header")]

        # Main status table
        table = TableData()
        table.add_row("page_id", value=str(source_data.get("page_id", "")))
        table.add_row("work_status_old_status", value=source_data.get("old_status", ""))
        table.add_row("work_status_new_status", value=source_data.get("new_status", ""))
        table.add_row("work_status_success", value=str(source_data.get("success", False)))

        # Current work status information
        table.add_row("page_sort_order", value=str(source_data.get("work_sort_order", 0)))

        # Add timestamp information if available
        if source_data.get("work_started_ts"):
            table.add_row("page_started_ts", value=_format_relative_time(source_data["work_started_ts"]))
        if source_data.get("work_ended_ts"):
            table.add_row("page_ended_ts", value=_format_relative_time(source_data["work_ended_ts"]))

        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_simple([
                    "page_id", "work_status_old_status", "work_status_new_status", "work_status_success",
                    "page_sort_order", "page_started_ts", "page_ended_ts"
                ]),
                block_type="work_status",
                table_overrides={"margin_l": 4},
            )
        )

        gateway.response.add_output(finalize_output(lines))
        log(f"Parser execution completed successfully with {len(lines)} lines")
        return trace_out(True)

    except Exception as exc:  # noqa: BLE001
        warn(f"Parser execution raised an exception: {exc}")
        report_error("backend", f"Parser execution raised an exception: {exc}")
        return trace_out(False)

