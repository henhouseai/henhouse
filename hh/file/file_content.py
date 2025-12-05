from __future__ import annotations

import datetime as dt
from typing import Dict, Any, Optional, List

from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.deploy.utils import detect_project_context
from pathlib import Path

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


class FileContentMixin:
    def flag_file_modification(self, comments: str) -> bool:
        trace_in()
        note = comments or ""
        now = dt.datetime.now()
        if not is_error():
            user_results = self.gateway.conn.read("SELECT USER() as db_user")
            db_user = user_results[0]["db_user"] if user_results else "unknown"
        if not is_error():
            affected = self.gateway.conn.update(
                """
                UPDATE files
                SET last_modified = %s,
                    username = %s,
                    comments = %s,
                    cache_built_at = NULL
                WHERE id = %s
                """,
                (now, db_user, note, self.id),
            )
            # Note: affected == 0 is not an error - it just means the values were already the same
            # (e.g., same timestamp due to datetime precision, same username/comments)
        if not is_error():
            self.last_modified = now
            self.username = db_user
            self.comments = note
        trace_out()
        return not is_error()

    def modify_description(self, description: Optional[str]) -> bool:
        trace_in()
        value = description or None
        if not is_error():
            affected = self.gateway.conn.update(
                "UPDATE files SET description = %s WHERE id = %s",
                (value, self.id),
            )
            if affected == 0:
                warn(f"Failed to update description for file {self.id}")
                report_error("action", f"Failed to update description for file {self.id}")
        if not is_error():
            self.description = value
            self.flag_file_modification("description updated")
        trace_out()
        return not is_error()

    def modify_visibility(self, visibility: int) -> bool:
        trace_in()
        log(f"Modifying visibility for file {self.id}: {self.visibility} -> {visibility}")
        if not is_error():
            affected = self.gateway.conn.update("UPDATE files SET visibility = %s WHERE id = %s", (visibility, self.id))
            if affected == 0:
                warn(f"Failed to update file {self.id} visibility - no rows affected")
                report_error("action", f"Failed to update file {self.id} visibility")
            else:
                self.visibility = visibility
                log(f"Successfully updated visibility for file {self.id}")
                self.flag_file_modification("visibility updated")
        trace_out()
        return not is_error()

    def get_file_data(self) -> Dict[str, Any]:
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

    def delete_from_database(self) -> bool:
        trace_in()
        if not is_error():
            self._move_to_deleted()
        if not is_error():
            affected = self.gateway.conn.delete("DELETE FROM files WHERE id = %s", (self.id,))
            if affected == 0:
                warn(f"Failed to delete file {self.id}")
                report_error("action", f"Failed to delete file {self.id}")
        trace_out()
        return not is_error()

    def _move_to_deleted(self) -> None:
        if not getattr(self, "file_path", None):
            return
        try:
            project_name, _ = detect_project_context()
            base_path = Path(f"/srv/files/{project_name}")
            current_file = base_path / self.file_path
            if not current_file.exists():
                log(f"File not found, skipping: {current_file}")
                return
            deleted_path = base_path / "deleted"
            deleted_path.mkdir(parents=True, exist_ok=True)
            deleted_file = deleted_path / current_file.name
            self.gateway.files.schedule_move(str(current_file), str(deleted_file))
            log(f"Scheduled file move to deleted folder: {self.file_path} -> deleted/{current_file.name}")
            self.file_path = f"deleted/{current_file.name}"
        except Exception as e:
            warn(f"Failed to schedule soft delete files: {str(e)}")
            report_error("file_operation", f"Failed to schedule soft delete: {str(e)}")

    def get_usage_data(self) -> List[Dict[str, Any]]:
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
                results = self.gateway.conn.read(query, [self.id])
                for row in results:
                    page_id = row['page_id']
                    page_name = row['page_name'] or f"Page {page_id}"
                    page_class = row['page_class']
                    usage_count = row['usage_count']
                    ranks_str = row['ranks']
                    
                    # Proactively check if page exists before trying to load it
                    page_exists = self.gateway.conn.read(
                        "SELECT 1 FROM pages WHERE id = %s",
                        (page_id,)
                    )
                    if not page_exists:
                        warn(f"Skipping orphaned file_group entry: page {page_id} does not exist")
                        continue
                    
                    # Get the page path for breadcrumb display
                    path_data = []
                    try:
                        from hh.page.page_registry import get_page
                        page = get_page(page_id=page_id)
                        if page:
                            path_data = page.get_path()
                        else:
                            debug(f"Page {page_id} exists but could not be loaded (class={page_class})")
                    except Exception as path_exc:
                        # If we can't load the page for path data, that's okay - we still have usage info
                        debug(f"Could not load page {page_id} for path data (class={page_class}): {path_exc}")
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

