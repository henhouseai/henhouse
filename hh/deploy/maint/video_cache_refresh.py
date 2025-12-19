"""Video cache refresh module for maintenance daemon."""

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


def fetch_stale_video_id() -> int | None:
    """Fetch one stale video ID from main database only.
    Staleness determined by: COALESCE(last_modified, uploaded) > cache_built_at OR cache_built_at IS NULL"""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return None
    rows = gateway.conn.read(
        """
        SELECT id
        FROM video
        WHERE COALESCE(last_modified, uploaded) > cache_built_at
           OR cache_built_at IS NULL
        ORDER BY COALESCE(last_modified, uploaded) DESC
        LIMIT 1
        """,
    )
    return rows[0]["id"] if rows else None


def count_stale_video() -> int:
    """Count stale video in main database only."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return 0
    rows = gateway.conn.read(
        """
        SELECT COUNT(*) AS cnt
        FROM video
        WHERE COALESCE(last_modified, uploaded) > cache_built_at
           OR cache_built_at IS NULL
        """,
    )
    return rows[0]["cnt"] if rows else 0


def rebuild_video(video_id: int) -> dict[str, Any] | None:
    """Rebuild cache for a single video ID. Returns error dict if failed, None if successful."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return {"entity": "video", "id": video_id, "error": "No gateway or connection available"}
    
    try:
        # Verify video exists first
        verify = gateway.conn.read("SELECT id, caption FROM video WHERE id = %s", [video_id])
        if not verify:
            error_msg = f"Video {video_id} does not exist in database"
            warn(error_msg)
            return {"entity": "video", "id": video_id, "error": error_msg}
        
        video_info = verify[0]
        video_caption = video_info.get('caption', 'no caption')
        
        from hh.video.video_registry import get_video
        video_obj = get_video(video_id)
        if not video_obj:
            error_msg = f"Video {video_id} (caption={video_caption}) could not be loaded"
            if is_error():
                errs = get_errors()
                if errs:
                    error_contents = [f"{e.error_type.value}: {e.content}" for e in errs]
                    error_msg = f"{error_msg}. Errors: {'; '.join(error_contents)}"
            warn(error_msg)
            return {"entity": "video", "id": video_id, "error": error_msg}
        
        video_obj.show_video()
        log(f"Successfully cached video {video_id} (caption={video_caption})")
        return None
    except Exception as exc:  # noqa: BLE001
        error_msg = f"Exception while caching video {video_id}: {type(exc).__name__}: {exc}"
        warn(error_msg)
        return {"entity": "video", "id": video_id, "error": error_msg}


@register_action("video_cache_refresh")
@register_command("video_cache_refresh")
def video_cache_refresh_action() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return False

    try:
        stale_video_id = fetch_stale_video_id()
        if stale_video_id is None:
            # No stale video to process
            payload = {
                "operation": "rebuild_video_cache",
                "video_id": None,
                "processed": False,
                "error": None,
                "video_remaining": 0,
            }
            gateway.response.set_action_response(success_payload(payload))
            log("No stale video to process")
            trace_out()
            return True

        log(f"Processing stale video {stale_video_id}")
        error = rebuild_video(stale_video_id)
        video_remaining = count_stale_video()

        error_msg: str | None = error.get("error") if error and isinstance(error, dict) else None
        payload = {
            "operation": "rebuild_video_cache",
            "video_id": stale_video_id,
            "processed": error is None,
            "error": error_msg,
            "video_remaining": video_remaining,
        }
        gateway.response.set_action_response(success_payload(payload))
        if error:
            log(f"Video cache refresh failed for video {stale_video_id}: {error.get('error', 'Unknown error')}")
        else:
            log(f"Video cache refresh completed for video {stale_video_id}, {video_remaining} remaining")
        trace_out()
        return not is_error()
    except Exception as exc:  # noqa: BLE001
        warn(f"Failed to refresh video cache: {exc}")
        report_error("action", f"Failed to refresh video cache: {exc}")
        trace_out()
        return False


@register_parser("video_cache_refresh")
def video_cache_refresh_parser() -> bool:
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
        json_data = gateway.response.get_action_response()
        source_data = get_data(json_data if json_data is not None else {})
        video_id = source_data.get("video_id")
        processed = source_data.get("processed", False)
        error = source_data.get("error")
        video_remaining = source_data.get("video_remaining", 0)

        lines = [render_header_block("l_video_cache_refresh_header")]

        table = TableData()
        has_remaining = video_remaining > 0
        
        # Add header row (visual anchor)
        table.add_row(
            "video_cache_refresh_header",
            info="",
        )
        
        if video_id is None:
            # No stale video
            table.add_row(
                "no_stale_video",
                info="No video need cache refresh",
            )
        else:
            # Video ID row
            table.add_row(
                "video_cache_video_id",
                info=str(video_id),
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
                    "video_cache_error",
                    info=error_msg,
                )
            
            # Remaining video row (only if there are remaining)
            if has_remaining:
                table.add_row(
                    "video_cache_refresh_remaining",
                    info=str(video_remaining),
                )

        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("video_cache_refresh_header")
                .add_simple(["no_stale_video", "video_cache_video_id", "refresh_status", "video_cache_refresh_remaining"])
                .add_simple_color("video_cache_error", "red"),
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


register_maintenance_tool("video_cache_refresh")
