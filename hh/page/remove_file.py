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


@register_action("remove_file")
@register_command("remove_file")
def remove_file() -> bool:
    """
    Remove a file instance from a page. If rank is omitted, removes all instances for that file on the page.
    """
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    if not gateway.is_set("page_id") and not gateway.is_set("id"):
        warn("No page ID provided")
        report_error("action", "Page ID is required")
    if not is_error():
        if not gateway.is_set("file_id"):
            warn("No file ID provided")
            report_error("action", "File ID is required")

    if not is_error():
        page_id_arg = gateway.get_arg("page_id") or gateway.get_arg("id")
        file_id_arg = gateway.get_arg("file_id")
        rank_arg = gateway.get_arg("rank")
        try:
            page_id = int(page_id_arg)
            file_id = int(file_id_arg)
        except (TypeError, ValueError):
            warn(f"Invalid IDs provided. Page: {page_id_arg}, File: {file_id_arg}")
            report_error("action", "IDs must be numbers")

    rank_int = None
    if not is_error() and rank_arg is not None:
        try:
            rank_int = int(rank_arg)
            if rank_int <= 0:
                raise ValueError()
        except ValueError:
            warn(f"Invalid rank: {rank_arg}")
            report_error("action", "Rank must be a positive number")

    # Load page
    if not is_error():
        page = get_page(page_id=page_id)
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")

    # Perform removal
    removed_count = 0
    if not is_error():
        if rank_int is not None:
            success = page.remove_file(file_id, rank_int)
            removed_count = 1 if success else 0
        else:
            # Remove all instances
            files = page.get_files_data()
            instances = [f for f in files if f.get("id") == file_id]
            for inst in instances:
                if is_error():
                    break
                rank_val = inst.get("file_rank")
                if rank_val is None:
                    continue
                if page.remove_file(file_id, rank_val):
                    removed_count += 1
            if not instances and not is_error():
                warn(f"No instances of file {file_id} found on page {page_id}")
                report_error("action", f"No instances of file {file_id} found on page {page_id}")

    # Reload page
    if not is_error():
        updated_page = get_page(page_id=page_id)
        if not updated_page:
            warn(f"Failed to reload page {page_id}")
            report_error("action", f"Failed to reload page {page_id}")

    if not is_error():
        response_data = updated_page.show_page()
        response_data.update(
            {
                "removed_count": removed_count,
                "file_id": file_id,
                "page_id": page_id,
                "operation": "remove_file",
            }
        )
        if rank_int is not None:
            response_data["rank"] = rank_int
        gateway.response.set_action_response(success_payload(response_data))

    trace_out()
    return not is_error()


