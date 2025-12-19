"""
Video processing utilities.

Provides functions for validating and processing video files.
Uses ffprobe for metadata extraction and validation.
Uses ffmpeg for transcoding to standard MP4 (H.264) format.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import os
import datetime
import subprocess
import json
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.system.dependency import register_dependency

# Register dependencies
_ffmpeg_available = False
_ffprobe_available = False

@register_dependency("ffmpeg")
def _check_ffmpeg():
    global _ffmpeg_available
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        _ffmpeg_available = (result.returncode == 0)
        return _ffmpeg_available
    except (FileNotFoundError, subprocess.TimeoutExpired):
        _ffmpeg_available = False
        return False

@register_dependency("ffprobe")
def _check_ffprobe():
    global _ffprobe_available
    try:
        result = subprocess.run(['ffprobe', '-version'], capture_output=True, timeout=5)
        _ffprobe_available = (result.returncode == 0)
        return _ffprobe_available
    except (FileNotFoundError, subprocess.TimeoutExpired):
        _ffprobe_available = False
        return False

_check_ffmpeg()
_check_ffprobe()

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


def validate_video_file(file_path: str) -> bool:
    """Validate that a file is a valid video file by attempting to probe it with ffprobe."""
    trace_in()
    if not _ffprobe_available:
        warn("ffprobe not available, skipping video validation")
        trace_out()
        return True  # Don't fail if tool not available
    
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'stream=codec_type',
            '-of', 'json',
            file_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if result.returncode != 0:
            warn(f"ffprobe failed: {result.stderr}")
            log(f"Video validation FAILED: ffprobe error - {file_path}")
            trace_out()
            return False
        
        try:
            data = json.loads(result.stdout)
            streams = data.get('streams', [])
            has_video = any(s.get('codec_type') == 'video' for s in streams)
            
            if not has_video:
                warn(f"No video stream found: {file_path}")
                log(f"Video validation FAILED: No video stream - {file_path}")
                trace_out()
                return False
            
            log(f"Video validation PASSED: {file_path}")
            trace_out()
            return True
        except json.JSONDecodeError:
            warn(f"Failed to parse ffprobe output: {file_path}")
            log(f"Video validation FAILED: Invalid ffprobe output - {file_path}")
            trace_out()
            return False
    except subprocess.TimeoutExpired:
        warn(f"ffprobe timeout validating {file_path}")
        log(f"Video validation FAILED: Timeout - {file_path}")
        trace_out()
        return False
    except Exception as e:
        warn(f"Failed to validate video file {file_path}: {str(e)}")
        log(f"Video validation FAILED: {file_path} - {str(e)}")
        trace_out()
        return False


def get_video_info(file_path: str) -> Optional[Dict[str, Any]]:
    """Extract video metadata using ffprobe."""
    trace_in()
    if not _ffprobe_available:
        warn("ffprobe not available")
        trace_out()
        return None
    
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'stream=width,height,duration,bit_rate:format=duration,size,bit_rate',
            '-of', 'json',
            file_path
        ]
        
        proc_result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        if proc_result.returncode != 0:
            warn(f"ffprobe failed: {proc_result.stderr}")
            trace_out()
            return None
        
        data = json.loads(proc_result.stdout)
        streams = data.get('streams', [])
        format_info = data.get('format', {})
        
        # Find video stream
        video_stream = next((s for s in streams if s.get('codec_type') == 'video'), None)
        
        if not video_stream:
            trace_out()
            return None
        
        # Get duration from format or stream
        duration = format_info.get('duration') or video_stream.get('duration')
        if duration:
            try:
                duration = float(duration)
            except (ValueError, TypeError):
                duration = None
        
        # Get bitrate from format or stream
        bitrate = format_info.get('bit_rate') or video_stream.get('bit_rate')
        if bitrate:
            try:
                bitrate = int(bitrate) // 1000  # Convert to kbps
            except (ValueError, TypeError):
                bitrate = None
        
        result = {
            'width': video_stream.get('width'),
            'height': video_stream.get('height'),
            'duration_seconds': duration,
            'bitrate': bitrate,
            'filesize': Path(file_path).stat().st_size
        }
        
        log(f"Successfully retrieved video info: {file_path} -> {result['width']}x{result['height']}, duration={result['duration_seconds']}s, bitrate={result['bitrate']}kbps, {result['filesize']} bytes")
        trace_out()
        return result
    except subprocess.TimeoutExpired:
        warn(f"ffprobe timeout getting info for {file_path}")
        trace_out()
        return None
    except Exception as e:
        warn(f"Failed to get video info for {file_path}: {str(e)}")
        log(f"Video info retrieval FAILED: {file_path} - {str(e)}")
        trace_out()
        return None


def create_date_directory(base_path: Path) -> Optional[Path]:
    """Create date-based directory structure (YYYY/MM/DD)."""
    trace_in()
    now = datetime.datetime.now()
    date_path = base_path / str(now.year) / str(now.month) / str(now.day)
    
    try:
        if date_path.exists():
            log(f"Date directory already exists: {date_path}")
            trace_out()
            return date_path
        
        date_path.mkdir(parents=True, exist_ok=True)
        os.chmod(date_path, 0o774)
        log(f"Successfully created date directory: {date_path} (permissions: 0o774)")
        trace_out()
        return date_path
    except Exception as e:
        error_msg = f"Failed to create date directory: {date_path}"
        warn(error_msg)
        log(f"Date directory creation FAILED: {base_path} -> {error_msg} - {str(e)}")
        trace_out()
        raise Exception(error_msg) from e


def transcode_to_mp4(source_path: str, destination_path: str, width: Optional[int] = None, height: Optional[int] = None, bitrate: int = 2500) -> bool:
    """Transcode video file to MP4 (H.264) format using ffmpeg.
    
    Args:
        source_path: Path to source video file
        destination_path: Path to output MP4 file
        width: Target width (None = keep aspect ratio, scale height)
        height: Target height (None = keep aspect ratio, scale width)
        bitrate: Target bitrate in kbps (default: 2500)
    
    Returns:
        True if successful, False otherwise
    """
    trace_in()
    if not _ffmpeg_available:
        warn("ffmpeg not available, cannot transcode")
        trace_out()
        return False
    
    try:
        # Ensure destination directory exists
        dest_dir = Path(destination_path).parent
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Build ffmpeg command: convert to H.264 in MP4 container
        cmd = [
            'ffmpeg',
            '-i', source_path,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',  # Good quality/size balance
            '-c:a', 'aac',
            '-b:a', '128k',  # Audio bitrate
            '-movflags', '+faststart',  # Enable streaming
            '-y',  # Overwrite output file
        ]
        
        # Add video scaling if dimensions specified
        if width or height:
            scale_filter = []
            if width and height:
                scale_filter.append(f'scale={width}:{height}')
            elif width:
                scale_filter.append(f'scale={width}:-1')  # Keep aspect ratio
            elif height:
                scale_filter.append(f'scale=-1:{height}')  # Keep aspect ratio
            
            if scale_filter:
                cmd.extend(['-vf', ','.join(scale_filter)])
        
        # Override bitrate if specified
        if bitrate:
            cmd.extend(['-b:v', f'{bitrate}k'])
        
        cmd.append(destination_path)
        
        log(f"Transcoding video: {source_path} -> {destination_path} (H.264 {width}x{height if height else 'auto'} {bitrate}kbps)")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minute timeout for video
        )
        
        if result.returncode != 0:
            warn(f"ffmpeg failed: {result.stderr}")
            log(f"Video transcoding FAILED: {source_path} -> {destination_path} - {result.stderr}")
            trace_out()
            return False
        
        if not Path(destination_path).exists():
            warn(f"Transcoded file not created: {destination_path}")
            log(f"Video transcoding FAILED: Output file missing - {destination_path}")
            trace_out()
            return False
        
        os.chmod(destination_path, 0o664)
        file_size = Path(destination_path).stat().st_size
        log(f"Video transcoding COMPLETED: {source_path} -> {destination_path} ({file_size} bytes, H.264 {bitrate}kbps)")
        trace_out()
        return True
    except subprocess.TimeoutExpired:
        warn(f"ffmpeg timeout transcoding {source_path}")
        log(f"Video transcoding FAILED: Timeout - {source_path}")
        trace_out()
        return False
    except Exception as e:
        warn(f"Failed to transcode video {source_path}: {str(e)}")
        log(f"Video transcoding FAILED: {source_path} -> {destination_path} - {str(e)}")
        trace_out()
        return False
