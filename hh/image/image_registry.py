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

_image_cache: Dict[int, Any] = {}


def get_image(image_id: int) -> Optional["Image"]:
    """Get image from hot cache or load from database. Image.__init__() handles cache hydration."""
    trace_in()
    if not image_id or image_id <= 0:
        warn(f"Invalid image ID: {image_id}")
        report_error("action", f"Invalid image ID: {image_id}")
        trace_out()
        return None
    
    # Check hot cache first
    debug(f"Checking if image {image_id} is in hot cache")
    if image_id in _image_cache:
        cached_image = _image_cache[image_id]
        log(f"Returning cached image {image_id}: '{cached_image.caption}'")
        trace_out()
        return _image_cache[image_id]
    
    # Create image instance (Image.__init__() handles main DB load and cache hydration)
    from hh.image.image import Image
    try:
        image_instance = Image(image_id=image_id)
        if image_instance and not is_error():
            # Store in hot cache
            _image_cache[image_id] = image_instance
            log(f"Retrieved image {image_id}: '{image_instance.caption}'")
    except Exception as e:
        warn(f"Failed to create image {image_id}: {str(e)}")
        report_error("backend", f"Failed to create image {image_id}: {str(e)}")
        trace_out()
        return None
    
    trace_out()
    return image_instance if not is_error() else None


def refresh_stale_image_caches() -> None:
    """Refresh cache database for all images in hot cache that have _cache_needs_refresh flag set.
    Called by gateway during commit process, after file operations but before database commit."""
    trace_in()
    
    if not _image_cache:
        log("No images in hot cache to refresh")
        trace_out()
        return
    
    refresh_count = 0
    for image_id, image_obj in list(_image_cache.items()):
        if getattr(image_obj, '_cache_needs_refresh', False):
            debug(f"Refreshing cache for image {image_id}")
            try:
                # Call the refresh method on the image object
                # Image uses self.gateway.conn which is already in a transaction
                if image_obj._refresh_cached_image():
                    refresh_count += 1
                    log(f"Successfully refreshed cache for image {image_id}")
                else:
                    warn(f"Failed to refresh cache for image {image_id}")
            except Exception as e:
                warn(f"Exception while refreshing cache for image {image_id}: {e}")
                report_error("cache_refresh", f"Failed to refresh cache for image {image_id}: {e}")
    
    if refresh_count > 0:
        log(f"Refreshed cache for {refresh_count} image(s) in hot cache")
    else:
        log("No images in hot cache needed cache refresh")
    
    trace_out()
