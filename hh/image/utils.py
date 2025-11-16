from PIL import Image, ImageOps
from pathlib import Path
from typing import Optional, List, Dict, Any
import os
import datetime
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

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

def load_image(file_path: str) -> Optional[Image.Image]:
    trace_in()
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


def validate_image_size(img: Image.Image, min_width: int = 300) -> bool:
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
    
    # ===== DEBUG CODE START: Detailed error message for directory creation failures =====
    # TODO: Remove this debug code after tracking down permission issues
    # Get current user/group info for debugging (before try block so available in except)
    import pwd
    import grp
    try:
        current_uid = os.getuid()
        current_gid = os.getgid()
        user_info = pwd.getpwuid(current_uid)
        group_info = grp.getgrgid(current_gid)
        user_str = f"{user_info.pw_name} (uid:{current_uid})"
        group_str = f"{group_info.gr_name} (gid:{current_gid})"
    except Exception:
        try:
            user_str = f"uid:{os.getuid()}"
            group_str = f"gid:{os.getgid()}"
        except Exception:
            user_str = "unknown"
            group_str = "unknown"
    # ===== DEBUG CODE END =====
    
    try:
        # ===== DEBUG CODE START: Check parent directory permissions =====
        parent_path = date_path.parent
        parent_exists = parent_path.exists()
        parent_perms = None
        parent_owner = None
        parent_group = None
        if parent_exists:
            try:
                stat_info = parent_path.stat()
                parent_perms = oct(stat_info.st_mode)[-3:]
                try:
                    parent_owner = pwd.getpwuid(stat_info.st_uid).pw_name
                except:
                    parent_owner = f"uid:{stat_info.st_uid}"
                try:
                    parent_group = grp.getgrgid(stat_info.st_gid).gr_name
                except:
                    parent_group = f"gid:{stat_info.st_gid}"
            except Exception:
                pass
        # ===== DEBUG CODE END =====
        
        date_path.mkdir(parents=True, exist_ok=True)
        # Set proper permissions
        os.chmod(date_path, 0o774)
        log(f"Successfully created date directory: {date_path} (permissions: 0o774)")
        trace_out()
        return date_path
    except Exception as e:
        # ===== DEBUG CODE START: Build detailed error message =====
        error_details = [f"Path: {date_path}", f"Error: {str(e)}", f"Current user: {user_str}", f"Current group: {group_str}"]
        if parent_exists:
            error_details.append(f"Parent: {parent_path} (exists: True, perms: {parent_perms}, owner: {parent_owner}, group: {parent_group})")
        else:
            error_details.append(f"Parent: {parent_path} (exists: False)")
        
        detailed_error = " | ".join(error_details)
        warn(f"Failed to create date directory: {detailed_error}")
        log(f"Date directory creation FAILED: {base_path} -> {detailed_error}")
        # Re-raise with detailed message
        raise Exception(f"Failed to create date directory: {detailed_error}") from e
        # ===== DEBUG CODE END =====
        trace_out()


def calculate_target_height(img: Image.Image, target_width: int) -> int:
    trace_in()
    width, height = img.size
    result = int(height * target_width / width)
    log(f"Calculated target height: {width}x{height} -> {target_width}x{result} (aspect ratio: {width/height:.3f})")
    trace_out()
    return result


def scale_image(img: Image.Image, target_width: int, target_height: int) -> Optional[Image.Image]:
    trace_in()
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


def write_jpg(img: Image.Image, filepath: Path, quality: int = 80) -> bool:
    trace_in()
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
