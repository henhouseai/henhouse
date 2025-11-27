from __future__ import annotations

import datetime as dt
import json
from typing import Any, Dict, Optional, List

from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.gateway.error.error_store import report_error, is_error


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


# Cache methods are NOT registered in the mixin registry - they are called directly
# by the wrapper system in image.py, similar to page_cache.py


class ImageCacheMixin:

    def _ensure_image_cache_entry(self) -> bool:
        """Ensure cache entry exists in cache database. Only creates if missing."""
        trace_in()
        try:
            existing = self.gateway.conn.read_cache(
                "SELECT 1 FROM images WHERE id = %s",
                (self.id,),
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
            self.gateway.conn.create_cache(
                """
                    INSERT INTO images (id, instances, pages, metadata, cache_built_at)
                    VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    self.id,
                    self._dump_json([]),  # Empty instances initially
                    self._dump_json([]),  # Empty pages initially
                    self._dump_json({}),  # Empty metadata initially
                    now,
                ),
            )
            debug(f"Created cache entry for image {self.id}")
        except Exception as exc:
            warn(f"Failed to insert cache entry for image {self.id}: {exc}")
            report_error("connection", f"Failed to create cache entry for image {self.id}")
            trace_out()
            return False

        trace_out()
        return True

    def _flag_cache_refresh(self) -> None:
        """Flag that the cache needs to be refreshed. Called by getters when they derive/calculate data."""
        self._cache_needs_refresh = True

    def _refresh_cached_image(self) -> bool:
        """Refresh the cache database with instances and pages (usage) fields. Called by gateway during commit."""
        trace_in()
        debug(f"_refresh_cached_image: Starting for image {self.id}")
        if not self.gateway or not self.gateway.conn:
            warn(f"_refresh_cached_image: gateway or connection not available for image {self.id}")
            trace_out()
            return False
        if not self._ensure_image_cache_entry():
            debug(f"_refresh_cached_image: Failed to ensure cache entry for image {self.id}")
            trace_out()
            return False

        # Ensure both fields are populated by calling their internal mixin methods
        # The getters check if field is populated first, and only hydrate if empty
        # This ensures we always have fully hydrated data to cache
        
        if not self.instances:
            self.instances = self.get_instances()
        
        # Get usage data if cached_usage is empty
        if not self.cached_usage:
            self.cached_usage = self._get_usage_data()
        
        # Serialize all data
        instances_json = self._dump_json(self.instances) if self.instances else None
        usage_json = self._dump_json(self.cached_usage) if self.cached_usage else None
        
        # Zip all main database fields into metadata for cache backup
        # This allows full image hydration from cache database without main DB access
        main_db_metadata = {
            'caption': self.caption,
            'username': self.username,
            'uploaded': self.uploaded.isoformat() if self.uploaded else None,
            'last_modified': self.last_modified.isoformat() if self.last_modified else None,
            'comments': self.comments,
            'visibility': self.visibility,
            'viewCount': self.view_count,
        }
        metadata_json = self._dump_json(main_db_metadata)
        
        now = dt.datetime.now()
        
        try:
            # Update cache database
            affected = self.gateway.conn.update_cache(
                """
                    UPDATE images
                    SET instances = %s,
                        pages = %s,
                        metadata = %s,
                        cache_built_at = %s
                    WHERE id = %s
                """,
                (
                    instances_json,
                    usage_json,
                    metadata_json,
                    now,
                    self.id,
                ),
            )
            # Update main database cache_built_at
            if affected > 0:
                self.gateway.conn.update(
                    """
                        UPDATE images
                        SET cache_built_at = %s
                        WHERE id = %s
                    """,
                    (now, self.id),
                )
                
                # Verify the data was actually written by reading it back
                verify_check = self.gateway.conn.read_cache(
                    "SELECT cache_built_at FROM images WHERE id = %s",
                    (self.id,),
                )
                if verify_check:
                    debug(f"_refresh_cached_image: Verification - cache entry has cache_built_at={verify_check[0].get('cache_built_at')}")
                else:
                    warn(f"_refresh_cached_image: Verification failed - cache entry not found after UPDATE")
            else:
                warn(f"_refresh_cached_image: UPDATE affected 0 rows for image {self.id} - cache entry may not exist")
            
            debug(f"Refreshed cache for image {self.id}: rows={affected}, instances={len(self.instances) if self.instances else 0}, usage={len(self.cached_usage) if self.cached_usage else 0}")
        except Exception as exc:
            warn(f"Failed to update cache for image {self.id}: {exc}")
            report_error("connection", f"Failed to update cache for image {self.id}")
            trace_out()
            return False

        self._cache_needs_refresh = False  # Reset flag after refresh
        
        trace_out()
        return not is_error()

    def _dump_json(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'), default=self._json_default)

    def _json_default(self, value: Any):
        if isinstance(value, (dt.datetime, dt.date)):
            return value.isoformat()
        return value
