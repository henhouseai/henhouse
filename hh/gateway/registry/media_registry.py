"""
Media type registry for dynamic media module discovery.

Allows media modules (audio, hh_image, video, file) to register their cache
refresh functions via decorators, enabling the gateway to refresh caches for
all active media types without hard imports.
"""

from typing import Dict, Any, Callable

# Storage for registered media types
_media_types: Dict[str, Dict[str, Any]] = {}

def register_media_type(media_type: str):
    """
    Decorator to register a media type with its cache refresh function.

    Usage in media module (e.g., audio/audio_registry.py):
        @register_media_type('audio')
        def refresh_stale_audio_caches():
            # implementation

    Args:
        media_type: Type identifier ('audio', 'image', 'video', 'file')
    """
    def decorator(func: Callable) -> Callable:
        _media_types[media_type] = {
            'refresh_cache_func': func,
            'media_type': media_type
        }
        return func
    return decorator

def get_registered_media_types() -> Dict[str, Dict[str, Any]]:
    """Get all registered media types."""
    return _media_types.copy()

def refresh_all_media_caches() -> None:
    """Refresh caches for all registered media types that are enabled."""
    for media_type, info in _media_types.items():
        refresh_func = info['refresh_cache_func']
        refresh_func()
