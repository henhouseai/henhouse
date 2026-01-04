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
_process_image()              Line 339
_process_size()               Line 425
_refresh_cached_image()       Line 459
_save_full_size()             Line 554
_soft_delete_files()          Line 580
add_image_instance()          Line 619
check_incoming_links()        Line 642
copy_instances()              Line 663
delete_from_database()        Line 687
flag_image_modification()     Line 707
get_best_instance()          Line 735
get_image_data()              Line 762
get_instances()               Line 810
get_instances_data()          Line 826
get_usage_count()             Line 847
get_used_by_pages()          Line 859
load_instances()              Line 870
modify_caption()             Line 892
modify_visibility()          Line 921
process_upload()             Line 936
show_image()                 Line 955
update_view_count()          Line 987
validate_caption()           Line 1004

"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, cast

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


class Image:

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

    def __init__(self, image_id: int):
        trace_in()
        self.gateway = get_gateway()
        debug(f"Initializing Image with id={image_id}")
        
        if not self.gateway or not self.gateway.conn:
            warn("Gateway or connection not available")
            report_error("connection", "Gateway or connection not available")
            trace_out()
            return
        
        # Initialize all fields
        self.id = image_id
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
                FROM images
                WHERE id = %s
            """
            try:
                cache_results = self.gateway.conn.read_cache(cache_query, [image_id])
                if cache_results:
                    cache_row = cache_results[0]
                    cache_last_modified = cache_row.get('last_modified')
                    cache_built_at = cache_row.get('cache_built_at')
                    
                    # Check staleness using cache DB only: cache.last_modified vs cache.cache_built_at
                    cache_last_modified_dt = normalize_datetime(cache_last_modified)
                    cache_built_at_dt = normalize_datetime(cache_built_at)
                    
                    if cache_built_at_dt is None:
                        debug(f"Cache for image {image_id} does not exist (cache_built_at is NULL)")
                    elif cache_last_modified_dt and cache_built_at_dt and cache_built_at_dt < cache_last_modified_dt:
                        debug(f"Cache for image {image_id} is stale (cache_built_at={cache_built_at_dt}, cache.last_modified={cache_last_modified_dt})")
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
                        log(f"Loaded image {image_id} entirely from cache: {self.caption}")
                        debug(f"Hydrated image {image_id} entirely from cache (built_at={cache_built_at_dt})")
                else:
                    debug(f"Cache for image {image_id} does not exist (no cache row found)")
            except Exception as e:
                warn(f"Failed to hydrate image {image_id} from cache: {e}")
                # Don't report error - cache hydration failure is not critical, will fall back to main DB
        
        # If cache is stale/missing, fall back to main database
        if not cache_hydrated and not is_error():
            # Load image data from main database
            query = "SELECT * FROM images WHERE id = %s"
            try:
                results = self.gateway.conn.read(query, [image_id])
                if not results:
                    warn(f"Image with id {image_id} not found")
                    report_error("action", f"Image with id {image_id} not found")
                    trace_out()
                    return
                
                image_data = results[0]
                self.caption = image_data.get('caption')
                self.username = image_data.get('username')
                self.uploaded = image_data.get('uploaded')
                self.visibility = image_data.get('visibility')
                self.view_count = image_data.get('viewCount')
                self.last_modified = image_data.get('last_modified')
                self.comments = image_data.get('comments')
                self.cache_built_at = image_data.get('cache_built_at')
                log(f"Loaded image {image_id} from main DB: {self.caption}")
            except Exception as e:
                warn(f"Failed to load image {image_id}: {e}")
                report_error("connection", f"Failed to load image {image_id}: {e}")
        
        trace_out()

    def _check_extra_actions(self) -> List[Dict[str, Any]]:
        trace_in()
        extra_actions = []
        if not is_error():
            # Check for orphaned image instances (instances without files)
            try:
                orphaned_instances = []
                instances = self.get_instances()
                for instance in instances:
                    if not instance.get('src') or not instance.get('filesize', 0) > 0:
                        orphaned_instances.append(instance)
                if orphaned_instances:
                    extra_actions.append({
                        'type': 'warning',
                        'message': f"Found {len(orphaned_instances)} orphaned image instances",
                        'details': cast(Any, orphaned_instances)
                    })
            except Exception as e:
                warn(f"Failed to check for orphaned instances: {str(e)}")
        if not is_error():
            # Check for images with no usage (orphaned images)
            try:
                usage_count = self.get_usage_count()
                if usage_count == 0:
                    extra_actions.append({
                        'type': 'info',
                        'message': "Image is not used by any pages",
                        'details': {"usage_count": usage_count}
                    })
            except Exception as e:
                warn(f"Failed to check usage count: {str(e)}")
        if not is_error():
            # Check for images with unusual file sizes or dimensions
            try:
                instances = self.get_instances()
                for instance in instances:
                    width = instance.get('width', 0)
                    height = instance.get('height', 0)
                    filesize = instance.get('filesize', 0)
                    # Check for unusually large files
                    if filesize > 10 * 1024 * 1024:  # 10MB
                        extra_actions.append({
                            'type': 'warning',
                            'message': f"Large file detected: {filesize} bytes",
                            'details': cast(Any, {
                                'instance': instance,
                                'filesize_mb': round(filesize / (1024 * 1024), 2)
                            })
                        })
                    # Check for unusual aspect ratios
                    if width > 0 and height > 0:
                        aspect_ratio = width / height
                        if aspect_ratio > 5 or aspect_ratio < 0.2:
                            extra_actions.append({
                                'type': 'info',
                                'message': f"Unusual aspect ratio: {aspect_ratio:.2f}",
                                'details': cast(Any, {
                                    'instance': instance,
                                    'aspect_ratio': aspect_ratio
                                })
                            })
            except Exception as e:
                warn(f"Failed to check image properties: {str(e)}")
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
            debug(f"Image {self.id}: returning cached usage data")
            trace_out()
            return self.cached_usage
        # Field is empty, need to hydrate from database
        usage_data = []
        if not is_error():
            try:
                query = """
                    SELECT 
                        ig.page_id,
                        p.name as page_name,
                        p.class as page_class,
                        COUNT(*) as usage_count,
                        GROUP_CONCAT(ig.image_rank ORDER BY ig.image_rank SEPARATOR ', ') as ranks
                    FROM image_groups ig
                    JOIN pages p ON ig.page_id = p.id
                    WHERE ig.image_id = %s
                    GROUP BY ig.page_id, p.name, p.class
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
                        warn(f"Skipping orphaned image_group entry: page {page_id} does not exist")
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
                log(f"Found {len(usage_data)} pages using image {self.id}")
            except Exception as e:
                warn(f"Failed to get usage data for image {self.id}: {str(e)}")
                report_error("backend", f"Failed to get usage data: {str(e)}")
        self.cached_usage = usage_data
        # Only flag cache refresh if we actually found usage data (data changed)
        if usage_data:  # Only flag if actual usage data was found
            self._flag_cache_refresh()
        trace_out()
        return usage_data

    def _is_file_shared(self, src_path: str) -> bool:
        try:
            query = "SELECT COUNT(*) as count FROM image_instances WHERE src = %s AND image_id != %s"
            results = self.gateway.conn.read(query, [src_path, self.id])
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

    def _process_image(self, source_file_path: str, filename_base: str) -> List[Dict[str, Any]]:
        trace_in()
        log(f"Starting image processing: {source_file_path} -> {filename_base}")
        try:
            from hh.image.image_utils import load_image, validate_image_size, create_date_directory
            from hh.image.image_size_tiers import IMAGE_SIZE_TIERS, MIN_IMAGE_WIDTH
            from pathlib import Path
            # Get base path for image storage
            try:
                from hh.deploy.deploy_utils import detect_project_context
                project_name, _ = detect_project_context()
                base_path = Path(f"/srv/images/{project_name}")
            except Exception as e:
                warn(f"Failed to detect project context: {e}")
                report_error("action", f"Failed to detect project context: {e}")
                trace_out()
                return []
            # Validate source file exists
            if not Path(source_file_path).exists():
                warn(f"Source file not found: {source_file_path}")
                report_error("action", f"Source file not found: {source_file_path}")
                log(f"Image processing FAILED: Source file not found - {source_file_path}")
                trace_out()
                return []
            # Load and validate image
            img = load_image(source_file_path)
            if not img:
                warn(f"Failed to load image: {source_file_path}")
                report_error("action", f"Failed to load image: {source_file_path}")
                log(f"Image processing FAILED: Could not load image - {source_file_path}")
                trace_out()
                return []
            # Validate minimum size requirements
            if not validate_image_size(img, min_width=MIN_IMAGE_WIDTH):
                warn(f"Image too small: {source_file_path}")
                report_error("action", f"Image too small: {source_file_path}")
                log(f"Image processing FAILED: Image too small - {source_file_path}")
                trace_out()
                return []
            # Create date-based directory structure
            try:
                date_path = create_date_directory(base_path)
                if not date_path:
                    warn(f"Failed to create date directory")
                    report_error("action", "Failed to create date directory")
                    log(f"Image processing FAILED: Could not create date directory - {base_path}")
                    trace_out()
                    return []
            except Exception as e:
                error_msg = str(e)
                warn(f"Failed to create date directory: {error_msg}")
                report_error("action", error_msg)
                log(f"Image processing FAILED: Could not create date directory - {base_path} - {error_msg}")
                trace_out()
                return []
            # Process image sizes - dynamic tier processing
            instances = []
            # 1. Always save full-size version first
            full_size_data = self._save_full_size(img, date_path, filename_base, base_path)
            if full_size_data:
                instances.append(full_size_data)
                log(f"Saved full-size image: {img.width}x{img.height}")
            # 2. Process each size tier dynamically
            size_tiers = IMAGE_SIZE_TIERS
            for tier_name, target_width in size_tiers.items():
                if not is_error():
                    # Only process if original is larger than target (prevent upsampling)
                    if img.width > target_width:
                        instance_data = self._process_size(img, tier_name, target_width, date_path, filename_base, base_path)
                        if instance_data:
                            instances.append(instance_data)
                            log(f"Created {tier_name} variant: {target_width}px (downsampled from {img.width}px)")
                    else:
                        log(f"Skipped {tier_name} variant: original {img.width}px <= target {target_width}px (no upsampling)")
            # Calculate total file size
            total_size = sum(instance['filesize'] for instance in instances)
            log(f"Image processing COMPLETED: {len(instances)} instances created, {total_size} bytes total, base_path={base_path}")
            trace_out()
            return instances
        except Exception as e:
            warn(f"Image processing failed: {str(e)}")
            report_error("action", f"Image processing failed: {str(e)}")
            log(f"Image processing FAILED: Unexpected error - {source_file_path} -> {str(e)}")
            trace_out()
            return []

    def _process_size(self, img, tier_name: str, target_width: int, date_path: Path, filename_base: str, base_path: Path) -> Optional[Dict[str, Any]]:
        trace_in()
        try:
            from hh.image.image_utils import calculate_target_height, scale_image, write_jpg
            # Calculate target dimensions
            target_height = calculate_target_height(img, target_width)
            # Scale image
            scaled_img = scale_image(img, target_width, target_height)
            if not scaled_img:
                log(f"Size processing FAILED: {tier_name} ({target_width}px) - scaling failed")
                trace_out()
                return None
            # Generate file path with tier name
            filepath = date_path / f"{filename_base}_{tier_name}.jpg"
            # Write image file
            if write_jpg(scaled_img, filepath, 80):  # Default quality
                result = {
                    'width': scaled_img.width,
                    'height': scaled_img.height,
                    'src': str(filepath.relative_to(base_path)),
                    'filesize': filepath.stat().st_size
                }
                log(f"Size processing SUCCESS: {tier_name} -> {scaled_img.width}x{scaled_img.height}, {result['filesize']} bytes, {result['src']}")
                trace_out()
                return result
            log(f"Size processing FAILED: {tier_name} ({target_width}px) - JPEG write failed")
            trace_out()
            return None
        except Exception as e:
            warn(f"Failed to process size {tier_name}: {str(e)}")
            log(f"Size processing FAILED: {tier_name} ({target_width}px) - {str(e)}")
            trace_out()
            return None

    def _refresh_cached_image(self) -> bool:
        """Refresh the cache database with instances and pages (usage) fields. Called by gateway during commit."""
        trace_in()
        debug(f"_refresh_cached_image: Starting for image {self.id}")
        if not self.gateway or not self.gateway.conn:
            warn(f"_refresh_cached_image: gateway or connection not available for image {self.id}")
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
                "images",
                """
                    INSERT INTO images (id, caption, username, uploaded, last_modified, comments, visibility, viewCount, instances, pages, cache_built_at)
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
                warn(f"_refresh_cached_image: Verification failed - cache entry not found after write")
            
            debug(f"Refreshed cache for image {self.id}: instances={len(self.instances) if self.instances else 0}, usage={len(self.cached_usage) if self.cached_usage else 0}")
        except Exception as exc:
            warn(f"Failed to update cache for image {self.id}: {exc}")
            report_error("connection", f"Failed to update cache for image {self.id}")
            trace_out()
            return False

        self._cache_needs_refresh = False  # Reset flag after refresh
        
        trace_out()
        return not is_error()

    def _save_full_size(self, img, date_path: Path, filename_base: str, base_path: Path) -> Optional[Dict[str, Any]]:
        trace_in()
        try:
            from hh.image.image_utils import write_jpg
            # Generate file path for full-size image
            filepath = date_path / f"{filename_base}.jpg"
            # Write original image as JPEG
            if write_jpg(img, filepath, 80):  # Default quality
                result = {
                    'width': img.width,
                    'height': img.height,
                    'src': str(filepath.relative_to(base_path)),
                    'filesize': filepath.stat().st_size
                }
                log(f"Full-size image saved: {img.width}x{img.height}, {result['filesize']} bytes, {result['src']}")
                trace_out()
                return result
            log(f"Full-size image save FAILED: {img.width}x{img.height} - JPEG write failed")
            trace_out()
            return None
        except Exception as e:
            warn(f"Failed to save full-size image: {str(e)}")
            log(f"Full-size image save FAILED: {img.width}x{img.height} - {str(e)}")
            trace_out()
            return None

    def _soft_delete_files(self) -> bool:
        trace_in()
        try:
            # Load instances if not already loaded (this populates self.instances)
            self.get_instances()
            # Get project context for base path
            from hh.deploy.deploy_utils import detect_project_context
            from pathlib import Path
            project_name, _ = detect_project_context()
            base_path = Path(f"/srv/images/{project_name}")
            deleted_path = base_path / "deleted"
            # Ensure deleted directory exists (will be created when file operations execute)
            deleted_path.mkdir(parents=True, exist_ok=True)
            # Process each instance file
            for instance in (self.instances or []):
                src_path = instance.get('src', '')
                if not src_path:
                    continue
                # Full path to the current file
                current_file = base_path / src_path
                if not current_file.exists():
                    log(f"File not found, skipping: {current_file}")
                    continue
                # Check if any other images still use this file
                if self._is_file_shared(src_path):
                    log(f"File is shared by other images, keeping: {src_path}")
                    continue
                # Schedule move file to deleted folder (buffered, will execute after DB commit)
                deleted_file = deleted_path / current_file.name
                self.gateway.files.schedule_move(str(current_file), str(deleted_file))
                log(f"Scheduled file move to deleted folder: {src_path} -> deleted/{current_file.name}")
            trace_out()
            return True
        except Exception as e:
            warn(f"Failed to schedule soft delete files: {str(e)}")
            report_error("file_operation", f"Failed to schedule soft delete: {str(e)}")
            trace_out()
            return False

    def add_image_instance(self, width: int, height: int, src: str, filesize: int) -> bool:
        trace_in()
        log(f"Adding image instance for image {self.id}: {width}x{height}")
        if not is_error():
            new_id = self.gateway.conn.create("""
                INSERT INTO image_instances (image_id, width, height, src, filesize)
                VALUES (%s, %s, %s, %s, %s)
            """, (self.id, width, height, src, filesize))
            if new_id is not None:
                # Add to instances list
                self.instances.append({
                    'width': width,
                    'height': height,
                    'src': src,
                    'filesize': filesize
                })
                log(f"Successfully added image instance for image {self.id}")
            else:
                warn(f"Failed to add image instance for image {self.id}")
                report_error("action", f"Failed to add image instance for image {self.id}")
        trace_out()
        return not is_error()

    def check_incoming_links(self) -> List[Dict[str, Any]]:
        trace_in()
        log(f"Checking incoming links for image {self.id}")
        links = []
        if not is_error():
            query = """
                SELECT image_links.id as page_id, pages.name as page_name
                FROM image_links 
                JOIN pages ON image_links.id = pages.id 
                WHERE image_links.resolution_id = %s
            """
            results = self.gateway.conn.read(query, [self.id])
            for row in results:
                links.append({
                    'page_id': row['page_id'],
                    'page_name': row['page_name']
                })
            log(f"Found {len(links)} incoming links for image {self.id}")
        trace_out()
        return links

    def copy_instances(self, target_image) -> bool:
        trace_in()
        log(f"Copying instances from image {target_image.id} to image {self.id}")
        if not is_error():
            # Get instances from target image
            target_instances = target_image.get_instances()
            if not target_instances:
                warn(f"No instances found in target image {target_image.id}")
                report_error("action", f"No instances found in target image {target_image.id}")
                trace_out()
                return False
            # Copy each instance
            copied_count = 0
            for instance in target_instances:
                if not self.add_image_instance(instance['width'], instance['height'], instance['src'], instance['filesize']):
                    warn(f"Failed to copy instance: {instance['width']}x{instance['height']}")
                    report_error("action", f"Failed to copy instance: {instance['width']}x{instance['height']}")
                    trace_out()
                    return False
                copied_count += 1
            log(f"Successfully copied {copied_count} instances from image {target_image.id} to image {self.id}")
        trace_out()
        return not is_error()

    def delete_from_database(self) -> bool:
        trace_in()
        log(f"Deleting image {self.id} from database")
        if not is_error():
            # Check if image is still used by any pages
            usage_count = self.get_usage_count()
            if usage_count > 0:
                warn(f"Cannot delete image {self.id}: still used by {usage_count} pages")
                report_error("action", f"Cannot delete image {self.id}: still used by {usage_count} pages")
                trace_out()
                return False
            # Soft delete: move files to deleted folder before removing from database
            self._soft_delete_files()
            # Delete image instances first
            self.gateway.conn.delete("DELETE FROM image_instances WHERE image_id = %s", [self.id])
            self.gateway.conn.delete("DELETE FROM images WHERE id = %s", [self.id])
            log(f"Successfully deleted image {self.id}")
        trace_out()
        return not is_error()

    def flag_image_modification(self, comments: str) -> bool:
        trace_in()
        note = comments or ""
        now = dt.datetime.now()
        if not is_error():
            user_results = self.gateway.conn.read("SELECT USER() as db_user")
            db_user = user_results[0]['db_user'] if user_results else 'unknown'
        if not is_error():
            affected = self.gateway.conn.update(
                """
                UPDATE images
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

    def get_best_instance(self, target_width: Optional[int] = None, target_height: Optional[int] = None) -> Optional[Dict[str, Any]]:
        trace_in()
        log(f"Finding best instance for image {self.id} (width={target_width}, height={target_height})")
        if not self.instances:
            log("No instances available")
            trace_out()
            return None
        if target_width is None and target_height is None:
            target_width = 300
        best = None
        if target_width:
            for instance in self.instances:
                if instance['width'] >= target_width:
                    if best is None or instance['width'] < best['width']:
                        best = instance
        elif target_height:
            for instance in self.instances:
                if instance['height'] >= target_height:
                    if best is None or instance['height'] < best['height']:
                        best = instance
        if best:
            log(f"Found best instance: {best['width']}x{best['height']}")
        else:
            log("No suitable instance found")
        trace_out()
        return best

    def get_image_data(self) -> Dict[str, Any]:
        trace_in()
        debug(f"Getting image data for image {self.id}")
        # Get instances data to compute derived fields
        instances = self.get_instances()
        
        # Compute derived fields from instances
        max_width = 0
        max_height = 0
        max_filesize = 0
        aspect_ratio = "N/A"
        file_path = "N/A"
        
        if instances:
            max_width = max(inst.get('width', 0) for inst in instances)
            max_height = max(inst.get('height', 0) for inst in instances)
            max_filesize = max(inst.get('filesize', 0) for inst in instances)
            if max_height > 0:
                aspect_ratio = f"{max_width/max_height:.3f}"
            # Get folder path from first instance
            if instances[0].get('src'):
                src_path = instances[0]['src']
                last_slash = src_path.rfind('/')
                if last_slash != -1:
                    file_path = src_path[:last_slash + 1]
                else:
                    file_path = src_path
        
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
            "max_width": max_width,
            "max_height": max_height,
            "max_filesize": max_filesize,
            "aspect_ratio": aspect_ratio,
            "file_path": file_path,
            "num_instances": len(instances)
        }
        trace_out()
        return data

    def get_instances(self) -> List[Dict[str, Any]]:
        trace_in()
        # Check if field is already populated
        if hasattr(self, 'instances') and self.instances:
            debug(f"Image {self.id}: returning cached instances")
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
                # Extract filename from src path
                from pathlib import Path
                src_path = instance.get('src', '')
                filename = Path(src_path).name if src_path else f"image_{self.id}_unknown"
                instance_data = {
                    'width': instance.get('width', 0),
                    'height': instance.get('height', 0),
                    'filesize': instance.get('filesize', 0),
                    'filename': filename,
                    'src': instance.get('src', '')
                }
                instances_data.append(instance_data)
            log(f"Prepared {len(instances_data)} instances for image {self.id}")
        trace_out()
        return instances_data

    def get_usage_count(self) -> int:
        trace_in()
        count = 0
        if not is_error():
            query = "SELECT COUNT(*) as count FROM image_groups WHERE image_id = %s"
            results = self.gateway.conn.read(query, [self.id])
            if results:
                count = results[0]['count']
        log(f"Image {self.id} is used by {count} pages")
        trace_out()
        return count

    def get_used_by_pages(self) -> List[int]:
        trace_in()
        page_ids = []
        if not is_error():
            query = "SELECT page_id FROM image_groups WHERE image_id = %s ORDER BY page_id"
            results = self.gateway.conn.read(query, [self.id])
            page_ids = [row['page_id'] for row in results]
        log(f"Image {self.id} is used by pages: {page_ids}")
        trace_out()
        return page_ids

    def load_instances(self) -> List[Dict[str, Any]]:
        trace_in()
        debug(f"Loading instances for image {self.id}")
        instances = []
        if not is_error():
            try:
                query = "SELECT * FROM image_instances WHERE image_id = %s ORDER BY width DESC"
                results = self.gateway.conn.read(query, [self.id])
                for row in results:
                    instances.append({
                        'width': row['width'],
                        'height': row['height'],
                        'src': row['src'],
                        'filesize': row['filesize']
                    })
                log(f"Loaded {len(instances)} instances for image {self.id}")
            except Exception as e:
                warn(f"Failed to load instances for image {self.id}: {str(e)}")
                report_error("backend", f"Failed to load instances: {str(e)}")
        trace_out()
        return instances

    def modify_caption(self, caption: str) -> bool:
        trace_in()
        log(f"Modifying caption for image {self.id}: '{self.caption}' -> '{caption}'")
        if caption == self.caption:
            log("Caption unchanged, no update needed")
            trace_out()
            return True
        if not is_error():
            log(f"Validating new caption '{caption}' for image {self.id}")
            if not self.validate_caption(caption):
                warn("Caption validation failed")
                report_error("action", "Caption validation failed")
            else:
                log(f"Caption validation passed for '{caption}'")
        if not is_error():
            log(f"Updating image {self.id} caption in database: '{self.caption}' -> '{caption}'")
            affected = self.gateway.conn.update("UPDATE images SET caption = %s WHERE id = %s", (caption, self.id))
            if affected == 0:
                warn(f"Failed to update image {self.id} caption - no rows affected")
                report_error("action", f"Failed to update image {self.id} caption")
            else:
                log(f"Successfully updated image {self.id} caption in database")
        if not is_error():
            self.caption = caption
            log(f"Successfully updated image {self.id} caption to '{caption}'")
            self.flag_image_modification("caption updated")
        trace_out()
        return not is_error()

    def modify_visibility(self, visibility: int) -> bool:
        trace_in()
        log(f"Modifying visibility for image {self.id}: {self.visibility} -> {visibility}")
        if not is_error():
            affected = self.gateway.conn.update("UPDATE images SET visibility = %s WHERE id = %s", (visibility, self.id))
            if affected == 0:
                warn(f"Failed to update image {self.id} visibility - no rows affected")
                report_error("action", f"Failed to update image {self.id} visibility")
            else:
                self.visibility = visibility
                log(f"Successfully updated visibility for image {self.id}")
                self.flag_image_modification("visibility updated")
        trace_out()
        return not is_error()

    def process_upload(self, uploaded_file_path: str, filename: str) -> bool:
        trace_in()
        log(f"Processing upload for image {self.id}: {uploaded_file_path}")
        if not is_error():
            instances_data = self._process_image(uploaded_file_path, filename)
            if not instances_data:
                warn("No image instances created")
                report_error("action", "Image processing failed")
                trace_out()
                return False
            # Save instances to database
            for instance_data in instances_data:
                if not self.add_image_instance(instance_data['width'], instance_data['height'], instance_data['src'], instance_data['filesize']):
                    trace_out()
                    return False
            log(f"Successfully processed {len(instances_data)} image instances")
        trace_out()
        return not is_error()

    def show_image(self) -> Dict[str, Any]:
        trace_in()
        cache_ready = getattr(self, 'cache_hydrated', False) and getattr(self, 'cached_usage', None) is not None
        if cache_ready:
            debug(f"Image {self.id}: cache available, methods will check cache independently")
        else:
            debug(f"Image {self.id}: cache miss or stale entry; rebuilding show_image payload")
        
        image_data = self.get_image_data()
        usage_data = self._get_usage_data()
        self.get_instances()  # Ensure instances are loaded before get_instances_data()
        instances_data = self.get_instances_data()
        
        extra_actions: List[Dict[str, Any]] = []
        if not is_error():
            extra_actions = self._check_extra_actions()
            if extra_actions:
                log(f"Found {len(extra_actions)} extra actions for image {self.id}")

        response_data: Dict[str, Any] = {
            "image": image_data,
            "usage": usage_data,
            "instances": instances_data
        }
        if extra_actions:
            response_data["extra_actions"] = extra_actions
        
        # Cache refresh will be handled by wrapper method system if flag is set
        log(f"Generated complete display data for image {self.id}: {self.caption}")
        trace_out()
        return response_data

    def update_view_count(self, increment: int = 1) -> bool:
        trace_in()
        log(f"Updating view count for image {self.id}: +{increment}")
        
        if not is_error():
            affected = self.gateway.conn.update("UPDATE images SET viewCount = viewCount + %s WHERE id = %s", 
                              (increment, self.id))
            if affected == 0:
                warn(f"Failed to update image {self.id} view count - no rows affected")
                report_error("action", f"Failed to update image {self.id} view count")
            else:
                self.view_count = (self.view_count or 0) + increment
                log(f"Successfully updated view count for image {self.id}")
        
        trace_out()
        return not is_error()

    def validate_caption(self, caption: str) -> bool:
        trace_in()
        log(f"Validating caption: '{caption}' for image {self.id}")
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
