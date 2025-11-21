from __future__ import annotations

import datetime as dt
import json
from typing import Any, Dict, Optional, List

from hh.gateway.connection.connection import r_query, c_query, u_query
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.gateway.error.error_store import report_error, is_error
from hh.image.image_method_registry import register_image_mixin_methods
from hh.image.image_registry import invalidate_image_cache_entry


trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None


@register_debug_init
def _initialize_image_cache_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


CACHE_VERSION = "v1"


@register_image_mixin_methods
def _register_cache_methods():
    return {
        'refresh_cached_image': {'mixin_method': '_refresh_cached_image', 'decorator': 'write'},
        'ensure_image_cache_entry': {'mixin_method': '_ensure_image_cache_entry', 'decorator': 'write'},
        'clear_cached_image_state': {'mixin_method': '_clear_cached_image_state', 'decorator': 'read'},
    }


class ImageCacheMixin:

    def _ensure_image_cache_entry(self) -> bool:
        trace_in()
        try:
            existing = r_query(
                self.conn,
                "SELECT 1 FROM images WHERE id = %s",
                (self.id,),
                use_secondary=True,
            )
        except Exception as exc:
            warn(f"Failed to check cache entry for image {self.id}: {exc}")
            report_error("connection", f"Failed to verify cache for image {self.id}")
            trace_out()
            return False

        if existing:
            trace_out()
            return True

        now = dt.datetime.now()
        try:
            c_query(
                self.conn,
                """
                    INSERT INTO images (
                        id, caption, username, uploaded, last_modified, comments, visibility, viewCount,
                        instances, pages, source_last_modified, cache_built_at, cache_version
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    self.id,
                    self.caption,
                    self.username,
                    self.uploaded,
                    self.last_modified or self.uploaded or now,
                    self.comments,
                    self.visibility if self.visibility is not None else 1,
                    self.view_count if self.view_count is not None else 0,
                    self._dump_json(self.instances or []),
                    self._dump_json([]),
                    self.last_modified or self.uploaded or now,
                    now,
                    CACHE_VERSION,
                ),
                use_secondary=True,
            )
            debug(f"Created cache entry for image {self.id}")
        except Exception as exc:
            warn(f"Failed to insert cache entry for image {self.id}: {exc}")
            report_error("connection", f"Failed to create cache entry for image {self.id}")
            trace_out()
            return False

        trace_out()
        return True

    def _refresh_cached_image(self, payload: Dict[str, Any]) -> bool:
        trace_in()
        if not payload:
            warn(f"No payload provided for image {self.id} cache refresh")
            trace_out()
            return False

        if not self._ensure_image_cache_entry():
            trace_out()
            return False

        image_block = payload.get("image", {}) or {}
        usage_data = payload.get("usage", []) or []
        instances_data = payload.get("instances", []) or []

        instances_json = self._dump_json(instances_data)
        usage_json = self._dump_json(usage_data)
        now = dt.datetime.now()
        payload_last_modified = image_block.get("last_modified") or self.last_modified
        source_last_modified = (
            payload_last_modified
            or image_block.get("uploaded")
            or self.uploaded
            or now
        )
        comments_value = image_block.get("comments", self.comments)

        try:
            u_query(
                self.conn,
                """
                    UPDATE images
                    SET caption = %s,
                        username = %s,
                        uploaded = %s,
                        last_modified = %s,
                        comments = %s,
                        visibility = %s,
                        viewCount = %s,
                        instances = %s,
                        pages = %s,
                        source_last_modified = %s,
                        cache_built_at = %s,
                        cache_version = %s
                    WHERE id = %s
                """,
                (
                    image_block.get("caption", self.caption),
                    image_block.get("username", self.username),
                    image_block.get("uploaded", self.uploaded),
                    payload_last_modified or source_last_modified,
                    comments_value,
                    image_block.get("visibility", self.visibility if self.visibility is not None else 1),
                    image_block.get("view_count", self.view_count if self.view_count is not None else 0),
                    instances_json,
                    usage_json,
                    source_last_modified,
                    now,
                    CACHE_VERSION,
                    self.id,
                ),
                use_secondary=True,
            )
            debug(
                f"Refreshed cache for image {self.id}: "
                f"instances={len(instances_data)}, usage_entries={len(usage_data)}"
            )
        except Exception as exc:
            warn(f"Failed to update cache for image {self.id}: {exc}")
            report_error("connection", f"Failed to update cache for image {self.id}")
            trace_out()
            return False

        invalidate_image_cache_entry(self.id)
        trace_out()
        return not is_error()

    def _clear_cached_image_state(self) -> None:
        trace_in()
        self.cached_usage = None
        self.cache_built_at = None
        self.cache_source_last_modified = None
        self.cache_hydrated = False
        trace_out()

    def _dump_json(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'), default=self._json_default)

    def _json_default(self, value: Any):
        if isinstance(value, (dt.datetime, dt.date)):
            return value.isoformat()
        return value
