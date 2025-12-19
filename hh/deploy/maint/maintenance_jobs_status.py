"""Maintenance jobs status module - checks what work needs to be done."""

from __future__ import annotations

from typing import Any, Dict

from hh.gateway.error.error_store import is_error, report_error
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


def count_stale_pages() -> int:
    """Count pages needing cache rebuild."""
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


def count_stale_images() -> int:
    """Count images needing cache rebuild."""
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


def count_stale_files() -> int:
    """Count files needing cache rebuild."""
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


def count_stale_audio() -> int:
    """Count audio needing cache rebuild."""
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


def count_stale_video() -> int:
    """Count video needing cache rebuild."""
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


def get_pending_jobs() -> Dict[str, int]:
    """Get count of pending jobs by type from maintenance_jobs table."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return {}
    rows = gateway.conn.read(
        """
        SELECT job_type, COUNT(*) AS cnt
        FROM maintenance_jobs
        WHERE status = 'pending'
        GROUP BY job_type
        ORDER BY job_type
        """,
    )
    return {row["job_type"]: row["cnt"] for row in rows} if rows else {}


def count_error_jobs() -> int:
    """Count jobs with error status in maintenance_jobs table."""
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        return 0
    rows = gateway.conn.read(
        """
        SELECT COUNT(*) AS cnt
        FROM maintenance_jobs
        WHERE status = 'error'
        """,
    )
    return rows[0]["cnt"] if rows else 0


@register_action("maintenance_jobs_status")
@register_command("maintenance_jobs_status")
def maintenance_jobs_status_action() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return False

    try:
        stale_pages = count_stale_pages()
        stale_images = count_stale_images()
        stale_files = count_stale_files()
        stale_audio = count_stale_audio()
        stale_video = count_stale_video()
        pending_jobs = get_pending_jobs()
        error_jobs = count_error_jobs()

        # Count work types available
        work_types = 0
        if stale_pages > 0:
            work_types += 1
        if stale_images > 0:
            work_types += 1
        if stale_files > 0:
            work_types += 1
        if stale_audio > 0:
            work_types += 1
        if stale_video > 0:
            work_types += 1
        work_types += len(pending_jobs)

        payload = {
            "stale_pages": stale_pages,
            "stale_images": stale_images,
            "stale_files": stale_files,
            "stale_audio": stale_audio,
            "stale_video": stale_video,
            "pending_jobs": pending_jobs,
            "error_jobs": error_jobs,
            "work_types": work_types,
            "has_work": work_types > 0,
        }
        gateway.response.set_action_response(success_payload(payload))
        log(f"Maintenance status: pages={stale_pages}, images={stale_images}, files={stale_files}, audio={stale_audio}, video={stale_video}, jobs={pending_jobs}, errors={error_jobs}")
        trace_out()
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"Failed to get maintenance status: {exc}")
        report_error("action", f"Failed to get maintenance status: {exc}")
        trace_out()
        return False


@register_parser("maintenance_jobs_status")
def maintenance_jobs_status_parser() -> bool:
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
        stale_pages = source_data.get("stale_pages", 0)
        stale_images = source_data.get("stale_images", 0)
        stale_files = source_data.get("stale_files", 0)
        stale_audio = source_data.get("stale_audio", 0)
        stale_video = source_data.get("stale_video", 0)
        pending_jobs = source_data.get("pending_jobs", {})
        error_jobs = source_data.get("error_jobs", 0)
        work_types = source_data.get("work_types", 0)
        has_work = source_data.get("has_work", False)

        lines = [render_header_block("l_maintenance_jobs_status_header")]

        table = TableData()
        table.add_row("maintenance_jobs_status_header", info="")

        # Cache rebuild status (always show, even if zero)
        table.add_row("stale_pages_count", info=str(stale_pages))
        table.add_row("stale_images_count", info=str(stale_images))
        table.add_row("stale_files_count", info=str(stale_files))
        table.add_row("stale_audio_count", info=str(stale_audio))
        table.add_row("stale_video_count", info=str(stale_video))

        # Job queue status
        if pending_jobs:
            for job_type, count in pending_jobs.items():
                table.add_row("pending_job", info=f"{job_type}: {count}")
        
        # Work status (dynamic field type)
        if has_work:
            table.add_row("work_available", info=str(work_types))
        else:
            table.add_row("no_work_available", info="")

        # Error status (dynamic field type)
        if error_jobs > 0:
            table.add_row("job_errors", info=str(error_jobs))
        else:
            table.add_row("no_job_errors", info="")

        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("maintenance_jobs_status_header")
                .add_simple(["stale_pages_count", "stale_images_count", "stale_files_count", "stale_audio_count", "stale_video_count", "pending_job"])
                .add_simple_color("work_available", "green")
                .add_simple_color("no_work_available", "yellow")
                .add_simple_color("job_errors", "red")
                .add_simple_color("no_job_errors", "green"),
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


register_maintenance_tool("maintenance_jobs_status")

