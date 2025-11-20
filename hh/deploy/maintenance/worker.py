import logging
import os
import signal
import sys
import time

from hh.deploy.cache.rebuild_cache import run_cache_rebuild_batch

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


def process_maintenance_jobs():
    """Run cache maintenance batch and log the outcome."""
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


