from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional

from hh.gateway.connection.connection import r_query, u_query, c_query, d_query
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.debug import (
    get_trace_in,
    get_trace_out,
    get_log,
    get_debug,
    get_warn,
    register_debug_init,
)
from hh.page.page_method_registry import register_page_mixin_methods
from hh.page.page_registry import get_page
from hh.file.file_registry import get_file_conn
from hh.file.utils import store_uploaded_file

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None


@register_debug_init
def _initialize_page_files_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


@register_page_mixin_methods
def _register_file_methods():
    return {
        "get_files_data": {"mixin_method": "_get_files_data", "decorator": "read"},
        "add_file": {"mixin_method": "_add_file", "decorator": "write"},
        "copy_files": {"mixin_method": "_copy_files", "decorator": "write"},
        "move_files": {"mixin_method": "_move_files", "decorator": "write"},
        "set_file_rank": {"mixin_method": "_set_file_rank", "decorator": "write"},
        "remove_file": {"mixin_method": "_remove_file", "decorator": "write"},
        "reorder_files": {"mixin_method": "_reorder_files", "decorator": "write"},
        "delete_all_file_groups": {"mixin_method": "_delete_all_file_groups", "decorator": "write"},
    }


class PageFilesMixin:
    def _get_files_data(self) -> List[Dict[str, Any]]:
        trace_in()
        cached_files = getattr(self, "cached_files", None)
        if cached_files is not None:
            trace_out()
            return cached_files

        files: List[Dict[str, Any]] = []
        if not is_error():
            rows = r_query(
                self.conn,
                """
                SELECT fg.file_rank,
                       f.id,
                       f.file_name,
                       f.file_path,
                       f.description,
                       f.mime_type,
                       f.size_bytes,
                       f.username,
                       f.uploaded,
                       f.last_modified,
                       f.comments,
                       f.visibility
                FROM file_groups fg
                JOIN files f ON f.id = fg.file_id
                WHERE fg.page_id = %s
                ORDER BY fg.file_rank
                """,
                [self.id],
            )
            for row in rows:
                files.append(
                    {
                        "id": row["id"],
                        "file_rank": row["file_rank"],
                        "file_name": row["file_name"],
                        "file_path": row["file_path"],
                        "description": row["description"],
                        "mime_type": row["mime_type"],
                        "size_bytes": row["size_bytes"],
                        "username": row["username"],
                        "uploaded": row["uploaded"],
                        "last_modified": row["last_modified"],
                        "comments": row["comments"],
                        "visibility": row["visibility"],
                    }
                )
        self.cached_files = files
        summary = getattr(self, "cached_file_summary", {}) or {}
        if not isinstance(summary, dict):
            summary = {}
        summary["files"] = files
        self.cached_file_summary = summary
        trace_out()
        return files

    def _add_file(
        self,
        temp_path: str,
        original_filename: str,
        description: Optional[str] = None,
    ) -> Optional[int]:
        trace_in()
        if not Path(temp_path).exists():
            warn(f"File not found: {temp_path}")
            report_error("action", f"File not found: {temp_path}")
        if is_error():
            trace_out()
            return None

        relative_path, _, size_bytes, mime_type = store_uploaded_file(temp_path, original_filename)
        new_file_id = self._create_file_record(
            file_name=Path(original_filename).name,
            file_path=relative_path,
            description=description or Path(original_filename).stem,
            mime_type=mime_type,
            size_bytes=size_bytes,
        )

        if not is_error() and new_file_id:
            if not self._add_file_to_group(new_file_id):
                warn(f"Failed to add file {new_file_id} to page group")
                report_error("action", f"Failed to add file {new_file_id} to page group")
            else:
                self._flag_related_file(new_file_id, f"added to page {self.id}")

        if not is_error():
            self._reset_cached_files()
            self.flag_page_modification("files updated")
        trace_out()
        return new_file_id

    def _create_file_record(
        self,
        file_name: str,
        file_path: str,
        description: Optional[str],
        mime_type: str,
        size_bytes: int,
    ) -> Optional[int]:
        trace_in()
        file_id = None
        if not is_error():
            user_results = r_query(self.conn, "SELECT USER() as db_user")
            db_user = user_results[0]["db_user"] if user_results else "unknown"
            file_id = c_query(
                self.conn,
                """
                INSERT INTO files (
                    file_name,
                    file_path,
                    description,
                    mime_type,
                    size_bytes,
                    username,
                    uploaded,
                    last_modified,
                    comments,
                    visibility
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW(), %s, 1)
                """,
                (
                    file_name,
                    file_path,
                    description,
                    mime_type,
                    size_bytes,
                    db_user,
                    "file uploaded",
                ),
            )
            log(f"Created file record {file_id} for page {self.id}")
        trace_out()
        return file_id

    def _add_file_to_group(self, file_id: int, rank: Optional[int] = None) -> bool:
        trace_in()
        if not is_error():
            if rank is None:
                results = r_query(
                    self.conn,
                    "SELECT COALESCE(MAX(file_rank), 0) + 1 AS next_rank FROM file_groups WHERE page_id = %s",
                    [self.id],
                )
                rank = results[0]["next_rank"] if results else 1
            new_id = c_query(
                self.conn,
                """
                INSERT INTO file_groups (page_id, file_id, file_rank)
                VALUES (%s, %s, %s)
                """,
                (self.id, file_id, rank),
            )
            if new_id is None:
                warn(f"Failed to add file {file_id} to page {self.id}")
                report_error("action", f"Failed to add file {file_id} to page {self.id}")
            else:
                self._reset_cached_files()
        trace_out()
        return not is_error()

    def _remove_file_from_group(self, file_id: int) -> bool:
        trace_in()
        if not is_error():
            affected = d_query(
                self.conn,
                "DELETE FROM file_groups WHERE page_id = %s AND file_id = %s",
                (self.id, file_id),
            )
            if affected == 0:
                warn(f"Failed to remove file {file_id} from page {self.id}")
                report_error("action", f"Failed to remove file {file_id} from page {self.id}")
            else:
                self._reset_cached_files()
        trace_out()
        return not is_error()

    def _copy_files(self, file_ids: List[int], target_rank: Optional[int] = None) -> bool:
        trace_in()
        if not file_ids:
            trace_out()
            return True

        original_count = len(self.get_files_data())
        copied = 0
        for file_id in file_ids:
            if is_error():
                break
            if self._add_file_to_group(file_id):
                copied += 1
                self._flag_related_file(file_id, f"copied to page {self.id}")

        if not is_error() and target_rank is not None and copied > 0:
            for i, file_id in enumerate(file_ids[:copied], start=0):
                self._set_file_rank(file_id, original_count + i + 1, target_rank + i)

        if not is_error() and copied > 0:
            self._reset_cached_files()
            self.flag_page_modification("files updated")
        trace_out()
        return not is_error()

    def _move_files(
        self,
        file_instances: List[Dict[str, int]],
        target_rank: Optional[int] = None,
    ) -> bool:
        trace_in()
        if not file_instances:
            trace_out()
            return True

        original_count = len(self.get_files_data())
        moved_count = 0
        source_pages = set()
        for instance in file_instances:
            if is_error():
                break
            file_id = instance["file_id"]
            source_page_id = instance["source_page_id"]
            source_rank = instance["source_rank"]

            affected = d_query(
                self.conn,
                """
                DELETE FROM file_groups
                WHERE page_id = %s AND file_id = %s AND file_rank = %s
                """,
                (source_page_id, file_id, source_rank),
            )
            if affected == 0:
                warn(f"Failed to remove file {file_id} from page {source_page_id}")
                continue

            source_pages.add(source_page_id)
            if self._add_file_to_group(file_id):
                moved_count += 1
                self._flag_related_file(file_id, f"moved to page {self.id}")

        if not is_error():
            for page_id in source_pages:
                source_page = get_page(page_id=page_id)
                if source_page:
                    source_page.reorder_files()

        if not is_error() and target_rank is not None and moved_count > 0:
            for i, instance in enumerate(file_instances[:moved_count]):
                file_id = instance["file_id"]
                self._set_file_rank(file_id, original_count + i + 1, target_rank + i)

        if not is_error() and moved_count > 0:
            self._reset_cached_files()
            self.flag_page_modification("files updated")
        trace_out()
        return not is_error()

    def _set_file_rank(self, file_id: int, current_rank: int, new_rank: int) -> bool:
        trace_in()
        if new_rank <= 0:
            warn(f"Invalid file rank: {new_rank}")
            report_error("action", f"Invalid file rank: {new_rank}")
            trace_out()
            return False

        if is_error():
            trace_out()
            return False

        rows = r_query(
            self.conn,
            """
            SELECT file_id
            FROM file_groups
            WHERE page_id = %s
            ORDER BY file_rank
            """,
            [self.id],
        )
        order = [row["file_id"] for row in rows]
        if file_id not in order:
            warn(f"File {file_id} not found in page {self.id}")
            report_error("action", f"File {file_id} not found in this page")
            trace_out()
            return False

        order.remove(file_id)
        target_index = max(0, min(new_rank - 1, len(order)))
        order.insert(target_index, file_id)

        for idx, fid in enumerate(order, start=1):
            u_query(
                self.conn,
                """
                UPDATE file_groups
                SET file_rank = %s
                WHERE page_id = %s AND file_id = %s
                """,
                (idx, self.id, fid),
            )

        if not is_error():
            self._reset_cached_files()
            self.flag_page_modification("files updated")
        trace_out()
        return not is_error()

    def _reorder_files(self) -> bool:
        trace_in()
        try:
            rows = r_query(
                self.conn,
                """
                SELECT file_id, file_rank
                FROM file_groups
                WHERE page_id = %s
                ORDER BY file_rank
                """,
                [self.id],
            )
            for idx, row in enumerate(rows, start=1):
                if row["file_rank"] != idx:
                    u_query(
                        self.conn,
                        """
                        UPDATE file_groups
                        SET file_rank = %s
                        WHERE page_id = %s AND file_id = %s
                        """,
                        (idx, self.id, row["file_id"]),
                    )
        except Exception as exc:  # noqa: BLE001
            warn(f"Failed to reorder files for page {self.id}: {exc}")
            report_error("action", f"Failed to reorder files for page {self.id}")
        if not is_error():
            self._reset_cached_files()
            self.flag_page_modification("files updated")
        trace_out()
        return not is_error()

    def _remove_file(self, file_id: int, file_rank: int) -> bool:
        trace_in()
        if not is_error():
            affected = d_query(
                self.conn,
                """
                DELETE FROM file_groups
                WHERE page_id = %s AND file_id = %s AND file_rank = %s
                """,
                (self.id, file_id, file_rank),
            )
            if affected == 0:
                warn(f"Failed to remove file {file_id} from page {self.id}")
                report_error("action", f"Failed to remove file {file_id}")
        if not is_error() and not self._reorder_files():
            trace_out()
            return False
        if not is_error():
            usage = self._get_file_usage_count(file_id)
            if usage == 0:
                file_obj = get_file_conn(self.conn, file_id=file_id)
                if file_obj:
                    file_obj.delete_from_database()
            self._flag_related_file(file_id, f"removed from page {self.id}")
            self._reset_cached_files()
            self.flag_page_modification("files updated")
        trace_out()
        return not is_error()

    def _delete_all_file_groups(self) -> bool:
        trace_in()
        file_ids: List[int] = []
        if not is_error():
            rows = r_query(
                self.conn,
                "SELECT DISTINCT file_id FROM file_groups WHERE page_id = %s",
                [self.id],
            )
            file_ids = [row["file_id"] for row in rows] if rows else []
            d_query(self.conn, "DELETE FROM file_groups WHERE page_id = %s", [self.id])

        if not is_error():
            for fid in file_ids:
                usage = self._get_file_usage_count(fid)
                if usage == 0:
                    file_obj = get_file_conn(self.conn, file_id=fid)
                    if file_obj:
                        file_obj.delete_from_database()

        if not is_error():
            self._reset_cached_files()
            self.flag_page_modification("files updated")
        trace_out()
        return not is_error()

    def _flag_related_file(self, file_id: int, comment: str) -> None:
        if is_error():
            return
        file_obj = get_file_conn(self.conn, file_id=file_id)
        if not file_obj:
            warn(f"Failed to load file {file_id} for modification flag")
            return
        file_obj.flag_file_modification(comment)

    def _get_file_usage_count(self, file_id: int) -> int:
        if is_error():
            return 0
        results = r_query(
            self.conn,
            "SELECT COUNT(*) AS cnt FROM file_groups WHERE file_id = %s",
            (file_id,),
        )
        return results[0]["cnt"] if results else 0

    def _reset_cached_files(self) -> None:
        if hasattr(self, "cached_files"):
            self.cached_files = None
        if hasattr(self, "cached_file_summary"):
            self.cached_file_summary = None
        if hasattr(self, "cached_upper_content"):
            self.cached_upper_content = None
        if hasattr(self, "cached_lower_content"):
            self.cached_lower_content = None
