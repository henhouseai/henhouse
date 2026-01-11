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

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
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

    def __init__(self, id: int):
        trace_in()
        self.gateway = get_gateway()
        log(f"Initializing Page with id={id}")
        
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
        
        # Try to hydrate from cache database first (check cache before main DB)
        cache_hydrated = False
        if not is_error():
            # Get entire cache row to check staleness (no main DB read needed)
            cache_query = """
                SELECT id, name, link, text, parent, class, last_modified, username, comments, visibility, displayStyle, viewCount,
                       display_name, prepared_text, children_summary, image_summary, file_summary, links_out, metadata, cache_built_at
                FROM pages
                WHERE id = %s
            """
            try:
                cache_results = self.gateway.conn.read_cache(cache_query, [id])
                if cache_results:
                    cache_row = cache_results[0]
                    cache_last_modified = cache_row.get('last_modified')
                    cache_built_at = cache_row.get('cache_built_at')
                    
                    # Check staleness using cache DB only: cache.last_modified vs cache.cache_built_at
                    cache_last_modified_dt = normalize_datetime(cache_last_modified)
                    cache_built_at_dt = normalize_datetime(cache_built_at)
                    
                    if cache_built_at_dt is None:
                        log(f"Cache for page {id} does not exist (cache_built_at is NULL)")
                    elif cache_last_modified_dt and cache_built_at_dt and cache_built_at_dt < cache_last_modified_dt:
                        log(f"Cache for page {id} is stale (cache_built_at={cache_built_at_dt}, cache.last_modified={cache_last_modified_dt})")
                    else:
                        # Cache is fresh - hydrate entirely from cache DB (no main DB access)
                        self.name = cache_row.get('name')
                        self.link = cache_row.get('link')
                        self.text = cache_row.get('text')
                        self.parent = cache_row.get('parent')
                        self.class_name = cache_row.get('class')
                        self.visibility = cache_row.get('visibility')
                        self.displayStyle = cache_row.get('displayStyle')
                        self.last_modified = cache_last_modified
                        self.username = cache_row.get('username')
                        self.comments = cache_row.get('comments')
                        metadata_raw = cache_row.get('metadata')
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
                        
                        # Call hook for subclasses to handle pre-metadata-extraction setup
                        if not is_error():
                            self._before_metadata_extraction()
                        
                        # Extract metadata fields as attributes
                        if isinstance(self.metadata, dict):
                            for key, value in self.metadata.items():
                                if not hasattr(self, key):
                                    setattr(self, key, value)
                                    log(f"Extracted metadata field: {key} = {value}")
                                else:
                                    log(f"Skipped metadata field '{key}' - attribute already exists")
                        
                        # Call hook for subclasses to handle post-metadata-extraction setup
                        if not is_error():
                            self._after_metadata_extraction()
                        
                        # Load expensive pre-computed data from cache database directly into the 5 derived fields
                        self.display_name = cache_row.get('display_name')
                        self.prepared_text = deserialize_json_blob(cache_row.get('prepared_text'), None)
                        self.children_by_class = deserialize_json_blob(cache_row.get('children_summary'), {})
                        self.images = deserialize_json_blob(cache_row.get('image_summary'), [])
                        self.files = deserialize_json_blob(cache_row.get('file_summary'), [])
                        self.cache_built_at = cache_built_at
                        self.cache_hydrated = True
                        cache_hydrated = True
                        text_length = len(self.text) if self.text else 0
                        log(f"Loaded page {id} entirely from cache: {self.name}")
                        log(f"Hydrated page {id} entirely from cache (built_at={cache_built_at_dt})")
                else:
                    log(f"Cache for page {id} does not exist (no cache row found)")
            except Exception as e:
                warn(f"Failed to hydrate page {id} from cache: {e}")
                # Don't report error - cache hydration failure is not critical, will fall back to main DB
        
        # If cache is stale/missing, fall back to main database
        if not cache_hydrated and not is_error():
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
                
                # Call hook for subclasses to handle pre-metadata-extraction setup
                if not is_error():
                    self._before_metadata_extraction()
                
                # Automatically extract all metadata fields as attributes
                if isinstance(self.metadata, dict):
                    for key, value in self.metadata.items():
                        if not hasattr(self, key):
                            setattr(self, key, value)
                            log(f"Extracted metadata field: {key} = {value}")
                        else:
                            log(f"Skipped metadata field '{key}' - attribute already exists")
                
                # Call hook for subclasses to handle post-metadata-extraction setup
                if not is_error():
                    self._after_metadata_extraction()
                
                text_length = len(self.text) if self.text else 0
                log(f"Loaded page {id} from main DB: {self.name}")
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

    @classmethod
    def _before_add_page(cls, parent_id: int, page_class: str, name: Optional[str]) -> None:
        """
        Hook called before page creation for validation or preparation.
        This is a classmethod (like PHP's static method) so it can be called on the class
        without needing an instance. Subclasses should override this.
        
        Args:
            parent_id: ID of the parent page
            page_class: Class name of the page to be created
            name: Name of the page to be created (may be None)
        """
        pass

    @classmethod
    def _after_add_page(cls, new_page_id: int):
        """
        Hook called after page creation to initialize class-specific data.
        This is a classmethod (like PHP's static method) so it can be called on the class
        without needing an instance. Subclasses should override this.
        """
        pass

    def _before_copy_page(self, target_page_id: int):
        """
        Hook called before copying a page.
        Subclasses can override this for validation or preparation.
        """
        pass

    def _after_copy_page(self, new_page_id: int):
        """
        Hook called after copying a page.
        Subclasses can override this for cleanup or recalculation.
        """
        pass

    def _before_move_page(self, target_page_id: int):
        """
        Hook called before moving a page.
        Subclasses can override this for validation or preparation.
        """
        pass

    def _after_move_page(self, old_parent_id: Optional[int], new_parent_id: int):
        """
        Hook called after moving a page.
        Subclasses can override this for cleanup or recalculation.
        """
        pass

    def _before_delete_page(self):
        """
        Hook called before deleting a page.
        Subclasses can override this for validation or preparation.
        """
        pass

    def _after_delete_page(self):
        """
        Hook called after deleting a page.
        Subclasses can override this for cleanup or recalculation.
        """
        pass

    def _get_child_page_ids(self) -> List[int]:
        """
        Get all child page IDs for recursive deletion.
        This queries all children regardless of class (matching legacy PHP behavior).
        For display purposes, use _get_children_query() which can filter by class.
        """
        trace_in()
        child_ids = []
        if not is_error():
            # Query all children regardless of class (legacy behavior for deletion)
            # _get_children_query() is for display and filters by class
            results = self.gateway.conn.read(
                "SELECT id FROM pages WHERE parent = %s",
                [self.id]
            )
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
            log(f"Page {self.id}: returning cached children_by_class")
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

    def _before_metadata_extraction(self) -> None:
        """
        Hook called before metadata fields are extracted as attributes.
        Subclasses can override this to prepare before metadata extraction.
        Called automatically in __init__() before metadata extraction.
        """
        # Default implementation does nothing - subclasses can override
        pass

    def _after_metadata_extraction(self) -> None:
        """
        Hook called after metadata fields are extracted as attributes.
        Subclasses can override this to normalize metadata, set defaults, or set up lazy computation.
        Called automatically in __init__() after metadata extraction but before cache hydration.
        """
        # Default implementation does nothing - subclasses can override
        pass

    @classmethod
    def get_section_header_links(cls, parent_id: int, section: str) -> List[str]:
        """
        Return list of link names for section header (capitalized, plural).

        Override in derived classes to customize header links for that section type.
        First link gets special treatment in TypeScript (table/tile toggle).
        Subsequent links use their text content as view_type.
        """
        return ['Pages']

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

    @staticmethod
    def _validate_metadata_ascii(data: Any, path: str = "metadata") -> tuple[bool, str]:
        """
        Recursively validate that all strings in metadata are ASCII-only.
        Allows printable ASCII (32-126) plus tab, newline, carriage return.
        Returns (is_valid, error_message).

        Metadata is stored in MySQL JSON fields and must be ASCII-only
        to avoid encoding issues. Use page text (modify_text) for Unicode content.

        Args:
            data: The data to validate (can be dict, list, str, int, float, bool, None)
            path: Current path for error messages (e.g., "metadata.log[0].message")

        Returns:
            Tuple of (is_valid, error_message)
        """
        if data is None:
            return True, ""

        if isinstance(data, bool):
            # Check bool before int since bool is subclass of int
            return True, ""

        if isinstance(data, (int, float)):
            return True, ""

        if isinstance(data, str):
            for i, char in enumerate(data):
                code = ord(char)
                # Allow: tab(9), newline(10), carriage return(13), printable ASCII(32-126)
                if code not in (9, 10, 13) and not (32 <= code <= 126):
                    return False, f"{path} contains non-ASCII character at position {i} (code {code}). Metadata must be ASCII-only. Use page text for Unicode content."
            return True, ""

        if isinstance(data, dict):
            for key, value in data.items():
                # Validate key is ASCII string
                if not isinstance(key, str):
                    return False, f"{path} has non-string key: {type(key).__name__}"
                is_valid, error_msg = Page._validate_metadata_ascii(key, f"{path}.key")
                if not is_valid:
                    return False, error_msg.replace(f"{path}.key", f"{path} key '{key}'")
                # Validate value recursively
                is_valid, error_msg = Page._validate_metadata_ascii(value, f"{path}.{key}")
                if not is_valid:
                    return False, error_msg
            return True, ""

        if isinstance(data, list):
            for i, item in enumerate(data):
                is_valid, error_msg = Page._validate_metadata_ascii(item, f"{path}[{i}]")
                if not is_valid:
                    return False, error_msg
            return True, ""

        # Unknown type - reject to be safe
        return False, f"{path} has unsupported type: {type(data).__name__}"

    def _get_metadata_dict(self) -> Dict[str, Any]:
        metadata = getattr(self, 'metadata', None)
        if isinstance(metadata, dict):
            return metadata
        parsed = self._parse_metadata_value(metadata)
        self.metadata = parsed
        return self.metadata

    def _write_metadata_dict(self, metadata: Dict[str, Any]) -> bool:
        trace_in()
        metadata = metadata or {}

        # Validate all strings in metadata are ASCII-only
        is_valid, error_msg = self._validate_metadata_ascii(metadata)
        if not is_valid:
            warn(error_msg)
            report_error("action", error_msg)
            trace_out()
            return False

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
    
    def finalize_response_http(self, source_data: Dict[str, Any]) -> None:
        """Hook called by HTTP backend to finalize response data before rendering.
        Default: removes page_summary badge for HTTP backend.
        Override in derived classes to customize behavior.
        """
        # Remove page_summary badge for HTTP backend (default behavior)
        badge_headers = source_data.get('badge_headers', {})
        if 'page_summary' in badge_headers:
            del badge_headers['page_summary']
    
    def finalize_response_parser(self, source_data: Dict[str, Any]) -> None:
        """Hook called by parser backend to finalize response data before rendering.
        Default: no-op (parser doesn't need any cleanup).
        Override in derived classes to customize behavior.
        """
        pass  # Parser backend doesn't need any cleanup by default

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

    def _flag_cache_refresh(self) -> None:
        self._cache_needs_refresh = True

    def _refresh_cached_page(self) -> bool:
        from .cache_operations import refresh_cached_page
        return refresh_cached_page(self)

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
        log(f"Enqueued maintenance job {job_id}: type={job_type}, priority={priority}")
        trace_out()
        return job_id

    def allow_class_inside(self, target_class: str) -> bool:
        return True

    @classmethod
    def allow_duplicate_names(cls) -> bool:
        return True

    @classmethod
    def allow_inside_of(cls, parent_class: str) -> bool:
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
            
            # Call before hook for validation or preparation
            if not is_error():
                NewPageClass._before_add_page(self.id, page_class, name_value)
            
            if not is_error():
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
                NewPageClass._after_add_page(new_page_id)
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
        return False

    @classmethod
    def auto_link_name(cls) -> bool:
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
            # Call before hook
            self._before_copy_page(target_page_id)
        if not is_error() and new_page_id > 0:
            # Copy text content
            if self.text:
                new_page = get_page(page_id=new_page_id)
                if new_page:
                    new_page.modify_text(self.text)
            # Copy metadata automatically
            if self.metadata:
                new_page = get_page(page_id=new_page_id)
                if new_page:
                    # Copy entire metadata dict to new page
                    source_metadata = self._get_metadata_dict()
                    if source_metadata:
                        new_page._write_metadata_dict(source_metadata.copy())
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
            # Recursively copy children if requested
            if recursive:
                self._copy_children_recursive(new_page_id, max_depth, copy_images=copy_images, copy_files=copy_files)
            # Call after hook
            self._after_copy_page(new_page_id)
            log(f"Successfully copied page {self.id} to page {new_page_id}")
        trace_out()
        return new_page_id

    def copy_media_items(self, media_type: str, item_ids: List[int], target_rank: Optional[int] = None) -> bool:
        from .media_operations import copy_media_items as copy_media_items_impl
        return copy_media_items_impl(self, media_type, item_ids, target_rank)

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
            # Call before hook
            self._before_delete_page()
        if not is_error():
            success = self.delete_from_database()
            if success:
                # Call after hook
                self._after_delete_page()
            if not success:
                warn(f"Failed to delete page {self.id}")
                report_error("action", f"Failed to delete page {self.id}")
        trace_out()
        return not is_error()

    def flag_page_modification(self, comments: str) -> bool:
        trace_in()
        # Get NOW() from database for consistency
        if not is_error():
            now_results = self.gateway.conn.read("SELECT NOW() as db_now")
            now = now_results[0]['db_now'] if now_results else dt.datetime.now()
        if not is_error():
            user_results = self.gateway.conn.read("SELECT USER() as db_user")
            db_user = user_results[0]['db_user'] if user_results else 'unknown'
        
        # Validate timestamp: last_modified must be strictly greater than cache_built_at
        # Use tolerance window to handle race conditions with maintenance daemon
        if not is_error():
            if self.cache_built_at is not None:
                TOLERANCE_SECONDS = 10  # Grace period for daemon race conditions

                if now <= self.cache_built_at:
                    # Calculate how far behind (or equal) we are
                    diff = (self.cache_built_at - now).total_seconds()

                    if diff <= TOLERANCE_SECONDS:
                        # Within tolerance - likely a race condition with maintenance daemon
                        # Set now to cache_built_at + 1 second to ensure modification wins
                        original_now = now
                        now = self.cache_built_at + dt.timedelta(seconds=1)
                        log(f"Adjusted last_modified: {original_now} -> {now} (was {diff:.2f}s behind cache_built_at)")
                    else:
                        # Outside tolerance - something is genuinely wrong (clock skew, stale data)
                        report_error("action", f"flag_page_modification: last_modified ({now}) is {diff:.2f}s behind cache_built_at ({self.cache_built_at}) - exceeds {TOLERANCE_SECONDS}s tolerance")
        
        if not is_error():
            affected = self.gateway.conn.update("""
                UPDATE pages SET last_modified = %s, username = %s, comments = %s WHERE id = %s
            """, (now, db_user, comments, self.id))
            # Note: affected == 0 is not an error - it just means the values were already the same
            # (e.g., same timestamp due to datetime precision, same username/comments)
        if not is_error():
            # Update object properties to match database
            self.last_modified = now
            self.username = db_user
            self.comments = comments
            # Buffer lightweight cache flag update (last_modified only)
            self.gateway.conn.buffer_cache_flag_modification("pages", self.id, now)
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

    @classmethod
    def get_section_html(cls, parent_id: int, section: str, view_type: str, class_name: Optional[str] = None) -> Optional[str]:
        # Base class returns None - use default rendering
        return None

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
        from .data_operations import get_children_data
        return get_children_data(self)

    def get_path(self) -> List[Dict[str, Any]]:
        from .data_operations import get_path
        return get_path(self)

    def get_page_data(self) -> Dict[str, Any]:
        from .data_operations import get_page_data
        return get_page_data(self)

    def get_page(self) -> Dict[str, Any]:
        from .data_operations import assemble_page_data
        return assemble_page_data(self)

    def get_prepared_text(self) -> Optional[List[Dict[str, Any]]]:
        from .data_operations import get_prepared_text
        return get_prepared_text(self)

    def get_files_data(self, rebuild: bool = False) -> List[Dict[str, Any]]:
        from .data_operations import get_files_data
        return get_files_data(self, rebuild)

    def get_images_data(self, rebuild: bool = False) -> List[Dict[str, Any]]:
        from .data_operations import get_images_data
        return get_images_data(self, rebuild)

    def get_audio_data(self, rebuild: bool = False) -> List[Dict[str, Any]]:
        from .data_operations import get_audio_data
        return get_audio_data(self, rebuild)

    def get_video_data(self, rebuild: bool = False) -> List[Dict[str, Any]]:
        from .data_operations import get_video_data
        return get_video_data(self, rebuild)

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
        # Call before hook
        if not is_error():
            self._before_move_page(target_page_id)
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
            # Call after hook
            old_parent_id = original_parent if original_parent else 0
            self._after_move_page(old_parent_id, target_page_id)
            log(f"Successfully moved page {self.id} to parent {target_page_id}")
        trace_out()
        return not is_error()

    def move_media_items(self, media_type: str, item_instances: List[Dict[str, int]], target_rank: Optional[int] = None) -> bool:
        from .media_operations import move_media_items as move_media_items_impl
        return move_media_items_impl(self, media_type, item_instances, target_rank)

    def remove_media_item(self, media_type: str, item_id: int, item_rank: int) -> bool:
        from .media_operations import remove_media_item as remove_media_item_impl
        return remove_media_item_impl(self, media_type, item_id, item_rank)

    def modify_display_style(self, display_style: int) -> bool:
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
            # Gate through auto_link_name() first - only update link if this class supports auto-linking
            if self.auto_link_name():
                # Check if name == link to determine if we should update the link
                # This allows for linkless pages (name exists but link is NULL) even when auto_link_name() is True
                if self.name == self.link:
                    log(f"Page {self.id} has auto-link enabled (name == link), updating link as well")
                    link_value = name_value if name_value is not None else None
                    log(f"Setting link to: {link_value}")
                    # Only update if link_value is different from current link
                    if link_value != self.link:
                        affected = self.gateway.conn.update("UPDATE pages SET link = %s WHERE id = %s", (link_value, self.id))
                        if affected == 0:
                            warn(f"Failed to update page {self.id} link - no rows affected")
                            report_error("action", f"Failed to update page {self.id} link")
                        else:
                            self.link = link_value
                            log(f"Successfully updated page {self.id} link to '{link_value}'")
                    else:
                        log(f"Link unchanged for page {self.id}, skipping update")
                else:
                    log(f"Page {self.id} is linkless (name != link), skipping link update")
            else:
                log(f"Page {self.id} does not have auto-link enabled (auto_link_name() == False), skipping link update")
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
        trace_in()
        metadata = self._get_metadata_dict()
        metadata[key] = value
        result = self._write_metadata_dict(metadata)
        trace_out()
        return result

    def set_media_rank(self, media_type: str, item_id: int, current_rank: int, new_rank: int) -> bool:
        from .media_operations import set_media_rank as set_media_rank_impl
        return set_media_rank_impl(self, media_type, item_id, current_rank, new_rank)

    def show_page(self) -> Dict[str, Any]:
        from .data_operations import show_page
        return show_page(self)

    def validate_name(
        self,
        name: str,
        page_class: str,
        exclude_id: Optional[int] = None,
        error_on_invalid: bool = True,
    ) -> bool:
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
                log(f"[validate_name suppressed] {warn_msg}")
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

