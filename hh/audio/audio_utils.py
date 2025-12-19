"""
Audio processing utilities.

Provides functions for validating and processing audio files.
Uses mutagen for metadata extraction and validation.
Uses ffmpeg for transcoding to standard AAC format.
"""

from pathlib import Path
from typing import Optional, Dict, Any, TYPE_CHECKING
import os
import datetime
import subprocess
import shutil
from uuid import uuid4
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.system.dependency import register_dependency

if TYPE_CHECKING:
    from mutagen import File as MutagenFile

# Register dependencies
MutagenFile = None
_ffmpeg_available = False

@register_dependency("mutagen")
def _load_mutagen():
    global MutagenFile
    try:
        from mutagen import File as _MutagenFile
        MutagenFile = _MutagenFile
        return True
    except ImportError:
        return False

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

_load_mutagen()
_check_ffmpeg()

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


def validate_audio_file(file_path: str) -> bool:
    """Validate that a file is a valid audio file by attempting to load it with mutagen."""
    trace_in()
    if MutagenFile is None:
        warn("mutagen not available, skipping audio validation")
        trace_out()
        return True  # Don't fail if library not available
    
    try:
        audio_file = MutagenFile(file_path)
        if audio_file is None:
            warn(f"Failed to load audio file: {file_path}")
            log(f"Audio validation FAILED: Could not load with mutagen - {file_path}")
            trace_out()
            return False
        
        # Check if file has audio properties
        if not hasattr(audio_file, 'info') or audio_file.info is None:
            warn(f"Audio file has no info: {file_path}")
            log(f"Audio validation FAILED: No audio info - {file_path}")
            trace_out()
            return False
        
        log(f"Audio validation PASSED: {file_path}")
        trace_out()
        return True
    except Exception as e:
        warn(f"Failed to validate audio file {file_path}: {str(e)}")
        log(f"Audio validation FAILED: {file_path} - {str(e)}")
        trace_out()
        return False


def get_audio_info(file_path: str) -> Optional[Dict[str, Any]]:
    """Extract audio metadata using mutagen."""
    trace_in()
    if MutagenFile is None:
        warn("mutagen not available")
        trace_out()
        return None
    
    try:
        audio_file = MutagenFile(file_path)
        if audio_file is None or audio_file.info is None:
            trace_out()
            return None
        
        info = audio_file.info
        result = {
            'duration_seconds': getattr(info, 'length', None),
            'bitrate': getattr(info, 'bitrate', None),
            'channels': getattr(info, 'channels', None),
            'sample_rate': getattr(info, 'sample_rate', None),
            'filesize': Path(file_path).stat().st_size
        }
        
        log(f"Successfully retrieved audio info: {file_path} -> duration={result['duration_seconds']}s, bitrate={result['bitrate']}, {result['filesize']} bytes")
        trace_out()
        return result
    except Exception as e:
        warn(f"Failed to get audio info for {file_path}: {str(e)}")
        log(f"Audio info retrieval FAILED: {file_path} - {str(e)}")
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


def transcode_to_aac(source_path: str, destination_path: str, bitrate: int = 192) -> bool:
    """Transcode audio file to AAC format using ffmpeg.
    
    Args:
        source_path: Path to source audio file
        destination_path: Path to output AAC (.m4a) file
        bitrate: Target bitrate in kbps (default: 192)
    
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
        
        # Build ffmpeg command: convert to AAC in M4A container
        cmd = [
            'ffmpeg',
            '-i', source_path,
            '-c:a', 'aac',
            '-b:a', f'{bitrate}k',
            '-y',  # Overwrite output file
            destination_path
        ]
        
        log(f"Transcoding audio: {source_path} -> {destination_path} (AAC {bitrate}kbps)")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        
        if result.returncode != 0:
            warn(f"ffmpeg failed: {result.stderr}")
            log(f"Audio transcoding FAILED: {source_path} -> {destination_path} - {result.stderr}")
            trace_out()
            return False
        
        if not Path(destination_path).exists():
            warn(f"Transcoded file not created: {destination_path}")
            log(f"Audio transcoding FAILED: Output file missing - {destination_path}")
            trace_out()
            return False
        
        os.chmod(destination_path, 0o664)
        file_size = Path(destination_path).stat().st_size
        log(f"Audio transcoding COMPLETED: {source_path} -> {destination_path} ({file_size} bytes, AAC {bitrate}kbps)")
        trace_out()
        return True
    except subprocess.TimeoutExpired:
        warn(f"ffmpeg timeout transcoding {source_path}")
        log(f"Audio transcoding FAILED: Timeout - {source_path}")
        trace_out()
        return False
    except Exception as e:
        warn(f"Failed to transcode audio {source_path}: {str(e)}")
        log(f"Audio transcoding FAILED: {source_path} -> {destination_path} - {str(e)}")
        trace_out()
        return False
