"""File cache refresh module for maintenance daemon."""

import logging
from typing import Any, Dict, List

from hh.gateway.connection.connection import (
    HenhouseConnection,
    get_connection,
    load_dsn_pair,
    r_query,
)
from hh.file.file_registry import get_file_conn


def fetch_stale_file_ids(conn, limit: int) -> List[int]:
    """Fetch stale file IDs from main database only.
    Staleness determined by: last_modified > cache_built_at OR cache_built_at IS NULL"""
    rows = r_query(
        conn,
        """
        SELECT id
        FROM files
        WHERE COALESCE(last_modified, uploaded) > cache_built_at
           OR cache_built_at IS NULL
        ORDER BY COALESCE(last_modified, uploaded) DESC
        LIMIT %s
        """,
        [limit],
    )
    return [row["id"] for row in rows]


def count_stale_files(conn) -> int:
    """Count stale files in main database only."""
    rows = r_query(
        conn,
        """
        SELECT COUNT(*) AS cnt
        FROM files
        WHERE COALESCE(last_modified, uploaded) > cache_built_at
           OR cache_built_at IS NULL
        """,
    )
    return rows[0]["cnt"] if rows else 0


def rebuild_files(conn, file_ids: List[int], errors: List[Dict[str, Any]]) -> List[int]:
    """Rebuild cache for a list of file IDs."""
    processed: List[int] = []
    for file_id in file_ids:
        try:
            file_obj = get_file_conn(conn, file_id)
            if not file_obj:
                raise RuntimeError(f"File {file_id} could not be loaded")
            # Trigger cache refresh by accessing usage data
            file_obj.get_usage_data()
            processed.append(file_id)
            logging.info("Cached file %s", file_id)
        except Exception as exc:  # noqa: BLE001
            logging.warning("Failed to cache file %s: %s", file_id, exc)
            errors.append({"entity": "file", "id": file_id, "error": str(exc)})
    return processed


def refresh_file_cache_batch(*, limit: int = 25) -> Dict[str, Any]:
    """Refresh file cache for a batch of stale files."""
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
        stale_files = fetch_stale_file_ids(primary_conn, limit)
        logging.debug("Found %s stale files (limit %s)", len(stale_files), limit)
        processed_files = rebuild_files(combined_conn, stale_files, errors)

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
            "operation": "rebuild_file_cache",
            "limit": limit,
            "files_processed": len(processed_files),
            "files_remaining": count_stale_files(primary_conn),
            "processed_file_ids": processed_files,
            "errors": errors,
        }
        if processed_files or errors:
            logging.info(
                "File cache rebuild complete: files=%s errors=%s",
                len(processed_files),
                len(errors),
            )
        return data
    finally:
        if cache_only_conn:
            cache_only_conn.close()
        if primary_conn:
            primary_conn.close()

