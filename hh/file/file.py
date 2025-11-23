from typing import Dict, Any, List, Optional
import datetime as dt
from hh.gateway.gateway import get_gateway
from hh.gateway.connection.utils import deserialize_json_blob, normalize_datetime
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.file.file_content import FileContentMixin
from hh.file.file_cache import FileCacheMixin

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


class File(FileContentMixin, FileCacheMixin):

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
            log(f"Loaded file {file_id}: {self.file_name}")
            
            # Try to hydrate from cache database if available and fresh
            if not is_error():
                cache_built_at_dt = normalize_datetime(self.cache_built_at)
                last_modified_dt = normalize_datetime(self.last_modified)
                
                if last_modified_dt and cache_built_at_dt and cache_built_at_dt < last_modified_dt:
                    debug(f"Cache for file {self.id} is stale (cache_built_at={cache_built_at_dt}, last_modified={last_modified_dt})")
                elif cache_built_at_dt is None:
                    debug(f"Cache for file {self.id} does not exist (cache_built_at is NULL)")
                else:
                    cache_query = """
                        SELECT id, pages, cache_built_at
                        FROM files
                        WHERE id = %s
                    """
                    try:
                        cache_results = self.gateway.conn.read_cache(cache_query, [self.id])
                        if cache_results:
                            cache_row = cache_results[0]
                            self.pages = deserialize_json_blob(cache_row.get('pages'), [])
                            self.cache_hydrated = True
                            debug(f"Hydrated file {self.id} from cache (built_at={self.cache_built_at})")
                    except Exception as e:
                        warn(f"Failed to hydrate file {self.id} from cache: {e}")
        except Exception as e:
            warn(f"Failed to load file {file_id}: {e}")
            report_error("connection", f"Failed to load file {file_id}: {e}")
        
        trace_out()
