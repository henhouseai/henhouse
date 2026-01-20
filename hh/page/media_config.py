"""
Media type configuration for page caching.

Maps media registry types to their page attributes and data accessors.
When new media types are added, register them here.
"""

from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from hh.page.page import Page

# Import getters lazily to avoid circular imports
def _get_media_type_config() -> Dict[str, Dict[str, Any]]:
    from .data_operations import (
        get_images_data,
        get_files_data,
        get_audio_data,
        get_video_data
    )

    return {
        'image': {
            'attribute': 'images',
            'getter': get_images_data
        },
        'file': {
            'attribute': 'files',
            'getter': get_files_data
        },
        'audio': {
            'attribute': 'audio',
            'getter': get_audio_data
        },
        'video': {
            'attribute': 'video',
            'getter': get_video_data
        }
    }

MEDIA_TYPE_CONFIG = None

def get_media_config() -> Dict[str, Dict[str, Any]]:
    """Get media type configuration, initialized lazily."""
    global MEDIA_TYPE_CONFIG
    if MEDIA_TYPE_CONFIG is None:
        MEDIA_TYPE_CONFIG = _get_media_type_config()
    return MEDIA_TYPE_CONFIG
