from __future__ import annotations

import datetime as dt
import json
from typing import Any, Dict, Optional, List

from hh.gateway.connection.connection import r_query, c_query, u_query
from hh.gateway.connection.decorators import db_write
from hh.gateway.connection.types import DatabaseConnection
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


# Cache methods are NOT registered in the mixin registry - they are called directly
# by the wrapper system in file.py, similar to page_cache.py


class FileCacheMixin:

    def _ensure_file_cache_entry(self, conn: DatabaseConnection) -> bool:
        """Ensure cache entry exists in cache database. Only creates if missing."""
        trace_in()
        try:
            existing = r_query(
                conn,
                "SELECT 1 FROM files WHERE id = %s",
                (self.id,),
                use_secondary=True,
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
            c_query(
                conn,
                """
                    INSERT INTO files (id, pages, cache_built_at)
                    VALUES (%s, %s, %s)
                """,
                (
                    self.id,
                    self._dump_json([]),  # Empty pages initially
                    now,
                ),
                use_secondary=True,
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

    @db_write
    def _refresh_cached_file_with_write_conn(self, conn: DatabaseConnection) -> bool:
        """Helper method decorated with @db_write to get a write connection for cache refresh.
        Used when original operation was a read operation."""
        self.conn = conn
        return self._refresh_cached_file(conn)

    def _refresh_cached_file(self, conn: DatabaseConnection) -> bool:
        """Refresh the cache database with pages (usage) field. Called by wrapper system at end of method calls.
        Takes conn as explicit parameter - must be provided by caller."""
        trace_in()
        debug(f"_refresh_cached_file: Starting for file {self.id}, conn={conn}")
        if conn is None:
            warn(f"_refresh_cached_file: conn is None for file {self.id}")
            trace_out()
            return False
        # If self.conn is None, set it to the supplied connection so internal methods can use it
        if self.conn is None:
            self.conn = conn
        if not self._ensure_file_cache_entry(conn):
            debug(f"_refresh_cached_file: Failed to ensure cache entry for file {self.id}")
            trace_out()
            return False

        # Ensure pages field is populated by calling internal mixin method
        # The getter checks if field is populated first, and only hydrates if empty
        # This ensures we always have fully hydrated data to cache
        
        # Get usage data if pages is empty
        if not self.pages:
            self.pages = self._get_usage_data()
        
        # Serialize all data
        pages_json = self._dump_json(self.pages) if self.pages else None
        
        now = dt.datetime.now()
        
        try:
            # Update cache database
            affected = u_query(
                conn,
                """
                    UPDATE files
                    SET pages = %s,
                        cache_built_at = %s
                    WHERE id = %s
                """,
                (
                    pages_json,
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
                        UPDATE files
                        SET cache_built_at = %s
                        WHERE id = %s
                    """,
                    (now, self.id),
                    use_secondary=False,
                )
                
                # Verify the data was actually written by reading it back
                verify_check = r_query(
                    conn,
                    "SELECT cache_built_at FROM files WHERE id = %s",
                    (self.id,),
                    use_secondary=True,
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

