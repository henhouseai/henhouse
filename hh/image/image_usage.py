from typing import List, Dict, Any
from hh.gateway.connection.connection import r_query
from hh.gateway.connection.decorators import db_read
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.image.image_method_registry import register_image_mixin_methods

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_image_usage_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)

@register_image_mixin_methods
def _register_usage_methods():
    return {
        'get_usage_count': {'mixin_method': '_get_usage_count', 'decorator': 'read'},
        'get_used_by_pages': {'mixin_method': '_get_used_by_pages', 'decorator': 'read'},
        'check_incoming_links': {'mixin_method': '_check_incoming_links', 'decorator': 'read'},
    }

class ImageUsageMixin:
    
    def _get_usage_count(self) -> int:
        trace_in()
        count = 0
        if not is_error():
            query = "SELECT COUNT(*) as count FROM image_groups WHERE image_id = %s"
            results = r_query(self.conn, query, [self.id])
            if results:
                count = results[0]['count']
        log(f"Image {self.id} is used by {count} pages")
        trace_out()
        return count


    def _get_used_by_pages(self) -> List[int]:
        trace_in()
        page_ids = []
        if not is_error():
            query = "SELECT page_id FROM image_groups WHERE image_id = %s ORDER BY page_id"
            results = r_query(self.conn, query, [self.id])
            page_ids = [row['page_id'] for row in results]
        log(f"Image {self.id} is used by pages: {page_ids}")
        trace_out()
        return page_ids


    def _check_incoming_links(self) -> List[Dict[str, Any]]:
        trace_in()
        log(f"Checking incoming links for image {self.id}")
        links = []
        if not is_error():
            query = """
                SELECT image_links.id as page_id, pages.name as page_name
                FROM image_links 
                JOIN pages ON image_links.id = pages.id 
                WHERE image_links.resolution_id = %s
            """
            results = r_query(self.conn, query, [self.id])
            for row in results:
                links.append({
                    'page_id': row['page_id'],
                    'page_name': row['page_name']
                })
            log(f"Found {len(links)} incoming links for image {self.id}")
        trace_out()
        return links
