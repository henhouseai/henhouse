from __future__ import annotations
from typing import List, Dict

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


@register_action("move_files")
@register_command("move_files")
def move_files() -> bool:
    """
    Move files from a source page to a target page.
    Supports optional comma-separated source_rank filter and optional target_rank insertion point.
    """
    trace_in()
    gateway = get_gateway()
    # Required arguments
    if not gateway.is_set("source_page") and not gateway.is_set("s_page"):
        warn("No source page ID provided")
        report_error("action", "Source page ID is required")
    if not is_error():
        if not gateway.is_set("target_page") and not gateway.is_set("t_page"):
            warn("No target page ID provided")
            report_error("action", "Target page ID is required")

    source_page_id: int = 0
    target_page_id: int = 0
    if not is_error():
        source_page_arg = gateway.get_arg("source_page") or gateway.get_arg("s_page")
        target_page_arg = gateway.get_arg("target_page") or gateway.get_arg("t_page")
        source_ranks_str = gateway.get_arg("source_rank") or gateway.get_arg("s_rank")
        target_rank_arg = gateway.get_arg("target_rank") or gateway.get_arg("t_rank")
        try:
            source_page_id = int(source_page_arg)
            target_page_id = int(target_page_arg)
        except (TypeError, ValueError):
            warn(f"Invalid IDs provided. Source: {source_page_arg}, Target: {target_page_arg}")
            report_error("action", "All IDs must be numbers")

    target_rank_int: int | None = None
    if not is_error() and target_rank_arg:
        try:
            target_rank_int = int(target_rank_arg)
            if target_rank_int <= 0:
                raise ValueError()
        except ValueError:
            warn(f"Invalid target rank: {target_rank_arg}")
            report_error("action", "Target rank must be a positive number")

    # Load pages
    source_page = None
    if not is_error():
        source_page = get_page(page_id=source_page_id)
        if not source_page:
            warn(f"Source page {source_page_id} not found")
            report_error("action", f"Source page {source_page_id} not found")
    target_page = None
    if not is_error():
        target_page = get_page(page_id=target_page_id)
        if not target_page:
            warn(f"Target page {target_page_id} not found")
            report_error("action", f"Target page {target_page_id} not found")

    # Determine file instances to move
    file_instances: List[Dict[str, int | None]] = []
    source_ranks: List[int] = []
    if not is_error() and source_page is not None:
        files = source_page.get_files_data()
        if source_ranks_str:
            try:
                source_ranks = [int(rank.strip()) for rank in source_ranks_str.split(",") if rank.strip()]
                if not source_ranks:
                    raise ValueError()
            except ValueError:
                warn(f"Invalid source ranks format: {source_ranks_str}")
                report_error("action", "Source ranks must be comma-separated numbers")
            if not is_error():
                for rank in source_ranks:
                    match = next((f for f in files if f.get("file_rank") == rank), None)
                    if not match:
                        warn(f"File not found at rank {rank} in source page {source_page_id}")
                        report_error("action", f"File not found at rank {rank} in source page {source_page_id}")
                        break
                    file_instances.append(
                        {
                            "file_id": match["id"],
                            "source_page_id": source_page_id,
                            "source_rank": rank,
                        }
                    )
        else:
            for f in files:
                file_instances.append(
                    {
                        "file_id": f["id"],
                        "source_page_id": source_page_id,
                        "source_rank": f.get("file_rank"),
                    }
                )

    if not is_error() and not file_instances:
        warn("No files to move")
        report_error("action", "No files to move")

    # Perform move
    if not is_error() and target_page is not None:
        log(f"Moving {len(file_instances)} files from page {source_page_id} to page {target_page_id}")
        success = target_page.move_media_items("file", file_instances, target_rank=target_rank_int)
        if not success:
            warn(f"Failed to move files from page {source_page_id} to page {target_page_id}")
            report_error("action", f"Failed to move files from page {source_page_id} to page {target_page_id}")

    # Reload target page and respond
    updated_page = None
    if not is_error():
        updated_page = get_page(page_id=target_page_id)
        if not updated_page:
            warn(f"Failed to reload target page {target_page_id}")
            report_error("action", f"Failed to reload target page {target_page_id}")

    if not is_error() and updated_page is not None:
        response_data = updated_page.show_page()
        response_data.update(
            {
                "moved_count": len(file_instances),
                "source_page_id": source_page_id,
                "target_page_id": target_page_id,
                "operation": "move_files",
            }
        )
        if source_ranks_str:
            response_data["source_ranks"] = source_ranks
        else:
            response_data["move_type"] = "all_files"
        if target_rank_int is not None:
            response_data["target_rank"] = target_rank_int
        gateway.response.set_action_response(success_payload(response_data))

    trace_out()
    return not is_error()


