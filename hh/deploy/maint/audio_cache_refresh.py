"""Audio cache refresh module for maintenance daemon."""

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


def fetch_stale_audio_id() -> int | None:
    """Fetch one stale audio ID from main database only.
    Staleness determined by: COALESCE(last_modified, uploaded) > cache_built_at OR cache_built_at IS NULL"""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return None
    rows = gateway.conn.read(
        """
        SELECT id
        FROM audio
        WHERE COALESCE(last_modified, uploaded) > cache_built_at
           OR cache_built_at IS NULL
        ORDER BY COALESCE(last_modified, uploaded) DESC
        LIMIT 1
        """,
    )
    return rows[0]["id"] if rows else None


def count_stale_audio() -> int:
    """Count stale audio in main database only."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return 0
    rows = gateway.conn.read(
        """
        SELECT COUNT(*) AS cnt
        FROM audio
        WHERE COALESCE(last_modified, uploaded) > cache_built_at
           OR cache_built_at IS NULL
        """,
    )
    return rows[0]["cnt"] if rows else 0


def rebuild_audio(audio_id: int) -> dict[str, Any] | None:
    """Rebuild cache for a single audio ID. Returns error dict if failed, None if successful."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return {"entity": "audio", "id": audio_id, "error": "No gateway or connection available"}
    
    try:
        # Verify audio exists first
        verify = gateway.conn.read("SELECT id, caption FROM audio WHERE id = %s", [audio_id])
        if not verify:
            error_msg = f"Audio {audio_id} does not exist in database"
            warn(error_msg)
            return {"entity": "audio", "id": audio_id, "error": error_msg}
        
        audio_info = verify[0]
        audio_caption = audio_info.get('caption', 'no caption')
        
        from hh.audio.audio_registry import get_audio
        audio_obj = get_audio(audio_id)
        if not audio_obj:
            error_msg = f"Audio {audio_id} (caption={audio_caption}) could not be loaded"
            if is_error():
                errs = get_errors()
                if errs:
                    error_contents = [f"{e.error_type.value}: {e.content}" for e in errs]
                    error_msg = f"{error_msg}. Errors: {'; '.join(error_contents)}"
            warn(error_msg)
            return {"entity": "audio", "id": audio_id, "error": error_msg}
        
        audio_obj.show_audio()
        log(f"Successfully cached audio {audio_id} (caption={audio_caption})")
        return None
    except Exception as exc:  # noqa: BLE001
        error_msg = f"Exception while caching audio {audio_id}: {type(exc).__name__}: {exc}"
        warn(error_msg)
        return {"entity": "audio", "id": audio_id, "error": error_msg}


@register_action("audio_cache_refresh")
@register_command("audio_cache_refresh")
def audio_cache_refresh_action() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return False

    try:
        stale_audio_id = fetch_stale_audio_id()
        if stale_audio_id is None:
            # No stale audio to process
            payload = {
                "operation": "rebuild_audio_cache",
                "audio_id": None,
                "processed": False,
                "error": None,
                "audio_remaining": 0,
            }
            gateway.response.set_action_response(success_payload(payload))
            log("No stale audio to process")
            trace_out()
            return True

        log(f"Processing stale audio {stale_audio_id}")
        error = rebuild_audio(stale_audio_id)
        audio_remaining = count_stale_audio()

        error_msg: str | None = error.get("error") if error and isinstance(error, dict) else None
        payload = {
            "operation": "rebuild_audio_cache",
            "audio_id": stale_audio_id,
            "processed": error is None,
            "error": error_msg,
            "audio_remaining": audio_remaining,
        }
        gateway.response.set_action_response(success_payload(payload))
        if error:
            log(f"Audio cache refresh failed for audio {stale_audio_id}: {error.get('error', 'Unknown error')}")
        else:
            log(f"Audio cache refresh completed for audio {stale_audio_id}, {audio_remaining} remaining")
        trace_out()
        return not is_error()
    except Exception as exc:  # noqa: BLE001
        warn(f"Failed to refresh audio cache: {exc}")
        report_error("action", f"Failed to refresh audio cache: {exc}")
        trace_out()
        return False


@register_parser("audio_cache_refresh")
def audio_cache_refresh_parser() -> bool:
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
        audio_id = source_data.get("audio_id")
        processed = source_data.get("processed", False)
        error = source_data.get("error")
        audio_remaining = source_data.get("audio_remaining", 0)

        lines = [render_header_block("l_audio_cache_refresh_header")]

        table = TableData()
        has_remaining = audio_remaining > 0
        
        # Add header row (visual anchor)
        table.add_row(
            "audio_cache_refresh_header",
            info="",
        )
        
        if audio_id is None:
            # No stale audio
            table.add_row(
                "no_stale_audio",
                info="No audio need cache refresh",
            )
        else:
            # Audio ID row
            table.add_row(
                "audio_cache_audio_id",
                info=str(audio_id),
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
                    "audio_cache_error",
                    info=error_msg,
                )
            
            # Remaining audio row (only if there are remaining)
            if has_remaining:
                table.add_row(
                    "audio_cache_refresh_remaining",
                    info=str(audio_remaining),
                )

        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("audio_cache_refresh_header")
                .add_simple(["no_stale_audio", "audio_cache_audio_id", "refresh_status", "audio_cache_refresh_remaining"])
                .add_simple_color("audio_cache_error", "red"),
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


register_maintenance_tool("audio_cache_refresh")
