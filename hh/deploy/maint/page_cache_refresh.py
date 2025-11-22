"""Page cache refresh module for maintenance daemon."""

import logging
from typing import Any, Dict, List

from hh.gateway.connection.connection import (
    HenhouseConnection,
    get_connection,
    load_dsn_pair,
    r_query,
)
from hh.page.page_registry import get_page_conn


def fetch_stale_page_ids(conn, limit: int) -> List[int]:
    """Fetch stale page IDs from main database only.
    Staleness determined by: last_modified > cache_built_at OR cache_built_at IS NULL"""
    rows = r_query(
        conn,
        """
        SELECT id
        FROM pages
        WHERE last_modified > cache_built_at
           OR cache_built_at IS NULL
        ORDER BY last_modified DESC
        LIMIT %s
        """,
        [limit],
    )
    return [row["id"] for row in rows]


def count_stale_pages(conn) -> int:
    """Count stale pages in main database only."""
    rows = r_query(
        conn,
        """
        SELECT COUNT(*) AS cnt
        FROM pages
        WHERE last_modified > cache_built_at
           OR cache_built_at IS NULL
        """,
    )
    return rows[0]["cnt"] if rows else 0


def rebuild_pages(conn, page_ids: List[int], errors: List[Dict[str, Any]]) -> List[int]:
    """Rebuild cache for a list of page IDs."""
    processed: List[int] = []
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


def refresh_page_cache_batch(*, limit: int = 25) -> Dict[str, Any]:
    """Refresh page cache for a batch of stale pages."""
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
        stale_pages = fetch_stale_page_ids(primary_conn, limit)
        logging.debug("Found %s stale pages (limit %s)", len(stale_pages), limit)
        processed_pages = rebuild_pages(combined_conn, stale_pages, errors)

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
            "operation": "rebuild_page_cache",
            "limit": limit,
            "pages_processed": len(processed_pages),
            "pages_remaining": count_stale_pages(primary_conn),
            "processed_page_ids": processed_pages,
            "errors": errors,
        }
        if processed_pages or errors:
            logging.info(
                "Page cache rebuild complete: pages=%s errors=%s",
                len(processed_pages),
                len(errors),
            )
        return data
    finally:
        if cache_only_conn:
            cache_only_conn.close()
        if primary_conn:
            primary_conn.close()

