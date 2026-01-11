"""Encoding corruption fix module for maintenance daemon and manual runs."""

from __future__ import annotations

import json
from typing import Optional, Dict, Any

from hh.gateway.gateway import get_gateway
from hh.gateway.registry.maintenance import register_maintenance_tool
from hh.gateway.registry.registry import register_action, register_command, register_parser
from hh.gateway.response.json_standard import success_payload, get_data
from hh.page.page_registry import get_page
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.deploy.maint.job_queue import claim_next_maintenance_job, update_maintenance_job
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


# Known corruption patterns mapping corrupted sequences to correct Unicode
CORRUPTION_PATTERNS = {
    "â†’": "→"
}


def apply_encoding_fixes(page_text: str, patterns_to_fix: Optional[list[str]] = None, dry_run: bool = False) -> dict[str, Any]:
    """Apply encoding corruption fixes to page text."""
    if patterns_to_fix is None:
        # Sort patterns by length (longest first) to avoid partial matches
        patterns_to_fix = sorted(CORRUPTION_PATTERNS.keys(), key=len, reverse=True)

    original_text = page_text
    fixes_applied = []
    total_fixes = 0

    # Fix each corrupted sequence (longest patterns first to avoid partial matches)
    for corrupted in patterns_to_fix:
        if corrupted in CORRUPTION_PATTERNS and corrupted in page_text:
            replacement = CORRUPTION_PATTERNS[corrupted]
            count = page_text.count(corrupted)
            if count > 0:
                if not dry_run:
                    page_text = page_text.replace(corrupted, replacement)
                fixes_applied.append({
                    "pattern": corrupted,
                    "replacement": replacement,  # Use the actual replacement from patterns
                    "count": count
                })
                total_fixes += count

    return {
        "original_text": original_text,
        "fixed_text": page_text,
        "fixes_applied": fixes_applied,
        "total_fixes": total_fixes,
        "dry_run": dry_run,
        "changed": page_text != original_text
    }


@register_command("encoding_corruption_fix")
@register_action("encoding_corruption_fix")
def encoding_corruption_fix() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("request", "No gateway available")
        trace_out()
        return False

    # Check if page_id was provided on command line
    page_id_arg = gateway.request.get_arg('page_id') or gateway.request.get_arg('id') if gateway.request else None
    if page_id_arg:
        try:
            page_id = int(page_id_arg)
            log(f"Processing page {page_id} directly (manual mode)")
            return _process_single_page(gateway, page_id)
        except (ValueError, TypeError):
            warn(f"Invalid page_id argument: {page_id_arg}")
            report_error("request", f"Invalid page_id argument: {page_id_arg}")
            trace_out()
            return False

    # Otherwise, work with maintenance job queue
    log("Checking for encoding_corruption_fix maintenance jobs")
    return _process_maintenance_job(gateway)


def _process_single_page(gateway, page_id: int) -> bool:
    """Process a single page directly (manual testing mode)."""
    try:
        # Check if dry run is active (connection module handles this automatically)
        is_dry_run = getattr(gateway.conn, '_dry_run', False)

        # Load the page
        page = get_page(page_id=page_id)
        if not page:
            warn(f"Page {page_id} could not be loaded")
            report_error("registry", f"Page {page_id} could not be loaded")
            trace_out()
            return False

        log(f"Processing page {page_id}: '{page.name}' (dry_run={is_dry_run})")

        # Apply fixes - let connection module handle dry run rollback automatically
        result = apply_encoding_fixes(page.text, dry_run=False)

        if result["total_fixes"] > 0:
            log(f"Found {result['total_fixes']} corruption fixes needed")

            if result["changed"]:
                # Update the page (connection module will rollback if dry_run=True)
                page.modify_text(result["fixed_text"])
                if is_dry_run:
                    log(f"Dry run: would apply {result['total_fixes']} fixes to page {page_id}")
                else:
                    log(f"Applied {result['total_fixes']} fixes to page {page_id}")
            else:
                log(f"No changes made to page {page_id}")
        else:
            log(f"No corruption found in page {page_id}")

        # Return success response
        gateway.response.set_action_response(
            success_payload({
                "operation": "encoding_corruption_fix",
                "page_id": page_id,
                "result": result,
                "dry_run": is_dry_run,
            })
        )

        trace_out()
        return True

    except Exception as exc:  # noqa: BLE001
        warn(f"Failed to process page {page_id}: {exc}")
        report_error("action", f"Failed to process page {page_id}: {exc}")
        trace_out()
        return False


def _process_maintenance_job(gateway) -> bool:
    """Process encoding corruption fix jobs from the maintenance queue."""
    # Claim an encoding_corruption_fix job
    job = claim_next_maintenance_job("encoding_corruption_fix")

    if not job:
        log("No encoding_corruption_fix job available")
        gateway.response.set_action_response(
            success_payload({
                "operation": "encoding_corruption_fix",
                "job_id": None,
                "page_id": None,
                "done": True,
                "message": "No job available",
            })
        )
        trace_out()
        return True

    job_id = job["id"]
    payload = job.get("payload") or {}
    progress = job.get("progress") or {}

    page_id = payload.get("page_id")
    patterns_to_fix = payload.get("patterns_to_fix", list(CORRUPTION_PATTERNS.keys()))
    dry_run = payload.get("dry_run", True)  # Default to dry run for safety

    if not page_id:
        warn(f"Job {job_id} missing required payload field: page_id")
        report_error("request", f"Job {job_id} missing required payload field: page_id")
        trace_out()
        return False

    log(f"Processing encoding_corruption_fix job {job_id} for page {page_id}")

    try:
        # Load the page
        page = get_page(page_id=page_id)
        if not page:
            warn(f"Page {page_id} could not be loaded")
            report_error("registry", f"Page {page_id} could not be loaded")
            trace_out()
            return False

        log(f"Processing page {page_id}: '{page.name}' (dry_run={dry_run})")

        # Apply fixes
        result = apply_encoding_fixes(page.text, patterns_to_fix, dry_run=dry_run)

        if result["total_fixes"] > 0:
            log(f"Found {result['total_fixes']} corruption fixes needed")

            if not dry_run and result["changed"]:
                # Update the page
                page.modify_text(result["fixed_text"])
                log(f"Applied {result['total_fixes']} fixes to page {page_id}")
            elif dry_run:
                log(f"Dry run: would apply {result['total_fixes']} fixes to page {page_id}")
            else:
                log(f"No changes applied to page {page_id}")
        else:
            log(f"No corruption found in page {page_id}")

        # Update job progress
        current_progress = progress.copy()
        pages_processed = current_progress.get("pages_processed", 0) + 1
        pages_modified = current_progress.get("pages_modified", 0)
        if result["changed"] and not dry_run:
            pages_modified += 1

        new_progress = {
            "pages_processed": pages_processed,
            "pages_modified": pages_modified,
            "last_page_id": page_id,
            "patterns_fixed": result["fixes_applied"],
        }

        # Mark job as completed (single-page jobs)
        update_maintenance_job(
            job_id=job_id,
            status="done",
            progress=new_progress,
        )

        # Return success response
        gateway.response.set_action_response(
            success_payload({
                "operation": "encoding_corruption_fix",
                "job_id": job_id,
                "page_id": page_id,
                "result": result,
                "dry_run": dry_run,
            })
        )

        log(f"Encoding corruption fix job {job_id} completed successfully")
        trace_out()
        return True

    except Exception as exc:  # noqa: BLE001
        warn(f"Failed to process job {job_id}: {exc}")
        report_error("action", f"Failed to process job {job_id}: {exc}")
        trace_out()
        return False


@register_parser("encoding_corruption_fix")
def encoding_corruption_fix_parser() -> bool:
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
        job_id = source_data.get("job_id")
        page_id = source_data.get("page_id")
        result = source_data.get("result")
        dry_run = source_data.get("dry_run", False)
        done = source_data.get("done", False)

        lines = [render_header_block("l_encoding_corruption_fix_header")]

        table = TableData()

        # Add header row
        table.add_row(
            "encoding_corruption_fix_header",
            info="",
        )

        if done and not page_id:
            # No job available
            table.add_row(
                "no_job_available",
                info=source_data.get("message", "No job available"),
            )
        elif result:
            # Job results
            if job_id:
                table.add_row(
                    "job_id",
                    info=f"Job ID: {job_id}",
                )

            table.add_row(
                "page_id",
                info=f"Page ID: {page_id}",
            )

            table.add_row(
                "dry_run",
                info=f"Dry Run: {'Yes' if dry_run else 'No'}",
            )

            fixes_count = result.get("total_fixes", 0)
            table.add_row(
                "fixes_applied",
                info=f"Fixes Applied: {fixes_count}",
            )

            if result.get("fixes_applied"):
                for fix in result["fixes_applied"]:
                    table.add_row(
                        f"fix_{fix['pattern']}",
                        info=f"'{fix['pattern']}' → '{fix['replacement']}' ({fix['count']} times)",
                    )

            if result.get("changed", False):
                status_msg = "Changes applied successfully" if not dry_run else "Changes would be applied (dry run)"
                table.add_row(
                    "status",
                    info=status_msg,
                )
            else:
                table.add_row(
                    "status",
                    info="No changes needed",
                )
        else:
            table.add_row(
                "error",
                info="An error occurred during processing",
            )

        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("encoding_corruption_fix_header")
                .add_simple(["no_job_available", "job_id", "page_id", "dry_run", "fixes_applied", "status"])
                .add_simple_color("error", "red"),
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


register_maintenance_tool("encoding_corruption_fix")