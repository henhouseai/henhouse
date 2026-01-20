"""
Audio Quality Tiers

This file defines quality tiers for audio processing.
The 'standard' tier is used by background maintenance tasks to transcode
original files to AAC format. Additional tiers can be created for different
quality levels.

Processing workflow:
1. Upload: Original file saved as 'full' instance (immediate)
2. Background task: Transcode to 'standard' AAC format (async)
3. Optional: Create additional quality tiers (async)
"""

from typing import Dict, Any

# Standard format for site: AAC in M4A container
AUDIO_STANDARD_FORMAT = 'aac'
AUDIO_STANDARD_EXTENSION = '.m4a'
AUDIO_STANDARD_MIME_TYPE = 'audio/mp4'

AUDIO_QUALITY_TIERS: Dict[str, Dict[str, Any]] = {
    'standard': {
        'bitrate': 192,  # kbps
        'format': 'aac',
        'container': 'm4a',
        'description': 'Standard AAC format for streaming (site default)'
    },
    'high': {
        'bitrate': 320,  # kbps
        'format': 'aac',
        'container': 'm4a',
        'description': 'High quality AAC audio'
    },
    'medium': {
        'bitrate': 192,  # kbps
        'format': 'aac',
        'container': 'm4a',
        'description': 'Medium quality AAC for streaming'
    },
    'low': {
        'bitrate': 128,  # kbps
        'format': 'aac',
        'container': 'm4a',
        'description': 'Low quality AAC for previews'
    }
}

# Minimum audio duration in seconds (for validation)
MIN_AUDIO_DURATION: float = 0.1  # 100ms minimum
