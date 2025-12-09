"""Image cache refresh module for maintenance daemon."""

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
from hh.image.image_registry import get_image
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


def fetch_stale_image_id() -> int | None:
    """Fetch one stale image ID from main database only.
    Staleness determined by: COALESCE(last_modified, uploaded) > cache_built_at OR cache_built_at IS NULL"""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return None
    rows = gateway.conn.read(
        """
        SELECT id
        FROM images
        WHERE COALESCE(last_modified, uploaded) > cache_built_at
           OR cache_built_at IS NULL
        ORDER BY COALESCE(last_modified, uploaded) DESC
        LIMIT 1
        """,
    )
    return rows[0]["id"] if rows else None


def count_stale_images() -> int:
    """Count stale images in main database only."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return 0
    rows = gateway.conn.read(
        """
        SELECT COUNT(*) AS cnt
        FROM images
        WHERE COALESCE(last_modified, uploaded) > cache_built_at
           OR cache_built_at IS NULL
        """,
    )
    return rows[0]["cnt"] if rows else 0


def rebuild_image(image_id: int) -> dict[str, Any] | None:
    """Rebuild cache for a single image ID. Returns error dict if failed, None if successful."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return {"entity": "image", "id": image_id, "error": "No gateway or connection available"}
    
    try:
        # Verify image exists first
        verify = gateway.conn.read("SELECT id, caption FROM images WHERE id = %s", [image_id])
        if not verify:
            error_msg = f"Image {image_id} does not exist in database"
            warn(error_msg)
            return {"entity": "image", "id": image_id, "error": error_msg}
        
        image_info = verify[0]
        image_caption = image_info.get('caption', 'no caption')
        
        image_obj = get_image(image_id)
        if not image_obj:
            error_msg = f"Image {image_id} (caption={image_caption}) could not be loaded"
            if is_error():
                errs = get_errors()
                if errs:
                    error_contents = [f"{e.error_type.value}: {e.content}" for e in errs]
                    error_msg = f"{error_msg}. Errors: {'; '.join(error_contents)}"
            warn(error_msg)
            return {"entity": "image", "id": image_id, "error": error_msg}
        
        image_obj.show_image()
        log(f"Successfully cached image {image_id} (caption={image_caption})")
        return None
    except Exception as exc:  # noqa: BLE001
        error_msg = f"Exception while caching image {image_id}: {type(exc).__name__}: {exc}"
        warn(error_msg)
        return {"entity": "image", "id": image_id, "error": error_msg}


@register_action("image_cache_refresh")
@register_command("image_cache_refresh")
def image_cache_refresh_action() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return False

    try:
        stale_image_id = fetch_stale_image_id()
        if stale_image_id is None:
            # No stale images to process
            payload = {
                "operation": "rebuild_image_cache",
                "image_id": None,
                "processed": False,
                "error": None,
                "images_remaining": 0,
            }
            gateway.response.set_action_response(success_payload(payload))
            log("No stale images to process")
            trace_out()
            return True

        log(f"Processing stale image {stale_image_id}")
        error = rebuild_image(stale_image_id)
        images_remaining = count_stale_images()

        payload = {
            "operation": "rebuild_image_cache",
            "image_id": stale_image_id,
            "processed": error is None,
            "error": error,
            "images_remaining": images_remaining,
        }
        gateway.response.set_action_response(success_payload(payload))
        if error:
            log(f"Image cache refresh failed for image {stale_image_id}: {error.get('error', 'Unknown error')}")
        else:
            log(f"Image cache refresh completed for image {stale_image_id}, {images_remaining} remaining")
        trace_out()
        return not is_error()
    except Exception as exc:  # noqa: BLE001
        warn(f"Failed to refresh image cache: {exc}")
        report_error("action", f"Failed to refresh image cache: {exc}")
        trace_out()
        return False


@register_parser("image_cache_refresh")
def image_cache_refresh_parser() -> bool:
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
        image_id = source_data.get("image_id")
        processed = source_data.get("processed", False)
        error = source_data.get("error")
        images_remaining = source_data.get("images_remaining", 0)

        lines = [render_header_block("l_image_cache_refresh_header")]

        table = TableData()
        has_remaining = images_remaining > 0
        
        # Add header row (visual anchor)
        table.add_row(
            "image_cache_refresh_header",
            info="",
        )
        
        if image_id is None:
            # No stale images
            table.add_row(
                "no_stale_images",
                info="No images need cache refresh",
            )
        else:
            # Image ID row
            table.add_row(
                "image_id",
                info=str(image_id),
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
                    "image_cache_error",
                    info=error_msg,
                )
            
            # Remaining images row (only if there are remaining)
            if has_remaining:
                table.add_row(
                    "image_cache_refresh_remaining",
                    info=str(images_remaining),
                )

        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("image_cache_refresh_header")
                .add_simple(["no_stale_images", "image_id", "refresh_status", "image_cache_refresh_remaining"])
                .add_simple_color("image_cache_error", "red"),
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


register_maintenance_tool("image_cache_refresh")
