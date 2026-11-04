"""
Media type registry for dynamic media module discovery.

Allows media modules (audio, hh_image, video, file) to register their cache
refresh functions and deletion metadata via decorators, enabling the gateway
to refresh caches and perform cleanup for all active media types without hard imports.
"""

from typing import Dict, Any, Callable, Optional

# Storage for registered media types
_media_types: Dict[str, Dict[str, Any]] = {}

def register_media_type(
    media_type: str,
    groups_table: str,
    get_func: Callable,
    flag_modification_method: str
):
    """
    Decorator to register a media type with its metadata and functions.

    Usage in media module (e.g., image/image_registry.py):
        @register_media_type(
            media_type='image',
            groups_table='image_groups',
            get_func=get_image,
            flag_modification_method='flag_image_modification'
        )
        def refresh_stale_image_caches():
            # implementation

    Args:
        media_type: Type identifier ('audio', 'image', 'video', 'file')
        groups_table: Name of the groups table (e.g., 'image_groups')
        get_func: Function to load media object by ID (e.g., get_image)
        flag_modification_method: Name of method to flag cache as stale (e.g., 'flag_image_modification')
    """
    def decorator(func: Callable) -> Callable:
        _media_types[media_type] = {
            'refresh_cache_func': func,
            'media_type': media_type,
            'groups_table': groups_table,
            'get_func': get_func,
            'flag_modification_method': flag_modification_method,
            'id_column': f'{media_type}_id'  # Derive column name from media type
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
