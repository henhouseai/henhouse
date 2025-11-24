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
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_command("regex_text")
@register_action("regex_text")
def regex_text() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        report_error("request", "No gateway available")
        trace_out()
        return False

    # Claim a page_name_update job (checks pending first, then running)
    job = claim_next_maintenance_job("page_name_update")
    
    if not job:
        log("No page_name_update job available")
        gateway.response.set_action_response(
            success_payload({
                "operation": "regex_text",
                "job_id": None,
                "resolution_id": None,
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
    old_name = payload.get("old_name")
    new_name = payload.get("new_name")
    
    if not (page_id and old_name and new_name):
        warn(f"Job {job_id} missing required payload fields")
        report_error("request", f"Job {job_id} missing required payload fields")
        trace_out()
        return False
    
    last_page_id = progress.get("last_page_id", 0)
    conn = gateway.conn
    
    # Find next resolution_id (page that references the source page_id)
    rows = conn.read(
        """
        SELECT DISTINCT id
        FROM links
        WHERE resolution_id = %s
          AND link NOT REGEXP '^[0-9]+$'
          AND id > %s
        ORDER BY id ASC
        LIMIT 1
        """,
        (page_id, last_page_id),
    )
    
    if not rows:
        log(f"No more pages to process for job {job_id}")
        gateway.response.set_action_response(
            success_payload({
                "operation": "regex_text",
                "job_id": job_id,
                "resolution_id": None,
                "done": True,
                "message": "No more pages to process",
            })
        )
        trace_out()
        return True
    
    resolution_id = rows[0]["id"]
    
    log(
        f"Processing job {job_id}: resolution page {resolution_id} "
        f"(source page={page_id}, {old_name} -> {new_name})"
    )
    
    page_obj = get_page(page_id=resolution_id)
    if not page_obj:
        warn(f"Page {resolution_id} could not be loaded")
        report_error("registry", f"Page {resolution_id} could not be loaded")
        trace_out()
        return False
    
    log(f"Processing maintenance rename for resolution page {resolution_id}")
    result = page_obj.regex_text(
        old_name=old_name,
        new_name=new_name,
    )
    
    gateway.response.set_action_response(
        success_payload({
            "operation": "regex_text",
            "job_id": job_id,
            "page_id": page_id,
            "resolution_id": resolution_id,
            "old_name": old_name,
            "new_name": new_name,
            "result": result,
        })
    )
    log(
        f"Maintenance rename for resolution page {resolution_id} completed: "
        f"processed={result.get('processed')}, modified={result.get('modified')}"
    )
    trace_out()
    return not is_error()


@register_parser("regex_text")
def regex_text_parser() -> bool:
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
        job_id = source_data.get("job_id")
        resolution_id = source_data.get("resolution_id")
        result = source_data.get("result")
        done = source_data.get("done", False)
        error_occurred = is_error()
        
        conn = gateway.conn
        
        # Update job table if we have a job_id
        if job_id:
            if error_occurred:
                # Set job status to error
                update_maintenance_job(
                    job_id=job_id,
                    status="error",
                )
                log(f"Set job {job_id} status to error")
            elif done:
                # Job is complete - get current progress to preserve it
                rows = conn.read(
                    "SELECT progress_json FROM maintenance_jobs WHERE id = %s",
                    (job_id,),
                )
                if rows:
                    current_progress = json.loads(rows[0]["progress_json"] or "{}")
                    update_maintenance_job(
                        job_id=job_id,
                        status="done",
                        progress=current_progress,
                    )
                    log(f"Set job {job_id} status to done")
            elif result:
                # Update progress and set status back to pending for next run
                # Get current progress from job
                rows = conn.read(
                    "SELECT progress_json FROM maintenance_jobs WHERE id = %s",
                    (job_id,),
                )
                if rows:
                    current_progress = json.loads(rows[0]["progress_json"] or "{}")
                    pages_processed = current_progress.get("pages_processed", 0) + 1
                    pages_modified = current_progress.get("pages_modified", 0)
                    if result.get("modified"):
                        pages_modified += 1
                    
                    new_progress = {
                        "last_page_id": resolution_id,
                        "pages_processed": pages_processed,
                        "pages_modified": pages_modified,
                    }
                    update_maintenance_job(
                        job_id=job_id,
                        status="pending",
                        progress=new_progress,
                    )
                    log(f"Updated job {job_id} progress and set to pending: last_page_id={resolution_id}, processed={pages_processed}, modified={pages_modified}")
        
        # Render output
        lines = [render_header_block("l_regex_text_header")]
        
        table = TableData()
        
        # Add header row (visual anchor)
        table.add_row(
            "regex_text_header",
            info="",
        )
        
        if done:
            # No more pages to process
            table.add_row(
                "no_more_pages",
                info=source_data.get("message", "No more pages to process"),
            )
        elif resolution_id is None:
            # No job available
            table.add_row(
                "no_job_available",
                info="No job available",
            )
        else:
            # Job ID row
            table.add_row(
                "job_id",
                info=str(job_id),
            )
            
            # Resolution ID row
            table.add_row(
                "resolution_id",
                info=str(resolution_id),
            )
            
            if error_occurred:
                # Error row
                error_msg = "An error occurred during processing"
                table.add_row(
                    "regex_text_error",
                    info=error_msg,
                )
            elif result:
                # Processed row
                processed = result.get("processed", 0)
                modified = result.get("modified", False)
                status_msg = f"Processed: {processed}, Modified: {modified}"
                table.add_row(
                    "regex_text_status",
                    info=status_msg,
                )
        
        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("regex_text_header")
                .add_simple(["no_more_pages", "no_job_available", "job_id", "resolution_id", "regex_text_status"])
                .add_simple_color("regex_text_error", "red"),
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


register_maintenance_tool("regex_text")
