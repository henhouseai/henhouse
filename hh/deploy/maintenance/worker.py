import json
import logging
import os
import signal
import sys
import time
from subprocess import CalledProcessError, check_output, STDOUT
from typing import Any, Dict, Optional

import json
import logging
import os
import signal
import sys
import time
from subprocess import CalledProcessError, check_output, STDOUT
from typing import Any, Dict, Optional

from hh.deploy.maint.job_queue import claim_next_maintenance_job, update_maintenance_job
from hh.gateway.connection.connection import (
    HenhouseConnection,
    get_connection,
    load_dsn_pair,
    r_query,
)
from hh.gateway.connection.decorators import db_read
from hh.image.image_registry import get_image_conn
from hh.page.page_registry import get_page_conn

PROJECT_NAME = "__PROJECT_NAME__"
SLEEP_INTERVAL_SECONDS = 5
CACHE_BATCH_LIMIT = 2  # Keep batches very small to avoid long-running transactions
NAME_JOB_BATCH_LIMIT = int(os.getenv("MAINTENANCE_NAME_BATCH", "25"))
CACHE_VERSION = "v1"


def _qualify_cache_table(cache_db: str, table: str) -> str:
    safe_db = cache_db.replace("`", "")
    safe_table = table.replace("`", "")
    return f"`{safe_db}`.`{safe_table}`"


def _fetch_stale_page_ids(conn, cache_db: str, limit: int) -> list[int]:
    cache_pages = _qualify_cache_table(cache_db, "pages")
    rows = r_query(
        conn,
        f"""
        SELECT p.id
        FROM pages p
        LEFT JOIN {cache_pages} cp ON cp.id = p.id
        WHERE cp.id IS NULL
           OR (p.last_modified IS NOT NULL
               AND (cp.source_last_modified IS NULL OR cp.source_last_modified < p.last_modified))
        ORDER BY p.last_modified DESC
        LIMIT %s
        """,
        [limit],
    )
    return [row["id"] for row in rows]


def _count_stale_pages(conn, cache_db: str) -> int:
    cache_pages = _qualify_cache_table(cache_db, "pages")
    rows = r_query(
        conn,
        f"""
        SELECT COUNT(*) AS cnt
        FROM pages p
        LEFT JOIN {cache_pages} cp ON cp.id = p.id
        WHERE cp.id IS NULL
           OR (p.last_modified IS NOT NULL
               AND (cp.source_last_modified IS NULL OR cp.source_last_modified < p.last_modified))
        """,
    )
    return rows[0]["cnt"] if rows else 0


def _fetch_stale_image_ids(conn, cache_db: str, limit: int) -> list[int]:
    cache_images = _qualify_cache_table(cache_db, "images")
    rows = r_query(
        conn,
        f"""
        SELECT i.id
        FROM images i
        LEFT JOIN {cache_images} ci ON ci.id = i.id
        WHERE ci.id IS NULL
           OR (
                ci.source_last_modified IS NULL
                OR (
                    COALESCE(i.last_modified, i.uploaded) IS NOT NULL
                    AND ci.source_last_modified < COALESCE(i.last_modified, i.uploaded)
                )
             )
        ORDER BY COALESCE(i.last_modified, i.uploaded) DESC
        LIMIT %s
        """,
        [limit],
    )
    return [row["id"] for row in rows]


def _count_stale_images(conn, cache_db: str) -> int:
    cache_images = _qualify_cache_table(cache_db, "images")
    rows = r_query(
        conn,
        f"""
        SELECT COUNT(*) AS cnt
        FROM images i
        LEFT JOIN {cache_images} ci ON ci.id = i.id
        WHERE ci.id IS NULL
           OR (
                ci.source_last_modified IS NULL
                OR (
                    COALESCE(i.last_modified, i.uploaded) IS NOT NULL
                    AND ci.source_last_modified < COALESCE(i.last_modified, i.uploaded)
                )
             )
        """,
    )
    return rows[0]["cnt"] if rows else 0


def _rebuild_pages(conn, page_ids: list[int], errors: list[dict[str, Any]]) -> list[int]:
    processed: list[int] = []
    for page_id in page_ids:
        try:
            page_obj = get_page_conn(conn, page_id)
            if not page_obj:
                raise RuntimeError(f"Page {page_id} not found")
            page_obj.show_page()
            processed.append(page_id)
            logging.info("Cached page %s", page_id)
        except Exception as exc:  # noqa: BLE001
            logging.warning("Failed to cache page %s: %s", page_id, exc)
            errors.append({"entity": "page", "id": page_id, "error": str(exc)})
    return processed


def _rebuild_images(conn, image_ids: list[int], errors: list[dict[str, Any]]) -> list[int]:
    processed: list[int] = []
    for image_id in image_ids:
        try:
            image_obj = get_image_conn(conn, image_id)
            if not image_obj:
                raise RuntimeError(f"Image {image_id} could not be loaded")
            image_obj.show_image()
            processed.append(image_id)
            logging.info("Cached image %s", image_id)
        except Exception as exc:  # noqa: BLE001
            logging.warning("Failed to cache image %s: %s", image_id, exc)
            errors.append({"entity": "image", "id": image_id, "error": str(exc)})
    return processed


def _perform_cache_rebuild(
    primary_conn,
    cache_conn,
    cache_db: str,
    limit: int,
    include_pages: bool,
    include_images: bool,
) -> Dict[str, Any]:
    errors: list[Dict[str, Any]] = []
    processed_pages: list[int] = []
    processed_images: list[int] = []

    if include_pages:
        stale_pages = _fetch_stale_page_ids(primary_conn, cache_db, limit)
        logging.debug("Found %s stale pages (limit %s)", len(stale_pages), limit)
        processed_pages = _rebuild_pages(cache_conn, stale_pages, errors)

    if include_images:
        stale_images = _fetch_stale_image_ids(primary_conn, cache_db, limit)
        logging.debug("Found %s stale images (limit %s)", len(stale_images), limit)
        processed_images = _rebuild_images(cache_conn, stale_images, errors)

    # Flush cache-side writes
    try:
        cache_side = (
            cache_conn.get_connection(use_secondary=True)
            if hasattr(cache_conn, "get_connection")
            else cache_conn
        )
        cache_side.commit()
    except Exception:
        pass

    data: Dict[str, Any] = {
        "operation": "rebuild_cache",
        "cache_database": cache_db,
        "limit": limit,
        "pages_processed": len(processed_pages),
        "images_processed": len(processed_images),
        "pages_remaining": _count_stale_pages(primary_conn, cache_db) if include_pages else 0,
        "images_remaining": _count_stale_images(primary_conn, cache_db) if include_images else 0,
        "processed_page_ids": processed_pages,
        "processed_image_ids": processed_images,
        "errors": errors,
    }
    if processed_pages or processed_images or errors:
        logging.info(
            "Cache rebuild complete: pages=%s images=%s errors=%s",
            len(processed_pages),
            len(processed_images),
            len(errors),
        )
    return data


def _run_cache_rebuild_batch(
    *, limit: int = 25, include_pages: bool = True, include_images: bool = True
) -> Dict[str, Any]:
    primary_dsn, cache_dsn = load_dsn_pair()
    if not primary_dsn or not cache_dsn:
        raise RuntimeError("Primary or cache DSN missing; cannot rebuild cache")

    cache_db = cache_dsn.get("database")
    if not cache_db:
        raise RuntimeError("Cache database name missing from DSN")

    primary_conn = None
    cache_only_conn = None
    try:
        primary_conn = get_connection(dict_cursor=True, dsn_override=primary_dsn)
        cache_only_conn = get_connection(dict_cursor=True, dsn_override=cache_dsn)
        if not primary_conn or not cache_only_conn:
            raise RuntimeError("Failed to open database connections for cache rebuild")

        combined_conn = HenhouseConnection(primary_conn, cache_only_conn)
        return _perform_cache_rebuild(primary_conn, combined_conn, cache_db, limit, include_pages, include_images)
    finally:
        if cache_only_conn:
            cache_only_conn.close()
        if primary_conn:
            primary_conn.close()


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


def _build_regex_text_args(job: Dict[str, Any], resolution_id: int) -> list[str]:
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
        result = _run_cache_rebuild_batch(
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


@db_read
def _get_referencing_page_ids(conn, source_page_id: int, last_page_id: int, batch_limit: int):
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


