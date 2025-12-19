from __future__ import annotations

from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page

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


@register_action("set_file_rank")
@register_command("set_file_rank")
def set_file_rank() -> bool:
    """
    Change the rank/position of a file within a page.
    """
    trace_in()
    gateway = get_gateway()
    # Required args
    if not gateway.is_set("page_id") and not gateway.is_set("id"):
        warn("No page ID provided")
        report_error("action", "Page ID is required")
    if not is_error():
        if not gateway.is_set("file_id"):
            warn("No file ID provided")
            report_error("action", "File ID is required")
    if not is_error():
        if not gateway.is_set("target_rank") and not gateway.is_set("t_rank"):
            warn("No target rank provided")
            report_error("action", "Target rank is required")

    page_id: int = 0
    file_id: int = 0
    target_rank: int = 0
    if not is_error():
        page_id_arg = gateway.get_arg("page_id") or gateway.get_arg("id")
        file_id_arg = gateway.get_arg("file_id")
        target_rank_arg = gateway.get_arg("target_rank") or gateway.get_arg("t_rank")
        current_rank_arg = gateway.get_arg("source_rank") or gateway.get_arg("s_rank")
        try:
            page_id = int(page_id_arg)
            file_id = int(file_id_arg)
            target_rank = int(target_rank_arg)
            if target_rank <= 0:
                raise ValueError()
        except (TypeError, ValueError):
            warn(f"Invalid arguments: page_id={page_id_arg}, file_id={file_id_arg}, target_rank={target_rank_arg}")
            report_error("action", "page_id, file_id, and target_rank must be positive numbers")

    current_rank: int | None = None
    if not is_error() and current_rank_arg:
        try:
            current_rank = int(current_rank_arg)
        except ValueError:
            warn(f"Invalid source rank: {current_rank_arg}")
            report_error("action", "source_rank must be a number")

    # Load page
    page = None
    if not is_error():
        page = get_page(page_id=page_id)
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")

    # Perform rank update
    if not is_error() and page is not None:
        log(f"Setting file {file_id} rank to {target_rank} on page {page_id}")
        success = page.set_media_rank("file", file_id, current_rank or target_rank, target_rank)
        if not success:
            warn(f"Failed to set rank for file {file_id} on page {page_id}")
            report_error("action", f"Failed to set rank for file {file_id} on page {page_id}")

    # Reload page
    updated_page = None
    if not is_error():
        updated_page = get_page(page_id=page_id)
        if not updated_page:
            warn(f"Failed to reload page {page_id}")
            report_error("action", f"Failed to reload page {page_id}")

    if not is_error() and updated_page is not None:
        response_data = updated_page.show_page()
        response_data.update(
            {
                "file_id": file_id,
                "page_id": page_id,
                "target_rank": target_rank,
                "source_rank": current_rank,
                "operation": "set_file_rank",
            }
        )
        gateway.response.set_action_response(success_payload(response_data))

    trace_out()
    return not is_error()


