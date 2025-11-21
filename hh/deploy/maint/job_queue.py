from __future__ import annotations

import json
from typing import Any, Dict, Optional

from hh.gateway.connection.connection import r_query, u_query
from hh.gateway.connection.decorators import db_write
from hh.gateway.registry.debug import (
    get_debug,
    get_log,
    get_trace_in,
    get_trace_out,
    get_warn,
    register_debug_init,
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


_JOB_COLUMNS = (
    "id, job_type, status, payload_json, progress_json, priority, attempts, "
    "error_message, created_at, updated_at, started_at, completed_at"
)


def _dump_json(data: Optional[Dict[str, Any]]) -> str:
    return json.dumps(data or {}, ensure_ascii=False, separators=(",", ":"))


def _load_json(value: Any) -> Dict[str, Any]:
    if value in (None, "", b""):
        return {}
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            warn(f"Failed to decode maintenance job JSON payload: {value[:200]}")
            return {}
    if isinstance(value, dict):
        return dict(value)
    return {}


def _deserialize_job(row: Dict[str, Any]) -> Dict[str, Any]:
    job = dict(row)
    job["payload"] = _load_json(job.pop("payload_json", None))
    job["progress"] = _load_json(job.pop("progress_json", None))
    return job


@db_write
def claim_next_maintenance_job(conn) -> Optional[Dict[str, Any]]:
    """
    Claim the next available job (pending jobs preferred, then running).
    Uses optimistic updates instead of explicit row locks.
    """
    trace_in()
    attempts = 0
    while attempts < 5:
        rows = r_query(
            conn,
            f"""
            SELECT {_JOB_COLUMNS}
            FROM maintenance_jobs
            WHERE status = 'pending'
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
            """,
        )
        pending_job = _deserialize_job(rows[0]) if rows else None
        if not pending_job:
            break
        affected = u_query(
            conn,
            """
            UPDATE maintenance_jobs
            SET status = 'running',
                attempts = attempts + 1,
                started_at = COALESCE(started_at, NOW(6)),
                updated_at = NOW(6)
            WHERE id = %s AND status = 'pending'
            """,
            (pending_job["id"],),
        )
        if affected:
            refreshed = r_query(
                conn,
                f"SELECT {_JOB_COLUMNS} FROM maintenance_jobs WHERE id = %s",
                (pending_job["id"],),
            )
            if refreshed:
                job = _deserialize_job(refreshed[0])
                trace_out()
                return job
        attempts += 1

    rows = r_query(
        conn,
        f"""
        SELECT {_JOB_COLUMNS}
        FROM maintenance_jobs
        WHERE status = 'running'
        ORDER BY priority DESC, created_at ASC
        LIMIT 1
        """,
    )
    running_job = _deserialize_job(rows[0]) if rows else None
    if running_job:
        trace_out()
        return running_job

    trace_out()
    return None


@db_write
def update_maintenance_job(
    conn,
    job_id: int,
    status: Optional[str] = None,
    progress: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> None:
    trace_in()
    fields = []
    params: list[Any] = []

    if progress is not None:
        fields.append("progress_json = %s")
        params.append(_dump_json(progress))

    if error_message is not None:
        fields.append("error_message = %s")
        params.append(error_message[:1000])

    if status:
        fields.append("status = %s")
        params.append(status)
        if status == "running":
            fields.append("started_at = COALESCE(started_at, NOW(6))")
        if status in {"done", "error"}:
            fields.append("completed_at = NOW(6)")

    if not fields:
        trace_out()
        return

    fields.append("updated_at = NOW(6)")
    params.append(job_id)

    sql = f"UPDATE maintenance_jobs SET {', '.join(fields)} WHERE id = %s"
    u_query(conn, sql, params)
    trace_out()

