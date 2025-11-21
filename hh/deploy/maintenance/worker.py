import logging
import os
import signal
import sys
import time
from subprocess import CalledProcessError, check_output, STDOUT
from typing import Any, Dict, Optional

from hh.deploy.cache.rebuild_cache import run_cache_rebuild_batch
from hh.deploy.maint.job_queue import claim_next_maintenance_job, update_maintenance_job
from hh.gateway.connection.connection import HenhouseConnection, get_connection, load_dsn_pair, r_query

PROJECT_NAME = "__PROJECT_NAME__"
SLEEP_INTERVAL_SECONDS = 5
CACHE_BATCH_LIMIT = 2  # Keep batches very small to avoid long-running transactions
NAME_JOB_BATCH_LIMIT = int(os.getenv("MAINTENANCE_NAME_BATCH", "25"))


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


def _open_connection_bundle() -> Optional[Dict[str, Any]]:
    primary_dsn, cache_dsn = load_dsn_pair()
    if not primary_dsn or not cache_dsn:
        logging.warning("Maintenance worker could not detect DSN pair")
        return None
    primary_conn = get_connection(dict_cursor=True, dsn_override=primary_dsn)
    cache_conn = get_connection(dict_cursor=True, dsn_override=cache_dsn)
    if not primary_conn or not cache_conn:
        logging.warning("Failed to open maintenance worker database connections")
        if primary_conn:
            primary_conn.close()
        if cache_conn:
            cache_conn.close()
        return None
    hen_conn = HenhouseConnection(primary_conn, cache_conn)
    return {"primary": primary_conn, "cache": cache_conn, "henhouse": hen_conn}


def _close_connection_bundle(bundle: Optional[Dict[str, Any]]) -> None:
    if not bundle:
        return
    try:
        bundle["primary"].close()
    except Exception:  # noqa: BLE001
        logging.exception("Failed to close primary connection")
    try:
        bundle["cache"].close()
    except Exception:  # noqa: BLE001
        logging.exception("Failed to close cache connection")


def _log_orphan_counts():
    primary_dsn, _ = load_dsn_pair()
    if not primary_dsn:
        logging.warning("Cannot check orphans: missing DSN")
        return
    conn = get_connection(dict_cursor=True, dsn_override=primary_dsn)
    if not conn:
        logging.warning("Cannot check orphans: failed to open connection")
        return
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
    finally:
        conn.close()


def _process_page_name_job(job: Dict[str, Any]) -> bool:
    payload = job.get("payload") or {}
    progress = job.get("progress") or {}
    job["progress"] = progress

    page_id = payload.get("page_id")
    old_name = payload.get("old_name")
    new_name = payload.get("new_name")

    if not (page_id and old_name and new_name):
        logging.warning("Job %s missing rename payload; marking done", job["id"])
        return True

    last_page_id = progress.get("last_page_id", 0)
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
        "--job_id",
        str(job["id"]),
    ]

    try:
        result_text = check_output(
            ["python3", f"/srv/{PROJECT_NAME}/maintenance_client.py"] + args,
            stderr=STDOUT,
            text=True,
        )
        logging.info("Maintenance job %s output: %s", job["id"], result_text.strip())
        return '"done": true' in result_text.lower()
    except CalledProcessError as exc:
        logging.error("Maintenance job %s failed: %s", job["id"], exc.output)
        return False


JOB_HANDLERS = {
    "page_name_update": _process_page_name_job,
}


def _process_job_queue():
    connections = _open_connection_bundle()
    if not connections:
        return

    job: Optional[Dict[str, Any]] = None
    try:
        connections["primary"].begin()
        job = claim_next_maintenance_job(connections["primary"])
        if not job:
            connections["primary"].commit()
            logging.debug("Maintenance job queue idle")
            return

        handler = JOB_HANDLERS.get(job["job_type"])
        if not handler:
            logging.error("Unknown maintenance job type '%s'", job["job_type"])
            update_maintenance_job(
                connections["primary"],
                job["id"],
                status="error",
                error_message=f"Unknown job type {job['job_type']}",
            )
            connections["primary"].commit()
            return

        logging.info("Processing maintenance job %s (%s)", job["id"], job["job_type"])
        job_complete = handler(job)
        connections["primary"].commit()
    except Exception as exc:  # noqa: BLE001
        connections["primary"].rollback()
        logging.exception("Maintenance job processing failed: %s", exc)
        if job:
            try:
                connections["primary"].begin()
                update_maintenance_job(
                    connections["primary"],
                    job["id"],
                    status="error",
                    progress=job.get("progress"),
                    error_message=str(exc),
                )
                connections["primary"].commit()
            except Exception:  # noqa: BLE001
                connections["primary"].rollback()
                logging.exception("Failed to mark job %s as error", job["id"])
    finally:
        _close_connection_bundle(connections)


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


