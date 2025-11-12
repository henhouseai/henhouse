from __future__ import annotations
from typing import Dict, Optional, Any
from hh.gateway.connection.connection import r_query
from hh.gateway.connection.decorators import db_read
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_class_registry import get_page_class

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

_page_cache: Dict[int, Any] = {}

@db_read
def get_page(conn, page_id: int) -> Optional[Any]:
    trace_in()
    if not page_id or page_id <= 0:
        warn(f"Invalid page ID: {page_id}")
        report_error("action", f"Invalid page ID: {page_id}")
    if not is_error():
        if page_id in _page_cache:
            cached_page = _page_cache[page_id]
            log(f"Returning cached page {page_id}: '{cached_page.name}' (class: {cached_page.class_name if hasattr(cached_page, 'class_name') else 'unknown'})")
            trace_out()
            return _page_cache[page_id]
    if not is_error():
        query = "SELECT class FROM pages WHERE id = %s"
        results = r_query(conn, query, [page_id])
        if not results:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    if not is_error():
        page_class_name = results[0].get('class', 'page')
        # Get the appropriate Page subclass from registry
        PageClass = get_page_class(page_class_name)
        if PageClass is None:
            # Fall back to base Page class
            log(f"Page class '{page_class_name}' not found in registry, using base Page class")
            from hh.page.page import Page
            PageClass = Page
        else:
            log(f"Using registered class for '{page_class_name}': {PageClass.__name__}")
    if not is_error():
        try:
            page_instance = PageClass(id=page_id)
        except Exception as e:
            warn(f"Failed to create page {page_id}: {str(e)}")
            report_error("backend", f"Failed to create page {page_id}: {str(e)}")
    if not is_error():
        _page_cache[page_id] = page_instance
        log(f"Retrieved page {page_id}: '{page_instance.name}' (class: {page_class_name})")
        trace_out()
        return page_instance
    trace_out()
    return None


def get_page_conn(conn, page_id: int) -> Optional[Any]:
    trace_in()
    if not page_id or page_id <= 0:
        warn(f"Invalid page ID: {page_id}")
        report_error("action", f"Invalid page ID: {page_id}")
    if not is_error():
        query = "SELECT class FROM pages WHERE id = %s"
        results = r_query(conn, query, [page_id])
        if not results:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    if not is_error():
        page_class_name = results[0].get('class', 'page')
        # Get the appropriate Page subclass from registry
        PageClass = get_page_class(page_class_name)
        if PageClass is None:
            # Fall back to base Page class
            log(f"Page class '{page_class_name}' not found in registry, using base Page class")
            from hh.page.page import Page
            PageClass = Page
        else:
            log(f"Using registered class for '{page_class_name}': {PageClass.__name__}")
    if not is_error():
        try:
            page_instance = PageClass(id=page_id, conn=conn)
        except Exception as e:
            warn(f"Failed to create page {page_id}: {str(e)}")
            report_error("backend", f"Failed to create page {page_id}: {str(e)}")
    if not is_error():
        log(f"Created page {page_id} with explicit connection: '{page_instance.name}' (class: {page_class_name})")
        trace_out()
        return page_instance
    trace_out()
    return None


@db_read
def find_page(conn, link: str) -> Optional[Any]:
    trace_in()
    if not link:
        warn("Empty link provided")
        report_error("action", "Empty link provided")
    query = "SELECT id FROM pages WHERE REPLACE(link, ' ', '') = %s"
    search_term = link.replace(' ', '')
    results = r_query(conn, query, [search_term])
    if not results:
        warn(f"No page found with link: {link}")
        report_error("link_resolution", f"No page found with link: {link}")
    else:
        page_id = results[0]['id']
        page_instance = get_page(page_id=page_id)
        if not page_instance:
            warn(f"Failed to load page {page_id} for link: {link}")
            report_error("action", f"Failed to load page {page_id} for link: {link}")
    if not is_error():
        log(f"Found page by link '{link}': page_id={page_id}, name='{page_instance.name if page_instance else 'N/A'}', loaded={page_instance is not None}")
        trace_out()
        return page_instance
    trace_out()
    return None

