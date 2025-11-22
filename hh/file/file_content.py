from __future__ import annotations

import datetime as dt
from typing import Dict, Any, Optional, List

from hh.gateway.connection.connection import r_query, u_query, d_query
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.file.file_method_registry import register_file_mixin_methods
from hh.file.utils import move_file_to_deleted

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None


@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_file_mixin_methods
def _register_content_methods():
    return {
        "flag_file_modification": {"mixin_method": "_flag_file_modification", "decorator": "write"},
        "delete_from_database": {"mixin_method": "_delete_from_database", "decorator": "write"},
        "get_file_data": {"mixin_method": "_get_file_data", "decorator": "read"},
        "modify_description": {"mixin_method": "_modify_description", "decorator": "write"},
        "get_usage_data": {"mixin_method": "_get_usage_data", "decorator": "read"},
    }


class FileContentMixin:
    def _flag_file_modification(self, comments: str) -> bool:
        trace_in()
        note = comments or ""
        now = dt.datetime.now()
        if not is_error():
            user_results = r_query(self.conn, "SELECT USER() as db_user")
            db_user = user_results[0]["db_user"] if user_results else "unknown"
        if not is_error():
            affected = u_query(
                self.conn,
                """
                UPDATE files
                SET last_modified = %s,
                    username = %s,
                        comments = %s
                WHERE id = %s
                """,
                (now, db_user, note, self.id),
            )
            if affected == 0:
                warn(f"Failed to flag modification for file {self.id} - no rows affected")
                report_error("action", f"Failed to flag modification for file {self.id}")
        if not is_error():
            self.last_modified = now
            self.username = db_user
            self.comments = note
        trace_out()
        return not is_error()

    def _modify_description(self, description: Optional[str]) -> bool:
        trace_in()
        value = description or None
        if not is_error():
            affected = u_query(
                self.conn,
                "UPDATE files SET description = %s WHERE id = %s",
                (value, self.id),
            )
            if affected == 0:
                warn(f"Failed to update description for file {self.id}")
                report_error("action", f"Failed to update description for file {self.id}")
        if not is_error():
            self.description = value
            self._flag_file_modification("description updated")
        trace_out()
        return not is_error()

    def _get_file_data(self) -> Dict[str, Any]:
        trace_in()
        data = {
            "id": self.id,
            "file_name": getattr(self, "file_name", None),
            "file_path": getattr(self, "file_path", None),
            "description": getattr(self, "description", None),
            "mime_type": getattr(self, "mime_type", None),
            "size_bytes": getattr(self, "size_bytes", None),
            "username": getattr(self, "username", None),
            "uploaded": getattr(self, "uploaded", None),
            "last_modified": getattr(self, "last_modified", None),
            "comments": getattr(self, "comments", None),
            "visibility": getattr(self, "visibility", None),
        }
        trace_out()
        return data

    def _delete_from_database(self) -> bool:
        trace_in()
        if not is_error():
            self._move_to_deleted()
        if not is_error():
            affected = d_query(self.conn, "DELETE FROM files WHERE id = %s", (self.id,))
            if affected == 0:
                warn(f"Failed to delete file {self.id}")
                report_error("action", f"Failed to delete file {self.id}")
        trace_out()
        return not is_error()

    def _move_to_deleted(self) -> None:
        if not getattr(self, "file_path", None):
            return
        new_path = move_file_to_deleted(self.file_path)
        if new_path:
            log(f"File {self.id} moved to deleted path {new_path}")
            self.file_path = new_path

    def _get_usage_data(self) -> List[Dict[str, Any]]:
        trace_in()
        usage_data = []
        if not is_error():
            try:
                query = """
                    SELECT 
                        fg.page_id,
                        p.name as page_name,
                        p.class as page_class,
                        COUNT(*) as usage_count,
                        GROUP_CONCAT(fg.file_rank ORDER BY fg.file_rank SEPARATOR ', ') as ranks
                    FROM file_groups fg
                    JOIN pages p ON fg.page_id = p.id
                    WHERE fg.file_id = %s
                    GROUP BY fg.page_id, p.name, p.class
                    ORDER BY p.name
                """
                results = r_query(self.conn, query, [self.id])
                for row in results:
                    page_id = row['page_id']
                    page_name = row['page_name'] or f"Page {page_id}"
                    page_class = row['page_class']
                    usage_count = row['usage_count']
                    ranks_str = row['ranks']
                    # Get the page path for breadcrumb display
                    from hh.page.page_registry import get_page
                    page = get_page(page_id=page_id)
                    path_data = page.get_path() if page else []
                    usage_item = {
                        'page_id': page_id,
                        'page_name': page_name,
                        'page_class': page_class,
                        'usage_count': usage_count,
                        'ranks': ranks_str,
                        'path': path_data
                    }
                    usage_data.append(usage_item)
                    log(f"Found usage: page {page_id} ({page_name}) - {usage_count} times (ranks {ranks_str})")
                log(f"Found {len(usage_data)} pages using file {self.id}")
            except Exception as e:
                warn(f"Failed to get usage data for file {self.id}: {str(e)}")
                report_error("backend", f"Failed to get usage data: {str(e)}")
        # Flag that cache needs refresh since we just hydrated
        if usage_data:  # Only flag if actual usage data was found
            self._flag_cache_refresh()
        trace_out()
        return usage_data

