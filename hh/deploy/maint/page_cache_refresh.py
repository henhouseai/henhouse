"""Page cache refresh module for maintenance daemon."""

from __future__ import annotations

from typing import Any

from hh.gateway.error.error_store import get_errors, is_error, report_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import (
    get_debug,
    get_log,
    get_trace_in,
    get_trace_out,
    get_warn,
    register_debug_init,
)
from hh.gateway.registry.maintenance import register_maintenance_tool
from hh.gateway.registry.registry import (
    register_action,
    register_command,
    register_parser,
)
from hh.gateway.response.json_standard import get_data, success_payload
from hh.page.page_registry import get_page
from hh.render.render import (
    FieldConfig,
    TableData,
    finalize_output,
    render_block,
    render_header_block,
)

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message=None: None


@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


def fetch_stale_page_id() -> int | None:
    """Fetch one stale page ID from main database only.
    Staleness determined by: last_modified > cache_built_at OR cache_built_at IS NULL"""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return None
    rows = gateway.conn.read(
        """
        SELECT id
        FROM pages
        WHERE last_modified > cache_built_at
           OR cache_built_at IS NULL
        ORDER BY last_modified DESC
        LIMIT 1
        """,
    )
    return rows[0]["id"] if rows else None


def count_stale_pages() -> int:
    """Count stale pages in main database only."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return 0
    rows = gateway.conn.read(
        """
        SELECT COUNT(*) AS cnt
        FROM pages
        WHERE last_modified > cache_built_at
           OR cache_built_at IS NULL
        """,
    )
    return rows[0]["cnt"] if rows else 0


def rebuild_page(page_id: int) -> dict[str, Any] | None:
    """Rebuild cache for a single page ID. Returns error dict if failed, None if successful."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return {"entity": "page", "id": page_id, "error": "No gateway or connection available"}
    
    try:
        # Verify page exists first
        verify = gateway.conn.read("SELECT id, class, name FROM pages WHERE id = %s", [page_id])
        if not verify:
            error_msg = f"Page {page_id} does not exist in database"
            warn(error_msg)
            return {"entity": "page", "id": page_id, "error": error_msg}
        
        page_info = verify[0]
        page_class = page_info.get('class', 'unknown')
        page_name = page_info.get('name', 'unnamed')
        
        page_obj = get_page(page_id)
        if not page_obj:
            error_msg = f"Page {page_id} (class={page_class}, name={page_name}) could not be loaded"
            if is_error():
                errs = get_errors()
                if errs:
                    error_contents = [f"{e.error_type.value}: {e.content}" for e in errs]
                    error_msg = f"{error_msg}. Errors: {'; '.join(error_contents)}"
            warn(error_msg)
            return {"entity": "page", "id": page_id, "error": error_msg}
        
        page_obj.show_page()
        log(f"Successfully cached page {page_id} (class={page_class}, name={page_name})")
        return None
    except Exception as exc:  # noqa: BLE001
        error_msg = f"Exception while caching page {page_id}: {type(exc).__name__}: {exc}"
        warn(error_msg)
        return {"entity": "page", "id": page_id, "error": error_msg}


@register_action("page_cache_refresh")
@register_command("page_cache_refresh")
def page_cache_refresh_action() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return False

    try:
        stale_page_id = fetch_stale_page_id()
        if stale_page_id is None:
            # No stale pages to process
            payload = {
                "operation": "rebuild_page_cache",
                "page_id": None,
                "processed": False,
                "error": None,
                "pages_remaining": 0,
            }
            gateway.response.set_action_response(success_payload(payload))
            log("No stale pages to process")
            trace_out()
            return True

        log(f"Processing stale page {stale_page_id}")
        error = rebuild_page(stale_page_id)
        pages_remaining = count_stale_pages()

        payload = {
            "operation": "rebuild_page_cache",
            "page_id": stale_page_id,
            "processed": error is None,
            "error": error,
            "pages_remaining": pages_remaining,
        }
        gateway.response.set_action_response(success_payload(payload))
        if error:
            log(f"Page cache refresh failed for page {stale_page_id}: {error.get('error', 'Unknown error')}")
        else:
            log(f"Page cache refresh completed for page {stale_page_id}, {pages_remaining} remaining")
        trace_out()
        return not is_error()
    except Exception as exc:  # noqa: BLE001
        warn(f"Failed to refresh page cache: {exc}")
        report_error("action", f"Failed to refresh page cache: {exc}")
        trace_out()
        return False


@register_parser("page_cache_refresh")
def page_cache_refresh_parser() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("backend", "No gateway available")
        trace_out()
        return False
    if not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    try:
        source_data = get_data(gateway.response.get_action_response())
        page_id = source_data.get("page_id")
        processed = source_data.get("processed", False)
        error = source_data.get("error")
        pages_remaining = source_data.get("pages_remaining", 0)

        lines = [render_header_block("l_page_cache_refresh_header")]

        table = TableData()
        has_remaining = pages_remaining > 0
        
        # Add header row (visual anchor)
        table.add_row(
            "page_cache_refresh_header",
            info="",
        )
        
        if page_id is None:
            # No stale pages
            table.add_row(
                "no_stale_pages",
                info="No pages need cache refresh",
            )
        else:
            # Page ID row
            table.add_row(
                "page_id",
                info=str(page_id),
            )
            
            if processed:
                # Refresh status row
                table.add_row(
                    "refresh_status",
                    info="Success",
                )
            else:
                # Error row
                error_msg = error.get("error", "Unknown error") if error else "Unknown error"
                table.add_row(
                    "page_cache_error",
                    info=error_msg,
                )
            
            # Remaining pages row (only if there are remaining)
            if has_remaining:
                table.add_row(
                    "page_cache_refresh_remaining",
                    info=str(pages_remaining),
                )

        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("page_cache_refresh_header")
                .add_simple(["no_stale_pages", "page_id", "refresh_status", "page_cache_refresh_remaining"])
                .add_simple_color("page_cache_error", "red"),
                block_type="maintenance",
                table_overrides={"margin_l": 4},
            )
        )

        gateway.response.add_output(finalize_output(lines))
        log(f"Parser execution completed successfully with {len(lines)} lines")
        trace_out()
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"Parser execution raised an exception: {exc}")
        report_error("backend", f"Parser execution raised an exception: {exc}")
        trace_out()
        return False


register_maintenance_tool("page_cache_refresh")

