from typing import List, Dict, Any
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.image.image_base import BaseImage

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

class ImageUsageMixin(BaseImage):
    
    def get_usage_count(self) -> int:
        trace_in()
        count = 0
        if not is_error():
            query = "SELECT COUNT(*) as count FROM image_groups WHERE image_id = %s"
            results = self.gateway.conn.read(query, [self.id])
            if results:
                count = results[0]['count']
        log(f"Image {self.id} is used by {count} pages")
        trace_out()
        return count


    def get_used_by_pages(self) -> List[int]:
        trace_in()
        page_ids = []
        if not is_error():
            query = "SELECT page_id FROM image_groups WHERE image_id = %s ORDER BY page_id"
            results = self.gateway.conn.read(query, [self.id])
            page_ids = [row['page_id'] for row in results]
        log(f"Image {self.id} is used by pages: {page_ids}")
        trace_out()
        return page_ids


    def check_incoming_links(self) -> List[Dict[str, Any]]:
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
            results = self.gateway.conn.read(query, [self.id])
            for row in results:
                links.append({
                    'page_id': row['page_id'],
                    'page_name': row['page_name']
                })
            log(f"Found {len(links)} incoming links for image {self.id}")
        trace_out()
        return links
