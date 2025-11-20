from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Tuple

from hh.gateway.connection.connection import load_dsn_pair, r_query, u_query
from hh.gateway.connection.decorators import db_read
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import (
    get_debug,
    get_log,
    get_trace_in,
    get_trace_out,
    get_warn,
    register_debug_init,
)
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.response.json_standard import success_payload
from hh.image.image_registry import get_image_conn
from hh.page.page_registry import get_page_conn

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

CACHE_VERSION = "v1"


@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


def _parse_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    value = value.strip().lower()
    if value in ("1", "true", "yes", "y", "on"):
        return True
    if value in ("0", "false", "no", "n", "off"):
        return False
    return None


def _qualify_cache_table(cache_db: str, table: str) -> str:
    safe_db = cache_db.replace("`", "")
    safe_table = table.replace("`", "")
    return f"`{safe_db}`.`{safe_table}`"


def _fetch_stale_page_ids(conn, cache_db: str, limit: int) -> List[int]:
    cache_pages = _qualify_cache_table(cache_db, "pages")
    sql = f"""
        SELECT p.id
        FROM pages p
        LEFT JOIN {cache_pages} cp ON cp.id = p.id
        WHERE cp.id IS NULL
           OR (p.last_modified IS NOT NULL
               AND (cp.source_last_modified IS NULL OR cp.source_last_modified < p.last_modified))
        ORDER BY p.last_modified DESC
        LIMIT %s
    """
    rows = r_query(conn, sql, [limit])
    return [row["id"] for row in rows]


def _count_stale_pages(conn, cache_db: str) -> int:
    cache_pages = _qualify_cache_table(cache_db, "pages")
    sql = f"""
        SELECT COUNT(*) AS cnt
        FROM pages p
        LEFT JOIN {cache_pages} cp ON cp.id = p.id
        WHERE cp.id IS NULL
           OR (p.last_modified IS NOT NULL
               AND (cp.source_last_modified IS NULL OR cp.source_last_modified < p.last_modified))
    """
    rows = r_query(conn, sql, [])
    return rows[0]["cnt"] if rows else 0


def _fetch_stale_image_ids(conn, cache_db: str, limit: int) -> List[int]:
    cache_images = _qualify_cache_table(cache_db, "images")
    sql = f"""
        SELECT i.id
        FROM images i
        LEFT JOIN {cache_images} ci ON ci.id = i.id
        WHERE ci.id IS NULL
           OR (ci.source_last_modified IS NULL OR (i.uploaded IS NOT NULL AND ci.source_last_modified < i.uploaded))
        ORDER BY i.uploaded DESC
        LIMIT %s
    """
    rows = r_query(conn, sql, [limit])
    return [row["id"] for row in rows]


def _count_stale_images(conn, cache_db: str) -> int:
    cache_images = _qualify_cache_table(cache_db, "images")
    sql = f"""
        SELECT COUNT(*) AS cnt
        FROM images i
        LEFT JOIN {cache_images} ci ON ci.id = i.id
        WHERE ci.id IS NULL
           OR (ci.source_last_modified IS NULL OR (i.uploaded IS NOT NULL AND ci.source_last_modified < i.uploaded))
    """
    rows = r_query(conn, sql, [])
    return rows[0]["cnt"] if rows else 0


def _rebuild_pages(conn, page_ids: List[int], errors: List[Dict[str, Any]]) -> List[int]:
    processed = []
    for page_id in page_ids:
        try:
            page_obj = get_page_conn(conn, page_id)
            if not page_obj:
                raise RuntimeError(f"Page {page_id} not found")
            page_obj.show_page()
            processed.append(page_id)
            log(f"Cached page {page_id}")
        except Exception as exc:  # noqa: BLE001
            warn(f"Failed to cache page {page_id}: {exc}")
            errors.append({"entity": "page", "id": page_id, "error": str(exc)})
    return processed


def _rebuild_images(conn, image_ids: List[int], errors: List[Dict[str, Any]]) -> List[int]:
    processed = []
    for image_id in image_ids:
        try:
            image_obj = get_image_conn(conn, image_id)
            if not image_obj:
                raise RuntimeError(f"Image {image_id} could not be loaded")
            image_obj.show_image()
            processed.append(image_id)
            log(f"Cached image {image_id}")
        except Exception as exc:  # noqa: BLE001
            warn(f"Failed to cache image {image_id}: {exc}")
            errors.append({"entity": "image", "id": image_id, "error": str(exc)})
    return processed


def _parse_limit_arg(raw_value: Optional[str]) -> int:
    default_limit = 25
    if not raw_value:
        return default_limit
    try:
        parsed = int(raw_value)
        return max(1, min(parsed, 250))
    except (TypeError, ValueError):
        return default_limit


@register_action("rebuild_cache")
@register_command("rebuild_cache")
@db_read
def rebuild_cache(conn) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False

    _, cache_dsn = load_dsn_pair()
    if not cache_dsn or not cache_dsn.get("database"):
        warn("Cache DSN was not detected")
        report_error("backend", "Cache DSN missing")
        trace_out()
        return False
    cache_db = cache_dsn["database"]

    limit = _parse_limit_arg(gateway.get_arg("limit"))
    pages_flag = _parse_bool(gateway.get_arg("pages"))
    images_flag = _parse_bool(gateway.get_arg("images"))

    if pages_flag is None and images_flag is None:
        include_pages = True
        include_images = True
    else:
        include_pages = bool(pages_flag)
        include_images = bool(images_flag)
        if not include_pages and not include_images:
            report_error("action", "At least one of pages/images must be true")
            trace_out()
            return False

    primary_conn = conn.primary if hasattr(conn, "primary") else conn
    cache_conn = conn

    errors: List[Dict[str, Any]] = []
    processed_pages: List[int] = []
    processed_images: List[int] = []

    try:
        if include_pages:
            stale_pages = _fetch_stale_page_ids(primary_conn, cache_db, limit)
            log(f"Found {len(stale_pages)} stale pages (limit {limit})")
            processed_pages = _rebuild_pages(cache_conn, stale_pages, errors)

        if include_images:
            stale_images = _fetch_stale_image_ids(primary_conn, cache_db, limit)
            log(f"Found {len(stale_images)} stale images (limit {limit})")
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

        data = {
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
        gateway.response.set_action_response(success_payload(data))
        log(
            f"Cache rebuild complete: pages={len(processed_pages)}, images={len(processed_images)}, "
            f"errors={len(errors)}"
        )
        trace_out()
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"Cache rebuild failed: {exc}")
        report_error("backend", f"Cache rebuild failed: {exc}")
        trace_out()
        return False

