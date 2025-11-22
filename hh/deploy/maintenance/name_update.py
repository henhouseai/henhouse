"""Name update job processing module for maintenance daemon."""

import json
import logging
import os
from subprocess import CalledProcessError, check_output, STDOUT
from typing import Any, Dict

PROJECT_NAME = "__PROJECT_NAME__"
NAME_JOB_BATCH_LIMIT = int(os.getenv("MAINTENANCE_NAME_BATCH", "25"))


def _extract_json_dict(output: str) -> Dict[str, Any] | None:
    """Extract JSON dictionary from command output."""
    if not output:
        return None
    for line in output.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def _extract_text_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract text payload from response."""
    data = payload.get("data")
    if isinstance(data, dict):
        content = data.get("content")
        if isinstance(content, list) and content:
            entry = content[0]
            if isinstance(entry, dict):
                text = entry.get("text")
                if isinstance(text, dict):
                    return text
        return data
    return {}


def _extract_result_block(payload_json: Dict[str, Any]) -> Dict[str, Any]:
    """Extract result block from payload."""
    text_payload = _extract_text_payload(payload_json)
    result_block = text_payload.get("result")
    if isinstance(result_block, dict):
        return result_block
    return {}


def _summarize_errors(payload: Dict[str, Any], fallback: str = "") -> str:
    """Summarize errors from payload."""
    errors = payload.get("errors")
    if isinstance(errors, dict):
        parts = [f"{key}: {value}" for key, value in errors.items()]
        if parts:
            return "; ".join(parts)
    if isinstance(errors, list):
        parts = []
        for entry in errors:
            if isinstance(entry, dict):
                parts.append(", ".join(f"{k}={v}" for k, v in entry.items()))
            else:
                parts.append(str(entry))
        if parts:
            return "; ".join(parts)
    data = payload.get("data")
    if isinstance(data, dict):
        message = data.get("message") or data.get("msg")
        if message:
            return str(message)
    return fallback or "maintenance action reported an error"


def _build_regex_text_args(job: Dict[str, Any], resolution_id: int) -> list[str]:
    """Build command arguments for regex_text command."""
    payload = job.get("payload") or {}
    page_id = payload.get("page_id")
    old_name = payload.get("old_name")
    new_name = payload.get("new_name")
    args = [
        "regex_text",
        "--page_id",
        str(page_id) if page_id is not None else "0",
        "--old_name",
        old_name,
        "--new_name",
        new_name,
        "--resolution_id",
        str(resolution_id),
    ]
    return args


def _run_regex_text_command(args: list[str], include_log: bool = False) -> Dict[str, Any]:
    """Run regex_text command and return result."""
    cmd_args = list(args)
    if include_log and "-log" not in cmd_args:
        cmd_args.insert(1, "-log")
    command = ["python3", f"/srv/{PROJECT_NAME}/maintenance_client.py"] + cmd_args
    try:
        result_text = check_output(command, stderr=STDOUT, text=True)
    except CalledProcessError as exc:
        output = exc.output.strip()
        payload_json = _extract_json_dict(output)
        message = _summarize_errors(payload_json or {}, fallback=output[:500])
        return {
            "success": False,
            "message": message,
            "raw_output": output,
            "result": _extract_result_block(payload_json) if payload_json else {},
        }

    payload_json = _extract_json_dict(result_text)
    if not payload_json:
        snippet = result_text.strip()[:500]
        return {
            "success": False,
            "message": f"Invalid maintenance output: {snippet}",
            "raw_output": result_text,
            "result": {},
        }
    if payload_json.get("status") == "error":
        message = _summarize_errors(payload_json)
        return {
            "success": False,
            "message": message,
            "raw_output": result_text,
            "result": _extract_result_block(payload_json),
        }

    return {
        "success": True,
        "result": _extract_result_block(payload_json),
        "raw_output": result_text,
    }


def _get_referencing_page_ids(conn, source_page_id: int, last_page_id: int, batch_limit: int):
    """Get page IDs that reference a source page."""
    from hh.gateway.connection.connection import r_query
    
    rows = r_query(
        conn,
        """
        SELECT DISTINCT id
        FROM links
        WHERE resolution_id = %s
          AND link NOT REGEXP '^[0-9]+$'
          AND id > %s
        ORDER BY id
        LIMIT %s
        """,
        (source_page_id, last_page_id, batch_limit + 1),
    )
    ids = [row["id"] for row in rows[:batch_limit]]
    has_more = len(rows) > batch_limit
    return ids, has_more


def process_page_name_job(job: Dict[str, Any], conn) -> Dict[str, Any]:
    """Process a page name update job."""
    payload = job.get("payload") or {}
    progress = job.get("progress") or {}
    job["progress"] = progress

    page_id = payload.get("page_id")
    old_name = payload.get("old_name")
    new_name = payload.get("new_name")

    if not (page_id and old_name and new_name):
        message = f"Job {job['id']} missing rename payload"
        logging.warning(message)
        return {
            "status": "error",
            "progress": progress,
            "error_message": message,
        }

    last_page_id = progress.get("last_page_id", 0)
    pages_processed = progress.get("pages_processed", 0)
    pages_modified = progress.get("pages_modified", 0)

    resolution_ids, has_more = _get_referencing_page_ids(
        source_page_id=page_id,
        last_page_id=last_page_id,
        batch_limit=NAME_JOB_BATCH_LIMIT,
    )
    if not resolution_ids:
        logging.info(
            "No referencing pages remaining for maintenance job %s (page_id=%s)",
            job["id"],
            page_id,
        )
        done_progress = {
            "last_page_id": last_page_id,
            "pages_processed": pages_processed,
            "pages_modified": pages_modified,
            "batch_count": 0,
            "done": True,
        }
        return {
            "status": "done",
            "progress": done_progress,
            "error_message": None,
        }

    batch_count = 0
    batch_modified = 0
    last_processed_id = last_page_id

    for resolution_id in resolution_ids:
        args = _build_regex_text_args(job, resolution_id)
        first_attempt = _run_regex_text_command(args)
        attempt_result = first_attempt
        if not first_attempt["success"]:
            logging.error("Maintenance job %s failed for page %s: %s", job["id"], resolution_id, first_attempt.get("message"))
            retry_attempt = _run_regex_text_command(args, include_log=True)
            if retry_attempt["success"]:
                logging.info("Maintenance job %s recovered for page %s after retry with -log", job["id"], resolution_id)
                attempt_result = retry_attempt
            else:
                combined_progress = {
                    "last_page_id": last_processed_id,
                    "pages_processed": pages_processed,
                    "pages_modified": pages_modified,
                    "batch_count": batch_count,
                    "batch_modified": batch_modified,
                    "done": False,
                }
                detailed_error = retry_attempt.get("raw_output") or first_attempt.get("raw_output") or ""
                message = retry_attempt.get("message") or first_attempt.get("message") or "maintenance handler failed"
                if detailed_error and detailed_error not in message:
                    message = f"{message}\n{detailed_error}"
                return {
                    "status": "error",
                    "progress": combined_progress,
                    "error_message": message.strip(),
                }

        batch_count += 1
        pages_processed += 1
        result_block = attempt_result.get("result") or {}
        if result_block.get("processed") or result_block.get("modified"):
            batch_modified += 1
            pages_modified += 1
        last_processed_id = resolution_id

    done = not has_more
    progress_payload = {
        "last_page_id": last_processed_id,
        "pages_processed": pages_processed,
        "pages_modified": pages_modified,
        "batch_count": batch_count,
        "batch_modified": batch_modified,
        "done": done,
    }
    status = "done" if done else "running"
    return {
        "status": status,
        "progress": progress_payload,
        "error_message": None,
    }

