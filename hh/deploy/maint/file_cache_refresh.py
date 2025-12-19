"""File cache refresh module for maintenance daemon."""

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
from hh.file.file_registry import get_file
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


def fetch_stale_file_id() -> int | None:
    """Fetch one stale file ID from main database only.
    Staleness determined by: COALESCE(last_modified, uploaded) > cache_built_at OR cache_built_at IS NULL"""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return None
    rows = gateway.conn.read(
        """
        SELECT id
        FROM files
        WHERE COALESCE(last_modified, uploaded) > cache_built_at
           OR cache_built_at IS NULL
        ORDER BY COALESCE(last_modified, uploaded) DESC
        LIMIT 1
        """,
    )
    return rows[0]["id"] if rows else None


def count_stale_files() -> int:
    """Count stale files in main database only."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return 0
    rows = gateway.conn.read(
        """
        SELECT COUNT(*) AS cnt
        FROM files
        WHERE COALESCE(last_modified, uploaded) > cache_built_at
           OR cache_built_at IS NULL
        """,
    )
    return rows[0]["cnt"] if rows else 0


def rebuild_file(file_id: int) -> dict[str, Any] | None:
    """Rebuild cache for a single file ID. Returns error dict if failed, None if successful."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return {"entity": "file", "id": file_id, "error": "No gateway or connection available"}
    
    try:
        # Verify file exists first
        verify = gateway.conn.read("SELECT id, file_name FROM files WHERE id = %s", [file_id])
        if not verify:
            error_msg = f"File {file_id} does not exist in database"
            warn(error_msg)
            return {"entity": "file", "id": file_id, "error": error_msg}
        
        file_info = verify[0]
        file_name = file_info.get('file_name', 'unnamed')
        
        file_obj = get_file(file_id)
        if not file_obj:
            error_msg = f"File {file_id} (name={file_name}) could not be loaded"
            if is_error():
                errs = get_errors()
                if errs:
                    error_contents = [f"{e.error_type.value}: {e.content}" for e in errs]
                    error_msg = f"{error_msg}. Errors: {'; '.join(error_contents)}"
            warn(error_msg)
            return {"entity": "file", "id": file_id, "error": error_msg}
        
        file_obj.get_usage_data()
        log(f"Successfully cached file {file_id} (name={file_name})")
        return None
    except Exception as exc:  # noqa: BLE001
        error_msg = f"Exception while caching file {file_id}: {type(exc).__name__}: {exc}"
        warn(error_msg)
        return {"entity": "file", "id": file_id, "error": error_msg}


@register_action("file_cache_refresh")
@register_command("file_cache_refresh")
def file_cache_refresh_action() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return False

    try:
        stale_file_id = fetch_stale_file_id()
        if stale_file_id is None:
            # No stale files to process
            payload = {
                "operation": "rebuild_file_cache",
                "file_id": None,
                "processed": False,
                "error": None,
                "files_remaining": 0,
            }
            gateway.response.set_action_response(success_payload(payload))
            log("No stale files to process")
            trace_out()
            return True

        log(f"Processing stale file {stale_file_id}")
        error = rebuild_file(stale_file_id)
        files_remaining = count_stale_files()

        error_msg: str | None = error.get("error") if error and isinstance(error, dict) else None
        payload = {
            "operation": "rebuild_file_cache",
            "file_id": stale_file_id,
            "processed": error is None,
            "error": error_msg,
            "files_remaining": files_remaining,
        }
        gateway.response.set_action_response(success_payload(payload))
        if error:
            log(f"File cache refresh failed for file {stale_file_id}: {error.get('error', 'Unknown error')}")
        else:
            log(f"File cache refresh completed for file {stale_file_id}, {files_remaining} remaining")
        trace_out()
        return not is_error()
    except Exception as exc:  # noqa: BLE001
        warn(f"Failed to refresh file cache: {exc}")
        report_error("action", f"Failed to refresh file cache: {exc}")
        trace_out()
        return False


@register_parser("file_cache_refresh")
def file_cache_refresh_parser() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("backend", "No gateway available")
        trace_out()
        return False
    if not gateway.response or not gateway.response.has_action_response():
        warn("No action response available")
        report_error("backend", "No action response available")
        trace_out()
        return False

    try:
        json_data = gateway.response.get_action_response()
        source_data = get_data(json_data) if json_data else {}
        file_id = source_data.get("file_id")
        processed = source_data.get("processed", False)
        error = source_data.get("error")
        files_remaining = source_data.get("files_remaining", 0)

        lines = [render_header_block("l_file_cache_refresh_header")]

        table = TableData()
        has_remaining = files_remaining > 0
        
        # Add header row (visual anchor)
        table.add_row(
            "file_cache_refresh_header",
            info="",
        )
        
        if file_id is None:
            # No stale files
            table.add_row(
                "no_stale_files",
                info="No files need cache refresh",
            )
        else:
            # File ID row
            table.add_row(
                "file_cache_file_id",
                info=str(file_id),
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
                    "file_cache_error",
                    info=error_msg,
                )
            
            # Remaining files row (only if there are remaining)
            if has_remaining:
                table.add_row(
                    "file_cache_refresh_remaining",
                    info=str(files_remaining),
                )

        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("file_cache_refresh_header")
                .add_simple(["no_stale_files", "file_cache_file_id", "refresh_status", "file_cache_refresh_remaining"])
                .add_simple_color("file_cache_error", "red"),
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


register_maintenance_tool("file_cache_refresh")
