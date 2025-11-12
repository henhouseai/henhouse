from __future__ import annotations
from typing import Dict, Any
from hh.gateway.connection.decorators import db_read
from hh.gateway.connection.connection import r_query
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error
from hh.page.page_registry import get_page, find_page
from hh.image.image_registry import get_image
from hh.page.page import Page
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

@register_action('count_pages')
@register_command('count_pages')
@db_read
def count_pages(conn) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    try:
        # Count pages table
        pages_query = "SELECT COUNT(*) as count FROM pages"
        pages_results = r_query(conn, pages_query, [])
        pages_count = pages_results[0]["count"] if pages_results else 0
        # Count images table
        images_query = "SELECT COUNT(*) as count FROM images"
        images_results = r_query(conn, images_query, [])
        images_count = images_results[0]["count"] if images_results else 0
        data = {
            "pages_count": pages_count,
            "images_count": images_count
        }
        gateway.response.set_action_response(success_payload(data))
        log(f"Counted {pages_count} pages and {images_count} images")
        trace_out()
        return True
    except Exception as e:
        warn(f"Count pages failed: {str(e)}")
        report_error("backend", f"Count pages failed: {str(e)}")
        trace_out()
        return False
