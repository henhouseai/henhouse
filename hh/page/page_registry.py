from __future__ import annotations
from typing import Dict, Optional, Any
import importlib
from hh.gateway.connection.utils import deserialize_json_blob, normalize_datetime
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_class_registry import get_page_class

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
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
    """Helper to get PageClass and load tools. Returns PageClass or None if error."""
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
    # Load tools for HTTP/API backend requests (pass page_id for primary page check)
    _load_tools_for_page_class(PageClass, page_id)
    return PageClass

def _load_tools_for_page_class(PageClass: type, page_id: int) -> None:
    """Dynamically import tools module for a page class and all its parent classes for HTTP or API backend.
    Only loads for primary page - not for child pages loaded during hydration."""
    trace_in()
    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()

    # Only load tools for HTTP or API backend requests (for app actions)
    # MCP uses cold cache for tools/list, doesn't need MRO walk
    if not gateway or gateway.backend not in ("http", "api"):
        trace_out()
        return

    # Only load for primary page - check if this page_id matches the request
    # This prevents app actions from child classes bleeding into response
    request_page_id = None
    if gateway.request:
        # Check various ways the page ID might be specified
        request_page_id = gateway.get_arg('id') or gateway.get_arg('page_id')

    if request_page_id and int(request_page_id) != page_id:
        log(f"Skipping tools load for child page {page_id} (primary is {request_page_id})")
        trace_out()
        return

    # Walk the MRO (Method Resolution Order) to load tools from each class in the inheritance chain
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
                tools_module = f"{base_module}.tools"

                # Skip if we've already loaded this module
                if tools_module in loaded_modules:
                    continue

                try:
                    importlib.import_module(tools_module)
                    loaded_modules.add(tools_module)
                    log(f"Loaded tools for {base_class.__name__} ({module_name}): {tools_module}")
                except ImportError:
                    # tools doesn't exist for this module, that's okay
                    log(f"No tools found for {base_class.__name__} ({module_name})")
    except Exception as e:
        warn(f"Error loading tools for {PageClass.__name__}: {e}")
    trace_out()

def get_page(page_id: int, with_subpath: bool = False) -> Optional[Any]:
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
    
    # If with_subpath=True, check for --subpath argument and resolve it
    if with_subpath and page_instance and not is_error():
        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        if gateway:
            subpath_arg = gateway.get_arg('subpath')
            if subpath_arg:
                log(f"Resolving subpath '{subpath_arg}' from base page {page_id}")
                resolved_page = resolve_path(page_instance, subpath_arg)
                if resolved_page:
                    log(f"Subpath resolved to page {resolved_page.id}")
                    page_instance = resolved_page
                else:
                    log(f"Subpath '{subpath_arg}' resolution failed, returning base page")

    trace_out()
    return page_instance if not is_error() else None


def find_page(link: str, with_subpath: bool = False) -> Optional[Any]:
    """Find page by link. Returns page instance or None. If with_subpath=True, also resolves subpath."""
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
    page_instance = get_page(page_id=page_id, with_subpath=with_subpath)
    if not page_instance:
        warn(f"Failed to load page {page_id} for link: {link}")
        report_error("action", f"Failed to load page {page_id} for link: {link}")
        trace_out()
        return None

    log(f"Found page by link '{link}': page_id={page_id}, name='{page_instance.name if page_instance else 'N/A'}', loaded={page_instance is not None}")
    trace_out()
    return page_instance


def get_child_by_name(parent_id: int, child_name: str) -> Optional[Any]:
    """
    Find a child page by name under a specific parent.

    Used for SubPage URL traversal where we need to walk down
    the page hierarchy by name segments.

    Args:
        parent_id: The ID of the parent page
        child_name: The name of the child to find

    Returns:
        Page instance if found, None otherwise
    """
    trace_in()

    if not parent_id or not child_name:
        trace_out()
        return None

    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("Gateway or connection not available")
        trace_out()
        return None

    # Look for child with matching name under this parent
    query = "SELECT id FROM pages WHERE parent = %s AND name = %s LIMIT 1"
    results = gateway.conn.read(query, [parent_id, child_name])

    if not results:
        log(f"No child named '{child_name}' found under parent {parent_id}")
        trace_out()
        return None

    child_id = results[0]['id']
    child_page = get_page(child_id)

    log(f"Found child '{child_name}' (id={child_id}) under parent {parent_id}")
    trace_out()
    return child_page


def get_child_count(parent_id: int, child_name: str) -> int:
    """
    Count how many children with a given name exist under a parent.

    Used by resolve_path() to detect ambiguous names (duplicates).
    """
    trace_in()

    if not parent_id or not child_name:
        trace_out()
        return 0

    from hh.gateway.gateway import get_gateway
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("Gateway or connection not available")
        trace_out()
        return 0

    # Count children with matching name under this parent
    query = "SELECT COUNT(*) as count FROM pages WHERE parent = %s AND name = %s"
    results = gateway.conn.read(query, [parent_id, child_name])

    count = results[0]['count'] if results else 0
    trace_out()
    return count


def resolve_path(base_page: Any, subpath: str) -> Optional[Any]:
    """
    Resolve a SubPage path starting from a base page.

    Traverses children by name, stopping at ambiguity. If duplicate names exist,
    resolves to the deepest unambiguous level to prevent unpredictable behavior.

    Args:
        base_page: Starting page instance (from name/id lookup)
        subpath: Remaining path segments separated by /

    Returns:
        Page instance at deepest unambiguous level, or base_page if no subpath

    Examples:
        base_page = find_page('alice')
        resolve_path(base_page, 'projects/task1') -> traverses to projects/task1
        resolve_path(base_page, 'projects') -> traverses to projects (if unambiguous)
        resolve_path(base_page, 'ambiguous') -> returns base_page if multiple 'ambiguous' children
    """
    trace_in()

    if not base_page:
        trace_out()
        return None

    if not subpath:
        # No subpath - return the base page
        trace_out()
        return base_page

    # Split subpath and traverse
    parts = subpath.split('/')
    page = base_page

    for segment in parts:
        if not segment:  # Skip empty segments
            continue

        # Check if there's exactly one child with this name
        child_count = get_child_count(page.id, segment)

        if child_count == 1:
            # Exactly one match - safe to traverse
            page = get_child_by_name(page.id, segment)
            if not page:
                # This shouldn't happen if count was 1, but safety check
                log(f"Unexpected: child '{segment}' count=1 but lookup failed")
                break
        elif child_count == 0:
            # No children with this name
            log(f"No children named '{segment}' under page {page.id}")
            break
        else:
            # Multiple children with same name - ambiguity detected
            log(f"Ambiguous: {child_count} children named '{segment}' under page {page.id}, stopping traversal")
            break

    log(f"Resolved subpath '{subpath}' from base page {base_page.id} to page {page.id}")
    trace_out()
    return page


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
