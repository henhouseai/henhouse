from __future__ import annotations

import datetime as dt
import json
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
from hh.tp.tp import TextProcessor

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

CACHE_VERSION = "v1"


def _json_default(value: Any):
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    return str(value)


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=_json_default)


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


def _store_page_cache(conn, page_obj, payload: Dict[str, Any]) -> None:
    page_block = payload.get("page", {}) or {}
    children_by_class = payload.get("children_by_class", {}) or {}
    images_data = payload.get("images", []) or []
    file_payload = {
        "upper_content": payload.get("upper_content", []) or [],
        "lower_content": payload.get("lower_content", []) or [],
    }
    badge_payload = payload.get("badge_headers", {}) or {}

    metadata_snapshot = _json_dumps(page_obj.metadata or {})
    children_json = _json_dumps(children_by_class)
    images_json = _json_dumps(images_data)
    file_json = _json_dumps(file_payload)
    links_json = _json_dumps(badge_payload)

    prepared_structure = None
    prepared_json = None
    try:
        processor = TextProcessor()
        prepared_structure = processor.preprocess(page_block.get("text") or "")
        if prepared_structure is not None:
            prepared_json = _json_dumps(prepared_structure)
            page_block["prepared_text"] = prepared_structure
    except Exception as exc:
        warn(f"Failed to preprocess text for page {page_obj.id}: {exc}")
        prepared_structure = None
        prepared_json = None

    source_last_modified = page_obj.last_modified or dt.datetime.utcnow()
    now = dt.datetime.utcnow()

    sql = """
        INSERT INTO pages (
            id, parent_id, class, name, link, text, metadata, prepared_text,
            children_summary, image_summary, file_summary, links_out,
            source_last_modified, cache_built_at, cache_version
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            parent_id = VALUES(parent_id),
            class = VALUES(class),
            name = VALUES(name),
            link = VALUES(link),
            text = VALUES(text),
            metadata = VALUES(metadata),
            prepared_text = VALUES(prepared_text),
            children_summary = VALUES(children_summary),
            image_summary = VALUES(image_summary),
            file_summary = VALUES(file_summary),
            links_out = VALUES(links_out),
            source_last_modified = VALUES(source_last_modified),
            cache_built_at = VALUES(cache_built_at),
            cache_version = VALUES(cache_version)
    """
    params = (
        page_obj.id,
        page_obj.parent,
        page_obj.class_name,
        page_obj.name,
        page_obj.link,
        page_block.get("text"),
        metadata_snapshot,
        prepared_json,
        children_json,
        images_json,
        file_json,
        links_json,
        source_last_modified,
        now,
        CACHE_VERSION,
    )
    u_query(conn, sql, params, use_secondary=True)


def _store_image_cache(conn, source_conn, image_id: int) -> None:
    image_obj = get_image_conn(source_conn, image_id)
    if not image_obj:
        raise RuntimeError(f"Image {image_id} could not be loaded")
    # Ensure instances are loaded for snapshot accuracy
    image_obj.load_instances()
    image_data = image_obj.get_image_data()
    instances_json = _json_dumps(image_data.get("instances", []))
    usage_rows = r_query(
        source_conn,
        """
            SELECT page_id, image_rank
            FROM image_groups
            WHERE image_id = %s
            ORDER BY image_rank
        """,
        [image_id],
    )
    pages_json = _json_dumps(usage_rows)
    source_last_modified = image_data.get("uploaded") or dt.datetime.utcnow()
    now = dt.datetime.utcnow()

    sql = """
        INSERT INTO images (
            id, caption, username, uploaded, visibility, viewCount,
            instances, pages, source_last_modified, cache_built_at, cache_version
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            caption = VALUES(caption),
            username = VALUES(username),
            uploaded = VALUES(uploaded),
            visibility = VALUES(visibility),
            viewCount = VALUES(viewCount),
            instances = VALUES(instances),
            pages = VALUES(pages),
            source_last_modified = VALUES(source_last_modified),
            cache_built_at = VALUES(cache_built_at),
            cache_version = VALUES(cache_version)
    """
    params = (
        image_id,
        image_data.get("caption"),
        image_data.get("username"),
        image_data.get("uploaded"),
        image_data.get("visibility"),
        image_data.get("view_count"),
        instances_json,
        pages_json,
        source_last_modified,
        now,
        CACHE_VERSION,
    )
    u_query(conn, sql, params, use_secondary=True)


def _rebuild_pages(conn, primary_conn, page_ids: List[int], errors: List[Dict[str, Any]]) -> List[int]:
    processed = []
    for page_id in page_ids:
        try:
            page_obj = get_page_conn(primary_conn, page_id)
            if not page_obj:
                raise RuntimeError(f"Page {page_id} not found")
            payload = page_obj.show_page()
            _store_page_cache(conn, page_obj, payload)
            processed.append(page_id)
            log(f"Cached page {page_id}")
        except Exception as exc:  # noqa: BLE001
            warn(f"Failed to cache page {page_id}: {exc}")
            errors.append({"entity": "page", "id": page_id, "error": str(exc)})
    return processed


def _rebuild_images(conn, primary_conn, image_ids: List[int], errors: List[Dict[str, Any]]) -> List[int]:
    processed = []
    for image_id in image_ids:
        try:
            _store_image_cache(conn, primary_conn, image_id)
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
            processed_pages = _rebuild_pages(cache_conn, primary_conn, stale_pages, errors)

        if include_images:
            stale_images = _fetch_stale_image_ids(primary_conn, cache_db, limit)
            log(f"Found {len(stale_images)} stale images (limit {limit})")
            processed_images = _rebuild_images(cache_conn, primary_conn, stale_images, errors)

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

