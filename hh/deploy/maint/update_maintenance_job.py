"""Update maintenance job status and progress."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from hh.gateway.error.error_store import is_error, report_error
from hh.gateway.gateway import get_gateway, trace_in, trace_out, log, warn
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


@register_action("update_maintenance_job")
@register_command("update_maintenance_job")
def update_maintenance_job_action() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return False

    # Get arguments
    job_id = gateway.get_arg("job_id") or gateway.get_arg("id")
    status = gateway.get_arg("status")
    progress_json = gateway.get_arg("progress")
    error_message = gateway.get_arg("error_message") or gateway.get_arg("error")

    if not job_id:
        warn("job_id is required")
        report_error("action", "job_id is required")
        trace_out()
        return False

    try:
        job_id = int(job_id)
    except ValueError:
        warn(f"Invalid job_id: {job_id}")
        report_error("action", f"Invalid job_id: {job_id}")
        trace_out()
        return False

    # Parse progress JSON if provided
    progress = None
    if progress_json:
        try:
            progress = json.loads(progress_json)
        except json.JSONDecodeError:
            warn(f"Invalid progress JSON: {progress_json}")
            report_error("action", f"Invalid progress JSON")
            trace_out()
            return False

    conn = gateway.conn

    # Build update query
    fields = []
    params = []

    if progress is not None:
        fields.append("progress_json = %s")
        params.append(json.dumps(progress, ensure_ascii=False, separators=(",", ":")))

    if error_message is not None:
        fields.append("error_message = %s")
        # Truncate if too long
        params.append(error_message[:10000] if len(error_message) > 10000 else error_message)

    if status:
        fields.append("status = %s")
        params.append(status)
        if status in {"done", "error"}:
            fields.append("completed_at = NOW(6)")

    # Always increment attempts and update timestamp
    fields.append("attempts = attempts + 1")
    fields.append("updated_at = NOW(6)")

    if not fields:
        warn("No fields to update")
        report_error("action", "No fields to update")
        trace_out()
        return False

    params.append(job_id)
    sql = f"UPDATE maintenance_jobs SET {', '.join(fields)} WHERE id = %s"
    
    try:
        affected = conn.update(sql, params)
        log(f"Updated job {job_id}: status={status}, affected={affected}")
        
        payload = {
            "job_id": job_id,
            "status": status,
            "updated": affected > 0,
            "fields_updated": len(fields),
        }
        gateway.response.set_action_response(success_payload(payload))
        trace_out()
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"Failed to update job {job_id}: {exc}")
        report_error("action", f"Failed to update job: {exc}")
        trace_out()
        return False


@register_parser("update_maintenance_job")
def update_maintenance_job_parser() -> bool:
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
        status = source_data.get("status")
        updated = source_data.get("updated", False)

        lines = [render_header_block("l_update_maintenance_job_header")]

        table = TableData()
        table.add_row("update_maintenance_job_header", info="")
        table.add_row("job_id", info=str(job_id))
        
        if status:
            table.add_row("job_status_updated", info=status)
        
        if updated:
            table.add_row("job_update_success", info="Updated")
        else:
            table.add_row("job_update_failed", info="Not found or no change")

        lines.append(
            render_block(
                table,
                FieldConfig()
                .add_header("update_maintenance_job_header")
                .add_simple(["job_id", "job_status_updated"])
                .add_simple_color("job_update_success", "green")
                .add_simple_color("job_update_failed", "red"),
                block_type="maintenance",
                table_overrides={"margin_l": 4},
            )
        )

        gateway.response.add_output(finalize_output(lines))
        log(f"Parser execution completed successfully")
        trace_out()
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"Parser execution raised an exception: {exc}")
        report_error("backend", f"Parser execution raised an exception: {exc}")
        trace_out()
        return False


register_maintenance_tool("update_maintenance_job")

