"""
Video Quality Tiers

This file defines quality tiers for video processing.
The 'standard' tier is used by background maintenance tasks to transcode
original files to MP4 (H.264) format. Additional tiers can be created for
different quality levels.

Processing workflow:
1. Upload: Original file saved as 'full' instance (immediate)
2. Background task: Transcode to 'standard' MP4 (H.264) format (async)
3. Optional: Create additional quality tiers (async)
"""

from typing import Dict, Any

# Standard format for site: H.264 in MP4 container
VIDEO_STANDARD_FORMAT = 'h264'
VIDEO_STANDARD_EXTENSION = '.mp4'
VIDEO_STANDARD_MIME_TYPE = 'video/mp4'

VIDEO_QUALITY_TIERS: Dict[str, Dict[str, Any]] = {
    'standard': {
        'width': None,  # Keep original dimensions
        'height': None,
        'bitrate': 2500,  # kbps
        'format': 'h264',
        'container': 'mp4',
        'description': 'Standard MP4 (H.264) format for streaming (site default)'
    },
    'high': {
        'width': 1920,
        'height': 1080,
        'bitrate': 5000,  # kbps
        'format': 'h264',
        'container': 'mp4',
        'description': 'High quality MP4 (1080p)'
    },
    'medium': {
        'width': 1280,
        'height': 720,
        'bitrate': 2500,  # kbps
        'format': 'h264',
        'container': 'mp4',
        'description': 'Medium quality MP4 (720p)'
    },
    'low': {
        'width': 854,
        'height': 480,
        'bitrate': 1000,  # kbps
        'format': 'h264',
        'container': 'mp4',
        'description': 'Low quality MP4 (480p) for previews'
    }
}

# Minimum video duration in seconds (for validation)
MIN_VIDEO_DURATION: float = 0.1  # 100ms minimum
