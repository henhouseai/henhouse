from typing import Optional, List, Dict, Any
from hh.gateway.connection.connection import r_query
from hh.gateway.connection.decorators import db_read
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.image.image import Image

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

_image_cache: Dict[int, Any] = {}

@db_read
def get_image(conn, image_id: int) -> Optional[Image]:
    trace_in()
    if not image_id or image_id <= 0:
        warn(f"Invalid image ID: {image_id}")
        report_error("action", f"Invalid image ID: {image_id}")
    if not is_error():
        if image_id in _image_cache:
            cached_image = _image_cache[image_id]
            log(f"Returning cached image {image_id}: '{cached_image.caption}'")
            trace_out()
            return _image_cache[image_id]
    if not is_error():
        query = "SELECT id FROM images WHERE id = %s"
        results = r_query(conn, query, [image_id])
        if not results:
            warn(f"Image {image_id} not found")
            report_error("action", f"Image {image_id} not found")
    if not is_error():
        try:
            image_instance = Image(image_id=image_id)
        except Exception as e:
            warn(f"Failed to create image {image_id}: {str(e)}")
            report_error("backend", f"Failed to create image {image_id}: {str(e)}")
    if not is_error():
        _image_cache[image_id] = image_instance
        log(f"Retrieved image {image_id}: '{image_instance.caption}'")
        trace_out()
        return image_instance
    trace_out()
    return None


def get_image_conn(conn: DatabaseConnection, image_id: int) -> Optional[Image]:
    """Get image with explicit connection - no caching, creates new instance"""
    trace_in()
    if not image_id or image_id <= 0:
        warn(f"Invalid image ID: {image_id}")
        report_error("action", f"Invalid image ID: {image_id}")
    if not is_error():
        query = "SELECT id FROM images WHERE id = %s"
        results = r_query(conn, query, [image_id])
        if not results:
            warn(f"Image {image_id} not found")
            report_error("action", f"Image {image_id} not found")
    if not is_error():
        try:
            image_instance = Image(image_id=image_id, conn=conn)
        except Exception as e:
            warn(f"Failed to retrieve image {image_id}: {str(e)}")
            report_error("backend", f"Failed to retrieve image {image_id}: {str(e)}")
    if not is_error():
        log(f"Retrieved image {image_id} with explicit connection: {conn}")
        trace_out()
        return image_instance
    trace_out()
    return None
