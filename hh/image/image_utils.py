from pathlib import Path
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import os
import datetime
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.system.dependency import register_dependency

if TYPE_CHECKING:
    from PIL import Image as PILImage

# Register pillow as a dependency
Image = None
ImageOps = None

@register_dependency("pillow")
def _load_pillow():
    global Image, ImageOps
    try:
        from PIL import Image as _Image, ImageOps as _ImageOps
        Image = _Image
        ImageOps = _ImageOps
        return True
    except ImportError:
        return False

_load_pillow()

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

def load_image(file_path: str) -> Optional["PILImage.Image"]:
    trace_in()
    if Image is None:
        warn("Image is None")
        trace_out()
        return None
    try:
        img = Image.open(file_path)
        original_mode = img.mode
        # Convert to RGB if needed (for PNG/GIF)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        width, height = img.size
        log(f"Successfully loaded image: {file_path} -> {width}x{height} pixels, mode: {original_mode}->{img.mode}")
        trace_out()
        return img
    except Exception as e:
        warn(f"Failed to load image {file_path}: {str(e)}")
        log(f"Image load failed: {file_path} - {str(e)}")
        trace_out()
        return None


def validate_image_size(img: "PILImage.Image", min_width: int = 300) -> bool:
    trace_in()
    width, height = img.size
    if width < min_width:
        warn(f"Image too small: {width}x{height} (min width: {min_width})")
        log(f"Size validation FAILED: {width}x{height} < {min_width} minimum width")
        trace_out()
        return False
    log(f"Size validation PASSED: {width}x{height} >= {min_width} minimum width")
    trace_out()
    return True


def create_date_directory(base_path: Path) -> Optional[Path]:
    trace_in()
    now = datetime.datetime.now()
    date_path = base_path / str(now.year) / str(now.month) / str(now.day)
    
    try:
        # Check if directory already exists - if so, skip mkdir (which can fail even with exist_ok=True
        # when directory was created by a different user)
        if date_path.exists():
            log(f"Date directory already exists: {date_path}")
            trace_out()
            return date_path
        
        date_path.mkdir(parents=True, exist_ok=True)
        # Set proper permissions
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


def calculate_target_height(img: "PILImage.Image", target_width: int) -> int:
    trace_in()
    if Image is None:
        warn("Image is None")
        trace_out()
        return 0
    width, height = img.size
    result = int(height * target_width / width)
    log(f"Calculated target height: {width}x{height} -> {target_width}x{result} (aspect ratio: {width/height:.3f})")
    trace_out()
    return result


def scale_image(img: "PILImage.Image", target_width: int, target_height: int) -> Optional["PILImage.Image"]:
    trace_in()
    if Image is None:
        warn("Image is None")
        trace_out()
        return None
    try:
        original_width, original_height = img.size
        scaled = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        log(f"Successfully scaled image: {original_width}x{original_height} -> {target_width}x{target_height} (LANCZOS resampling)")
        trace_out()
        return scaled
    except Exception as e:
        warn(f"Failed to scale image: {str(e)}")
        log(f"Image scaling FAILED: {img.size} -> {target_width}x{target_height} - {str(e)}")
        trace_out()
        return None


def write_jpg(img: "PILImage.Image", filepath: Path, quality: int = 80) -> bool:
    trace_in()
    if Image is None:
        warn("Image is None")
        trace_out()
        return False
    try:
        img.save(filepath, 'JPEG', quality=quality, optimize=True)
        os.chmod(filepath, 0o664)
        file_size = filepath.stat().st_size
        width, height = img.size
        log(f"Successfully wrote JPEG: {filepath} -> {width}x{height} pixels, {file_size} bytes, quality={quality}, permissions=0o664")
        trace_out()
        return True
    except Exception as e:
        warn(f"Failed to write image {filepath}: {str(e)}")
        log(f"JPEG write FAILED: {filepath} (quality={quality}) - {str(e)}")
        trace_out()
        return False


def cleanup_unused_files(file_paths: List[str], base_path: Path) -> int:
    trace_in()
    cleaned = 0
    total_files = len(file_paths)
    for file_path in file_paths:
        full_path = base_path / file_path
        if full_path.exists():
            try:
                full_path.unlink()
                cleaned += 1
                log(f"Cleaned up unused file: {file_path}")
            except Exception as e:
                warn(f"Failed to cleanup file {file_path}: {str(e)}")
    log(f"Cleanup completed: {cleaned}/{total_files} files removed from {base_path}")
    trace_out()
    return cleaned


def get_image_info(file_path: str) -> Optional[Dict[str, Any]]:
    trace_in()
    if Image is None:
        warn("Image is None")
        trace_out()
        return None
    try:
        with Image.open(file_path) as img:
            result = {
                'width': img.size[0],
                'height': img.size[1],
                'format': img.format,
                'mode': img.mode,
                'filesize': Path(file_path).stat().st_size
            }
        log(f"Successfully retrieved image info: {file_path} -> {result['width']}x{result['height']} {result['format']} ({result['mode']}), {result['filesize']} bytes")
        trace_out()
        return result
    except Exception as e:
        warn(f"Failed to get image info for {file_path}: {str(e)}")
        log(f"Image info retrieval FAILED: {file_path} - {str(e)}")
        trace_out()
        return None
