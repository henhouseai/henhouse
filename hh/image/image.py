from typing import Dict, Any, List, Optional
import datetime as dt
from hh.gateway.gateway import get_gateway
from hh.gateway.connection.utils import deserialize_json_blob, normalize_datetime
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.image.image_validation import ImageValidationMixin
from hh.image.image_content import ImageContentMixin
from hh.image.image_instances import ImageInstancesMixin
from hh.image.image_usage import ImageUsageMixin
from hh.image.image_display import ImageDisplayMixin
from hh.image.image_cache import ImageCacheMixin

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


class Image(
    ImageValidationMixin,
    ImageContentMixin,
    ImageInstancesMixin,
    ImageUsageMixin,
    ImageDisplayMixin,
    ImageCacheMixin,
):

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
            log(f"Loaded image {image_id}: {self.caption}")
            
            # Try to hydrate from cache database if available and fresh
            if not is_error():
                # Check if cache exists and is fresh
                cache_built_at_dt = normalize_datetime(self.cache_built_at)
                last_modified_dt = normalize_datetime(self.last_modified)
                
                if last_modified_dt and cache_built_at_dt and cache_built_at_dt < last_modified_dt:
                    debug(f"Cache for image {self.id} is stale (cache_built_at={cache_built_at_dt}, last_modified={last_modified_dt})")
                elif cache_built_at_dt is None:
                    debug(f"Cache for image {self.id} does not exist (cache_built_at is NULL)")
                else:
                    # Get cache row from cache database
                    cache_query = """
                        SELECT id, instances, pages, cache_built_at
                        FROM images
                        WHERE id = %s
                    """
                    try:
                        cache_results = self.gateway.conn.read_cache(cache_query, [self.id])
                        if cache_results:
                            cache_row = cache_results[0]
                            # Load expensive pre-computed data from cache database directly into live fields
                            self.instances = deserialize_json_blob(cache_row.get('instances'), [])
                            # Use cached_usage for now to match existing code, but this should be renamed to pages
                            self.cached_usage = deserialize_json_blob(cache_row.get('pages'), [])
                            self.cache_hydrated = True
                            debug(f"Hydrated image {self.id} from cache (built_at={self.cache_built_at})")
                    except Exception as e:
                        warn(f"Failed to hydrate image {self.id} from cache: {e}")
                        # Don't report error - cache hydration failure is not critical
        except Exception as e:
            warn(f"Failed to load image {image_id}: {e}")
            report_error("connection", f"Failed to load image {image_id}: {e}")
        
        trace_out()
