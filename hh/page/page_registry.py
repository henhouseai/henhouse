from __future__ import annotations
from typing import Dict, Optional, Any
import importlib
import json
import datetime as dt
from hh.gateway.connection.connection import r_query
from hh.gateway.connection.decorators import db_read
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.gateway import get_gateway
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
_cached_page_payloads: Dict[int, Dict[str, Any]] = {}


def _deserialize_json_blob(blob, default):
    if blob in (None, '', b''):
        return default
    if isinstance(blob, (bytes, bytearray)):
        blob = blob.decode('utf-8')
    if isinstance(blob, str):
        try:
            return json.loads(blob)
        except json.JSONDecodeError:
            return default
    if isinstance(blob, (dict, list)):
        return blob
    return default


def _serialize_dt(value):
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    return value


def _build_cached_page_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    metadata = _deserialize_json_blob(row.get('metadata'), {})
    children_by_class = _deserialize_json_blob(row.get('children_summary'), {})
    images = _deserialize_json_blob(row.get('image_summary'), [])
    file_summary = _deserialize_json_blob(row.get('file_summary'), {})
    badge_headers = _deserialize_json_blob(row.get('links_out'), {})
    prepared_text = _deserialize_json_blob(row.get('prepared_text'), None)

    upper_content = file_summary.get('upper_content', []) if isinstance(file_summary, dict) else []
    lower_content = file_summary.get('lower_content', []) if isinstance(file_summary, dict) else []

    page_block = {
        "id": row.get('id'),
        "name": row.get('name'),
        "link": row.get('link'),
        "parent": row.get('parent_id'),
        "class": row.get('class'),
        "visibility": None,
        "text": row.get('text'),
        "prepared_text": prepared_text,
        "metadata": metadata,
        "last_modified": _serialize_dt(row.get('source_last_modified')),
        "cache_built_at": _serialize_dt(row.get('cache_built_at')),
        "cache_version": row.get('cache_version'),
    }

    payload = {
        "page": page_block,
        "children_by_class": children_by_class or {},
        "images": images or [],
        "badge_headers": badge_headers or {},
        "upper_content": upper_content,
        "lower_content": lower_content,
        "_cache_info": {
            "source_last_modified": _serialize_dt(row.get('source_last_modified')),
            "cache_built_at": _serialize_dt(row.get('cache_built_at')),
            "version": row.get('cache_version'),
        }
    }
    return payload

def _load_mcp_utils_for_page_class(PageClass: type) -> None:
    """Dynamically import mcp_utils module for a page class and all its parent classes for HTTP or MCP backend."""
    trace_in()
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
                    debug(f"No mcp_utils found for {base_class.__name__} ({module_name})")
    except Exception as e:
        warn(f"Error loading mcp_utils for {PageClass.__name__}: {e}")
    trace_out()

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
        # Load mcp_utils for HTTP backend requests (works for both registered and base Page class)
        _load_mcp_utils_for_page_class(PageClass)
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
        # Load mcp_utils for HTTP backend requests (works for both registered and base Page class)
        _load_mcp_utils_for_page_class(PageClass)
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
def get_page_cached_payload(conn, page_id: int) -> Optional[Dict[str, Any]]:
    trace_in()
    if not page_id or page_id <= 0:
        warn(f"Invalid page ID: {page_id}")
        report_error("action", f"Invalid page ID: {page_id}")
    if not is_error():
        if page_id in _cached_page_payloads:
            debug(f"Returning cached payload for page {page_id} from hot cache")
            trace_out()
            return _cached_page_payloads[page_id]
    if not is_error():
        query = """
            SELECT id, parent_id, class, name, link, text, metadata,
                   prepared_text, children_summary, image_summary, file_summary, links_out,
                   source_last_modified, cache_built_at, cache_version
            FROM pages
            WHERE id = %s
        """
        results = r_query(conn, query, [page_id], use_secondary=True)
        if not results:
            debug(f"Cached page {page_id} not found in cache database")
        else:
            payload = _build_cached_page_payload(results[0])
            _cached_page_payloads[page_id] = payload
            debug(f"Loaded cached payload for page {page_id} (cache version={payload['_cache_info']['version']})")
            trace_out()
            return payload
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

