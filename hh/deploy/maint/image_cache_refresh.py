"""Image cache refresh module for maintenance daemon."""

import logging
from typing import Any, Dict, List

from hh.gateway.connection.connection import (
    HenhouseConnection,
    get_connection,
    load_dsn_pair,
    r_query,
)
from hh.image.image_registry import get_image_conn


def fetch_stale_image_ids(conn, limit: int) -> List[int]:
    """Fetch stale image IDs from main database only.
    Staleness determined by: last_modified > cache_built_at OR cache_built_at IS NULL"""
    rows = r_query(
        conn,
        """
        SELECT id
        FROM images
        WHERE COALESCE(last_modified, uploaded) > cache_built_at
           OR cache_built_at IS NULL
        ORDER BY COALESCE(last_modified, uploaded) DESC
        LIMIT %s
        """,
        [limit],
    )
    return [row["id"] for row in rows]


def count_stale_images(conn) -> int:
    """Count stale images in main database only."""
    rows = r_query(
        conn,
        """
        SELECT COUNT(*) AS cnt
        FROM images
        WHERE COALESCE(last_modified, uploaded) > cache_built_at
           OR cache_built_at IS NULL
        """,
    )
    return rows[0]["cnt"] if rows else 0


def rebuild_images(conn, image_ids: List[int], errors: List[Dict[str, Any]]) -> List[int]:
    """Rebuild cache for a list of image IDs."""
    from hh.gateway.connection.connection import r_query
    from hh.gateway.error.error_store import is_error, get_errors
    
    processed: List[int] = []
    for image_id in image_ids:
        try:
            # Verify image exists first
            verify = r_query(conn, "SELECT id FROM images WHERE id = %s", [image_id])
            if not verify:
                logging.warning("Image %s does not exist in database (skipping)", image_id)
                errors.append({"entity": "image", "id": image_id, "error": "Image does not exist in database"})
                continue
            
            image_obj = get_image_conn(conn, image_id)
            if not image_obj:
                error_msg = f"Image {image_id} could not be loaded"
                if is_error():
                    errs = get_errors()
                    if errs:
                        # Get the most recent error message
                        error_contents = [str(e.content) for e in errs[-3:]]  # Last 3 errors
                        error_msg = f"Image {image_id} could not be loaded: {'; '.join(error_contents)}"
                logging.warning("Failed to load image %s: %s", image_id, error_msg)
                errors.append({"entity": "image", "id": image_id, "error": error_msg})
                continue
            
            image_obj.show_image()
            processed.append(image_id)
            logging.info("Cached image %s", image_id)
        except Exception as exc:  # noqa: BLE001
            logging.warning("Failed to cache image %s: %s", image_id, exc)
            errors.append({"entity": "image", "id": image_id, "error": str(exc)})
    return processed


def refresh_image_cache_batch(*, limit: int = 25) -> Dict[str, Any]:
    """Refresh image cache for a batch of stale images."""
    primary_dsn, cache_dsn = load_dsn_pair()
    if not primary_dsn or not cache_dsn:
        raise RuntimeError("Primary or cache DSN missing; cannot rebuild cache")

    primary_conn = None
    cache_only_conn = None
    try:
        primary_conn = get_connection(dict_cursor=True, dsn_override=primary_dsn)
        cache_only_conn = get_connection(dict_cursor=True, dsn_override=cache_dsn)
        if not primary_conn or not cache_only_conn:
            raise RuntimeError("Failed to open database connections for cache rebuild")

        combined_conn = HenhouseConnection(primary_conn, cache_only_conn)
        
        errors: List[Dict[str, Any]] = []
        stale_images = fetch_stale_image_ids(primary_conn, limit)
        logging.debug("Found %s stale images (limit %s)", len(stale_images), limit)
        processed_images = rebuild_images(combined_conn, stale_images, errors)

        # Flush cache-side writes
        try:
            cache_side = (
                combined_conn.get_connection(use_secondary=True)
                if hasattr(combined_conn, "get_connection")
                else cache_only_conn
            )
            cache_side.commit()
        except Exception:
            pass

        data: Dict[str, Any] = {
            "operation": "rebuild_image_cache",
            "limit": limit,
            "images_processed": len(processed_images),
            "images_remaining": count_stale_images(primary_conn),
            "processed_image_ids": processed_images,
            "errors": errors,
        }
        if processed_images or errors:
            logging.info(
                "Image cache rebuild complete: images=%s errors=%s",
                len(processed_images),
                len(errors),
            )
        return data
    finally:
        if cache_only_conn:
            cache_only_conn.close()
        if primary_conn:
            primary_conn.close()

