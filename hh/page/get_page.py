from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page, find_page

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

@register_action('get_page')
@register_command('get_page')
def get_page_action() -> bool:
    """Return JSON-friendly page data (AJAX). Supports lookup by ID, name, or link."""
    trace_in()
    gateway = get_gateway()
    # Support id, name, or link parameters (like show_page)
    if not gateway.is_set('id') and not gateway.is_set('name') and not gateway.is_set('link'):
        warn("No page identifier provided")
        report_error("action", "Page ID, name, or link is required")
    page_obj = None
    page_id: int | None = None
    search_term: str | None = None
    if not is_error():
        page_id_arg = gateway.get_arg('id')
        page_name = gateway.get_arg('name')
        page_link = gateway.get_arg('link')
        # Determine which parameter was provided
        if page_id_arg:
            log(f"Using page ID: {page_id_arg}")
            try:
                page_id = int(page_id_arg)
            except ValueError:
                warn(f"Invalid page ID: {page_id_arg}")
                report_error("action", "Page ID must be a number")
            if not is_error() and page_id is not None:
                page_obj = get_page(page_id=page_id, with_subpath=True)
                if not page_obj:
                    warn(f"Page {page_id} not found")
                    report_error("action", f"Page {page_id} not found")
        elif page_name or page_link:
            # Use name as alias for link
            search_term = page_name if page_name else page_link
            log(f"Searching for page with name/link: {search_term}")
            page_obj = find_page(link=search_term, with_subpath=True)
            if not page_obj:
                warn(f"No page found with name/link: {search_term}")
                report_error("action", f"No page found with name/link: {search_term}")

    if not is_error() and page_obj is not None:
        response_data = page_obj.get_page()
        gateway.response.set_action_response(success_payload(response_data))
        # Log success with appropriate identifier
        if page_id:
            log(f"Successfully assembled AJAX page payload for ID {page_id}")
        else:
            log(f"Successfully assembled AJAX page payload for '{search_term}'")

    trace_out()
    return not is_error()


