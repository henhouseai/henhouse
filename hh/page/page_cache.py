from __future__ import annotations
from typing import Optional, List, Dict, Any
import json
import datetime as dt
from decimal import Decimal

from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.gateway.error.error_store import report_error, is_error
from hh.tp.tp import TextProcessor

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None


@register_debug_init
def _initialize_page_cache_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


# Cache methods are not registered as mixin methods - they're called internally by the wrapper system


class PageCacheMixin:

    def _ensure_cache_entry(self) -> bool:
        trace_in()
        try:
            existing = self.gateway.conn.read_cache(
                "SELECT 1 FROM pages WHERE id = %s",
                (self.id,),
            )
        except Exception as exc:
            warn(f"Failed to check cache entry for page {self.id}: {exc}")
            report_error("connection", f"Failed to verify cache for page {self.id}")
            trace_out()
            return False

        if existing:
            trace_out()
            return True

        now = dt.datetime.now()
        try:
            self.gateway.conn.create_cache(
                """
                    INSERT INTO pages (id, cache_built_at)
                    VALUES (%s, %s)
                """,
                (
                    self.id,
                    now,
                ),
            )
            debug(f"Created cache entry for page {self.id}")
        except Exception as exc:
            warn(f"Failed to insert cache entry for page {self.id}: {exc}")
            report_error("connection", f"Failed to create cache entry for page {self.id}")
            trace_out()
            return False

        trace_out()
        return True

    def _flag_cache_refresh(self) -> None:
        """Flag that the cache needs to be refreshed. Called by getters when they hydrate data."""
        self._cache_needs_refresh = True

    def _refresh_cached_page(self) -> bool:
        """Refresh the cache database with all 5 derived fields. Called by refresh_stale_page_caches() during gateway commit."""
        trace_in()
        debug(f"_refresh_cached_page: Starting for page {self.id}")

        tier_level = getattr(self.gateway.response, "user_tier_level", 0) if self.gateway and self.gateway.response else 0
        if tier_level < 3:
            debug(
                f"_refresh_cached_page: Skipping cache write for page {self.id} (tier_level={tier_level})"
            )
            self._cache_needs_refresh = False
            trace_out()
            return True

        if not self._ensure_cache_entry():
            debug(f"_refresh_cached_page: Failed to ensure cache entry for page {self.id}")
            trace_out()
            return False

        # Ensure all 5 fields are populated by calling their internal mixin methods
        # The getters check if field is populated first, and only hydrate if empty
        # This ensures we always have fully hydrated data to cache
        
        if not self.display_name:
            self.display_name = self._get_display_name()
        
        if self.prepared_text is None:
            self.prepared_text = self.get_prepared_text()
        
        children = self._get_children_by_class()
        self.children_by_class = children if children else {}
        
        if not self.images:
            self.images = self.get_images_data()
        
        if not self.files:
            self.files = self.get_files_data()
        
        # Serialize all data
        display_name_str = self.display_name
        prepared_json = self._dump_json(self.prepared_text) if self.prepared_text is not None else None
        children_json = self._dump_json(self.children_by_class) if self.children_by_class else None
        images_json = self._dump_json(self.images) if self.images else None
        files_json = self._dump_json(self.files) if self.files else None
        
        # Zip all main database fields into metadata for cache backup
        # This allows full page hydration from cache database without main DB access
        main_db_metadata = {
            'name': self.name,
            'link': self.link,
            'text': self.text,
            'parent': self.parent,
            'class': self.class_name,
            'last_modified': self.last_modified.isoformat() if self.last_modified else None,
            'username': self.username,
            'comments': self.comments,
            'visibility': self.visibility,
            'displayStyle': getattr(self, 'displayStyle', None),
            'viewCount': getattr(self, 'viewCount', None),
        }
        # Include existing metadata if present (merge with main DB fields)
        existing_metadata = getattr(self, 'metadata', {}) or {}
        if isinstance(existing_metadata, dict):
            # Merge existing metadata, but main DB fields take precedence
            main_db_metadata.update(existing_metadata)
        metadata_json = self._dump_json(main_db_metadata)
        
        now = dt.datetime.now()
        
        try:
            # Update cache database
            affected = self.gateway.conn.update_cache(
                """
                    UPDATE pages
                    SET display_name = %s,
                        prepared_text = %s,
                        children_summary = %s,
                        image_summary = %s,
                        file_summary = %s,
                        links_out = %s,
                        metadata = %s,
                        cache_built_at = %s
                    WHERE id = %s
                """,
                (
                    display_name_str,
                    prepared_json,
                    children_json,
                    images_json,
                    files_json,
                    self._dump_json({}),  # links_out - currently not used, store empty dict
                    metadata_json,
                    now,
                    self.id,
                ),
            )
            # Update main database cache_built_at
            if affected > 0:
                self.gateway.conn.update(
                    """
                        UPDATE pages
                        SET cache_built_at = %s
                        WHERE id = %s
                    """,
                    (now, self.id),
                )
                
                # Verify the data was actually written by reading it back
                verify_check = self.gateway.conn.read_cache(
                    "SELECT display_name, cache_built_at FROM pages WHERE id = %s",
                    (self.id,),
                )
                if verify_check:
                    debug(f"_refresh_cached_page: Verification - cache entry has display_name='{verify_check[0].get('display_name')}', cache_built_at={verify_check[0].get('cache_built_at')}")
                else:
                    warn(f"_refresh_cached_page: Verification failed - cache entry not found after UPDATE")
            else:
                # 0 rows affected doesn't necessarily mean an error - could just mean no change was needed
                debug(f"_refresh_cached_page: UPDATE affected 0 rows for page {self.id} - no change needed")
            
            debug(f"Refreshed cache for page {self.id}: rows={affected}")
        except Exception as exc:
            warn(f"Failed to update cache for page {self.id}: {exc}")
            report_error("connection", f"Failed to update cache for page {self.id}")
            trace_out()
            return False

        self._cache_needs_refresh = False  # Reset flag after refresh
        
        trace_out()
        return not is_error()

    def _serialize_metadata(self) -> str:
        metadata = getattr(self, 'metadata', {}) or {}
        if not isinstance(metadata, dict):
            metadata = {}
        return self._dump_json(metadata)

    def _dump_json(self, value: Any) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(',', ':'),
            default=self._json_default,
        )

    def _json_default(self, value: Any):
        if isinstance(value, (dt.datetime, dt.date)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (bytes, bytearray)):
            try:
                return value.decode('utf-8')
            except Exception:
                return value.decode('utf-8', errors='ignore')
        if isinstance(value, set):
            return list(value)
        return value

