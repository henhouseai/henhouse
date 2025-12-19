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

_audio_cache: Dict[int, Any] = {}


if TYPE_CHECKING:
    from hh.audio.audio import Audio


def get_audio(audio_id: int) -> Optional["Audio"]:
    """Get audio from hot cache or load from database. Audio.__init__() handles cache hydration."""
    trace_in()
    if not audio_id or audio_id <= 0:
        warn(f"Invalid audio ID: {audio_id}")
        report_error("action", f"Invalid audio ID: {audio_id}")
        trace_out()
        return None
    
    # Check hot cache first
    debug(f"Checking if audio {audio_id} is in hot cache")
    if audio_id in _audio_cache:
        cached_audio = _audio_cache[audio_id]
        log(f"Returning cached audio {audio_id}: '{cached_audio.caption}'")
        trace_out()
        return _audio_cache[audio_id]
    
    # Create audio instance (Audio.__init__() handles main DB load and cache hydration)
    from hh.audio.audio import Audio
    try:
        audio_instance = Audio(audio_id=audio_id)
        if audio_instance and not is_error():
            # Store in hot cache
            _audio_cache[audio_id] = audio_instance
            log(f"Retrieved audio {audio_id}: '{audio_instance.caption}'")
    except Exception as e:
        warn(f"Failed to create audio {audio_id}: {str(e)}")
        report_error("backend", f"Failed to create audio {audio_id}: {str(e)}")
        trace_out()
        return None
    
    trace_out()
    return audio_instance if not is_error() else None


def refresh_stale_audio_caches() -> None:
    """Refresh cache database for all audio in hot cache that have _cache_needs_refresh flag set.
    Called by gateway during commit process, after file operations but before database commit."""
    trace_in()
    
    if not _audio_cache:
        log("No audio in hot cache to refresh")
        trace_out()
        return
    
    refresh_count = 0
    for audio_id, audio_obj in list(_audio_cache.items()):
        if getattr(audio_obj, '_cache_needs_refresh', False):
            debug(f"Refreshing cache for audio {audio_id}")
            try:
                # Call the refresh method on the audio object
                # Audio uses self.gateway.conn which is already in a transaction
                if audio_obj._refresh_cached_audio():
                    refresh_count += 1
                    log(f"Successfully refreshed cache for audio {audio_id}")
                else:
                    warn(f"Failed to refresh cache for audio {audio_id}")
            except Exception as e:
                warn(f"Exception while refreshing cache for audio {audio_id}: {e}")
                report_error("cache_refresh", f"Failed to refresh cache for audio {audio_id}: {e}")
    
    if refresh_count > 0:
        log(f"Refreshed cache for {refresh_count} audio item(s) in hot cache")
    else:
        log("No audio in hot cache needed cache refresh")
    
    trace_out()
