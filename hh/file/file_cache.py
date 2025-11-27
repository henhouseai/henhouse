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
def _initialize_file_cache_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


class FileCacheMixin:

    def _ensure_file_cache_entry(self) -> bool:
        """Ensure cache entry exists in cache database. Only creates if missing."""
        trace_in()
        if not self.gateway or not self.gateway.conn:
            warn("Gateway or connection not available for cache entry check")
            report_error("connection", f"Failed to verify cache for file {self.id}")
            trace_out()
            return False
        try:
            existing = self.gateway.conn.read_cache(
                "SELECT 1 FROM files WHERE id = %s",
                (self.id,),
            )
        except Exception as exc:
            warn(f"Failed to check cache entry for file {self.id}: {exc}")
            report_error("connection", f"Failed to verify cache for file {self.id}")
            trace_out()
            return False

        if existing:
            trace_out()
            return True

        now = dt.datetime.now()
        try:
            self.gateway.conn.create_cache(
                """
                    INSERT INTO files (id, pages, metadata, cache_built_at)
                    VALUES (%s, %s, %s, %s)
                """,
                (
                    self.id,
                    self._dump_json([]),  # Empty pages initially
                    self._dump_json({}),  # Empty metadata initially
                    now,
                ),
            )
            debug(f"Created cache entry for file {self.id}")
        except Exception as exc:
            warn(f"Failed to insert cache entry for file {self.id}: {exc}")
            report_error("connection", f"Failed to create cache entry for file {self.id}")
            trace_out()
            return False

        trace_out()
        return True

    def _flag_cache_refresh(self) -> None:
        """Flag that the cache needs to be refreshed. Called by getters when they hydrate data."""
        self._cache_needs_refresh = True

    def _refresh_cached_file(self) -> bool:
        """Refresh the cache database with pages (usage) field. Called by gateway during commit."""
        trace_in()
        debug(f"_refresh_cached_file: Starting for file {self.id}")
        if not self.gateway or not self.gateway.conn:
            warn("Gateway or connection not available for cache refresh")
            trace_out()
            return False
        
        if not self._ensure_file_cache_entry():
            debug(f"_refresh_cached_file: Failed to ensure cache entry for file {self.id}")
            trace_out()
            return False

        # Ensure pages field is populated by calling internal mixin method
        # The getter checks if field is populated first, and only hydrates if empty
        # This ensures we always have fully hydrated data to cache
        
        # Get usage data if pages is empty
        if not self.pages:
            self.pages = self.get_usage_data()
        
        # Serialize all data
        pages_json = self._dump_json(self.pages) if self.pages else None
        
        # Zip all main database fields into metadata for cache backup
        # This allows full file hydration from cache database without main DB access
        main_db_metadata = {
            'file_name': self.file_name,
            'file_path': self.file_path,
            'description': self.description,
            'mime_type': self.mime_type,
            'size_bytes': self.size_bytes,
            'username': self.username,
            'uploaded': self.uploaded.isoformat() if self.uploaded else None,
            'last_modified': self.last_modified.isoformat() if self.last_modified else None,
            'comments': self.comments,
            'visibility': self.visibility,
        }
        metadata_json = self._dump_json(main_db_metadata)
        
        now = dt.datetime.now()
        
        try:
            # Update cache database
            affected = self.gateway.conn.update_cache(
                """
                    UPDATE files
                    SET pages = %s,
                        metadata = %s,
                        cache_built_at = %s
                    WHERE id = %s
                """,
                (
                    pages_json,
                    metadata_json,
                    now,
                    self.id,
                ),
            )
            # Update main database cache_built_at
            if affected > 0:
                self.gateway.conn.update(
                    """
                        UPDATE files
                        SET cache_built_at = %s
                        WHERE id = %s
                    """,
                    (now, self.id),
                )
                
                # Verify the data was actually written by reading it back
                verify_check = self.gateway.conn.read_cache(
                    "SELECT cache_built_at FROM files WHERE id = %s",
                    (self.id,),
                )
                if verify_check:
                    debug(f"_refresh_cached_file: Verification - cache entry has cache_built_at={verify_check[0].get('cache_built_at')}")
                else:
                    warn(f"_refresh_cached_file: Verification failed - cache entry not found after UPDATE")
            else:
                warn(f"_refresh_cached_file: UPDATE affected 0 rows for file {self.id} - cache entry may not exist")
            
            debug(f"Refreshed cache for file {self.id}: rows={affected}, usage={len(self.pages) if self.pages else 0}")
        except Exception as exc:
            warn(f"Failed to update cache for file {self.id}: {exc}")
            report_error("connection", f"Failed to update cache for file {self.id}")
            trace_out()
            return False

        self._cache_needs_refresh = False  # Reset flag after refresh
        
        trace_out()
        return not is_error()

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
        return value

