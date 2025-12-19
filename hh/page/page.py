"""
TABLE OF CONTENTS (Alphabetical Order)
======================================

__init__()                    Line 226
_add_badge_headers()          Line 534
_add_file_to_group()          Line 559
_add_image_to_group()         Line 512
_add_lower_content()           Line 553
_add_page_class_information()  Line 504
_add_upper_content()           Line 556
_check_children_recursive()    Line 269
_copy_children_recursive()     Line 290
_copy_page_class_information() Line 308
_create_file_record()          Line 583
_create_image_record()         Line 626
_delete_all_image_groups()     Line 642
_delete_page_class_information() Line 678
_dump_json()                  Line 681
_enqueue_maintenance_job()     Line 883
_ensure_cache_entry()         Line 703
_flag_cache_refresh()         Line 742
_flag_related_file()          Line 411
_flag_related_image()          Line 402
_get_child_page_data()         Line 331
_get_child_page_ids()          Line 311
_get_child_row_field_type()    Line 343
_get_children_by_class()       Line 349
_get_children_query()          Line 324
_get_display_name()            Line 386
_get_file_usage_count()        Line 420
_get_metadata_dict()           Line 479
_json_default()               Line 689
_parse_metadata_value()        Line 463
_refresh_cached_page()         Line 746
_remove_file_from_group()      Line 429
_remove_image_from_group()     Line 444
_serialize_metadata()          Line 877
_write_metadata_dict()         Line 488
add_file()                    Line 1145
add_image()                   Line 1480
add_page()                    Line 1187
allow_class_inside()          Line 902
allow_duplicate_names()       Line 907
allow_inside_of()             Line 912
allow_null_names()            Line 1038
auto_link_name()              Line 1043
can_move_to_page()            Line 1047
copy_media_items()            Line 1410
copy_page()                   Line 1327
delete_all_file_groups()      Line 1593
delete_from_database()        Line 1618
delete_page()                 Line 1635
flag_page_modification()      Line 1682
get_allowed_child_classes()   Line 1712
get_child_count()             Line 1821
get_children_data()           Line 1834
getChildrenOf()               Line 1752
get_files_data()              Line 1975
get_images_data()             Line 2033
get_page()                    Line 1911
get_page_data()               Line 1890
get_path()                    Line 1856
get_prepared_text()           Line 1954
modify_display_style()        Line 2491
modify_name()                 Line 2507
modify_text()                 Line 2577
modify_visibility()           Line 2620
move_media_items()            Line 2266
move_page()                   Line 2233
regex_text()                  Line 2636
remove_media_item()           Line 2393
reorder_files()               Line 2202
reorder_images()              Line 2170
set_media_rank()              Line 2683
set_metadata_value()          Line 2674
show_page()                   Line 2840
validate_name()               Line 2913

"""

from typing import Dict, Any, List, Optional
import json
import datetime as dt
import re
from pathlib import Path
from decimal import Decimal
from hh.gateway.gateway import get_gateway
from hh.gateway.connection.utils import deserialize_json_blob, normalize_datetime
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page
from hh.page.page_class_registry import register_page_class, get_page_class, get_all_page_classes
from hh.tp.tp import TextProcessor
from hh.image.image_registry import get_image
from hh.image.image import Image
from hh.file.file_registry import get_file
from hh.file.file_utils import store_uploaded_file
from hh.gateway.registry.mcp_whitelist import MCPWhitelist

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


@register_page_class('page')
class Page:

    id: int
    gateway: Any
    parent: Optional[int]
    class_name: Optional[str]
    name: Optional[str]
    link: Optional[str]
    text: Optional[str]
    visibility: Optional[int]
    last_modified: Optional[dt.datetime]
    username: Optional[str]
    comments: Optional[str]
    metadata: Optional[Dict[str, Any]]
    displayStyle: Optional[int]
    viewCount: Optional[int]
    display_name: Optional[str]
    prepared_text: Optional[Any]
    children_by_class: Dict[str, Any]
    images: List[Any]
    files: List[Any]
    audio: List[Any]
    video: List[Any]
    cache_built_at: Optional[Any]
    cache_hydrated: bool
    _cache_needs_refresh: bool

    # Media types supported for copy/move/remove/set_rank operations
    MEDIA_TYPES = ["image", "audio", "video", "file"]

    @staticmethod
    def _get_media_table_name(media_type: str) -> str:
        """Get table name for media type (e.g., 'image' -> 'image_groups')."""
        return f"{media_type}_groups"

    @staticmethod
    def _get_media_id_field(media_type: str) -> str:
        """Get ID field name for media type (e.g., 'image' -> 'image_id')."""
        return f"{media_type}_id"

    @staticmethod
    def _get_media_rank_field(media_type: str) -> str:
        """Get rank field name for media type (e.g., 'image' -> 'image_rank')."""
        return f"{media_type}_rank"

    def _get_media_data_method(self, media_type: str):
        """Get the data retrieval method for media type."""
        method_map = {
            "image": self.get_images_data,
            "audio": self.get_audio_data if hasattr(self, 'get_audio_data') else None,
            "video": self.get_video_data if hasattr(self, 'get_video_data') else None,
            "file": self.get_files_data,
        }
        return method_map.get(media_type)

    def _get_add_to_group_method(self, media_type: str):
        """Get the add-to-group method for media type."""
        method_map = {
            "image": self._add_image_to_group,
            "audio": self._add_audio_to_group if hasattr(self, '_add_audio_to_group') else None,
            "video": self._add_video_to_group if hasattr(self, '_add_video_to_group') else None,
            "file": self._add_file_to_group,
        }
        return method_map.get(media_type)

    def _get_reorder_method(self, media_type: str):
        """Get the reorder method for media type."""
        method_map = {
            "image": self.reorder_images,
            "audio": self.reorder_audio if hasattr(self, 'reorder_audio') else None,
            "video": self.reorder_video if hasattr(self, 'reorder_video') else None,
            "file": self.reorder_files,
        }
        return method_map.get(media_type)

    def _get_flag_related_method(self, media_type: str):
        """Get the flag-related method for media type (if exists)."""
        method_map = {
            "image": self._flag_related_image,
            "file": self._flag_related_file,
        }
        return method_map.get(media_type)

    def _get_usage_count_method(self, media_type: str):
        """Get the usage count method for media type (if exists)."""
        if media_type == "file":
            return self._get_file_usage_count
        elif media_type == "image":
            # Images have get_usage_count on the Image object itself
            return None
        return None

    @staticmethod
    def _validate_media_type(media_type: str) -> str:
        """Validate media type and return normalized version (defaults to 'file')."""
        if not media_type:
            return "file"
        media_type = media_type.lower()
        if media_type not in Page.MEDIA_TYPES:
            warn(f"Invalid media type: {media_type}. Must be one of {Page.MEDIA_TYPES}")
            report_error("action", f"Invalid media type: {media_type}")
            return "file"  # Default fallback
        return media_type

    def __init__(self, id: int):
        trace_in()
        self.gateway = get_gateway()
        debug(f"Initializing Page with id={id}")
        
        if not self.gateway or not self.gateway.conn:
            warn("Gateway or connection not available")
            report_error("connection", "Gateway or connection not available")
            trace_out()
            return
        
        # Initialize all fields
        self.id = id
        self.name = None
        self.link = None
        self.parent = None
        self.class_name = None
        self.visibility = None
        self.text = None
        self.last_modified = None
        self.username = None
        self.comments = None
        self.metadata = {}
        # Five derived fields that get hydrated from cache or computed lazily
        self.display_name = None
        self.prepared_text = None
        self.children_by_class = {}
        self.images = []
        self.files = []
        self.audio = []
        self.video = []
        self.cache_built_at = None
        self.cache_hydrated = False
        self._cache_needs_refresh = False
        
        # Load page data from main database
        query = "SELECT * FROM pages WHERE id = %s"
        try:
            results = self.gateway.conn.read(query, [id])
            if not results:
                warn(f"Page with id {id} not found")
                report_error("action", f"Page with id {id} not found")
                trace_out()
                return
            
            page_data = results[0]
            self.name = page_data.get('name')
            self.link = page_data.get('link')
            self.parent = page_data.get('parent')
            self.class_name = page_data.get('class')
            self.visibility = page_data.get('visibility')
            self.displayStyle = page_data.get('displayStyle')
            self.text = page_data.get('text')
            self.last_modified = page_data.get('last_modified')
            self.cache_built_at = page_data.get('cache_built_at')
            self.username = page_data.get('username')
            self.comments = page_data.get('comments')
            metadata_raw = page_data.get('metadata')
            if metadata_raw in (None, '', b''):
                self.metadata = {}
            else:
                try:
                    if isinstance(metadata_raw, (bytes, bytearray)):
                        metadata_raw = metadata_raw.decode('utf-8')
                    self.metadata = json.loads(metadata_raw) if isinstance(metadata_raw, str) else metadata_raw
                    if not isinstance(self.metadata, dict):
                        self.metadata = {}
                except (ValueError, TypeError):
                    self.metadata = {}
            
            # Automatically extract all metadata fields as attributes
            # This allows subclasses to access metadata fields directly (e.g., self.path, self.language)
            # without needing to manually extract them
            # Only sets attributes that don't already exist, automatically protecting existing fields
            if isinstance(self.metadata, dict):
                for key, value in self.metadata.items():
                    # Only set if attribute doesn't already exist (protects existing Page fields)
                    if not hasattr(self, key):
                        setattr(self, key, value)
                        debug(f"Extracted metadata field: {key} = {value}")
                    else:
                        debug(f"Skipped metadata field '{key}' - attribute already exists")
            
            text_length = len(self.text) if self.text else 0
            log(f"Loaded page {id}: {self.name}")
            
            # Try to hydrate from cache database if available and fresh
            if not is_error():
                # Check if cache exists and is fresh
                cache_built_at_dt = normalize_datetime(self.cache_built_at)
                last_modified_dt = normalize_datetime(self.last_modified)
                
                if last_modified_dt and cache_built_at_dt and cache_built_at_dt < last_modified_dt:
                    debug(f"Cache for page {self.id} is stale (cache_built_at={cache_built_at_dt}, last_modified={last_modified_dt})")
                elif cache_built_at_dt is None:
                    debug(f"Cache for page {self.id} does not exist (cache_built_at is NULL)")
                else:
                    # Get cache row from cache database
                    cache_query = """
                        SELECT id, display_name, prepared_text, children_summary, image_summary, file_summary, links_out, cache_built_at
                        FROM pages
                        WHERE id = %s
                    """
                    try:
                        cache_results = self.gateway.conn.read_cache(cache_query, [self.id])
                        if cache_results:
                            cache_row = cache_results[0]
                            # Load expensive pre-computed data from cache database directly into the 5 derived fields
                            self.display_name = cache_row.get('display_name')
                            self.prepared_text = deserialize_json_blob(cache_row.get('prepared_text'), None)
                            self.children_by_class = deserialize_json_blob(cache_row.get('children_summary'), {})
                            self.images = deserialize_json_blob(cache_row.get('image_summary'), [])
                            self.files = deserialize_json_blob(cache_row.get('file_summary'), [])
                            self.cache_hydrated = True
                            debug(f"Hydrated page {self.id} from cache (built_at={self.cache_built_at})")
                    except Exception as e:
                        warn(f"Failed to hydrate page {self.id} from cache: {e}")
                        # Don't report error - cache hydration failure is not critical
        except Exception as e:
            warn(f"Failed to load page {id}: {e}")
            report_error("connection", f"Failed to load page {id}: {e}")
        
        trace_out()

    def _check_children_recursive(self) -> List[int]:
        trace_in()
        child_array = []
        if not is_error():
            # Start with this page's direct children
            direct_children = self._get_child_page_ids()
            child_array.extend(direct_children)
            # Recursively get children of children
            for child_id in direct_children:
                if not is_error():
                    child_page = get_page(page_id=child_id)
                    if child_page:
                        grand_children = child_page._check_children_recursive()
                        child_array.extend(grand_children)
                    else:
                        warn(f"Failed to load child page {child_id} for recursive check")
                        report_error("action", f"Failed to load child page {child_id}")
        log(f"Found {len(child_array)} total child pages (including nested) for page {self.id}")
        trace_out()
        return child_array

    def _copy_children_recursive(self, parent_id: int, max_depth: Optional[int] = None, current_depth: int = 0, copy_images: bool = False, copy_files: bool = False) -> None:
        trace_in()
        if max_depth is not None and current_depth >= max_depth:
            log(f"Reached max depth {max_depth}, stopping recursion")
            trace_out()
            return
        if not is_error():
            child_ids = self._get_child_page_ids()
            for child_id in child_ids:
                if not is_error():
                    child_page = get_page(page_id=child_id)
                    if child_page:
                        # Copy child to new parent, passing through copy_images and copy_files flags
                        copied_child_id = child_page.copy_page(parent_id, recursive=True, max_depth=max_depth, copy_images=copy_images, copy_files=copy_files)
                        if copied_child_id > 0:
                            log(f"Copied child page {child_id} to {copied_child_id}")
        trace_out()

    def _copy_page_class_information(self, new_page_id: int):
        pass

    def _get_child_page_ids(self) -> List[int]:
        trace_in()
        child_ids = []
        if not is_error():
            query, params = self._get_children_query(self.id)
            results = self.gateway.conn.read(query, params)
            if results:
                child_ids = [row['id'] for row in results]
        log(f"Child page IDs for page {self.id}: {len(child_ids)} found -> {child_ids}")
        trace_out()
        return child_ids

    @staticmethod
    def _get_children_query(parent_id: int) -> tuple[str, list]:
        # Default: only return children of class 'page', sorted by name
        return (
            "SELECT id FROM pages WHERE parent = %s AND class = 'page' ORDER BY name",
            [parent_id]
        )

    def _get_child_page_data(self) -> Dict[str, Any]:
        """Return simplified data for child pages in tables: id, name, parent, class."""
        trace_in()
        data = {
            "id": self.id,
            "name": self.name,
            "parent": self.parent,
            "class": self.class_name
        }
        trace_out()
        return data

    def _get_child_row_field_type(self) -> str:
        """Return the field type for this page when displayed as a child row.
        Override in subclasses to customize the label/icon shown in child tables.
        """
        return 'page'

    def _get_children_by_class(self) -> Dict[str, Dict[str, Any]]:
        # Check if field is already populated
        if hasattr(self, 'children_by_class') and self.children_by_class:
            debug(f"Page {self.id}: returning cached children_by_class")
            return self.children_by_class
        # Field is empty, need to hydrate from database
        trace_in()
        children_by_class = {}
        # Get distinct classes of children (equivalent to legacy line 242)
        query = f"SELECT DISTINCT class FROM pages WHERE parent = {self.id}"
        results = self.gateway.conn.read(query, [])
        if results:
            for row in results:
                child_class = row['class']
                log(f"Found child class: {child_class}")
                # For each class, get its children using that class's static getChildrenOf method
                # This is where derived classes' getChildrenOf() gets called
                PageClass = get_page_class(child_class)
                if PageClass is None:
                    warn(f"Page class '{child_class}' not found")
                    report_error("action", f"Page class '{child_class}' not found")
                    continue
                children_data = PageClass.getChildrenOf(self.id)
                if children_data:
                    children_by_class[child_class] = {
                        'class': child_class,
                        'children': children_data
                    }
        log(f"Grouped children into {len(children_by_class)} classes: {list(children_by_class.keys())}")
        self.children_by_class = children_by_class
        # Only flag cache refresh if we actually found children (data changed)
        # If we just confirmed there are no children (empty dict), no need to refresh
        if children_by_class:
            self._flag_cache_refresh()
        trace_out()
        return children_by_class

    def _get_display_name(self) -> str:
        """
        Get the display name for this page, with fallback logic.
        Override this method in subclasses to provide custom display names.
        Checks cached display_name first, then computes if needed.
        """
        # Check if field is already populated
        if hasattr(self, 'display_name') and self.display_name:
            return self.display_name
        # Field is empty, compute it
        display_name = self.name or f"Page {self.id}"
        self.display_name = display_name
        # Flag that cache needs refresh since we just computed
        self._flag_cache_refresh()
        return display_name

    def _flag_related_image(self, image_id: int, comment: str) -> None:
        if is_error() or not image_id:
            return
        image = get_image(image_id)
        if not image:
            warn(f"Failed to load image {image_id} for modification flag")
            return
        image.flag_image_modification(comment)

    def _flag_related_file(self, file_id: int, comment: str) -> None:
        if is_error():
            return
        file_obj = get_file(file_id=file_id)
        if not file_obj:
            warn(f"Failed to load file {file_id} for modification flag")
            return
        file_obj.flag_file_modification(comment)

    def _get_file_usage_count(self, file_id: int) -> int:
        if is_error():
            return 0
        results = self.gateway.conn.read(
            "SELECT COUNT(*) AS cnt FROM file_groups WHERE file_id = %s",
            (file_id,),
        )
        return results[0]["cnt"] if results else 0

    def _remove_file_from_group(self, file_id: int) -> bool:
        trace_in()
        if not is_error():
            affected = self.gateway.conn.delete(
                "DELETE FROM file_groups WHERE page_id = %s AND file_id = %s",
                (self.id, file_id),
            )
            if affected == 0:
                warn(f"Failed to remove file {file_id} from page {self.id}")
                report_error("action", f"Failed to remove file {file_id} from page {self.id}")
            else:
                self.get_files_data(rebuild=True)
        trace_out()
        return not is_error()

    def _remove_image_from_group(self, image_id: int) -> bool:
        trace_in()
        log(f"Removing image {image_id} from page {self.id} image group")
        if not is_error():
            affected = self.gateway.conn.delete("DELETE FROM image_groups WHERE page_id = %s AND image_id = %s", (self.id, image_id))
            if affected == 0:
                warn(f"Failed to remove image {image_id} from page {self.id}")
                report_error("action", f"Failed to remove image {image_id} from page {self.id}")
            # Reorder remaining images
            if not is_error() and not self.reorder_images():
                warn(f"Failed to reorder images after removing image {image_id}")
                report_error("action", f"Failed to reorder images after removal")
            if not is_error():
                log(f"Successfully removed image {image_id} from page {self.id}")
                self._flag_related_image(image_id, f"removed from page {self.id}")
        trace_out()
        return not is_error()

    @staticmethod
    def _parse_metadata_value(metadata: Any) -> Dict[str, Any]:
        if metadata in (None, '', b''):
            return {}
        try:
            if isinstance(metadata, (bytes, bytearray)):
                metadata = metadata.decode('utf-8')
            if isinstance(metadata, str):
                parsed = json.loads(metadata)
            else:
                parsed = metadata
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, TypeError):
            pass
        return {}

    def _get_metadata_dict(self) -> Dict[str, Any]:
        """Return the in-memory metadata dict, normalizing raw storage as needed."""
        metadata = getattr(self, 'metadata', None)
        if isinstance(metadata, dict):
            return metadata
        parsed = self._parse_metadata_value(metadata)
        self.metadata = parsed
        return self.metadata

    def _write_metadata_dict(self, metadata: Dict[str, Any]) -> bool:
        """Persist the provided metadata dict to the database."""
        trace_in()
        metadata = metadata or {}
        metadata_json = json.dumps(metadata, ensure_ascii=False, separators=(',', ':'))
        success = True
        if not is_error():
            affected = self.gateway.conn.update("UPDATE pages SET metadata = %s WHERE id = %s", (metadata_json, self.id))
            if affected == 0:
                log(f"Metadata for page {self.id} already up to date; no rows affected")
        if success:
            self.metadata = metadata
        trace_out()
        return success and not is_error()

    @classmethod
    def _add_page_class_information(cls, new_page_id: int):
        """
        Hook called after page creation to add class-specific data.
        This is a classmethod (like PHP's static method) so it can be called on the class
        without needing an instance. Subclasses should override this.
        """
        pass

    def _add_image_to_group(self, image_id: int, rank: Optional[int] = None) -> bool:
        trace_in()
        log(f"Adding image {image_id} to page {self.id} image group")
        if not is_error():
            # Get next rank if not provided
            if rank is None:
                results = self.gateway.conn.read("SELECT COALESCE(MAX(image_rank), 0) + 1 as next_rank FROM image_groups WHERE page_id = %s", [self.id])
                rank = results[0]['next_rank'] if results else 1
            # Insert into image_groups
            new_id = self.gateway.conn.create("""
                INSERT INTO image_groups (page_id, image_id, image_rank)
                VALUES (%s, %s, %s)
            """, (self.id, image_id, rank))
            if new_id is not None:
                log(f"Successfully added image {image_id} to page {self.id} with rank {rank}")
                self._flag_related_image(image_id, f"added to page {self.id}")
            else:
                warn(f"Failed to add image {image_id} to page {self.id}")
                report_error("action", f"Failed to add image {image_id} to page {self.id}")
        trace_out()
        return not is_error()

    def _add_audio_to_group(self, audio_id: int, rank: Optional[int] = None) -> bool:
        trace_in()
        log(f"Adding audio {audio_id} to page {self.id} audio group")
        if not is_error():
            # Get next rank if not provided
            if rank is None:
                results = self.gateway.conn.read("SELECT COALESCE(MAX(audio_rank), 0) + 1 as next_rank FROM audio_groups WHERE page_id = %s", [self.id])
                rank = results[0]['next_rank'] if results else 1
            # Insert into audio_groups
            new_id = self.gateway.conn.create("""
                INSERT INTO audio_groups (page_id, audio_id, audio_rank)
                VALUES (%s, %s, %s)
            """, (self.id, audio_id, rank))
            if new_id is not None:
                log(f"Successfully added audio {audio_id} to page {self.id} with rank {rank}")
            else:
                warn(f"Failed to add audio {audio_id} to page {self.id}")
                report_error("action", f"Failed to add audio {audio_id} to page {self.id}")
        trace_out()
        return not is_error()

    def _add_video_to_group(self, video_id: int, rank: Optional[int] = None) -> bool:
        trace_in()
        log(f"Adding video {video_id} to page {self.id} video group")
        if not is_error():
            # Get next rank if not provided
            if rank is None:
                results = self.gateway.conn.read("SELECT COALESCE(MAX(video_rank), 0) + 1 as next_rank FROM video_groups WHERE page_id = %s", [self.id])
                rank = results[0]['next_rank'] if results else 1
            # Insert into video_groups
            new_id = self.gateway.conn.create("""
                INSERT INTO video_groups (page_id, video_id, video_rank)
                VALUES (%s, %s, %s)
            """, (self.id, video_id, rank))
            if new_id is not None:
                log(f"Successfully added video {video_id} to page {self.id} with rank {rank}")
            else:
                warn(f"Failed to add video {video_id} to page {self.id}")
                report_error("action", f"Failed to add video {video_id} to page {self.id}")
        trace_out()
        return not is_error()

    def _add_badge_headers(self) -> Dict[str, Any]:
        badge_headers = {}
        page_data = self.get_page_data()
        # Calculate children count from children_by_class
        children_by_class = self._get_children_by_class()
        children_count = sum(len(group['children']) for group in children_by_class.values())
        # Add page summary as first badge
        badge_headers['page_summary'] = {
            'page_id': page_data.get('id'),
            'name': page_data.get('name'),
            'link': page_data.get('link'),
            'parent': page_data.get('parent'),
            'class': page_data.get('class'),
            'modified': page_data.get('last_modified'),
            'username': page_data.get('username'),
            'children': children_count
        }
        return badge_headers

    def _add_lower_content(self) -> List[str]:
        return []

    def _add_upper_content(self) -> List[str]:
        return []

    def _add_file_to_group(self, file_id: int, rank: Optional[int] = None) -> bool:
        trace_in()
        if not is_error():
            if rank is None:
                results = self.gateway.conn.read(
                    "SELECT COALESCE(MAX(file_rank), 0) + 1 AS next_rank FROM file_groups WHERE page_id = %s",
                    [self.id],
                )
                rank = results[0]["next_rank"] if results else 1
            new_id = self.gateway.conn.create(
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
                self.get_files_data(rebuild=True)
        trace_out()
        return not is_error()

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
            user_results = self.gateway.conn.read("SELECT USER() as db_user")
            db_user = user_results[0]["db_user"] if user_results else "unknown"
            file_id = self.gateway.conn.create(
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

    def _create_image_record(self, caption: Optional[str] = None) -> Optional[int]:
        trace_in()
        # Insert image record (no parent or rank - those are in image_groups)
        image_id = None
        if not is_error():
            user_results = self.gateway.conn.read("SELECT USER() as db_user")
            db_user = user_results[0]['db_user'] if user_results else 'unknown'
        if not is_error():
            image_id = self.gateway.conn.create("""
                INSERT INTO images (caption, username, uploaded, last_modified, comments, visibility, viewCount)
                VALUES (%s, %s, NOW(), NOW(), %s, 1, 0)
            """, (caption, db_user, "image created"))
            log(f"Created image record {image_id}")
        trace_out()
        return image_id

    def _create_audio_record(self, caption: Optional[str] = None) -> Optional[int]:
        trace_in()
        # Insert audio record (no parent or rank - those are in audio_groups)
        audio_id = None
        if not is_error():
            user_results = self.gateway.conn.read("SELECT USER() as db_user")
            db_user = user_results[0]['db_user'] if user_results else 'unknown'
        if not is_error():
            audio_id = self.gateway.conn.create("""
                INSERT INTO audio (caption, username, uploaded, last_modified, comments, visibility, viewCount)
                VALUES (%s, %s, NOW(), NOW(), %s, 1, 0)
            """, (caption, db_user, "audio created"))
            log(f"Created audio record {audio_id}")
        trace_out()
        return audio_id

    def _create_video_record(self, caption: Optional[str] = None) -> Optional[int]:
        trace_in()
        # Insert video record (no parent or rank - those are in video_groups)
        video_id = None
        if not is_error():
            user_results = self.gateway.conn.read("SELECT USER() as db_user")
            db_user = user_results[0]['db_user'] if user_results else 'unknown'
        if not is_error():
            video_id = self.gateway.conn.create("""
                INSERT INTO video (caption, username, uploaded, last_modified, comments, visibility, viewCount)
                VALUES (%s, %s, NOW(), NOW(), %s, 1, 0)
            """, (caption, db_user, "video created"))
            log(f"Created video record {video_id}")
        trace_out()
        return video_id

    def _delete_all_image_groups(self) -> bool:
        trace_in()
        log(f"Deleting all image_groups entries for page {self.id}")
        if not is_error():
            # Get all unique image_ids from this page's image_groups before deleting
            results = self.gateway.conn.read("SELECT DISTINCT image_id FROM image_groups WHERE page_id = %s", [self.id])
            image_ids = [row['image_id'] for row in results] if results else []
            log(f"Found {len(image_ids)} unique images in page {self.id} image_groups")
        
        if not is_error():
            # Delete all image_groups entries for this page
            affected = self.gateway.conn.delete("DELETE FROM image_groups WHERE page_id = %s", [self.id])
            log(f"Deleted {affected} image_groups entries for page {self.id}")
        
        # Check each image to see if it should be deleted (no longer used by any pages)
        if not is_error() and image_ids:
            for image_id in image_ids:
                if not is_error():
                    image = get_image(image_id)
                    if image:
                        usage_count = image.get_usage_count()
                        if usage_count == 0:
                            log(f"Image {image_id} no longer used by any pages, deleting from database")
                            if not image.delete_from_database():
                                warn(f"Failed to delete unused image {image_id}")
                                report_error("action", f"Failed to delete unused image {image_id}")
                        else:
                            log(f"Image {image_id} still used by {usage_count} pages, keeping in database")
                    else:
                        warn(f"Failed to load image {image_id} for usage check")
                        report_error("action", f"Failed to load image {image_id}")
        if not is_error():
            self.flag_page_modification("images updated")
        trace_out()
        return not is_error()

    def _delete_all_audio_groups(self) -> bool:
        trace_in()
        log(f"Deleting all audio_groups entries for page {self.id}")
        if not is_error():
            # Get all unique audio_ids from this page's audio_groups before deleting
            results = self.gateway.conn.read("SELECT DISTINCT audio_id FROM audio_groups WHERE page_id = %s", [self.id])
            audio_ids = [row['audio_id'] for row in results] if results else []
            log(f"Found {len(audio_ids)} unique audio in page {self.id} audio_groups")
        
        if not is_error():
            # Delete all audio_groups entries for this page
            affected = self.gateway.conn.delete("DELETE FROM audio_groups WHERE page_id = %s", [self.id])
            log(f"Deleted {affected} audio_groups entries for page {self.id}")
        
        # Check each audio to see if it should be deleted (no longer used by any pages)
        if not is_error() and audio_ids:
            from hh.audio.audio_registry import get_audio
            for audio_id in audio_ids:
                if not is_error():
                    audio = get_audio(audio_id)
                    if audio:
                        usage_count = audio.get_usage_count()
                        if usage_count == 0:
                            log(f"Audio {audio_id} no longer used by any pages, deleting from database")
                            if not audio.delete_from_database():
                                warn(f"Failed to delete unused audio {audio_id}")
                                report_error("action", f"Failed to delete unused audio {audio_id}")
                        else:
                            log(f"Audio {audio_id} still used by {usage_count} pages, keeping in database")
                    else:
                        warn(f"Failed to load audio {audio_id} for usage check")
                        report_error("action", f"Failed to load audio {audio_id}")
        if not is_error():
            self.flag_page_modification("audio updated")
        trace_out()
        return not is_error()

    def _delete_all_video_groups(self) -> bool:
        trace_in()
        log(f"Deleting all video_groups entries for page {self.id}")
        if not is_error():
            # Get all unique video_ids from this page's video_groups before deleting
            results = self.gateway.conn.read("SELECT DISTINCT video_id FROM video_groups WHERE page_id = %s", [self.id])
            video_ids = [row['video_id'] for row in results] if results else []
            log(f"Found {len(video_ids)} unique video in page {self.id} video_groups")
        
        if not is_error():
            # Delete all video_groups entries for this page
            affected = self.gateway.conn.delete("DELETE FROM video_groups WHERE page_id = %s", [self.id])
            log(f"Deleted {affected} video_groups entries for page {self.id}")
        
        # Check each video to see if it should be deleted (no longer used by any pages)
        if not is_error() and video_ids:
            from hh.video.video_registry import get_video
            for video_id in video_ids:
                if not is_error():
                    video = get_video(video_id)
                    if video:
                        usage_count = video.get_usage_count()
                        if usage_count == 0:
                            log(f"Video {video_id} no longer used by any pages, deleting from database")
                            if not video.delete_from_database():
                                warn(f"Failed to delete unused video {video_id}")
                                report_error("action", f"Failed to delete unused video {video_id}")
                        else:
                            log(f"Video {video_id} still used by {usage_count} pages, keeping in database")
                    else:
                        warn(f"Failed to load video {video_id} for usage check")
                        report_error("action", f"Failed to load video {video_id}")
        if not is_error():
            self.flag_page_modification("video updated")
        trace_out()
        return not is_error()

    def _delete_page_class_information(self):
        pass

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
        # The getters set the attributes themselves, so we just call them
        # This ensures we always have fully hydrated data to cache
        
        if not self.display_name:
            self._get_display_name()
        
        if self.prepared_text is None:
            self.get_prepared_text()
        
        if not self.children_by_class:
            self._get_children_by_class()
        
        if not self.images:
            self.get_images_data()
        
        if not self.files:
            self.get_files_data()
        
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
            # Always bump main database cache_built_at even when UPDATE is a no-op
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
            if affected == 0:
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

    def allow_class_inside(self, target_class: str) -> bool:
        """Instance method: checks if this page instance can contain pages of target_class"""
        return True

    @classmethod
    def allow_duplicate_names(cls) -> bool:
        """Static method: checks if this page class allows duplicate names"""
        return True

    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
        """Static method: checks if this page class can be inside pages of parent_class"""
        return True

    def add_file(
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

        stored = store_uploaded_file(temp_path, original_filename)
        if stored is None:
            warn(f"Failed to store uploaded file: {original_filename}")
            report_error("file_upload", f"Failed to store file {original_filename}")
            trace_out()
            return None
        relative_path, _, size_bytes, mime_type = stored
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
            self.get_files_data(rebuild=True)
            self.flag_page_modification("files updated")
        trace_out()
        return new_file_id

    def add_page(self, page_class: str = 'page', name: Optional[str] = None) -> Optional[int]:
        trace_in()
        # Get current database user
        user_results = self.gateway.conn.read("SELECT USER() as db_user")
        db_user = user_results[0]['db_user'] if user_results else 'unknown'
        
        # Look up the page class to check its configuration
        NewPageClass = get_page_class(page_class)
        if not NewPageClass:
            warn(f"Page class '{page_class}' not found")
            report_error("action", f"Page class '{page_class}' not found")
            trace_out()
            return None
        
        # Check if this parent can contain the new page class
        if not is_error():
            if not self.allow_class_inside(page_class):
                warn(f"Page {self.id} (class={self.class_name}) cannot contain pages with class={page_class}")
                report_error("action", f"Page {self.id} cannot contain pages with class '{page_class}'")
        
        # Check if new page class can be inside this parent (static method on new page's class)
        if not is_error():
            if not NewPageClass.allow_inside_of(self.class_name):
                warn(f"Page class '{page_class}' cannot be inside page class '{self.class_name}'")
                report_error("action", f"Page class '{page_class}' cannot be inside page class '{self.class_name}'")
        
        # Check if null names are allowed for this class
        if not is_error():
            allow_null = NewPageClass.allow_null_names()
            if not allow_null and (not name or len(name.strip()) == 0):
                warn(f"Page class '{page_class}' does not allow null names")
                report_error("action", f"Page class '{page_class}' requires a name")
        
        # Validate name if provided
        if not is_error() and name:
            if not self.validate_name(name, page_class):
                warn("Page name validation failed")
                report_error("action", "Page name validation failed")
        
        # Determine link value based on auto_link_name setting
        new_page_id = None
        if not is_error():
            # Normalize: convert empty string to None for database storage (like _modify_name does)
            name_value = None if (name is None or (isinstance(name, str) and len(name.strip()) == 0)) else name
            auto_link = NewPageClass.auto_link_name()
            # Set link_value: if auto_link is True and name_value is provided, use name_value as link
            # Otherwise, set to None
            link_value = name_value if (auto_link and name_value is not None) else None
            
            try:
                now = dt.datetime.now()
                new_page_id = self.gateway.conn.create("""
                    INSERT INTO pages (parent, name, link, class, last_modified, username, visibility, displayStyle)
                    VALUES (%s, %s, %s, %s, %s, %s, 1, 1)
                """, (self.id, name_value, link_value, page_class, now, db_user))
                log(f"Created new page: id={new_page_id}, name='{name_value}', parent={self.id}, class='{page_class}'")
            except Exception as e:
                warn(f"Failed to create page: {str(e)}")
                report_error("backend", f"Failed to create page: {str(e)}")
        if not is_error() and new_page_id:
            # Call hook to initialize class-specific data
            # Get the page class for the new page and call its static method
            # This matches PHP pattern: call_user_func(array($classTranslationArray[$class]['upper'], 'addPageClassInformation'), ...)
            NewPageClass = get_page_class(page_class)
            if not NewPageClass:
                warn(f"Page class '{page_class}' not found")
                report_error("action", f"Page class '{page_class}' not found")
            else:
                # Call the classmethod on the new page's class
                NewPageClass._add_page_class_information(new_page_id)
            # Flag parent modification so cache system sees the hierarchy change
            self.flag_page_modification("child added")
        if new_page_id:
            log("Page creation completed successfully")
        else:
            log("Page creation encountered problems")
        trace_out()
        return new_page_id

    @classmethod
    def allow_null_names(cls) -> bool:
        """Static method: checks if this page class allows null names"""
        return False

    @classmethod
    def auto_link_name(cls) -> bool:
        """Static method: checks if this page class auto-generates links from names"""
        return True

    def can_move_to_page(self, target_page_id: int) -> bool:
        trace_in()
        if target_page_id == self.id:
            warn("Cannot move page into itself")
            report_error("action", "Cannot move page into itself")
            trace_out()
            return False
        if not is_error():
            target_page = get_page(page_id=target_page_id)
            if not target_page:
                warn(f"Target page {target_page_id} does not exist")
                report_error("action", f"Target page {target_page_id} does not exist")
                trace_out()
                return False
            if target_page.class_name is None or self.class_name is None:
                warn("Page class missing for move validation")
                report_error("action", "Page class missing for move validation")
                trace_out()
                return False
        if is_error():
            trace_out()
            return False
        # mypy guard
        assert target_page is not None
        assert target_page.class_name is not None
        assert self.class_name is not None
        if not is_error():
            # Check if target is a child of this page (would create circular reference)
            child_ids = self._check_children_recursive()
            if target_page_id in child_ids:
                warn(f"Cannot move page into its own child (page {target_page_id})")
                report_error("action", f"Cannot move page into its own child (page {target_page_id})")
                trace_out()
                return False
        if not is_error():
            # Check class compatibility
            if not target_page.allow_class_inside(self.class_name):
                warn(f"Target page {target_page_id} (class={target_page.class_name}) cannot contain pages with class={self.class_name}")
                report_error("action", f"Target page cannot contain pages with class '{self.class_name}'")
                trace_out()
                return False
        if not is_error():
            if not self.__class__.allow_inside_of(target_page.class_name):
                warn(f"Page class '{self.class_name}' cannot be inside page class '{target_page.class_name}'")
                report_error("action", f"Page class '{self.class_name}' cannot be inside page class '{target_page.class_name}'")
                trace_out()
                return False
        log(f"Page {self.id} can be moved to page {target_page_id}")
        trace_out()
        return not is_error()

    def copy_page(self, target_page_id: int, recursive: bool = False, max_depth: Optional[int] = None, copy_images: bool = False, copy_files: bool = False) -> int:
        trace_in()
        # Validate the copy is allowed (same as move validation)
        if not self.can_move_to_page(target_page_id):
            warn("Copy validation failed")
            report_error("action", "Copy validation failed")
            trace_out()
            return 0
        new_page_id = 0
        if not is_error():
            # Determine name for copy
            name = self.name if self.name else ''
            if not self.name:  # this page has no name
                if not self.allow_null_names():
                    warn("Cannot copy page with null name")
                    report_error("action", "Cannot copy page with null name")
            else:  # this page has a name - figure out a good name for the copy
                name_ctr = 1
                loop_failsafe = 100
                good_name = False
                while not good_name and (name_ctr < loop_failsafe):
                    log(f"Trying name '{name}' (attempt {name_ctr})")
                    # Use validate_name on the target parent page (use self's class since that's what the copied page will be)
                    target_page = get_page(page_id=target_page_id)
                    if target_page:
                        if target_page.validate_name(name, self.class_name, error_on_invalid=False):
                            good_name = True
                            log(f"Name '{name}' is valid")
                        else:
                            log(f"Name '{name}' failed validation, generating new name")
                            name = f"copy{' ' + str(name_ctr) if name_ctr > 1 else ''} of {self.name}"
                            name_ctr += 1
                    else:
                        warn(f"Target page {target_page_id} not found during name validation")
                        break
                if name_ctr == loop_failsafe:
                    warn("Copy name generation loop failsafe hit")
                    report_error("action", "Copy name generation failed")
        if not is_error():
            # Create the new page using add_page
            target_page = get_page(page_id=target_page_id)
            if target_page:
                new_page_id = target_page.add_page(self.class_name, name)
            else:
                warn(f"Target page {target_page_id} not found")
                report_error("action", f"Target page {target_page_id} not found")
        if not is_error() and new_page_id > 0:
            # Copy text content
            if self.text:
                new_page = get_page(page_id=new_page_id)
                if new_page:
                    new_page.modify_text(self.text)
            # Copy images if requested
            if copy_images:
                source_images = self.get_images_data()
                if source_images:
                    new_page = get_page(page_id=new_page_id)
                    if new_page:
                        # Extract image IDs in order (preserving rank order)
                        image_ids = [img['id'] for img in source_images]
                        if image_ids:
                            if not new_page.copy_media_items("image", image_ids):
                                warn(f"Failed to copy images from page {self.id} to page {new_page_id}")
            # Copy files if requested
            if copy_files:
                source_files = self.get_files_data()
                if source_files:
                    new_page = get_page(page_id=new_page_id)
                    if new_page:
                        # Extract file IDs in order (preserving rank order)
                        file_ids = [f['id'] for f in source_files]
                        if file_ids:
                            if not new_page.copy_media_items("file", file_ids):
                                warn(f"Failed to copy files from page {self.id} to page {new_page_id}")
            # Call class-specific copy logic hook
            self._copy_page_class_information(new_page_id)
            # Recursively copy children if requested
            if recursive:
                self._copy_children_recursive(new_page_id, max_depth, copy_images=copy_images, copy_files=copy_files)
            log(f"Successfully copied page {self.id} to page {new_page_id}")
        trace_out()
        return new_page_id

    def copy_media_items(self, media_type: str, item_ids: List[int], target_rank: Optional[int] = None) -> bool:
        """
        Generalized method to copy media items (images, audio, video, files) to this page.
        
        Args:
            media_type: Type of media ('image', 'audio', 'video', 'file') - defaults to 'file'
            item_ids: List of item IDs to copy
            target_rank: Optional target rank to insert at (1-based)
        
        Returns:
            bool: True if successful, False otherwise
        """
        trace_in()
        media_type = self._validate_media_type(media_type)
        if is_error():
            trace_out()
            return False
        
        log(f"Copying {len(item_ids)} {media_type} items to page {self.id}")
        
        # Get helper methods
        get_data_method = self._get_media_data_method(media_type)
        add_to_group_method = self._get_add_to_group_method(media_type)
        
        if not get_data_method or not add_to_group_method:
            warn(f"Required methods not found for media type {media_type}")
            report_error("action", f"Media type {media_type} not fully supported")
            trace_out()
            return False
        
        # Record original count before copying
        original_count = len(get_data_method())
        
        copied_count = 0
        for item_id in item_ids:
            if not is_error():
                if add_to_group_method(item_id):
                    copied_count += 1
                    log(f"Successfully copied {media_type} {item_id} to page {self.id}")
                    # Flag related item if method exists
                    flag_method = self._get_flag_related_method(media_type)
                    if flag_method:
                        flag_method(item_id, f"copied to page {self.id}")
                else:
                    warn(f"Failed to copy {media_type} {item_id} to page {self.id}")
        
        log(f"Successfully copied {copied_count}/{len(item_ids)} {media_type} items to page {self.id}")
        
        # Set ranks if target_rank is specified
        if not is_error() and target_rank is not None and copied_count > 0:
            log(f"Setting ranks starting from {target_rank}")
            for i, item_id in enumerate(item_ids[:copied_count]):
                target_rank_for_item = target_rank + i
                # The copied items were added at the end, so their old ranks are original_count + i + 1
                old_rank = original_count + i + 1
                
                log(f"Setting {media_type} {item_id} from rank {old_rank} to rank {target_rank_for_item}")
                success = self.set_media_rank(media_type, item_id, old_rank, target_rank_for_item)
                if not success:
                    warn(f"Failed to set {media_type} {item_id} rank to {target_rank_for_item}")
                    report_error("action", f"Failed to set {media_type} {item_id} rank to {target_rank_for_item}")
        
        if not is_error() and copied_count > 0:
            # Rebuild hot cache immediately with the copied items
            get_data_method(rebuild=True)
            self.flag_page_modification(f"{media_type}s updated")
        
        trace_out()
        return not is_error()

    def add_image(self, file_path: str, caption: Optional[str] = None) -> Optional[int]:
        trace_in()
        log(f"Adding image to page {self.id}: {file_path}")
        # Use filename as default caption if no caption provided
        if not caption:
            caption = Path(file_path).stem  # Get filename without extension
            log(f"Using filename as caption: {caption}")
        # Create the image record in a separate write transaction
        image_id = self._create_image_record(caption=caption)
        # Add image to this page's image group
        if not is_error() and image_id:
            if not self._add_image_to_group(image_id):
                warn(f"Failed to add image {image_id} to page group")
                report_error("action", f"Failed to add image {image_id} to page group")
        # Process the image file
        if not is_error() and image_id:
            image = get_image(image_id)
            if not image:
                warn(f"Image {image_id} not found")
                report_error("action", f"Image {image_id} not found")
            else:
                if not image.process_upload(uploaded_file_path=file_path, filename=f"image_{image_id}"):
                    warn(f"Failed to process image {image_id}")
                    report_error("action", f"Failed to process image {image_id}")
                else:
                    image.flag_image_modification("image uploaded")
        if image_id:
            log(f"Image creation completed successfully")
        else:
            log("Image creation encountered problems")
        if image_id and not is_error():
            # Rebuild hot cache immediately with the new image
            self.get_images_data(rebuild=True)
            self.flag_page_modification("images updated")
        trace_out()
        return image_id

    def add_audio(self, file_path: str, caption: Optional[str] = None) -> Optional[int]:
        trace_in()
        log(f"Adding audio to page {self.id}: {file_path}")
        # Use filename as default caption if no caption provided
        if not caption:
            caption = Path(file_path).stem  # Get filename without extension
            log(f"Using filename as caption: {caption}")
        # Create the audio record in a separate write transaction
        audio_id = self._create_audio_record(caption=caption)
        # Add audio to this page's audio group
        if not is_error() and audio_id:
            if not self._add_audio_to_group(audio_id):
                warn(f"Failed to add audio {audio_id} to page group")
                report_error("action", f"Failed to add audio {audio_id} to page group")
        # Process the audio file
        if not is_error() and audio_id:
            from hh.audio.audio_registry import get_audio
            audio = get_audio(audio_id)
            if not audio:
                warn(f"Audio {audio_id} not found")
                report_error("action", f"Audio {audio_id} not found")
            else:
                if not audio.process_upload(uploaded_file_path=file_path, filename=f"audio_{audio_id}"):
                    warn(f"Failed to process audio {audio_id}")
                    report_error("action", f"Failed to process audio {audio_id}")
                else:
                    audio.flag_audio_modification("audio uploaded")
        if audio_id:
            log(f"Audio creation completed successfully")
        else:
            log("Audio creation encountered problems")
        if audio_id and not is_error():
            # Rebuild hot cache immediately with the new audio
            self.get_audio_data(rebuild=True)
            self.flag_page_modification("audio updated")
        trace_out()
        return audio_id

    def add_video(self, file_path: str, caption: Optional[str] = None) -> Optional[int]:
        trace_in()
        log(f"Adding video to page {self.id}: {file_path}")
        # Use filename as default caption if no caption provided
        if not caption:
            caption = Path(file_path).stem  # Get filename without extension
            log(f"Using filename as caption: {caption}")
        # Create the video record in a separate write transaction
        video_id = self._create_video_record(caption=caption)
        # Add video to this page's video group
        if not is_error() and video_id:
            if not self._add_video_to_group(video_id):
                warn(f"Failed to add video {video_id} to page group")
                report_error("action", f"Failed to add video {video_id} to page group")
        # Process the video file
        if not is_error() and video_id:
            from hh.video.video_registry import get_video
            video = get_video(video_id)
            if not video:
                warn(f"Video {video_id} not found")
                report_error("action", f"Video {video_id} not found")
            else:
                if not video.process_upload(uploaded_file_path=file_path, filename=f"video_{video_id}"):
                    warn(f"Failed to process video {video_id}")
                    report_error("action", f"Failed to process video {video_id}")
                else:
                    video.flag_video_modification("video uploaded")
        if video_id:
            log(f"Video creation completed successfully")
        else:
            log("Video creation encountered problems")
        if video_id and not is_error():
            # Rebuild hot cache immediately with the new video
            self.get_video_data(rebuild=True)
            self.flag_page_modification("video updated")
        trace_out()
        return video_id

    def delete_all_file_groups(self) -> bool:
        trace_in()
        file_ids: List[int] = []
        if not is_error():
            rows = self.gateway.conn.read(
                "SELECT DISTINCT file_id FROM file_groups WHERE page_id = %s",
                [self.id],
            )
            file_ids = [row["file_id"] for row in rows] if rows else []
            self.gateway.conn.delete("DELETE FROM file_groups WHERE page_id = %s", [self.id])

        if not is_error():
            for fid in file_ids:
                usage = self._get_file_usage_count(fid)
                if usage == 0:
                    file_obj = get_file(file_id=fid)
                    if file_obj:
                        file_obj.delete_from_database()

        if not is_error():
            self.get_files_data(rebuild=True)
            self.flag_page_modification("files updated")
        trace_out()
        return not is_error()

    def delete_from_database(self) -> bool:
        trace_in()
        log(f"Deleting page {self.id} from database")
        success = False
        if not is_error():
            affected = self.gateway.conn.delete("DELETE FROM pages WHERE id = %s", [self.id])
            if affected > 0:
                success = True
                log(f"Successfully deleted page {self.id} from database")
            else:
                warn(f"Failed to delete page {self.id} - no rows affected")
                report_error("action", f"Failed to delete page {self.id}")
        else:
            log(f"Failed to delete page {self.id} from database due to errors")
        trace_out()
        return success

    def delete_page(self) -> bool:
        trace_in()
        gateway = get_gateway()
        if not gateway:
            warn("No gateway available")
            report_error("action", "No gateway available")
        if not is_error():
            confirm = gateway.get_arg('confirm')
            if not confirm:
                warn("Confirmation required for page deletion")
                report_error("action", "Confirmation required for page deletion")
        if not is_error():
            child_ids = self._get_child_page_ids()
        if not is_error():
            for child_id in child_ids:
                if not is_error():
                    child_page = get_page(child_id)
                    if child_page:
                        child_page.delete_page()  # Recursive call - uses same connection/transaction
                    else:
                        warn(f"Failed to load child page {child_id}")
                        report_error("action", f"Failed to load child page {child_id}")
        if not is_error():
            # Delete all image_groups entries and clean up unused images before deleting page
            if hasattr(self, '_delete_all_image_groups'):
                if not self._delete_all_image_groups():
                    warn(f"Failed to delete image_groups for page {self.id}")
                    report_error("action", f"Failed to delete image_groups for page {self.id}")
            if hasattr(self, '_delete_all_audio_groups'):
                if not self._delete_all_audio_groups():
                    warn(f"Failed to delete audio_groups for page {self.id}")
                    report_error("action", f"Failed to delete audio_groups for page {self.id}")
            if hasattr(self, '_delete_all_video_groups'):
                if not self._delete_all_video_groups():
                    warn(f"Failed to delete video_groups for page {self.id}")
                    report_error("action", f"Failed to delete video_groups for page {self.id}")
        if not is_error():
            # Call hook to clean up class-specific data before deleting
            self._delete_page_class_information()
        if not is_error():
            success = self.delete_from_database()
            if not success:
                warn(f"Failed to delete page {self.id}")
                report_error("action", f"Failed to delete page {self.id}")
        trace_out()
        return not is_error()

    def flag_page_modification(self, comments: str) -> bool:
        """Standardized method to update page modification audit trail"""
        trace_in()
        now = dt.datetime.now()
        if not is_error():
            user_results = self.gateway.conn.read("SELECT USER() as db_user")
            db_user = user_results[0]['db_user'] if user_results else 'unknown'
        if not is_error():
            affected = self.gateway.conn.update("""
                UPDATE pages SET last_modified = %s, username = %s, comments = %s, cache_built_at = NULL WHERE id = %s
            """, (now, db_user, comments, self.id))
            # Note: affected == 0 is not an error - it just means the values were already the same
            # (e.g., same timestamp due to datetime precision, same username/comments)
        if not is_error():
            # Update object properties to match database
            self.last_modified = now
            self.username = db_user
            self.comments = comments
            log(f"Updated page {self.id} modification flags: {comments}")
        if not is_error():
            # If this is not a "child page modified" comment, also flag the parent
            # This prevents infinite recursion up the tree
            if comments != "child page modified":
                if self.parent and self.parent != 0:
                    parent_page = get_page(page_id=self.parent)
                    if parent_page:
                        parent_page.flag_page_modification("child page modified")
        trace_out()
        return not is_error()

    def get_allowed_child_classes(self) -> List[Dict[str, Any]]:
        """Get list of page classes that are allowed as children of this page."""
        trace_in()
        allowed_classes = []
        
        # Get all registered page classes
        all_classes = get_all_page_classes()
        log(f"Checking {len(all_classes)} page classes for compatibility with parent page {self.id} (class={self.class_name})")
        
        # Check each class
        for class_name, PageClass in all_classes.items():
            if PageClass is None:
                continue
            
            # Check both conditions (same as _add_page does)
            # 1. Parent can contain this class
            parent_allows = self.allow_class_inside(class_name)
            # 2. Child class can be inside parent
            child_allows = PageClass.allow_inside_of(self.class_name)
            
            if parent_allows and child_allows:
                # Both checks passed - this class is allowed
                allow_null = PageClass.allow_null_names()
                allow_duplicate = PageClass.allow_duplicate_names()
                auto_link = PageClass.auto_link_name()
                allowed_classes.append({
                    'class_name': class_name,
                    'allow_null_names': allow_null,
                    'allow_duplicate_names': allow_duplicate,
                    'auto_link_name': auto_link
                })
                log(f"Class '{class_name}' is allowed (allow_null_names={allow_null}, allow_duplicate_names={allow_duplicate}, auto_link_name={auto_link})")
            else:
                log(f"Class '{class_name}' is not allowed (parent_allows={parent_allows}, child_allows={child_allows})")
        
        log(f"Found {len(allowed_classes)} allowed child classes for page {self.id}")
        trace_out()
        return allowed_classes

    @classmethod
    def getChildrenOf(cls, parent_id: int, view_type: str = 'tile') -> List[Dict[str, Any]]:
        """
        Class method to get children of a specific class type for a parent page.
        Matches legacy getChildrenOf() pattern - called as class method on child class.
        Each child class can override this to customize default view_type and class-specific behavior.
        
        Uses the class's own _get_children_query() method to get children of that specific class.
        
        Args:
            parent_id: ID of the parent page
            view_type: 'table' or 'tile' (default 'tile' for base class)
        
        Returns:
            List of child page data dictionaries
        """
        trace_in()
        gateway = get_gateway()
        if not gateway or not gateway.conn:
            warn("Gateway or connection not available")
            report_error("connection", "Gateway or connection not available")
            trace_out()
            return []
        
        # Use the class's own _get_children_query() method
        query, params = cls._get_children_query(parent_id)  # type: ignore[arg-type,call-arg]
        log(f"Using query for class '{cls.__name__}': {query[:500]}...")
        results = gateway.conn.read(query, params)
        children_data = []
        
        if view_type == 'table':
            # Return data formatted for table rendering
            if results:
                for row in results:
                    child_page = get_page(page_id=row['id'])
                    if child_page:
                        child_data = child_page._get_child_page_data()
                        # Add child count for this child page
                        child_count = child_page.get_child_count()
                        child_data['num_children'] = child_count
                        # Add field type for row rendering
                        child_data['field_type'] = child_page._get_child_row_field_type()
                        # Add format metadata
                        child_data['_format'] = 'table'
                        children_data.append(child_data)
            log(f"Loaded {len(children_data)} children for class 'page' (table format)")
        else:  # view_type == 'tile'
            # Return data formatted for tile rendering
            if results:
                for row in results:
                    child_page = get_page(page_id=row['id'])
                    if child_page:
                        child_data = child_page._get_child_page_data()
                        # Add display_name (derived field)
                        display_name = child_page._get_display_name()
                        child_data['display_name'] = display_name
                        # Add first image for tile rendering
                        images_data = child_page.get_images_data()
                        if images_data and len(images_data) > 0:
                            child_data['images'] = [images_data[0]]  # Just first image
                        else:
                            child_data['images'] = []
                        # Add format metadata
                        child_data['_format'] = 'tile'
                        children_data.append(child_data)
            log(f"Loaded {len(children_data)} children for class 'page' (tile format)")
        
        trace_out()
        return children_data

    def get_child_count(self) -> int:
        trace_in()
        count = 0
        if not is_error():
            results = self.gateway.conn.read("SELECT COUNT(*) as count FROM pages WHERE parent = %s", [self.id])
            if results:
                count = results[0]['count']
            else:
                warn(f"Failed to get child count for page {self.id}")
        log(f"Page {self.id} has {count} children")
        trace_out()
        return count

    def get_children_data(self) -> List[Dict[str, Any]]:
        trace_in()
        children_data = []
        if not is_error():
            child_ids = self._get_child_page_ids()
        if not is_error():
            for i, child_id in enumerate(child_ids):
                if not is_error():
                    child_page = get_page(page_id=child_id)
                    if child_page:
                        child_data = child_page.get_page_data()
                        # Add child count for this child page
                        child_count = child_page.get_child_count()
                        child_data['num_children'] = child_count
                        children_data.append(child_data)
                    else:
                        warn(f"Failed to load child page {child_id}")
                        report_error("action", f"Failed to load child page {child_id}")
        log(f"Loaded {len(children_data)}/{len(child_ids)} child pages for page {self.id}: {[c['name'] for c in children_data]}")
        trace_out()
        return children_data

    def get_path(self) -> List[Dict[str, Any]]:
        trace_in()
        path = []
        current_page = self
        level = 0
        while current_page and current_page.parent != 0:
            level += 1
            path.append({
                "id": current_page.id,
                "name": current_page._get_display_name(),
                "class": current_page.class_name
            })
            # Get parent page
            if current_page.parent is None:
                break
            parent_page = get_page(page_id=current_page.parent)
            if not parent_page:
                warn(f"Parent page {current_page.parent} not found for page {current_page.id}")
                break
            current_page = parent_page
        # Add root page (parent = 0)
        if current_page:
            level += 1
            path.append({
                "id": current_page.id,
                "name": current_page._get_display_name(),
                "class": current_page.class_name
            })
        # Reverse to get root -> current order
        path.reverse()
        log(f"Built path for page {self.id}: {len(path)} levels -> {[p['name'] for p in path]}")
        trace_out()
        return path

    def get_page_data(self) -> Dict[str, Any]:
        trace_in()
        data: Dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "link": self.link,
            "parent": self.parent,
            "class": self.class_name,
            "visibility": self.visibility,
            "text": self.text,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "username": self.username,
            "comments": self.comments
        }
        # Add breadcrumb path if available
        path_data = self.get_path()
        if path_data:
            data['path'] = path_data
        trace_out()
        return data

    def get_page(self) -> Dict[str, Any]:
        """Assemble a minimal JSON-friendly payload for AJAX consumption."""
        trace_in()
        page_data = self.get_page_data()
        images_data = self.get_images_data()
        children_by_class = self._get_children_by_class()
        
        # Add path data if available
        if 'path' not in page_data:
            path_data = self.get_path()
            if path_data:
                page_data['path'] = path_data

        # Minimal shape; client can expand later
        result: Dict[str, Any] = {
            'page': page_data,
            'images': images_data,
            'children_by_class': children_by_class,
        }
        
        # Add available app actions if MCP backend
        gateway = get_gateway()
        
        # Only include available_actions for MCP backend, not HTTP (HTTP renders them server-side)
        if gateway and gateway.backend == "mcp" and gateway.response:
            try:
                user_tier_level = gateway.response.get_user_tier_level()
                
                # get_app_actions() adds 4 to user_tier_level and checks for app actions at that tier
                app_actions = MCPWhitelist.get_app_actions(user_tier_level)
                
                if app_actions:
                    # Add source field to mark these as hot_cache
                    for action in app_actions:
                        action['source'] = 'hot_cache'
                    result['available_actions'] = app_actions
                    log(f"Added {len(app_actions)} app actions to get_page response")
            except Exception as e:
                log(f"Error getting app actions: {e}")
        
        trace_out()
        return result

    def get_prepared_text(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get the prepared text for this page. Checks cached prepared_text first, then processes if needed.
        """
        trace_in()
        # Check if field is already populated
        if hasattr(self, 'prepared_text') and self.prepared_text is not None:
            trace_out()
            return self.prepared_text
        # Field is empty, need to process text
        processor = TextProcessor()
        prepared = processor.preprocess(self.text or "")
        if prepared is not None:
            self.prepared_text = prepared
            # Only flag cache refresh if we actually processed text content
            # If we just confirmed there's no text (empty list), no need to refresh
            if prepared:
                self._flag_cache_refresh()
        trace_out()
        return prepared

    def get_files_data(self, rebuild: bool = False) -> List[Dict[str, Any]]:
        trace_in()
        # If rebuild flag is set, clear the cache to force a rebuild
        if rebuild:
            self.files = []
        # Check if field is already populated
        if hasattr(self, 'files') and self.files:
            trace_out()
            return self.files
        # Field is empty, need to hydrate from database
        files: List[Dict[str, Any]] = []
        if not is_error():
            rows = self.gateway.conn.read(
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
        self.files = files
        # Only flag cache refresh if we actually found files (data changed)
        # If we just confirmed there are no files (empty array), no need to refresh
        if files:
            self._flag_cache_refresh()
        trace_out()
        return files

    def get_images_data(self, rebuild: bool = False) -> List[Dict[str, Any]]:
        trace_in()
        # If rebuild flag is set, clear the cache to force a rebuild
        if rebuild:
            self.images = []
        # Check if field is already populated
        if hasattr(self, 'images') and self.images:
            debug(f"Page {self.id}: returning cached images")
            trace_out()
            return self.images
        # Field is empty, need to hydrate from database
        images_data = []
        if not is_error():
            try:
                results = self.gateway.conn.read("""
                    SELECT i.id, ig.image_rank 
                    FROM image_groups ig 
                    JOIN images i ON ig.image_id = i.id 
                    WHERE ig.page_id = %s 
                    ORDER BY ig.image_rank
                """, [self.id])
                for row in results:
                    image_id = row['id']
                    image_rank = row['image_rank']
                    image = get_image(image_id)
                    if image:
                        # Ensure instances are fully loaded before getting image_data
                        image.get_instances()
                        image_data = image.get_image_data()
                        image_data['image_rank'] = image_rank  # Add rank from image_groups
                        images_data.append(image_data)
                        log(f"Loaded image {image_id} (rank {image_rank}): {image_data.get('caption', 'untitled')}")
                    else:
                        warn(f"Failed to load image {image_id}")
                log(f"Loaded {len(images_data)} images for page {self.id}")
            except Exception as e:
                warn(f"Failed to load images for page {self.id}: {str(e)}")
                report_error("backend", f"Failed to load images: {str(e)}")
        self.images = images_data
        # Only flag cache refresh if we actually found images (data changed)
        if images_data:  # Only flag if actual images were loaded
            self._flag_cache_refresh()
        trace_out()
        return images_data

    def get_audio_data(self, rebuild: bool = False) -> List[Dict[str, Any]]:
        trace_in()
        # If rebuild flag is set, clear the cache to force a rebuild
        if rebuild:
            self.audio = []
        # Check if field is already populated
        if hasattr(self, 'audio') and self.audio:
            debug(f"Page {self.id}: returning cached audio")
            trace_out()
            return self.audio
        # Field is empty, need to hydrate from database
        audio_data = []
        if not is_error():
            try:
                from hh.audio.audio_registry import get_audio
                results = self.gateway.conn.read("""
                    SELECT a.id, ag.audio_rank 
                    FROM audio_groups ag 
                    JOIN audio a ON ag.audio_id = a.id 
                    WHERE ag.page_id = %s 
                    ORDER BY ag.audio_rank
                """, [self.id])
                for row in results:
                    audio_id = row['id']
                    audio_rank = row['audio_rank']
                    audio = get_audio(audio_id)
                    if audio:
                        # Ensure instances are fully loaded before getting audio_data
                        audio.get_instances()
                        audio_data_item = audio.get_audio_data()
                        audio_data_item['audio_rank'] = audio_rank  # Add rank from audio_groups
                        audio_data.append(audio_data_item)
                        log(f"Loaded audio {audio_id} (rank {audio_rank}): {audio_data_item.get('caption', 'untitled')}")
                    else:
                        warn(f"Failed to load audio {audio_id}")
                log(f"Loaded {len(audio_data)} audio for page {self.id}")
            except Exception as e:
                warn(f"Failed to load audio for page {self.id}: {str(e)}")
                report_error("backend", f"Failed to load audio: {str(e)}")
        self.audio = audio_data
        # Only flag cache refresh if we actually found audio (data changed)
        if audio_data:  # Only flag if actual audio were loaded
            self._flag_cache_refresh()
        trace_out()
        return audio_data

    def get_video_data(self, rebuild: bool = False) -> List[Dict[str, Any]]:
        trace_in()
        # If rebuild flag is set, clear the cache to force a rebuild
        if rebuild:
            self.video = []
        # Check if field is already populated
        if hasattr(self, 'video') and self.video:
            debug(f"Page {self.id}: returning cached video")
            trace_out()
            return self.video
        # Field is empty, need to hydrate from database
        video_data = []
        if not is_error():
            try:
                from hh.video.video_registry import get_video
                results = self.gateway.conn.read("""
                    SELECT v.id, vg.video_rank 
                    FROM video_groups vg 
                    JOIN video v ON vg.video_id = v.id 
                    WHERE vg.page_id = %s 
                    ORDER BY vg.video_rank
                """, [self.id])
                for row in results:
                    video_id = row['id']
                    video_rank = row['video_rank']
                    video = get_video(video_id)
                    if video:
                        # Ensure instances are fully loaded before getting video_data
                        video.get_instances()
                        video_data_item = video.get_video_data()
                        video_data_item['video_rank'] = video_rank  # Add rank from video_groups
                        video_data.append(video_data_item)
                        log(f"Loaded video {video_id} (rank {video_rank}): {video_data_item.get('caption', 'untitled')}")
                    else:
                        warn(f"Failed to load video {video_id}")
                log(f"Loaded {len(video_data)} video for page {self.id}")
            except Exception as e:
                warn(f"Failed to load video for page {self.id}: {str(e)}")
                report_error("backend", f"Failed to load video: {str(e)}")
        self.video = video_data
        # Only flag cache refresh if we actually found video (data changed)
        if video_data:  # Only flag if actual video were loaded
            self._flag_cache_refresh()
        trace_out()
        return video_data

    def reorder_images(self) -> bool:
        trace_in()
        log(f"Reordering images in page {self.id}")
        try:
            results = self.gateway.conn.read("""
                SELECT image_id, image_rank FROM image_groups 
                WHERE page_id = %s 
                ORDER BY image_rank
            """, [self.id])
            for i, img in enumerate(results, 1):
                current_rank = img['image_rank']
                new_rank = i
                # Only update if the rank actually needs to change
                if current_rank != new_rank:
                    affected = self.gateway.conn.update("""
                        UPDATE image_groups SET image_rank = %s 
                        WHERE page_id = %s AND image_id = %s AND image_rank = %s
                    """, (new_rank, self.id, img['image_id'], current_rank))
                    if affected == 0:
                        warn(f"Failed to reorder image {img['image_id']} to rank {new_rank}")
                        report_error("action", f"Failed to reorder image {img['image_id']}")
                else:
                    log(f"Image {img['image_id']} already at correct rank {current_rank}, skipping update")
            log(f"Successfully reordered {len(results)} images in page {self.id}")
        except Exception as e:
            warn(f"Failed to reorder images in page {self.id}: {str(e)}")
            report_error("action", f"Failed to reorder images in page {self.id}")
        if not is_error():
            self.flag_page_modification("images updated")
        trace_out()
        return not is_error()

    def reorder_files(self) -> bool:
        trace_in()
        try:
            rows = self.gateway.conn.read(
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
                    self.gateway.conn.update(
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
            self.get_files_data(rebuild=True)
            self.flag_page_modification("files updated")
        trace_out()
        return not is_error()

    def move_page(self, target_page_id: int) -> bool:
        trace_in()
        # Validate the move is allowed
        if not self.can_move_to_page(target_page_id):
            warn("Move validation failed")
            report_error("action", "Move validation failed")
            trace_out()
            return False
        original_parent = self.parent
        if not is_error():
            # Perform the actual move
            affected = self.gateway.conn.update("UPDATE pages SET parent = %s WHERE id = %s", (target_page_id, self.id))
            if affected == 0:
                warn(f"Failed to move page {self.id} - no rows affected")
                report_error("action", f"Failed to move page {self.id}")
        if not is_error():
            # Update object property and audit trail
            self.parent = target_page_id
            self.flag_page_modification("page moved")
            # Flag old parent so cache sees removals
            if original_parent and original_parent != 0 and original_parent != target_page_id:
                old_parent = get_page(page_id=original_parent)
                if old_parent:
                    old_parent.flag_page_modification("child moved out")
            # Flag new parent for additions
            if target_page_id and target_page_id != 0:
                new_parent = get_page(page_id=target_page_id)
                if new_parent:
                    new_parent.flag_page_modification("child moved in")
            log(f"Successfully moved page {self.id} to parent {target_page_id}")
        trace_out()
        return not is_error()

    def move_media_items(self, media_type: str, item_instances: List[Dict[str, int]], target_rank: Optional[int] = None) -> bool:
        """
        Generalized method to move media items (images, audio, video, files) from source pages to this page.
        
        Args:
            media_type: Type of media ('image', 'audio', 'video', 'file') - defaults to 'file'
            item_instances: List of dicts with keys: {media_type}_id, source_page_id, source_rank
            target_rank: Optional target rank to insert at (1-based)
        
        Returns:
            bool: True if successful, False otherwise
        """
        trace_in()
        media_type = self._validate_media_type(media_type)
        if is_error():
            trace_out()
            return False
        
        if not item_instances:
            trace_out()
            return True
        
        log(f"Moving {len(item_instances)} {media_type} instances to page {self.id}")
        
        # Get helper methods and field names
        get_data_method = self._get_media_data_method(media_type)
        add_to_group_method = self._get_add_to_group_method(media_type)
        reorder_method = self._get_reorder_method(media_type)
        table_name = self._get_media_table_name(media_type)
        id_field = self._get_media_id_field(media_type)
        rank_field = self._get_media_rank_field(media_type)
        
        if not get_data_method or not add_to_group_method or not reorder_method:
            warn(f"Required methods not found for media type {media_type}")
            report_error("action", f"Media type {media_type} not fully supported")
            trace_out()
            return False
        
        # Record original count before moving
        original_count = len(get_data_method())
        
        moved_count = 0
        source_pages_affected = set()
        for instance in item_instances:
            if is_error():
                break
            
            item_id = instance[id_field]
            source_page_id = instance["source_page_id"]
            source_rank = instance["source_rank"]
            
            if not is_error():
                # Verify the specific instance exists
                results = self.gateway.conn.read(f"""
                    SELECT COUNT(*) as count FROM {table_name} 
                    WHERE page_id = %s AND {id_field} = %s AND {rank_field} = %s
                """, (source_page_id, item_id, source_rank))
                if not results or results[0]['count'] == 0:
                    warn(f"{media_type.capitalize()} {item_id} (rank {source_rank}) not found in source page {source_page_id}")
                    continue
                
                # Remove this specific instance from source page
                affected = self.gateway.conn.delete(f"""
                    DELETE FROM {table_name} 
                    WHERE page_id = %s AND {id_field} = %s AND {rank_field} = %s
                """, (source_page_id, item_id, source_rank))
                if affected == 0:
                    warn(f"Failed to remove {media_type} {item_id} (rank {source_rank}) from source page {source_page_id}")
                    continue
                
                # Flag related item if method exists
                flag_method = self._get_flag_related_method(media_type)
                if flag_method:
                    flag_method(item_id, f"removed from page {source_page_id}")
                
                # Add to this page
                if add_to_group_method(item_id):
                    moved_count += 1
                    source_pages_affected.add(source_page_id)
                    log(f"Successfully moved {media_type} {item_id} (rank {source_rank}) from page {source_page_id} to page {self.id}")
                    if flag_method:
                        flag_method(item_id, f"moved to page {self.id}")
                else:
                    warn(f"Failed to move {media_type} {item_id} (rank {source_rank}) to page {self.id}")
        
        # Reorder remaining items in all affected source pages
        if not is_error() and moved_count > 0:
            for source_page_id in source_pages_affected:
                source_page = get_page(page_id=source_page_id)
                if source_page:
                    source_reorder_method = source_page._get_reorder_method(media_type)
                    if source_reorder_method:
                        if not source_reorder_method():
                            warn(f"Failed to reorder {media_type}s in source page {source_page_id}")
                            report_error("action", f"Failed to reorder {media_type}s in source page {source_page_id}")
                        # Rebuild source page hot cache immediately
                        source_get_data_method = source_page._get_media_data_method(media_type)
                        if source_get_data_method:
                            source_get_data_method(rebuild=True)
                else:
                    warn(f"Failed to load source page {source_page_id} for reordering")
                    report_error("action", f"Failed to load source page {source_page_id}")
        
        # Set ranks if target_rank is specified
        if not is_error() and target_rank is not None and moved_count > 0:
            log(f"Setting ranks starting from {target_rank}")
            for i, instance in enumerate(item_instances[:moved_count]):
                item_id = instance[id_field]
                target_rank_for_item = target_rank + i
                # We know exactly where we placed this item
                old_rank = original_count + i + 1
                
                log(f"Setting {media_type} {item_id} from rank {old_rank} to rank {target_rank_for_item}")
                success = self.set_media_rank(media_type, item_id, old_rank, target_rank_for_item)
                if not success:
                    warn(f"Failed to set {media_type} {item_id} rank to {target_rank_for_item}")
                    report_error("action", f"Failed to set {media_type} {item_id} rank to {target_rank_for_item}")
        
        log(f"Successfully moved {moved_count} {media_type} instances to page {self.id}")
        if not is_error() and moved_count > 0:
            # Rebuild hot cache immediately with the moved items
            get_data_method(rebuild=True)
            self.flag_page_modification(f"{media_type}s updated")
        
        trace_out()
        return not is_error()

    def remove_media_item(self, media_type: str, item_id: int, item_rank: int) -> bool:
        """
        Generalized method to remove a media item (image, audio, video, file) from this page.
        
        Args:
            media_type: Type of media ('image', 'audio', 'video', 'file') - defaults to 'file'
            item_id: ID of the item to remove
            item_rank: Rank of the item to remove (1-based)
        
        Returns:
            bool: True if successful, False otherwise
        """
        trace_in()
        media_type = self._validate_media_type(media_type)
        if is_error():
            trace_out()
            return False
        
        log(f"Removing {media_type} {item_id} (rank {item_rank}) from page {self.id}")
        
        # Get helper methods and field names
        get_data_method = self._get_media_data_method(media_type)
        reorder_method = self._get_reorder_method(media_type)
        table_name = self._get_media_table_name(media_type)
        id_field = self._get_media_id_field(media_type)
        rank_field = self._get_media_rank_field(media_type)
        
        if not get_data_method or not reorder_method:
            warn(f"Required methods not found for media type {media_type}")
            report_error("action", f"Media type {media_type} not fully supported")
            trace_out()
            return False
        
        if not is_error():
            # Remove from groups table
            affected = self.gateway.conn.delete(f"""
                DELETE FROM {table_name} 
                WHERE page_id = %s AND {id_field} = %s AND {rank_field} = %s
            """, (self.id, item_id, item_rank))
            if affected == 0:
                warn(f"Failed to remove {media_type} {item_id} (rank {item_rank}) from page {self.id}")
                report_error("action", f"Failed to remove {media_type} {item_id} (rank {item_rank})")
            
            # Reorder remaining items in this page
            if not is_error() and not reorder_method():
                warn(f"Failed to reorder {media_type}s after removing {media_type} {item_id}")
                report_error("action", f"Failed to reorder {media_type}s after removal")
            
            # Rebuild hot cache immediately without the removed item
            get_data_method(rebuild=True)
        
        # Check if item should be deleted (no longer used by any pages)
        if not is_error():
            # Get usage count method if it exists
            usage_count_method = self._get_usage_count_method(media_type)
            if usage_count_method:
                usage_count = usage_count_method(item_id)
                if usage_count == 0:
                    log(f"{media_type.capitalize()} {item_id} no longer used by any pages, deleting from database")
                    # Import and delete the item object
                    if media_type == "image":
                        from hh.image.image_registry import get_image
                        image_obj = get_image(item_id)
                        if image_obj and hasattr(image_obj, 'delete_from_database'):
                            if not image_obj.delete_from_database():
                                warn(f"Failed to delete unused {media_type} {item_id}")
                                report_error("action", f"Failed to delete unused {media_type} {item_id}")
                    elif media_type == "file":
                        from hh.file.file_registry import get_file
                        file_obj = get_file(file_id=item_id)
                        if file_obj and hasattr(file_obj, 'delete_from_database'):
                            file_obj.delete_from_database()
                    # Audio/video deletion would go here when implemented
                else:
                    log(f"{media_type.capitalize()} {item_id} still used by {usage_count} pages, keeping in database")
            else:
                # For types without usage count method, try to load and delete if possible
                if media_type == "image":
                    from hh.image.image_registry import get_image
                    image_obj = get_image(item_id)
                    if image_obj:
                        usage_count = image_obj.get_usage_count() if hasattr(image_obj, 'get_usage_count') else 1
                        if usage_count == 0 and hasattr(image_obj, 'delete_from_database'):
                            if not image_obj.delete_from_database():
                                warn(f"Failed to delete unused {media_type} {item_id}")
                                report_error("action", f"Failed to delete unused {media_type} {item_id}")
        
        if not is_error():
            log(f"Successfully removed {media_type} {item_id} (rank {item_rank}) from page {self.id}")
            self.flag_page_modification(f"{media_type}s updated")
            # Flag related item if method exists
            flag_method = self._get_flag_related_method(media_type)
            if flag_method:
                flag_method(item_id, f"removed from page {self.id}")
        
        trace_out()
        return not is_error()

    def modify_display_style(self, display_style: int) -> bool:
        """Modify the display style of a page"""
        trace_in()
        log(f"Modifying display style for page {self.id}: {getattr(self, 'displayStyle', None)} -> {display_style}")
        if not is_error():
            affected = self.gateway.conn.update("UPDATE pages SET displayStyle = %s WHERE id = %s", (display_style, self.id))
            if affected == 0:
                warn(f"Failed to update page {self.id} display style - no rows affected")
                report_error("action", f"Failed to update page {self.id} display style")
            else:
                self.displayStyle = display_style
                log(f"Successfully updated display style for page {self.id}")
                self.flag_page_modification("display style updated")
        trace_out()
        return not is_error()

    def modify_name(self, name: Optional[str] = None) -> bool:
        trace_in()
        # Normalize: convert None or empty string to None for database storage
        name_value = None if (name is None or (isinstance(name, str) and len(name.strip()) == 0)) else name
        current_name = self.name if self.name is not None else None
        log(f"Starting name modification for page {self.id}: '{current_name}' -> '{name_value}'")
        if name_value == current_name:
            log("Name unchanged, no update needed")
            trace_out()
            return True
        old_name = self.name
        log(f"Old name: '{old_name}', new name: '{name_value}'")
        if not is_error():
            # For validation, pass empty string if name_value is None (validation expects string)
            validation_name = name_value if name_value is not None else ""
            log(f"Validating new name '{validation_name}' for page {self.id}")
            parent_page = get_page(page_id=self.parent) if self.parent else None
            if not parent_page:
                warn(f"Parent page {self.parent} not found for validation")
                report_error("action", f"Parent page {self.parent} not found")
            elif not parent_page.validate_name(validation_name, self.class_name, exclude_id=self.id):
                warn("Page name validation failed")
                report_error("action", "Page name validation failed")
            else:
                log(f"Name validation passed for '{validation_name}'")
        if not is_error():
            log(f"Updating page {self.id} name in database: '{old_name}' -> '{name_value}'")
            affected = self.gateway.conn.update("UPDATE pages SET name = %s WHERE id = %s", (name_value, self.id))
            if affected == 0:
                warn(f"Failed to update page {self.id} name - no rows affected")
                report_error("action", f"Failed to update page {self.id} name")
            else:
                log(f"Successfully updated page {self.id} name in database")
        if not is_error():
            if self.name == self.link:
                log(f"Page {self.id} has auto-link enabled (name == link), updating link as well")
                link_value = name_value if (self.auto_link_name() and name_value is not None) else None
                log(f"Setting link to: {link_value}")
                affected = self.gateway.conn.update("UPDATE pages SET link = %s WHERE id = %s", (link_value, self.id))
                if affected == 0:
                    warn(f"Failed to update page {self.id} link - no rows affected")
                    report_error("action", f"Failed to update page {self.id} link")
                else:
                    self.link = link_value
                    log(f"Successfully updated page {self.id} link to '{link_value}'")
            else:
                log(f"Page {self.id} does not have auto-link enabled, skipping link update")
        if not is_error():
            modification_type = 'name and link' if self.auto_link_name() else 'name'
            log(f"Flagging page modification: {modification_type} changed")
            self.flag_page_modification(f"{modification_type} changed")
        if not is_error() and old_name and name_value:
            try:
                job_id = self._enqueue_maintenance_job(
                    "page_name_update",
                    {
                        "page_id": self.id,
                        "old_name": old_name,
                        "new_name": name_value,
                    },
                )
                log(f"Enqueued maintenance job {job_id} for page {self.id} name change")
            except Exception as exc:  # noqa: BLE001
                warn(f"Failed to enqueue maintenance job for page {self.id}: {exc}")
        if not is_error():
            self.name = name_value
            log(f"Successfully updated page {self.id} name to '{name_value}'")
        trace_out()
        return not is_error()

    def modify_text(self, text: str) -> bool:
        trace_in()
        # Check if text is actually changing
        if text == self.text:
            log(f"Text modification skipped for page {self.id}: content unchanged (length: {len(text)})")
            trace_out()
            return True
        # Validate text with TextProcessor
        processor = TextProcessor()
        preprocessed = processor.preprocess(text)
        if preprocessed is None:
            log(f"Text modification failed for page {self.id}: TextProcessor validation failed - parse errors detected in text (length: {len(text)})")
            trace_out()
            return False
        if not is_error():
            # Text validation passed, proceed with update
            text_value = None if text == "" else text
            affected = self.gateway.conn.update("UPDATE pages SET text = %s WHERE id = %s", (text_value, self.id))
            if affected == 0:
                warn(f"Failed to update page {self.id} text - no rows affected")
                report_error("action", f"Failed to update page {self.id} text")
        if not is_error():
            self.flag_page_modification("text changed")
        if not is_error():
            # Update links table with parsed link information (like PHP version)
            if not processor.update_links_table(self.gateway.conn, self.id):
                log(f"Text modification failed for page {self.id}: database update succeeded but links table update failed")
                warn("Failed to update links table")
                report_error("action", "Failed to update links table")
                trace_out()
                return False
        if not is_error():
            # Update prepared_text field with the newly processed text
            self.prepared_text = preprocessed
            # Flag that cache needs refresh
            self._flag_cache_refresh()
        if not is_error():
            # Update object property to match what was stored in database
            self.text = None if text == "" else text
            log(f"Text modification completed for page {self.id}: updated text (length: {len(text)}), validated with TextProcessor, updated links table")
        trace_out()
        return not is_error()

    def modify_visibility(self, visibility: int) -> bool:
        """Modify the visibility of a page"""
        trace_in()
        log(f"Modifying visibility for page {self.id}: {self.visibility} -> {visibility}")
        if not is_error():
            affected = self.gateway.conn.update("UPDATE pages SET visibility = %s WHERE id = %s", (visibility, self.id))
            if affected == 0:
                warn(f"Failed to update page {self.id} visibility - no rows affected")
                report_error("action", f"Failed to update page {self.id} visibility")
            else:
                self.visibility = visibility
                log(f"Successfully updated visibility for page {self.id}")
                self.flag_page_modification("visibility updated")
        trace_out()
        return not is_error()

    def regex_text(
        self,
        *,
        old_name: str,
        new_name: str,
    ) -> Dict[str, object]:
        trace_in()
        result: Dict[str, object] = {
            "page_id": self.id,
            "processed": 0,
            "modified": False,
        }

        if not old_name or not new_name:
            trace_out()
            return result

        existing_text = self.text or ""
        replacements = [
            (f"[[{old_name}]]", f"[[{new_name}]]"),
            (f"[[{old_name}][", f"[[{new_name}]["),
            (f"{{{{{old_name}}}}}", f"{{{{{new_name}}}}}"),
            (f"{{{{{old_name}}}{{", f"{{{{{new_name}}}{{"),
        ]

        updated_text = existing_text
        for pattern, replacement in replacements:
            updated_text = re.sub(re.escape(pattern), replacement, updated_text)

        if updated_text != existing_text:
            if not self.modify_text(updated_text):
                raise RuntimeError(f"Failed to update text for page {self.id}")
            result["processed"] = 1
            result["modified"] = True

        trace_out()
        return result

    def set_metadata_value(self, key: str, value: Any) -> bool:
        """Set a metadata value inside the specified namespace (or root) and persist it."""
        trace_in()
        metadata = self._get_metadata_dict()
        metadata[key] = value
        result = self._write_metadata_dict(metadata)
        trace_out()
        return result

    def set_media_rank(self, media_type: str, item_id: int, current_rank: int, new_rank: int) -> bool:
        """
        Generalized method to set the rank of a media item (image, audio, video, file) within this page.
        Uses hybrid approach: efficient delete-and-reflow for single moves, then verifies sequential ranks.
        
        Args:
            media_type: Type of media ('image', 'audio', 'video', 'file') - defaults to 'file'
            item_id: ID of the item to reorder
            current_rank: Current rank of the item (1-based)
            new_rank: Desired new rank of the item (1-based)
        
        Returns:
            bool: True if successful, False otherwise
        """
        trace_in()
        media_type = self._validate_media_type(media_type)
        if is_error():
            trace_out()
            return False
        
        log(f"Setting {media_type} {item_id} rank from {current_rank} to {new_rank} in page {self.id}")
        
        # Validate new_rank is positive integer
        if new_rank <= 0:
            warn(f"Invalid {media_type} rank: {new_rank} (must be positive)")
            report_error("action", f"Invalid {media_type} rank: {new_rank} (must be positive)")
            trace_out()
            return False
        
        # Check if no update needed
        if new_rank == current_rank:
            log(f"{media_type.capitalize()} rank unchanged, no update needed")
            trace_out()
            return True
        
        # Get helper methods and field names
        get_data_method = self._get_media_data_method(media_type)
        reorder_method = self._get_reorder_method(media_type)
        table_name = self._get_media_table_name(media_type)
        id_field = self._get_media_id_field(media_type)
        rank_field = self._get_media_rank_field(media_type)
        
        if not get_data_method or not reorder_method:
            warn(f"Required methods not found for media type {media_type}")
            report_error("action", f"Media type {media_type} not fully supported")
            trace_out()
            return False
        
        if not is_error():
            # Step 1: Delete the target row
            affected = self.gateway.conn.delete(f"""
                DELETE FROM {table_name} 
                WHERE page_id = %s AND {id_field} = %s AND {rank_field} = %s
            """, (self.id, item_id, current_rank))
            if affected == 0:
                warn(f"Failed to delete {media_type} {item_id} at rank {current_rank}")
                report_error("action", f"Failed to delete {media_type} {item_id} at rank {current_rank}")
                trace_out()
                return False
            
            # Step 2: Determine direction and reflow other items
            if new_rank < current_rank:
                # Moving up: scoot items DOWN (increase ranks) from current_rank-1 to new_rank (backwards)
                log(f"Moving up: scooting items down from rank {current_rank-1} to {new_rank}")
                for rank in range(current_rank - 1, new_rank - 1, -1):
                    # Get the item_id at this rank
                    results = self.gateway.conn.read(f"""
                        SELECT {id_field} FROM {table_name} 
                        WHERE page_id = %s AND {rank_field} = %s
                    """, (self.id, rank))
                    if results:
                        other_item_id = results[0][id_field]
                        affected = self.gateway.conn.update(f"""
                            UPDATE {table_name} 
                            SET {rank_field} = {rank_field} + 1 
                            WHERE page_id = %s AND {id_field} = %s AND {rank_field} = %s
                        """, (self.id, other_item_id, rank))
                        if affected == 0:
                            warn(f"Failed to scoot down rank {rank}")
                            report_error("action", f"Failed to scoot down rank {rank}")
            else:
                # Moving down: scoot items UP (decrease ranks) from current_rank+1 to new_rank (forwards)
                log(f"Moving down: scooting items up from rank {current_rank+1} to {new_rank}")
                for rank in range(current_rank + 1, new_rank + 1):
                    # Get the item_id at this rank
                    results = self.gateway.conn.read(f"""
                        SELECT {id_field} FROM {table_name} 
                        WHERE page_id = %s AND {rank_field} = %s
                    """, (self.id, rank))
                    if results:
                        other_item_id = results[0][id_field]
                        affected = self.gateway.conn.update(f"""
                            UPDATE {table_name} 
                            SET {rank_field} = {rank_field} - 1 
                            WHERE page_id = %s AND {id_field} = %s AND {rank_field} = %s
                        """, (self.id, other_item_id, rank))
                        if affected == 0:
                            warn(f"Failed to scoot up rank {rank}")
                            report_error("action", f"Failed to scoot up rank {rank}")
            
            # Step 3: Insert new row with desired rank
            if not is_error():
                new_id = self.gateway.conn.create(f"""
                    INSERT INTO {table_name} (page_id, {id_field}, {rank_field}) 
                    VALUES (%s, %s, %s)
                """, (self.id, item_id, new_rank))
                if new_id is None:
                    warn(f"Failed to insert {media_type} {item_id} at rank {new_rank}")
                    report_error("action", f"Failed to insert {media_type} {item_id} at rank {new_rank}")
            
            # Step 4: Verify and fix any gaps (ensure sequential ranks 1, 2, 3...)
            if not is_error():
                log(f"Verifying sequential ranks for {media_type}s in page {self.id}")
                # Get all items ordered by current rank
                results = self.gateway.conn.read(f"""
                    SELECT {id_field}, {rank_field} FROM {table_name} 
                    WHERE page_id = %s 
                    ORDER BY {rank_field}
                """, [self.id])
                
                if results:
                    # Check if ranks are sequential (1, 2, 3...)
                    needs_reflow = False
                    for i, row in enumerate(results, start=1):
                        if row[rank_field] != i:
                            needs_reflow = True
                            break
                    
                    # If gaps found, reflow everything to ensure sequential ranks
                    if needs_reflow:
                        log(f"Gaps detected in {media_type} ranks, reflowing to ensure sequential order")
                        for i, row in enumerate(results, start=1):
                            current_db_rank = row[rank_field]
                            if current_db_rank != i:
                                affected = self.gateway.conn.update(f"""
                                    UPDATE {table_name} 
                                    SET {rank_field} = %s 
                                    WHERE page_id = %s AND {id_field} = %s AND {rank_field} = %s
                                """, (i, self.id, row[id_field], current_db_rank))
                                if affected == 0:
                                    warn(f"Failed to reflow {media_type} {row[id_field]} to rank {i}")
                                    report_error("action", f"Failed to reflow {media_type} {row[id_field]}")
                        log(f"Successfully reflowed {len(results)} {media_type}s to sequential ranks")
                    else:
                        log(f"All {len(results)} {media_type}s already have sequential ranks")
            
            if not is_error():
                log(f"Successfully reordered {media_type} {item_id} to rank {new_rank} in page {self.id}")
                # Rebuild hot cache immediately with updated ranks
                get_data_method(rebuild=True)
        
        if not is_error():
            self.flag_page_modification(f"{media_type}s updated")
        
        trace_out()
        return not is_error()

    def show_page(self) -> Dict[str, Any]:
        trace_in()
        cache_ready = getattr(self, 'cache_hydrated', False) and self.children_by_class is not None
        lightweight = False
        gateway = get_gateway()
        if gateway and gateway.backend == "mcp":
            lightweight = True
        if cache_ready and not lightweight:
            debug(f"Page {self.id}: cache available, methods will check cache independently")
        if lightweight:
            debug(f"Page {self.id}: cache miss or stale entry; rebuilding lightweight payload")
        else:
            debug(f"Page {self.id}: cache miss or stale entry; rebuilding show_page payload")
        page_data = self.get_page_data()
        images_data = self.get_images_data()
        files_data = self.get_files_data()
        children_by_class = self._get_children_by_class()
        badge_headers = self._add_badge_headers()
        upper_content = self._add_upper_content()
        lower_content = self._add_lower_content()

        prepared_payload = self.get_prepared_text()
        if prepared_payload is not None:
            page_data = dict(page_data)
            page_data['prepared_text'] = prepared_payload

        if lightweight:
            response_data = {
                "page": page_data,
                "images": images_data,
                "children_by_class": children_by_class,
                "files": files_data,
            }
            if gateway and gateway.backend == "mcp" and gateway.response:
                try:
                    user_tier_level = gateway.response.get_user_tier_level()
                    app_actions = MCPWhitelist.get_app_actions(user_tier_level)
                    if app_actions:
                        for action in app_actions:
                            action['source'] = 'hot_cache'
                        response_data['available_actions'] = app_actions
                except Exception as exc:
                    warn(f"Failed to load MCP actions: {exc}")
        else:
            response_data = {
                "page": page_data,
                "children_by_class": children_by_class,
                "images": images_data,
                "files": files_data,
                "badge_headers": badge_headers,
                "upper_content": upper_content,
                "lower_content": lower_content,
            }

        # Cache refresh will be handled by wrapper method system if flag is set

        total_children = sum(len(group['children']) for group in children_by_class.values())
        file_count = len(files_data)
        if lightweight:
            log(
                f"Assembled lightweight display data for page {self.id}: "
                f"{total_children} children in {len(children_by_class)} classes, "
                f"{len(images_data)} images, {file_count} files"
            )
        else:
            log(
                f"Assembled display data for page {self.id}: "
                f"{total_children} children in {len(children_by_class)} classes, "
                f"{len(images_data)} images, {file_count} files"
            )
        trace_out()
        return response_data

    def validate_name(
        self,
        name: str,
        page_class: str,
        exclude_id: Optional[int] = None,
        error_on_invalid: bool = True,
    ) -> bool:
        """Validate a page name. Uses parent's connection and parent_id, but checks new page's class settings."""
        trace_in()
        NewPageClass = get_page_class(page_class)
        if not NewPageClass:
            warn(f"Page class '{page_class}' not found for validation")
            report_error("action", f"Page class '{page_class}' not found")
            trace_out()
            return False

        def fail(warn_msg: str, log_msg: Optional[str] = None) -> bool:
            if error_on_invalid:
                warn(warn_msg)
            else:
                debug(f"[validate_name suppressed] {warn_msg}")
            if log_msg:
                log(log_msg)
            trace_out()
            return False

        log(f"Validating name: '{name}' for parent {self.parent}, page_class: {page_class}, exclude_id: {exclude_id}")
        if not name or len(name) == 0:
            if not NewPageClass.allow_null_names():
                return fail("Page name cannot be empty", "Validation failed: empty name not allowed")
            else:
                log("Validation passed: empty name allowed")
                trace_out()
                return True
        if len(name) > 255:
            return fail(
                f"Page name too long: {len(name)} characters (max 255)",
                f"Validation failed: name too long ({len(name)} chars)",
            )
        if name and name.isdigit():
            return fail("Page name cannot be all digits", "Validation failed: name is all digits")
        if name and any(char in name for char in ['{', '}', '[', ']']):
            return fail(f"Page name contains illegal characters: {name}", "Validation failed: illegal characters")
        if name and not NewPageClass.allow_duplicate_names():
            log(f"Checking for duplicate names under parent {self.parent}")
            if exclude_id:
                results = self.gateway.conn.read("SELECT id FROM pages WHERE parent = %s AND name = %s AND id != %s", 
                              (self.parent, name, exclude_id))
            else:
                results = self.gateway.conn.read("SELECT id FROM pages WHERE parent = %s AND name = %s", 
                              (self.parent, name))
            if results:
                existing_page_id = results[0]['id']
                return fail(
                    f"Page name '{name}' already exists under parent {self.parent} (page ID: {existing_page_id})",
                    f"Validation failed: duplicate name found (existing page {existing_page_id})",
                )
            log("Duplicate name check passed")
        if name and NewPageClass.auto_link_name():
            log(f"Checking for duplicate links (auto_link_name enabled)")
            if exclude_id:
                results = self.gateway.conn.read("SELECT id FROM pages WHERE link = %s AND id != %s", (name, exclude_id))
            else:
                results = self.gateway.conn.read("SELECT id FROM pages WHERE link = %s", (name,))
            if results:
                existing_page_id = results[0]['id']
                return fail(
                    f"Page link '{name}' already exists (page ID: {existing_page_id})",
                    f"Validation failed: duplicate link found (existing page {existing_page_id})",
                )
            log("Duplicate link check passed")
        log(f"Name validation successful for '{name}'")
        trace_out()
        return True

