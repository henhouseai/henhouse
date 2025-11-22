from __future__ import annotations
from typing import Optional, List, Dict, Any
import json
import datetime as dt
from decimal import Decimal

from hh.gateway.connection.connection import r_query, u_query, c_query
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.connection.decorators import db_write
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_method_registry import register_page_mixin_methods
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

    def _ensure_cache_entry(self, conn: DatabaseConnection) -> bool:
        trace_in()
        try:
            existing = r_query(
                conn,
                "SELECT 1 FROM pages WHERE id = %s",
                (self.id,),
                use_secondary=True,
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
            c_query(
                conn,
                """
                    INSERT INTO pages (id, cache_built_at)
                    VALUES (%s, %s)
                """,
                (
                    self.id,
                    now,
                ),
                use_secondary=True,
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

    @db_write
    def _refresh_cached_page_with_write_conn(self, conn: DatabaseConnection) -> bool:
        """Helper method decorated with @db_write to get a write connection for cache refresh.
        Used when original operation was a read operation."""
        self.conn = conn
        return self._refresh_cached_page(conn)

    def _refresh_cached_page(self, conn: DatabaseConnection) -> bool:
        """Refresh the cache database with all 5 derived fields. Called by wrapper system at end of method calls.
        Takes conn as explicit parameter - must be provided by caller."""
        trace_in()
        debug(f"_refresh_cached_page: Starting for page {self.id}, conn={conn}")
        if conn is None:
            warn(f"_refresh_cached_page: conn is None for page {self.id}")
            trace_out()
            return False
        # If self.conn is None, set it to the supplied connection so internal methods can use it
        if self.conn is None:
            self.conn = conn
        if not self._ensure_cache_entry(conn):
            debug(f"_refresh_cached_page: Failed to ensure cache entry for page {self.id}")
            trace_out()
            return False

        # Ensure all 5 fields are populated by calling their internal mixin methods
        # The getters check if field is populated first, and only hydrate if empty
        # This ensures we always have fully hydrated data to cache
        
        if not self.display_name:
            self.display_name = self._get_display_name()
        
        if self.prepared_text is None:
            self.prepared_text = self._get_prepared_text()
        
        children = self._get_children_by_class()
        self.children_by_class = children if children else {}
        
        if not self.images:
            self.images = self._get_images_data()
        
        if not self.files:
            self.files = self._get_files_data()
        
        # Serialize all data
        display_name_str = self.display_name
        prepared_json = self._dump_json(self.prepared_text) if self.prepared_text is not None else None
        children_json = self._dump_json(self.children_by_class) if self.children_by_class else None
        images_json = self._dump_json(self.images) if self.images else None
        files_json = self._dump_json(self.files) if self.files else None
        
        now = dt.datetime.now()
        
        try:
            # Update cache database
            affected = u_query(
                conn,
                """
                    UPDATE pages
                    SET display_name = %s,
                        prepared_text = %s,
                        children_summary = %s,
                        image_summary = %s,
                        file_summary = %s,
                        links_out = %s,
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
                    now,
                    self.id,
                ),
                use_secondary=True,
            )
            # Update main database cache_built_at
            if affected > 0:
                u_query(
                    conn,
                    """
                        UPDATE pages
                        SET cache_built_at = %s
                        WHERE id = %s
                    """,
                    (now, self.id),
                    use_secondary=False,
                )
                
                # Verify the data was actually written by reading it back
                verify_check = r_query(
                    conn,
                    "SELECT display_name, cache_built_at FROM pages WHERE id = %s",
                    (self.id,),
                    use_secondary=True,
                )
                if verify_check:
                    debug(f"_refresh_cached_page: Verification - cache entry has display_name='{verify_check[0].get('display_name')}', cache_built_at={verify_check[0].get('cache_built_at')}")
                else:
                    warn(f"_refresh_cached_page: Verification failed - cache entry not found after UPDATE")
            else:
                warn(f"_refresh_cached_page: UPDATE affected 0 rows for page {self.id} - cache entry may not exist")
            
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

