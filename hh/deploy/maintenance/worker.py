import logging
import os
import signal
import sys
import time
from typing import Any, Dict, Optional

from hh.deploy.maint.job_queue import claim_next_maintenance_job, update_maintenance_job
from hh.gateway.connection.connection import get_connection, load_dsn_pair
from hh.deploy.maint.page_cache_refresh import refresh_page_cache_batch
from hh.deploy.maint.image_cache_refresh import refresh_image_cache_batch
from hh.deploy.maint.file_cache_refresh import refresh_file_cache_batch
from hh.deploy.maint.orphan_checks import check_orphans
from hh.deploy.maint.name_update import process_page_name_job

PROJECT_NAME = "__PROJECT_NAME__"
SLEEP_INTERVAL_SECONDS = 5
CACHE_BATCH_LIMIT = 2  # Keep batches very small to avoid long-running transactions




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
    """Run cache refresh batches for pages, images, and files."""
    try:
        # Refresh page cache
        page_result = refresh_page_cache_batch(limit=CACHE_BATCH_LIMIT)
        pages_processed = page_result.get("pages_processed", 0)
        pages_remaining = page_result.get("pages_remaining", 0)
        
        # Refresh image cache
        image_result = refresh_image_cache_batch(limit=CACHE_BATCH_LIMIT)
        images_processed = image_result.get("images_processed", 0)
        images_remaining = image_result.get("images_remaining", 0)
        
        # Refresh file cache
        file_result = refresh_file_cache_batch(limit=CACHE_BATCH_LIMIT)
        files_processed = file_result.get("files_processed", 0)
        files_remaining = file_result.get("files_remaining", 0)

        if pages_processed or images_processed or files_processed:
            logging.info(
                "Cache rebuild batch: pages=%s images=%s files=%s remaining_pages=%s remaining_images=%s remaining_files=%s",
                pages_processed,
                images_processed,
                files_processed,
                pages_remaining,
                images_remaining,
                files_remaining,
            )
        else:
            logging.debug(
                "Cache rebuild idle: remaining_pages=%s remaining_images=%s remaining_files=%s",
                pages_remaining,
                images_remaining,
                files_remaining,
            )
    except Exception as exc:  # noqa: BLE001
        logging.exception("Cache rebuild batch failed: %s", exc)


def log_orphan_counts(conn) -> None:
    """Check and log orphan counts with IDs."""
    counts = check_orphans()
    
    orphan_pages = counts.get("orphan_pages", [])
    orphan_link_sources = counts.get("orphan_link_sources", [])
    orphan_link_targets = counts.get("orphan_link_targets", [])
    orphan_image_pages = counts.get("orphan_image_pages", [])
    orphan_image_targets = counts.get("orphan_image_targets", [])
    orphan_image_group_pages = counts.get("orphan_image_group_pages", [])
    orphan_image_group_images = counts.get("orphan_image_group_images", [])
    orphan_file_group_pages = counts.get("orphan_file_group_pages", [])
    orphan_file_group_files = counts.get("orphan_file_group_files", [])

    if orphan_pages:
        page_ids = ",".join(str(p) for p in orphan_pages)
        logging.warning("Orphan pages detected (child missing parent): %s [IDs: %s]", len(orphan_pages), page_ids)
    if orphan_link_sources or orphan_link_targets:
        source_ids = ",".join(str(s) for s in orphan_link_sources) if orphan_link_sources else "none"
        target_ids = ",".join(str(t) for t in orphan_link_targets) if orphan_link_targets else "none"
        logging.warning(
            "Orphan links detected: source_missing=%s [IDs: %s] target_missing=%s [IDs: %s]",
            len(orphan_link_sources),
            source_ids,
            len(orphan_link_targets),
            target_ids,
        )
    if orphan_image_pages or orphan_image_targets:
        page_ids = ",".join(str(p) for p in orphan_image_pages) if orphan_image_pages else "none"
        image_ids = ",".join(str(i) for i in orphan_image_targets) if orphan_image_targets else "none"
        logging.warning(
            "Orphan image links detected: page_missing=%s [IDs: %s] image_missing=%s [IDs: %s]",
            len(orphan_image_pages),
            page_ids,
            len(orphan_image_targets),
            image_ids,
        )
    if orphan_image_group_pages or orphan_image_group_images:
        page_ids = ",".join(str(p) for p in orphan_image_group_pages) if orphan_image_group_pages else "none"
        image_ids = ",".join(str(i) for i in orphan_image_group_images) if orphan_image_group_images else "none"
        logging.warning(
            "Orphan image_groups detected: page_missing=%s [IDs: %s] image_missing=%s [IDs: %s]",
            len(orphan_image_group_pages),
            page_ids,
            len(orphan_image_group_images),
            image_ids,
        )
    if orphan_file_group_pages or orphan_file_group_files:
        page_ids = ",".join(str(p) for p in orphan_file_group_pages) if orphan_file_group_pages else "none"
        file_ids = ",".join(str(f) for f in orphan_file_group_files) if orphan_file_group_files else "none"
        logging.warning(
            "Orphan file_groups detected: page_missing=%s [IDs: %s] file_missing=%s [IDs: %s]",
            len(orphan_file_group_pages),
            page_ids,
            len(orphan_file_group_files),
            file_ids,
        )


def _log_orphan_counts():
    """Check and log orphan counts."""
    try:
        primary_dsn, _ = load_dsn_pair()
        if not primary_dsn:
            return
        conn = get_connection(dict_cursor=True, dsn_override=primary_dsn)
        if conn:
            try:
                log_orphan_counts(conn)
            finally:
                conn.close()
    except Exception as exc:  # noqa: BLE001
        logging.exception("Failed to check orphan counts: %s", exc)


def _process_page_name_job_wrapper(job: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for page name job that provides connection."""
    primary_dsn, _ = load_dsn_pair()
    if not primary_dsn:
        return {
            "status": "error",
            "progress": job.get("progress", {}),
            "error_message": "Primary DSN missing",
        }
    conn = get_connection(dict_cursor=True, dsn_override=primary_dsn)
    try:
        return process_page_name_job(job, conn)
    finally:
        if conn:
            conn.close()


JOB_HANDLERS = {
    "page_name_update": _process_page_name_job_wrapper,
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


