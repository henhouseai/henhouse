"""
TABLE OF CONTENTS (Alphabetical Order)
======================================

__init__()                    Line 48
_check_extra_actions()        Line 132
_dump_json()                  Line 198
_flag_cache_refresh()         Line 201
_get_usage_data()             Line 248
_is_file_shared()             Line 322
_json_default()               Line 334
_process_audio()              Line 339
_refresh_cached_audio()       Line 459
_soft_delete_files()          Line 580
add_audio_instance()          Line 619
copy_instances()              Line 663
delete_from_database()        Line 687
flag_audio_modification()     Line 707
get_audio_data()              Line 762
get_instances()               Line 810
get_instances_data()          Line 826
get_usage_count()             Line 847
get_used_by_pages()          Line 859
load_instances()              Line 870
modify_caption()             Line 892
modify_visibility()          Line 921
process_upload()             Line 936
show_audio()                 Line 955
update_view_count()          Line 987
validate_caption()           Line 1004

"""

from __future__ import annotations

import datetime as dt
import json
import mimetypes
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, cast
from uuid import uuid4

from hh.gateway.gateway import get_gateway
from hh.gateway.connection.utils import deserialize_json_blob, normalize_datetime
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
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


class Audio:

    id: int
    gateway: Any
    caption: Optional[str]
    username: Optional[str]
    uploaded: Optional[dt.datetime]
    visibility: Optional[int]
    view_count: Optional[int]
    last_modified: Optional[dt.datetime]
    comments: Optional[str]
    instances: List[Any]
    cached_usage: Optional[List[Any]]
    cache_built_at: Optional[Any]
    cache_source_last_modified: Optional[Any]
    cache_hydrated: bool
    _cache_needs_refresh: bool

    def __init__(self, audio_id: int):
        trace_in()
        self.gateway = get_gateway()
        debug(f"Initializing Audio with id={audio_id}")
        
        if not self.gateway or not self.gateway.conn:
            warn("Gateway or connection not available")
            report_error("connection", "Gateway or connection not available")
            trace_out()
            return
        
        # Initialize all fields
        self.id = audio_id
        self.caption = None
        self.username = None
        self.uploaded = None
        self.visibility = None
        self.last_modified = None
        self.comments = None
        self.view_count = None
        self.instances = []
        self.cached_usage = None
        self.cache_built_at = None
        self.cache_source_last_modified = None
        self.cache_hydrated = False
        self._cache_needs_refresh = False
        
        # Try to hydrate from cache database first (check cache before main DB)
        cache_hydrated = False
        if not is_error():
            # Get entire cache row to check staleness (no main DB read needed)
            cache_query = """
                SELECT id, caption, username, uploaded, last_modified, comments, visibility, viewCount,
                       instances, pages, cache_built_at
                FROM audio
                WHERE id = %s
            """
            try:
                cache_results = self.gateway.conn.read_cache(cache_query, [audio_id])
                if cache_results:
                    cache_row = cache_results[0]
                    cache_last_modified = cache_row.get('last_modified')
                    cache_built_at = cache_row.get('cache_built_at')
                    
                    # Check staleness using cache DB only: cache.last_modified vs cache.cache_built_at
                    cache_last_modified_dt = normalize_datetime(cache_last_modified)
                    cache_built_at_dt = normalize_datetime(cache_built_at)
                    
                    if cache_built_at_dt is None:
                        debug(f"Cache for audio {audio_id} does not exist (cache_built_at is NULL)")
                    elif cache_last_modified_dt and cache_built_at_dt and cache_built_at_dt < cache_last_modified_dt:
                        debug(f"Cache for audio {audio_id} is stale (cache_built_at={cache_built_at_dt}, cache.last_modified={cache_last_modified_dt})")
                    else:
                        # Cache is fresh - hydrate entirely from cache DB (no main DB access)
                        self.caption = cache_row.get('caption')
                        self.username = cache_row.get('username')
                        self.uploaded = cache_row.get('uploaded')
                        self.visibility = cache_row.get('visibility')
                        self.view_count = cache_row.get('viewCount')
                        self.last_modified = cache_last_modified
                        self.comments = cache_row.get('comments')
                        # Load expensive pre-computed data from cache database directly into live fields
                        self.instances = deserialize_json_blob(cache_row.get('instances'), [])
                        # Use cached_usage for now to match existing code, but this should be renamed to pages
                        self.cached_usage = deserialize_json_blob(cache_row.get('pages'), [])
                        self.cache_built_at = cache_built_at
                        self.cache_hydrated = True
                        cache_hydrated = True
                        log(f"Loaded audio {audio_id} entirely from cache: {self.caption}")
                        debug(f"Hydrated audio {audio_id} entirely from cache (built_at={cache_built_at_dt})")
                else:
                    debug(f"Cache for audio {audio_id} does not exist (no cache row found)")
            except Exception as e:
                warn(f"Failed to hydrate audio {audio_id} from cache: {e}")
                # Don't report error - cache hydration failure is not critical, will fall back to main DB
        
        # If cache is stale/missing, fall back to main database
        if not cache_hydrated and not is_error():
            # Load audio data from main database
            query = "SELECT * FROM audio WHERE id = %s"
            try:
                results = self.gateway.conn.read(query, [audio_id])
                if not results:
                    warn(f"Audio with id {audio_id} not found")
                    report_error("action", f"Audio with id {audio_id} not found")
                    trace_out()
                    return
                
                audio_data = results[0]
                self.caption = audio_data.get('caption')
                self.username = audio_data.get('username')
                self.uploaded = audio_data.get('uploaded')
                self.visibility = audio_data.get('visibility')
                self.view_count = audio_data.get('viewCount')
                self.last_modified = audio_data.get('last_modified')
                self.comments = audio_data.get('comments')
                self.cache_built_at = audio_data.get('cache_built_at')
                log(f"Loaded audio {audio_id} from main DB: {self.caption}")
            except Exception as e:
                warn(f"Failed to load audio {audio_id}: {e}")
                report_error("connection", f"Failed to load audio {audio_id}: {e}")
        
        trace_out()

    def _check_extra_actions(self) -> List[Dict[str, Any]]:
        trace_in()
        extra_actions = []
        if not is_error():
            # Check for orphaned audio instances (instances without files)
            try:
                orphaned_instances = []
                instances = self.get_instances()
                for instance in instances:
                    if not instance.get('file_path') or not instance.get('size_bytes', 0) > 0:
                        orphaned_instances.append(instance)
                if orphaned_instances:
                    extra_actions.append({
                        'type': 'warning',
                        'message': f"Found {len(orphaned_instances)} orphaned audio instances",
                        'details': cast(Any, orphaned_instances)
                    })
            except Exception as e:
                warn(f"Failed to check for orphaned instances: {str(e)}")
        if not is_error():
            # Check for audio with no usage (orphaned audio)
            try:
                usage_count = self.get_usage_count()
                if usage_count == 0:
                    extra_actions.append({
                        'type': 'info',
                        'message': "Audio is not used by any pages",
                        'details': {"usage_count": usage_count}
                    })
            except Exception as e:
                warn(f"Failed to check usage count: {str(e)}")
        if not is_error():
            # Check for audio with unusual file sizes
            try:
                instances = self.get_instances()
                for instance in instances:
                    size_bytes = instance.get('size_bytes', 0)
                    # Check for unusually large files
                    if size_bytes > 100 * 1024 * 1024:  # 100MB
                        extra_actions.append({
                            'type': 'warning',
                            'message': f"Large file detected: {size_bytes} bytes",
                            'details': cast(Any, {
                                'instance': instance,
                                'filesize_mb': round(size_bytes / (1024 * 1024), 2)
                            })
                        })
            except Exception as e:
                warn(f"Failed to check audio properties: {str(e)}")
        trace_out()
        return extra_actions

    def _dump_json(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'), default=self._json_default)

    def _flag_cache_refresh(self) -> None:
        """Flag that the cache needs to be refreshed. Called by getters when they derive/calculate data."""
        self._cache_needs_refresh = True

    def _get_usage_data(self) -> List[Dict[str, Any]]:
        trace_in()
        # Check if field is already populated
        if hasattr(self, 'cached_usage') and self.cached_usage is not None:
            debug(f"Audio {self.id}: returning cached usage data")
            trace_out()
            return self.cached_usage
        # Field is empty, need to hydrate from database
        usage_data = []
        if not is_error():
            try:
                query = """
                    SELECT 
                        ag.page_id,
                        p.name as page_name,
                        p.class as page_class,
                        COUNT(*) as usage_count,
                        GROUP_CONCAT(ag.audio_rank ORDER BY ag.audio_rank SEPARATOR ', ') as ranks
                    FROM audio_groups ag
                    JOIN pages p ON ag.page_id = p.id
                    WHERE ag.audio_id = %s
                    GROUP BY ag.page_id, p.name, p.class
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
                        warn(f"Skipping orphaned audio_group entry: page {page_id} does not exist")
                        continue
                    
                    # Get the page path for breadcrumb display
                    # Handle failures gracefully - we can still show usage without the path
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
                log(f"Found {len(usage_data)} pages using audio {self.id}")
            except Exception as e:
                warn(f"Failed to get usage data for audio {self.id}: {str(e)}")
                report_error("backend", f"Failed to get usage data: {str(e)}")
        self.cached_usage = usage_data
        # Only flag cache refresh if we actually found usage data (data changed)
        if usage_data:  # Only flag if actual usage data was found
            self._flag_cache_refresh()
        trace_out()
        return usage_data

    def _is_file_shared(self, file_path: str) -> bool:
        try:
            query = "SELECT COUNT(*) as count FROM audio_instances WHERE file_path = %s AND audio_id != %s"
            results = self.gateway.conn.read(query, [file_path, self.id])
            if results:
                count = results[0]['count']
                return count > 0
            return False
        except Exception as e:
            warn(f"Failed to check if file is shared: {str(e)}")
            return False

    def _json_default(self, value: Any):
        if isinstance(value, (dt.datetime, dt.date)):
            return value.isoformat()
        return value

    def _process_audio(self, source_file_path: str, filename_base: str) -> List[Dict[str, Any]]:
        trace_in()
        log(f"Starting audio processing: {source_file_path} -> {filename_base}")
        try:
            from hh.image.image_utils import create_date_directory
            from hh.deploy.deploy_utils import detect_project_context
            
            # Get base path for audio storage
            try:
                project_name, _ = detect_project_context()
                base_path = Path(f"/srv/audio/{project_name}")
            except Exception as e:
                warn(f"Failed to detect project context: {e}")
                report_error("action", f"Failed to detect project context: {e}")
                trace_out()
                return []
            
            # Validate source file exists
            if not Path(source_file_path).exists():
                warn(f"Source file not found: {source_file_path}")
                report_error("action", f"Source file not found: {source_file_path}")
                log(f"Audio processing FAILED: Source file not found - {source_file_path}")
                trace_out()
                return []
            
            # Validate MIME type
            import mimetypes
            mime_type = mimetypes.guess_type(source_file_path)[0] or "application/octet-stream"
            if not mime_type.startswith('audio/'):
                warn(f"Invalid MIME type for audio file: {mime_type}")
                report_error("action", f"Invalid MIME type for audio file: {mime_type}")
                log(f"Audio processing FAILED: Invalid MIME type - {source_file_path} ({mime_type})")
                trace_out()
                return []
            
            # Validate audio file (attempt to load with mutagen)
            from hh.audio.audio_utils import validate_audio_file, get_audio_info
            if not validate_audio_file(source_file_path):
                warn(f"Failed to validate audio file: {source_file_path}")
                report_error("action", f"Invalid or corrupted audio file: {source_file_path}")
                log(f"Audio processing FAILED: File validation failed - {source_file_path}")
                trace_out()
                return []
            
            # Create date-based directory structure
            try:
                date_path = create_date_directory(base_path)
                if not date_path:
                    warn(f"Failed to create date directory")
                    report_error("action", "Failed to create date directory")
                    log(f"Audio processing FAILED: Could not create date directory - {base_path}")
                    trace_out()
                    return []
            except Exception as e:
                error_msg = str(e)
                warn(f"Failed to create date directory: {error_msg}")
                report_error("action", error_msg)
                log(f"Audio processing FAILED: Could not create date directory - {base_path} - {error_msg}")
                trace_out()
                return []
            
            # Copy file to date-based directory
            original_name = Path(source_file_path).name
            sanitized_stem = "".join(ch if ch.isalnum() or ch in (".", "_", "-", " ") else "-" for ch in Path(original_name).stem)
            sanitized_stem = sanitized_stem.strip() or "file"
            suffix = Path(original_name).suffix
            unique_suffix = uuid4().hex[:8]
            stored_filename = f"{sanitized_stem}-{unique_suffix}{suffix}"
            
            destination = date_path / stored_filename
            try:
                shutil.copy2(source_file_path, destination)
                os.chmod(destination, 0o664)
            except Exception as e:
                warn(f"Failed to copy audio file: {str(e)}")
                report_error("action", f"Failed to copy audio file: {str(e)}")
                log(f"Audio processing FAILED: Could not copy file - {source_file_path} -> {destination}")
                trace_out()
                return []
            
            # Get file size
            size_bytes = destination.stat().st_size
            
            # Extract audio metadata if available
            audio_info = get_audio_info(str(destination))
            duration_seconds = audio_info.get('duration_seconds') if audio_info else None
            bitrate = audio_info.get('bitrate') if audio_info else None
            
            # Create relative path
            relative_path = str(destination.relative_to(base_path))
            
            # Create single 'full' instance (original file)
            instance_data = {
                'instance_type': 'full',
                'file_path': relative_path,
                'mime_type': mime_type,
                'size_bytes': size_bytes,
                'duration_seconds': duration_seconds,
                'bitrate': bitrate
            }
            
            # Note: Standard AAC version will be created by background maintenance task
            # This allows immediate streaming of original while transcoding happens async
            
            log(f"Audio processing COMPLETED: 1 instance created, {size_bytes} bytes, base_path={base_path}")
            trace_out()
            return [instance_data]
        except Exception as e:
            warn(f"Audio processing failed: {str(e)}")
            report_error("action", f"Audio processing failed: {str(e)}")
            log(f"Audio processing FAILED: Unexpected error - {source_file_path} -> {str(e)}")
            trace_out()
            return []

    def _refresh_cached_audio(self) -> bool:
        """Refresh the cache database with instances and pages (usage) fields. Called by gateway during commit."""
        trace_in()
        debug(f"_refresh_cached_audio: Starting for audio {self.id}")
        if not self.gateway or not self.gateway.conn:
            warn(f"_refresh_cached_audio: gateway or connection not available for audio {self.id}")
            trace_out()
            return False
        # Ensure both fields are populated by calling their internal mixin methods
        # The getters check if field is populated first, and only hydrate if empty
        # The getters set the attributes themselves, so we just call them
        # This ensures we always have fully hydrated data to cache
        
        if not self.instances:
            self.get_instances()
        
        if not self.cached_usage:
            self._get_usage_data()
        
        # Serialize all data
        instances_json = self._dump_json(self.instances) if self.instances else None
        usage_json = self._dump_json(self.cached_usage) if self.cached_usage else None
        
        now = dt.datetime.now()
        
        try:
            # Buffer cache database write with all main DB fields as first-class columns
            # plus derived fields
            # Uses INSERT ... ON DUPLICATE KEY UPDATE to handle both insert and update cases
            self.gateway.conn.buffer_cache(
                "audio",
                """
                    INSERT INTO audio (id, caption, username, uploaded, last_modified, comments, visibility, viewCount, instances, pages, cache_built_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        caption = VALUES(caption),
                        username = VALUES(username),
                        uploaded = VALUES(uploaded),
                        last_modified = VALUES(last_modified),
                        comments = VALUES(comments),
                        visibility = VALUES(visibility),
                        viewCount = VALUES(viewCount),
                        instances = VALUES(instances),
                        pages = VALUES(pages),
                        cache_built_at = VALUES(cache_built_at)
                """,
                (
                    self.id,
                    self.caption,
                    self.username,
                    self.uploaded,
                    self.last_modified,
                    self.comments,
                    self.visibility,
                    self.view_count,
                    instances_json,
                    usage_json,
                    now,
                ),
            )
            # Always bump main database cache_built_at
            self.gateway.conn.update(
                """
                    UPDATE audio
                    SET cache_built_at = %s
                    WHERE id = %s
                """,
                (now, self.id),
            )
            # Verify the data was actually written by reading it back
            verify_check = self.gateway.conn.read_cache(
                "SELECT cache_built_at FROM audio WHERE id = %s",
                (self.id,),
            )
            if verify_check:
                debug(f"_refresh_cached_audio: Verification - cache entry has cache_built_at={verify_check[0].get('cache_built_at')}")
            else:
                warn(f"_refresh_cached_audio: Verification failed - cache entry not found after write")
            
            debug(f"Refreshed cache for audio {self.id}: instances={len(self.instances) if self.instances else 0}, usage={len(self.cached_usage) if self.cached_usage else 0}")
        except Exception as exc:
            warn(f"Failed to update cache for audio {self.id}: {exc}")
            report_error("connection", f"Failed to update cache for audio {self.id}")
            trace_out()
            return False

        self._cache_needs_refresh = False  # Reset flag after refresh
        
        trace_out()
        return not is_error()

    def _soft_delete_files(self) -> bool:
        trace_in()
        try:
            # Load instances if not already loaded (this populates self.instances)
            self.get_instances()
            # Get project context for base path
            from hh.deploy.deploy_utils import detect_project_context
            from pathlib import Path
            project_name, _ = detect_project_context()
            base_path = Path(f"/srv/audio/{project_name}")
            deleted_path = base_path / "deleted"
            # Ensure deleted directory exists (will be created when file operations execute)
            deleted_path.mkdir(parents=True, exist_ok=True)
            # Process each instance file
            for instance in (self.instances or []):
                file_path = instance.get('file_path', '')
                if not file_path:
                    continue
                # Full path to the current file
                current_file = base_path / file_path
                if not current_file.exists():
                    log(f"File not found, skipping: {current_file}")
                    continue
                # Check if any other audio still use this file
                if self._is_file_shared(file_path):
                    log(f"File is shared by other audio, keeping: {file_path}")
                    continue
                # Schedule move file to deleted folder (buffered, will execute after DB commit)
                deleted_file = deleted_path / current_file.name
                self.gateway.files.schedule_move(str(current_file), str(deleted_file))
                log(f"Scheduled file move to deleted folder: {file_path} -> deleted/{current_file.name}")
            trace_out()
            return True
        except Exception as e:
            warn(f"Failed to schedule soft delete files: {str(e)}")
            report_error("file_operation", f"Failed to schedule soft delete: {str(e)}")
            trace_out()
            return False

    def add_audio_instance(self, instance_type: str, file_path: str, mime_type: str, size_bytes: int, duration_seconds: Optional[float] = None, bitrate: Optional[int] = None) -> bool:
        trace_in()
        log(f"Adding audio instance for audio {self.id}: {instance_type}")
        if not is_error():
            new_id = self.gateway.conn.create("""
                INSERT INTO audio_instances (audio_id, instance_type, file_path, mime_type, size_bytes, duration_seconds, bitrate)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (self.id, instance_type, file_path, mime_type, size_bytes, duration_seconds, bitrate))
            if new_id is not None:
                # Add to instances list
                self.instances.append({
                    'instance_type': instance_type,
                    'file_path': file_path,
                    'mime_type': mime_type,
                    'size_bytes': size_bytes,
                    'duration_seconds': duration_seconds,
                    'bitrate': bitrate
                })
                log(f"Successfully added audio instance for audio {self.id}")
            else:
                warn(f"Failed to add audio instance for audio {self.id}")
                report_error("action", f"Failed to add audio instance for audio {self.id}")
        trace_out()
        return not is_error()

    def copy_instances(self, target_audio) -> bool:
        trace_in()
        log(f"Copying instances from audio {target_audio.id} to audio {self.id}")
        if not is_error():
            # Get instances from target audio
            target_instances = target_audio.get_instances()
            if not target_instances:
                warn(f"No instances found in target audio {target_audio.id}")
                report_error("action", f"No instances found in target audio {target_audio.id}")
                trace_out()
                return False
            # Copy each instance
            copied_count = 0
            for instance in target_instances:
                if not self.add_audio_instance(
                    instance['instance_type'],
                    instance['file_path'],
                    instance['mime_type'],
                    instance['size_bytes'],
                    instance.get('duration_seconds'),
                    instance.get('bitrate')
                ):
                    warn(f"Failed to copy instance: {instance['instance_type']}")
                    report_error("action", f"Failed to copy instance: {instance['instance_type']}")
                    trace_out()
                    return False
                copied_count += 1
            log(f"Successfully copied {copied_count} instances from audio {target_audio.id} to audio {self.id}")
        trace_out()
        return not is_error()

    def delete_from_database(self) -> bool:
        trace_in()
        log(f"Deleting audio {self.id} from database")
        if not is_error():
            # Check if audio is still used by any pages
            usage_count = self.get_usage_count()
            if usage_count > 0:
                warn(f"Cannot delete audio {self.id}: still used by {usage_count} pages")
                report_error("action", f"Cannot delete audio {self.id}: still used by {usage_count} pages")
                trace_out()
                return False
            # Soft delete: move files to deleted folder before removing from database
            self._soft_delete_files()
            # Delete audio instances first
            self.gateway.conn.delete("DELETE FROM audio_instances WHERE audio_id = %s", [self.id])
            self.gateway.conn.delete("DELETE FROM audio WHERE id = %s", [self.id])
            log(f"Successfully deleted audio {self.id}")
        trace_out()
        return not is_error()

    def flag_audio_modification(self, comments: str) -> bool:
        trace_in()
        note = comments or ""
        now = dt.datetime.now()
        if not is_error():
            user_results = self.gateway.conn.read("SELECT USER() as db_user")
            db_user = user_results[0]['db_user'] if user_results else 'unknown'
        if not is_error():
            affected = self.gateway.conn.update(
                """
                UPDATE audio
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

    def get_audio_data(self) -> Dict[str, Any]:
        trace_in()
        debug(f"Getting audio data for audio {self.id}")
        # Get instances data to compute derived fields
        instances = self.get_instances()
        
        # Compute derived fields from instances
        max_filesize = 0
        file_path = "N/A"
        mime_type = "N/A"
        duration_seconds = None
        bitrate = None
        
        if instances:
            max_filesize = max(inst.get('size_bytes', 0) for inst in instances)
            # Get folder path from first instance
            if instances[0].get('file_path'):
                file_path_str = instances[0]['file_path']
                last_slash = file_path_str.rfind('/')
                if last_slash != -1:
                    file_path = file_path_str[:last_slash + 1]
                else:
                    file_path = file_path_str
            # Get MIME type from first instance
            if instances[0].get('mime_type'):
                mime_type = instances[0]['mime_type']
            # Get duration and bitrate from first instance (if available)
            if instances[0].get('duration_seconds'):
                duration_seconds = instances[0]['duration_seconds']
            if instances[0].get('bitrate'):
                bitrate = instances[0]['bitrate']
        
        data = {
            "id": self.id,
            "caption": self.caption,
            "username": self.username,
            "uploaded": self.uploaded,
            "last_modified": self.last_modified,
            "comments": self.comments,
            "visibility": self.visibility,
            "view_count": self.view_count,
            "instances": self.instances,
            "max_filesize": max_filesize,
            "file_path": file_path,
            "mime_type": mime_type,
            "duration_seconds": duration_seconds,
            "bitrate": bitrate,
            "num_instances": len(instances)
        }
        trace_out()
        return data

    def get_instances(self) -> List[Dict[str, Any]]:
        trace_in()
        # Check if field is already populated
        if hasattr(self, 'instances') and self.instances:
            debug(f"Audio {self.id}: returning cached instances")
            trace_out()
            return self.instances.copy()
        # Field is empty, need to hydrate from database
        instances = self.load_instances()
        self.instances = instances
        # Only flag cache refresh if we actually found instances (data changed)
        if instances:  # Only flag if actual instances were loaded
            self._flag_cache_refresh()
        trace_out()
        return self.instances.copy()

    def get_instances_data(self) -> List[Dict[str, Any]]:
        trace_in()
        instances_data = []
        if not is_error():
            for instance in self.instances:
                # Extract filename from file_path
                from pathlib import Path
                file_path = instance.get('file_path', '')
                filename = Path(file_path).name if file_path else f"audio_{self.id}_unknown"
                instance_data = {
                    'instance_type': instance.get('instance_type', 'full'),
                    'file_path': instance.get('file_path', ''),
                    'mime_type': instance.get('mime_type', ''),
                    'size_bytes': instance.get('size_bytes', 0),
                    'duration_seconds': instance.get('duration_seconds'),
                    'bitrate': instance.get('bitrate'),
                    'filename': filename
                }
                instances_data.append(instance_data)
            log(f"Prepared {len(instances_data)} instances for audio {self.id}")
        trace_out()
        return instances_data

    def get_usage_count(self) -> int:
        trace_in()
        count = 0
        if not is_error():
            query = "SELECT COUNT(*) as count FROM audio_groups WHERE audio_id = %s"
            results = self.gateway.conn.read(query, [self.id])
            if results:
                count = results[0]['count']
        log(f"Audio {self.id} is used by {count} pages")
        trace_out()
        return count

    def get_used_by_pages(self) -> List[int]:
        trace_in()
        page_ids = []
        if not is_error():
            query = "SELECT page_id FROM audio_groups WHERE audio_id = %s ORDER BY page_id"
            results = self.gateway.conn.read(query, [self.id])
            page_ids = [row['page_id'] for row in results]
        log(f"Audio {self.id} is used by pages: {page_ids}")
        trace_out()
        return page_ids

    def load_instances(self) -> List[Dict[str, Any]]:
        trace_in()
        debug(f"Loading instances for audio {self.id}")
        instances = []
        if not is_error():
            try:
                query = "SELECT * FROM audio_instances WHERE audio_id = %s ORDER BY instance_type"
                results = self.gateway.conn.read(query, [self.id])
                for row in results:
                    instances.append({
                        'instance_type': row['instance_type'],
                        'file_path': row['file_path'],
                        'mime_type': row['mime_type'],
                        'size_bytes': row['size_bytes'],
                        'duration_seconds': row.get('duration_seconds'),
                        'bitrate': row.get('bitrate')
                    })
                log(f"Loaded {len(instances)} instances for audio {self.id}")
            except Exception as e:
                warn(f"Failed to load instances for audio {self.id}: {str(e)}")
                report_error("backend", f"Failed to load instances: {str(e)}")
        trace_out()
        return instances

    def modify_caption(self, caption: str) -> bool:
        trace_in()
        log(f"Modifying caption for audio {self.id}: '{self.caption}' -> '{caption}'")
        if caption == self.caption:
            log("Caption unchanged, no update needed")
            trace_out()
            return True
        if not is_error():
            log(f"Validating new caption '{caption}' for audio {self.id}")
            if not self.validate_caption(caption):
                warn("Caption validation failed")
                report_error("action", "Caption validation failed")
            else:
                log(f"Caption validation passed for '{caption}'")
        if not is_error():
            log(f"Updating audio {self.id} caption in database: '{self.caption}' -> '{caption}'")
            affected = self.gateway.conn.update("UPDATE audio SET caption = %s WHERE id = %s", (caption, self.id))
            if affected == 0:
                warn(f"Failed to update audio {self.id} caption - no rows affected")
                report_error("action", f"Failed to update audio {self.id} caption")
            else:
                log(f"Successfully updated audio {self.id} caption in database")
        if not is_error():
            self.caption = caption
            log(f"Successfully updated audio {self.id} caption to '{caption}'")
            self.flag_audio_modification("caption updated")
        trace_out()
        return not is_error()

    def modify_visibility(self, visibility: int) -> bool:
        trace_in()
        log(f"Modifying visibility for audio {self.id}: {self.visibility} -> {visibility}")
        if not is_error():
            affected = self.gateway.conn.update("UPDATE audio SET visibility = %s WHERE id = %s", (visibility, self.id))
            if affected == 0:
                warn(f"Failed to update audio {self.id} visibility - no rows affected")
                report_error("action", f"Failed to update audio {self.id} visibility")
            else:
                self.visibility = visibility
                log(f"Successfully updated visibility for audio {self.id}")
                self.flag_audio_modification("visibility updated")
        trace_out()
        return not is_error()

    def process_upload(self, uploaded_file_path: str, filename: str) -> bool:
        trace_in()
        log(f"Processing upload for audio {self.id}: {uploaded_file_path}")
        if not is_error():
            instances_data = self._process_audio(uploaded_file_path, filename)
            if not instances_data:
                warn("No audio instances created")
                report_error("action", "Audio processing failed")
                trace_out()
                return False
            # Save instances to database
            for instance_data in instances_data:
                if not self.add_audio_instance(
                    instance_data['instance_type'],
                    instance_data['file_path'],
                    instance_data['mime_type'],
                    instance_data['size_bytes'],
                    instance_data.get('duration_seconds'),
                    instance_data.get('bitrate')
                ):
                    trace_out()
                    return False
            log(f"Successfully processed {len(instances_data)} audio instances")
            
            # Enqueue maintenance job for transcoding to standard AAC format
            if not is_error():
                try:
                    job_id = self._enqueue_maintenance_job(
                        "audio_transcode",
                        {
                            "audio_id": self.id,
                        },
                    )
                    log(f"Enqueued maintenance job {job_id} for audio {self.id} transcoding")
                except Exception as exc:  # noqa: BLE001
                    warn(f"Failed to enqueue maintenance job for audio {self.id}: {exc}")
        trace_out()
        return not is_error()

    def show_audio(self) -> Dict[str, Any]:
        trace_in()
        cache_ready = getattr(self, 'cache_hydrated', False) and getattr(self, 'cached_usage', None) is not None
        if cache_ready:
            debug(f"Audio {self.id}: cache available, methods will check cache independently")
        else:
            debug(f"Audio {self.id}: cache miss or stale entry; rebuilding show_audio payload")
        
        audio_data = self.get_audio_data()
        usage_data = self._get_usage_data()
        self.get_instances()  # Ensure instances are loaded before get_instances_data()
        instances_data = self.get_instances_data()
        
        extra_actions: List[Dict[str, Any]] = []
        if not is_error():
            extra_actions = self._check_extra_actions()
            if extra_actions:
                log(f"Found {len(extra_actions)} extra actions for audio {self.id}")

        response_data: Dict[str, Any] = {
            "audio": audio_data,
            "usage": usage_data,
            "instances": instances_data
        }
        if extra_actions:
            response_data["extra_actions"] = extra_actions
        
        # Cache refresh will be handled by wrapper method system if flag is set
        log(f"Generated complete display data for audio {self.id}: {self.caption}")
        trace_out()
        return response_data

    def update_view_count(self, increment: int = 1) -> bool:
        trace_in()
        log(f"Updating view count for audio {self.id}: +{increment}")
        
        if not is_error():
            affected = self.gateway.conn.update("UPDATE audio SET viewCount = viewCount + %s WHERE id = %s", 
                              (increment, self.id))
            if affected == 0:
                warn(f"Failed to update audio {self.id} view count - no rows affected")
                report_error("action", f"Failed to update audio {self.id} view count")
            else:
                self.view_count = (self.view_count or 0) + increment
                log(f"Successfully updated view count for audio {self.id}")
        
        trace_out()
        return not is_error()

    def _enqueue_maintenance_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        priority: int = 0,
    ) -> int:
        trace_in()
        payload_json = json.dumps(payload or {}, ensure_ascii=False, separators=(",", ":"))
        job_id = self.gateway.conn.create(
            """
            INSERT INTO maintenance_jobs (job_type, status, payload_json, priority)
            VALUES (%s, 'pending', %s, %s)
            """,
            (job_type, payload_json, priority),
        )
        debug(f"Enqueued maintenance job {job_id}: type={job_type}, priority={priority}")
        trace_out()
        return job_id

    def validate_caption(self, caption: str) -> bool:
        trace_in()
        log(f"Validating caption: '{caption}' for audio {self.id}")
        if len(caption) > 255:
            warn(f"Caption too long: {len(caption)} characters (max 255)")
            log(f"Validation failed: caption too long ({len(caption)} chars)")
            trace_out()
            return False
        if caption and caption.isdigit():
            warn("Caption cannot be all digits")
            log("Validation failed: caption is all digits")
            trace_out()
            return False
        if any(char in caption for char in ['{', '}', '[', ']', ':']):
            warn(f"Caption contains illegal characters: {caption}")
            log("Validation failed: illegal characters")
            trace_out()
            return False
        log(f"Caption validation successful for '{caption}'")
        trace_out()
        return True
