"""
TABLE OF CONTENTS (Alphabetical Order)
======================================

__init__()                    Line 50
_dump_json()                  Line 132
_flag_cache_refresh()         Line 140
_json_default()               Line 191
_move_to_deleted()            Line 196
_refresh_cached_file()        Line 219
delete_from_database()        Line 313
flag_file_modification()      Line 325
get_file_data()               Line 353
get_usage_data()              Line 371
modify_description()          Line 444
modify_visibility()            Line 461

"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from hh.gateway.gateway import get_gateway
from hh.gateway.connection.utils import deserialize_json_blob, normalize_datetime
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.deploy.deploy_utils import detect_project_context
from hh.page.page_registry import get_page

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


class File:

    id: int
    gateway: Any
    file_name: Optional[str]
    file_path: Optional[str]
    description: Optional[str]
    mime_type: Optional[str]
    size_bytes: Optional[int]
    username: Optional[str]
    uploaded: Optional[dt.datetime]
    last_modified: Optional[dt.datetime]
    comments: Optional[str]
    visibility: Optional[int]
    pages: List[Any]
    cache_built_at: Optional[Any]
    cache_hydrated: bool
    _cache_needs_refresh: bool

    def __init__(self, file_id: int):
        trace_in()
        self.gateway = get_gateway()
        debug(f"Initializing File with id={file_id}")
        
        if not self.gateway or not self.gateway.conn:
            warn("Gateway or connection not available")
            report_error("connection", "Gateway or connection not available")
            trace_out()
            return
        
        # Initialize all fields
        self.id = file_id
        self.file_name = None
        self.file_path = None
        self.description = None
        self.mime_type = None
        self.size_bytes = None
        self.username = None
        self.uploaded = None
        self.last_modified = None
        self.comments = None
        self.visibility = None
        self.pages = []  # Usage data (which pages use this file)
        self.cache_built_at = None
        self.cache_hydrated = False
        self._cache_needs_refresh = False
        
        # Try to hydrate from cache database first (check cache before main DB)
        cache_hydrated = False
        if not is_error():
            # Get entire cache row to check staleness (no main DB read needed)
            cache_query = """
                SELECT id, file_name, file_path, description, mime_type, size_bytes, username, uploaded, last_modified, comments, visibility,
                       pages, cache_built_at
                FROM files
                WHERE id = %s
            """
            try:
                cache_results = self.gateway.conn.read_cache(cache_query, [file_id])
                if cache_results:
                    cache_row = cache_results[0]
                    cache_last_modified = cache_row.get('last_modified')
                    cache_built_at = cache_row.get('cache_built_at')
                    
                    # Check staleness using cache DB only: cache.last_modified vs cache.cache_built_at
                    cache_last_modified_dt = normalize_datetime(cache_last_modified)
                    cache_built_at_dt = normalize_datetime(cache_built_at)
                    
                    if cache_built_at_dt is None:
                        debug(f"Cache for file {file_id} does not exist (cache_built_at is NULL)")
                    elif cache_last_modified_dt and cache_built_at_dt and cache_built_at_dt < cache_last_modified_dt:
                        debug(f"Cache for file {file_id} is stale (cache_built_at={cache_built_at_dt}, cache.last_modified={cache_last_modified_dt})")
                    else:
                        # Cache is fresh - hydrate entirely from cache DB (no main DB access)
                        self.file_name = cache_row.get('file_name')
                        self.file_path = cache_row.get('file_path')
                        self.description = cache_row.get('description')
                        self.mime_type = cache_row.get('mime_type')
                        self.size_bytes = cache_row.get('size_bytes')
                        self.username = cache_row.get('username')
                        self.uploaded = cache_row.get('uploaded')
                        self.last_modified = cache_last_modified
                        self.comments = cache_row.get('comments')
                        self.visibility = cache_row.get('visibility')
                        self.pages = deserialize_json_blob(cache_row.get('pages'), [])
                        self.cache_built_at = cache_built_at
                        self.cache_hydrated = True
                        cache_hydrated = True
                        log(f"Loaded file {file_id} entirely from cache: {self.file_name}")
                        debug(f"Hydrated file {file_id} entirely from cache (built_at={cache_built_at_dt})")
                else:
                    debug(f"Cache for file {file_id} does not exist (no cache row found)")
            except Exception as e:
                warn(f"Failed to hydrate file {file_id} from cache: {e}")
                # Don't report error - cache hydration failure is not critical, will fall back to main DB
        
        # If cache is stale/missing, fall back to main database
        if not cache_hydrated and not is_error():
            # Load file data from main database
            query = "SELECT * FROM files WHERE id = %s"
            try:
                results = self.gateway.conn.read(query, [file_id])
                if not results:
                    warn(f"File with id {file_id} not found")
                    report_error("action", f"File with id {file_id} not found")
                    trace_out()
                    return
                
                file_data = results[0]
                self.file_name = file_data.get('file_name')
                self.file_path = file_data.get('file_path')
                self.description = file_data.get('description')
                self.mime_type = file_data.get('mime_type')
                self.size_bytes = file_data.get('size_bytes')
                self.username = file_data.get('username')
                self.uploaded = file_data.get('uploaded')
                self.last_modified = file_data.get('last_modified')
                self.comments = file_data.get('comments')
                self.visibility = file_data.get('visibility')
                self.cache_built_at = file_data.get('cache_built_at')
                log(f"Loaded file {file_id} from main DB: {self.file_name}")
            except Exception as e:
                warn(f"Failed to load file {file_id}: {e}")
                report_error("connection", f"Failed to load file {file_id}: {e}")
        
        trace_out()

    def _dump_json(self, value: Any) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(',', ':'),
            default=self._json_default,
        )

    def _flag_cache_refresh(self) -> None:
        """Flag that the cache needs to be refreshed. Called by getters when they hydrate data."""
        self._cache_needs_refresh = True

    def _json_default(self, value: Any):
        if isinstance(value, (dt.datetime, dt.date)):
            return value.isoformat()
        return value

    def _move_to_deleted(self) -> None:
        if not getattr(self, "file_path", None):
            return
        try:
            project_name, _ = detect_project_context()
            base_path = Path(f"/srv/files/{project_name}")
            file_path_str = self.file_path
            if file_path_str is None:
                return
            current_file = base_path / file_path_str
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

    def _refresh_cached_file(self) -> bool:
        """Refresh the cache database with pages (usage) field. Called by gateway during commit."""
        trace_in()
        debug(f"_refresh_cached_file: Starting for file {self.id}")
        if not self.gateway or not self.gateway.conn:
            warn("Gateway or connection not available for cache refresh")
            trace_out()
            return False
        
        # Ensure pages field is populated by calling internal mixin method
        # The getter checks if field is populated first, and only hydrates if empty
        # The getter sets the attribute itself, so we just call it
        # This ensures we always have fully hydrated data to cache
        
        if not self.pages:
            self.get_usage_data()
        
        # Serialize all data
        pages_json = self._dump_json(self.pages) if self.pages else None
        
        now = dt.datetime.now()
        
        try:
            # Buffer cache database write with all main DB fields as first-class columns
            # plus derived fields
            # Uses INSERT ... ON DUPLICATE KEY UPDATE to handle both insert and update cases
            self.gateway.conn.buffer_cache(
                "files",
                """
                    INSERT INTO files (id, file_name, file_path, description, mime_type, size_bytes, username, uploaded, last_modified, comments, visibility, pages, cache_built_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        file_name = VALUES(file_name),
                        file_path = VALUES(file_path),
                        description = VALUES(description),
                        mime_type = VALUES(mime_type),
                        size_bytes = VALUES(size_bytes),
                        username = VALUES(username),
                        uploaded = VALUES(uploaded),
                        last_modified = VALUES(last_modified),
                        comments = VALUES(comments),
                        visibility = VALUES(visibility),
                        pages = VALUES(pages),
                        cache_built_at = VALUES(cache_built_at)
                """,
                (
                    self.id,
                    self.file_name,
                    self.file_path,
                    self.description,
                    self.mime_type,
                    self.size_bytes,
                    self.username,
                    self.uploaded,
                    self.last_modified,
                    self.comments,
                    self.visibility,
                    pages_json,
                    now,
                ),
            )
            # Always bump main database cache_built_at
            self.gateway.conn.update(
                """
                    UPDATE files
                    SET cache_built_at = %s
                    WHERE id = %s
                """,
                (now, self.id),
            )
            # Note: Cache writes are buffered, so verification would fail until write_cache() is called
            # Verification removed since buffered writes aren't immediately visible in cache DB
            
            debug(f"Refreshed cache for file {self.id}: usage={len(self.pages) if self.pages else 0}")
        except Exception as exc:
            warn(f"Failed to update cache for file {self.id}: {exc}")
            report_error("connection", f"Failed to update cache for file {self.id}")
            trace_out()
            return False

        self._cache_needs_refresh = False  # Reset flag after refresh
        
        trace_out()
        return not is_error()

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

    def flag_file_modification(self, comments: str) -> bool:
        trace_in()
        note = comments or ""
        # Get NOW() from database for consistency
        if not is_error():
            now_results = self.gateway.conn.read("SELECT NOW() as db_now")
            now = now_results[0]['db_now'] if now_results else dt.datetime.now()
        if not is_error():
            user_results = self.gateway.conn.read("SELECT USER() as db_user")
            db_user = user_results[0]["db_user"] if user_results else "unknown"
        
        # Validate timestamp: last_modified must be strictly greater than cache_built_at
        if not is_error():
            if self.cache_built_at is not None:
                if now < self.cache_built_at:
                    report_error("action", f"flag_file_modification: last_modified ({now}) cannot be less than cache_built_at ({self.cache_built_at})")
                elif now == self.cache_built_at:
                    # Increment by 1 second to ensure strict inequality
                    now = now + dt.timedelta(seconds=1)
                    # Verify it's now greater
                    if now <= self.cache_built_at:
                        report_error("action", f"flag_file_modification: After incrementing, last_modified ({now}) is still not greater than cache_built_at ({self.cache_built_at})")
        
        if not is_error():
            affected = self.gateway.conn.update(
                """
                UPDATE files
                SET last_modified = %s,
                    username = %s,
                    comments = %s
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
            # Buffer lightweight cache flag update (last_modified only)
            self.gateway.conn.buffer_cache_flag_modification("files", self.id, now)
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

    def show_file(self) -> Dict[str, Any]:
        trace_in()
        file_data = self.get_file_data()
        usage_data = self.get_usage_data()
        
        response_data: Dict[str, Any] = {
            "file": file_data,
            "usage": usage_data
        }
        
        log(f"Generated complete display data for file {self.id}: {self.file_name}")
        trace_out()
        return response_data

    def get_usage_data(self) -> List[Dict[str, Any]]:
        trace_in()
        # Check if field is already populated
        if hasattr(self, 'pages') and self.pages:
            debug(f"File {self.id}: returning cached usage data")
            trace_out()
            return self.pages
        # Field is empty, need to hydrate from database
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
        self.pages = usage_data
        # Only flag cache refresh if we actually found usage data (data changed)
        if usage_data:  # Only flag if actual usage data was found
            self._flag_cache_refresh()
        trace_out()
        return usage_data

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
