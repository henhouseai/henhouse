from __future__ import annotations
from typing import Dict, Optional, Any
import importlib
from hh.gateway.connection.utils import deserialize_json_blob, normalize_datetime
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


def _get_page_class_and_load_utils(page_id: int) -> Optional[type]:
    """Helper to get PageClass and load mcp_utils. Returns PageClass or None if error."""
    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("Gateway or connection not available")
        report_error("connection", "Gateway or connection not available")
        return None
    
    query = "SELECT class FROM pages WHERE id = %s"
    results = gateway.conn.read(query, [page_id])
    if not results:
        warn(f"Page {page_id} not found")
        report_error("action", f"Page {page_id} not found")
        return None
    
    page_class_name = str(results[0].get('class') or 'page')
    # Get the appropriate Page subclass from registry
    PageClass = get_page_class(page_class_name)
    if PageClass is None:
        # Fall back to base Page class
        log(f"Page class '{page_class_name}' not found in registry, using base Page class")
        from hh.page.page import Page
        PageClass = Page
    else:
        log(f"Using registered class for '{page_class_name}': {PageClass.__name__}")
    # Load mcp_utils for HTTP backend requests (works for both registered and base Page class)
    _load_mcp_utils_for_page_class(PageClass)
    return PageClass

def _load_mcp_utils_for_page_class(PageClass: type) -> None:
    """Dynamically import mcp_utils module for a page class and all its parent classes for HTTP or MCP backend."""
    trace_in()
    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()
    if not gateway or gateway.backend not in ("http", "mcp"):
        # Only load mcp_utils for HTTP or MCP backend requests
        trace_out()
        return
    
    # Walk the MRO (Method Resolution Order) to load mcp_utils from each class in the inheritance chain
    loaded_modules = set()  # Track loaded modules to avoid duplicates
    
    try:
        for base_class in PageClass.__mro__:
            # Skip mixins, object, and base classes that don't have meaningful modules
            if (base_class is object or 
                base_class.__name__.endswith('Mixin') or
                not hasattr(base_class, '__module__') or
                not base_class.__module__):
                continue
            
            module_name = base_class.__module__
            # Extract base module path (e.g., 'hh.page.page' -> 'hh.page')
            module_parts = module_name.split('.')
            if len(module_parts) >= 2:
                base_module = '.'.join(module_parts[:-1])
                mcp_utils_module = f"{base_module}.mcp_utils"
                
                # Skip if we've already loaded this module
                if mcp_utils_module in loaded_modules:
                    continue
                
                try:
                    importlib.import_module(mcp_utils_module)
                    loaded_modules.add(mcp_utils_module)
                    log(f"Loaded mcp_utils for {base_class.__name__} ({module_name}): {mcp_utils_module}")
                except ImportError:
                    # mcp_utils doesn't exist for this module, that's okay
                    log(f"No mcp_utils found for {base_class.__name__} ({module_name})")
    except Exception as e:
        warn(f"Error loading mcp_utils for {PageClass.__name__}: {e}")
    trace_out()

def get_page(page_id: int) -> Optional[Any]:
    """Get page from hot cache or load from database. Page.__init__() handles cache hydration."""
    trace_in()
    if not page_id or page_id <= 0:
        warn(f"Invalid page ID: {page_id}")
        report_error("action", f"Invalid page ID: {page_id}")
        trace_out()
        return None
    
    # Check hot cache first
    log(f"Checking if page {page_id} is in hot cache")
    if page_id in _page_cache:
        cached_page = _page_cache[page_id]
        log(f"Returning cached page {page_id}: '{cached_page.name}' (class: {cached_page.class_name if hasattr(cached_page, 'class_name') else 'unknown'})")
        trace_out()
        return _page_cache[page_id]
    
    # Get page class (needs database query to determine subclass)
    PageClass = _get_page_class_and_load_utils(page_id)
    if not PageClass or is_error():
        trace_out()
        return None
    
    # Create page instance (Page.__init__() handles main DB load and cache hydration)
    try:
        page_instance = PageClass(id=page_id)
        if page_instance and not is_error():
            # Store in hot cache
            _page_cache[page_id] = page_instance
            log(f"Retrieved page {page_id}: '{page_instance.name}' (class: {page_instance.class_name})")
    except Exception as e:
        warn(f"Failed to create page {page_id}: {str(e)}")
        report_error("backend", f"Failed to create page {page_id}: {str(e)}")
        trace_out()
        return None
    
    trace_out()
    return page_instance if not is_error() else None


def find_page(link: str) -> Optional[Any]:
    """Find page by link. Returns page instance or None."""
    trace_in()
    if not link:
        warn("Empty link provided")
        report_error("action", "Empty link provided")
        trace_out()
        return None
    
    # Lazy import gateway locally for the link lookup query
    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("Gateway or connection not available")
        report_error("connection", "Gateway or connection not available")
        trace_out()
        return None
    
    query = "SELECT id FROM pages WHERE REPLACE(link, ' ', '') = %s"
    search_term = link.replace(' ', '')
    results = gateway.conn.read(query, [search_term])
    
    if not results:
        warn(f"No page found with link: {link}")
        report_error("link_resolution", f"No page found with link: {link}")
        trace_out()
        return None
    
    page_id = results[0]['id']
    page_instance = get_page(page_id=page_id)
    if not page_instance:
        warn(f"Failed to load page {page_id} for link: {link}")
        report_error("action", f"Failed to load page {page_id} for link: {link}")
        trace_out()
        return None
    
    log(f"Found page by link '{link}': page_id={page_id}, name='{page_instance.name if page_instance else 'N/A'}', loaded={page_instance is not None}")
    trace_out()
    return page_instance


def refresh_stale_page_caches() -> None:
    """Refresh cache database for all pages in hot cache that have _cache_needs_refresh flag set.
    Called by gateway during commit process, after file operations but before database commit."""
    trace_in()
    
    if not _page_cache:
        log("No pages in hot cache to refresh")
        trace_out()
        return
    
    refresh_count = 0
    for page_id, page_obj in list(_page_cache.items()):
        if getattr(page_obj, '_cache_needs_refresh', False):
            log(f"Refreshing cache for page {page_id}")
            try:
                # Call the refresh method on the page object
                # Page uses self.gateway.conn which is already in a transaction
                if page_obj._refresh_cached_page():
                    refresh_count += 1
                    log(f"Successfully refreshed cache for page {page_id}")
                else:
                    warn(f"Failed to refresh cache for page {page_id}")
            except Exception as e:
                warn(f"Exception while refreshing cache for page {page_id}: {e}")
                report_error("cache_refresh", f"Failed to refresh cache for page {page_id}: {e}")
    
    if refresh_count > 0:
        log(f"Refreshed cache for {refresh_count} page(s) in hot cache")
    else:
        log("No pages in hot cache needed cache refresh")
    
    trace_out()
