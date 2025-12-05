from typing import Dict, Any, List, Optional
import json
import datetime as dt
from hh.gateway.gateway import get_gateway
from hh.gateway.connection.utils import deserialize_json_blob, normalize_datetime
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_validation import PageValidationMixin
from hh.page.page_hierarchy import PageHierarchyMixin
from hh.page.page_content import PageContentMixin
from hh.page.page_maintenance import PageMaintenanceMixin
from hh.page.page_images import PageImagesMixin
from hh.page.page_files import PageFilesMixin
from hh.page.page_display import PageDisplayMixin
from hh.page.page_ajax import PageAjaxMixin
from hh.page.page_cache import PageCacheMixin
from hh.page.page_class_registry import register_page_class

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
class Page(
    PageValidationMixin,
    PageHierarchyMixin,
    PageContentMixin,
    PageMaintenanceMixin,
    PageFilesMixin,
    PageImagesMixin,
    PageDisplayMixin,
    PageAjaxMixin,
    PageCacheMixin,
):

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

