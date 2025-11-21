import json
import logging
import os
import signal
import sys
import time
from subprocess import CalledProcessError, check_output, STDOUT
from typing import Any, Dict, Optional

from hh.deploy.cache.rebuild_cache import run_cache_rebuild_batch
from hh.deploy.maint.job_queue import claim_next_maintenance_job, update_maintenance_job
from hh.gateway.connection.connection import r_query
from hh.gateway.connection.decorators import db_read

PROJECT_NAME = "__PROJECT_NAME__"
SLEEP_INTERVAL_SECONDS = 5
CACHE_BATCH_LIMIT = 2  # Keep batches very small to avoid long-running transactions
NAME_JOB_BATCH_LIMIT = int(os.getenv("MAINTENANCE_NAME_BATCH", "25"))


def _extract_json_dict(output: str) -> Optional[Dict[str, Any]]:
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
    text_payload = _extract_text_payload(payload_json)
    result_block = text_payload.get("result")
    if isinstance(result_block, dict):
        return result_block
    return {}


def _summarize_errors(payload: Dict[str, Any], fallback: str = "") -> str:
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


def _build_regex_text_args(job: Dict[str, Any]) -> list[str]:
    progress = job.get("progress") or {}
    last_page_id = progress.get("last_page_id", 0)
    payload = job.get("payload") or {}
    page_id = payload.get("page_id")
    old_name = payload.get("old_name")
    new_name = payload.get("new_name")
    args = [
        "regex_text",
        "--page_id",
        str(page_id),
        "--old_name",
        old_name,
        "--new_name",
        new_name,
        "--last_page_id",
        str(last_page_id),
        "--batch_limit",
        str(NAME_JOB_BATCH_LIMIT),
    ]
    return args


def _run_regex_text_command(args: list[str], include_log: bool = False) -> Dict[str, Any]:
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
        progress = {}
        if payload_json:
            progress = _extract_result_block(payload_json)
        return {
            "success": False,
            "message": message,
            "raw_output": output,
            "progress": progress,
        }

    payload_json = _extract_json_dict(result_text)
    if not payload_json:
        snippet = result_text.strip()[:500]
        return {
            "success": False,
            "message": f"Invalid maintenance output: {snippet}",
            "raw_output": result_text,
            "progress": {},
        }
    if payload_json.get("status") == "error":
        message = _summarize_errors(payload_json)
        progress = _extract_result_block(payload_json)
        return {
            "success": False,
            "message": message,
            "raw_output": result_text,
            "progress": progress,
        }

    progress = _extract_result_block(payload_json)
    done = bool(progress.get("done"))
    last_page_id = progress.get("last_page_id")
    processed = progress.get("processed")
    logging.info(
        "Maintenance regex_text progress: processed=%s last_page_id=%s done=%s",
        processed,
        last_page_id,
        done,
    )
    return {
        "success": True,
        "status": "done" if done else "running",
        "progress": progress,
        "raw_output": result_text,
    }


def configure_logging():
    log_level = os.getenv("MAINTENANCE_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def handle_shutdown(signum, frame):  # noqa: D401, ANN001
    logging.info("Received signal %s, shutting down maintenance worker", signum)
    sys.exit(0)


def _run_cache_batch():
    try:
        result = run_cache_rebuild_batch(
            limit=CACHE_BATCH_LIMIT,
            include_pages=True,
            include_images=True,
        )
    except Exception as exc:  # noqa: BLE001
        logging.exception("Cache rebuild batch failed: %s", exc)
        return

    pages_processed = result.get("pages_processed", 0)
    images_processed = result.get("images_processed", 0)
    pages_remaining = result.get("pages_remaining")
    images_remaining = result.get("images_remaining")

    if pages_processed or images_processed:
        logging.info(
            "Cache rebuild batch: pages=%s images=%s remaining_pages=%s remaining_images=%s",
            pages_processed,
            images_processed,
            pages_remaining,
            images_remaining,
        )
    else:
        logging.debug(
            "Cache rebuild idle: remaining_pages=%s remaining_images=%s",
            pages_remaining,
            images_remaining,
        )


@db_read
def _log_orphan_counts(conn):
    try:
        orphan_pages = r_query(
            conn,
            """
            SELECT COUNT(*) AS cnt
            FROM pages child
            LEFT JOIN pages parent ON parent.id = child.parent
            WHERE child.parent <> 0 AND parent.id IS NULL
            """,
        )[0]["cnt"]

        orphan_link_sources = r_query(
            conn,
            """
            SELECT COUNT(*) AS cnt
            FROM links l
            LEFT JOIN pages p ON p.id = l.id
            WHERE p.id IS NULL
            """,
        )[0]["cnt"]

        orphan_link_targets = r_query(
            conn,
            """
            SELECT COUNT(*) AS cnt
            FROM links l
            LEFT JOIN pages p ON p.id = l.resolution_id
            WHERE p.id IS NULL
            """,
        )[0]["cnt"]

        orphan_image_pages = r_query(
            conn,
            """
            SELECT COUNT(*) AS cnt
            FROM image_links il
            LEFT JOIN pages p ON p.id = il.id
            WHERE p.id IS NULL
            """,
        )[0]["cnt"]

        orphan_image_targets = r_query(
            conn,
            """
            SELECT COUNT(*) AS cnt
            FROM image_links il
            LEFT JOIN images i ON i.id = il.resolution_id
            WHERE i.id IS NULL
            """,
        )[0]["cnt"]

        if orphan_pages:
            logging.warning("Orphan pages detected (child missing parent): %s", orphan_pages)
        if orphan_link_sources or orphan_link_targets:
            logging.warning(
                "Orphan links detected: source_missing=%s target_missing=%s",
                orphan_link_sources,
                orphan_link_targets,
            )
        if orphan_image_pages or orphan_image_targets:
            logging.warning(
                "Orphan image links detected: page_missing=%s image_missing=%s",
                orphan_image_pages,
                orphan_image_targets,
            )
    except Exception as exc:  # noqa: BLE001
        logging.exception("Failed to check orphan counts: %s", exc)


def _process_page_name_job(job: Dict[str, Any]) -> Dict[str, Any]:
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

    args = _build_regex_text_args(job)
    first_attempt = _run_regex_text_command(args)
    if first_attempt["success"]:
        return {
            "status": first_attempt["status"],
            "progress": first_attempt.get("progress") or progress,
            "error_message": None,
        }

    logging.error("Maintenance job %s failed: %s", job["id"], first_attempt.get("message"))
    retry_attempt = _run_regex_text_command(args, include_log=True)
    if retry_attempt["success"]:
        logging.info("Maintenance job %s recovered after retry with -log", job["id"])
        return {
            "status": retry_attempt["status"],
            "progress": retry_attempt.get("progress") or progress,
            "error_message": None,
        }

    combined_progress = (
        retry_attempt.get("progress")
        or first_attempt.get("progress")
        or progress
    )
    detailed_error = retry_attempt.get("raw_output") or first_attempt.get("raw_output") or ""
    message = retry_attempt.get("message") or first_attempt.get("message") or "maintenance handler failed"
    if detailed_error and detailed_error not in message:
        message = f"{message}\n{detailed_error}"
    return {
        "status": "error",
        "progress": combined_progress,
        "error_message": message.strip(),
    }


JOB_HANDLERS = {
    "page_name_update": _process_page_name_job,
}


def _process_job_queue():
    job: Optional[Dict[str, Any]] = None
    try:
        job = claim_next_maintenance_job()
        if not job:
            logging.debug("Maintenance job queue idle")
            return

        handler = JOB_HANDLERS.get(job["job_type"])
        if not handler:
            logging.error("Unknown maintenance job type '%s'", job["job_type"])
            update_maintenance_job(
                job_id=job["id"],
                status="error",
                error_message=f"Unknown job type {job['job_type']}",
            )
            return

        logging.info("Processing maintenance job %s (%s)", job["id"], job["job_type"])
        handler_result = handler(job)
        if not isinstance(handler_result, dict):
            handler_result = {
                "status": "error",
                "progress": job.get("progress"),
                "error_message": "Handler returned invalid response",
            }

        status = handler_result.get("status") or "running"
        progress_payload = handler_result.get("progress") or job.get("progress") or {}
        if not isinstance(progress_payload, dict):
            progress_payload = {}
        error_message = handler_result.get("error_message")

        update_maintenance_job(
            job_id=job["id"],
            status=status,
            progress=progress_payload,
            error_message=error_message,
        )

        if status == "error":
            logging.error(
                "Maintenance job %s marked as error: %s",
                job["id"],
                error_message or "maintenance handler failed",
            )
        elif status == "done":
            logging.info("Maintenance job %s completed", job["id"])
        else:
            logging.debug("Maintenance job %s progress updated", job["id"])

    except Exception as exc:  # noqa: BLE001
        logging.exception("Maintenance job processing failed: %s", exc)
        if job:
            try:
                update_maintenance_job(
                    job_id=job["id"],
                    status="error",
                    progress=job.get("progress"),
                    error_message=str(exc),
                )
            except Exception:  # noqa: BLE001
                logging.exception("Failed to mark job %s as error", job["id"])


def process_maintenance_jobs():
    """Run cache maintenance and queued maintenance work."""
    _run_cache_batch()
    _log_orphan_counts()
    _process_job_queue()


def main():
    configure_logging()
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    logging.info("Starting maintenance worker for project %s", PROJECT_NAME)

    while True:
        process_maintenance_jobs()
        time.sleep(SLEEP_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()


