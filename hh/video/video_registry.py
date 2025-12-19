from __future__ import annotations

from typing import Optional, Dict, Any, TYPE_CHECKING
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

_video_cache: Dict[int, Any] = {}


if TYPE_CHECKING:
    from hh.video.video import Video


def get_video(video_id: int) -> Optional["Video"]:
    """Get video from hot cache or load from database. Video.__init__() handles cache hydration."""
    trace_in()
    if not video_id or video_id <= 0:
        warn(f"Invalid video ID: {video_id}")
        report_error("action", f"Invalid video ID: {video_id}")
        trace_out()
        return None
    
    # Check hot cache first
    debug(f"Checking if video {video_id} is in hot cache")
    if video_id in _video_cache:
        cached_video = _video_cache[video_id]
        log(f"Returning cached video {video_id}: '{cached_video.caption}'")
        trace_out()
        return _video_cache[video_id]
    
    # Create video instance (Video.__init__() handles main DB load and cache hydration)
    from hh.video.video import Video
    try:
        video_instance = Video(video_id=video_id)
        if video_instance and not is_error():
            # Store in hot cache
            _video_cache[video_id] = video_instance
            log(f"Retrieved video {video_id}: '{video_instance.caption}'")
    except Exception as e:
        warn(f"Failed to create video {video_id}: {str(e)}")
        report_error("backend", f"Failed to create video {video_id}: {str(e)}")
        trace_out()
        return None
    
    trace_out()
    return video_instance if not is_error() else None


def refresh_stale_video_caches() -> None:
    """Refresh cache database for all video in hot cache that have _cache_needs_refresh flag set.
    Called by gateway during commit process, after file operations but before database commit."""
    trace_in()
    
    if not _video_cache:
        log("No video in hot cache to refresh")
        trace_out()
        return
    
    refresh_count = 0
    for video_id, video_obj in list(_video_cache.items()):
        if getattr(video_obj, '_cache_needs_refresh', False):
            debug(f"Refreshing cache for video {video_id}")
            try:
                # Call the refresh method on the video object
                # Video uses self.gateway.conn which is already in a transaction
                if video_obj._refresh_cached_video():
                    refresh_count += 1
                    log(f"Successfully refreshed cache for video {video_id}")
                else:
                    warn(f"Failed to refresh cache for video {video_id}")
            except Exception as e:
                warn(f"Exception while refreshing cache for video {video_id}: {e}")
                report_error("cache_refresh", f"Failed to refresh cache for video {video_id}: {e}")
    
    if refresh_count > 0:
        log(f"Refreshed cache for {refresh_count} video item(s) in hot cache")
    else:
        log("No video in hot cache needed cache refresh")
    
    trace_out()
