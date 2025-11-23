from __future__ import annotations

from typing import Optional, Dict, Any
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error

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

_file_cache: Dict[int, Any] = {}


def get_file(file_id: int) -> Optional["File"]:
    """Get file from hot cache or load from database. File.__init__() handles cache hydration."""
    trace_in()
    if not file_id or file_id <= 0:
        warn(f"Invalid file ID: {file_id}")
        report_error("action", f"Invalid file ID: {file_id}")
        trace_out()
        return None
    
    # Check hot cache first
    debug(f"Checking if file {file_id} is in hot cache")
    if file_id in _file_cache:
        cached_file = _file_cache[file_id]
        log(f"Returning cached file {file_id}: '{cached_file.file_name}'")
        trace_out()
        return _file_cache[file_id]
    
    # Create file instance (File.__init__() handles main DB load and cache hydration)
    from hh.file.file import File
    try:
        file_instance = File(file_id=file_id)
        if file_instance and not is_error():
            # Store in hot cache
            _file_cache[file_id] = file_instance
            log(f"Retrieved file {file_id}: '{file_instance.file_name}'")
    except Exception as e:
        warn(f"Failed to create file {file_id}: {str(e)}")
        report_error("backend", f"Failed to create file {file_id}: {str(e)}")
        trace_out()
        return None
    
    trace_out()
    return file_instance if not is_error() else None


def refresh_stale_file_caches() -> None:
    """Refresh cache database for all files in hot cache that have _cache_needs_refresh flag set.
    Called by gateway during commit process, after file operations but before database commit."""
    trace_in()
    
    if not _file_cache:
        log("No files in hot cache to refresh")
        trace_out()
        return
    
    refresh_count = 0
    # Iterate over a copy of items to prevent "dictionary changed size during iteration" error
    for file_id, file_obj in list(_file_cache.items()): 
        if getattr(file_obj, '_cache_needs_refresh', False):
            debug(f"Refreshing cache for file {file_id}")
            try:
                # Call the refresh method on the file object
                # File uses self.gateway.conn which is already in a transaction
                if file_obj._refresh_cached_file():
                    refresh_count += 1
                    log(f"Successfully refreshed cache for file {file_id}")
                else:
                    warn(f"Failed to refresh cache for file {file_id}")
            except Exception as e:
                warn(f"Exception while refreshing cache for file {file_id}: {e}")
                report_error("cache_refresh", f"Failed to refresh cache for file {file_id}: {e}")
    
    if refresh_count > 0:
        log(f"Refreshed cache for {refresh_count} file(s) in hot cache")
    else:
        log("No files in hot cache needed cache refresh")
    
    trace_out()

