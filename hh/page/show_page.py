from __future__ import annotations
from typing import Dict, Any
from hh.gateway.connection.decorators import db_read
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page, find_page
from hh.image.image_registry import get_image
#from hh.page.page import Page
#from hh.image.image import Image


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

@register_action('show_page')
@register_command('show_page')
def show_page() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_set('id') and not gateway.is_set('name') and not gateway.is_set('link'):
        warn("No page identifier provided")
        report_error("action", "Page ID, name, or link is required")
    if not is_error():
        page_id = gateway.get_arg('id')
        page_name = gateway.get_arg('name')
        page_link = gateway.get_arg('link')
        # Determine which parameter was provided
        if page_id:
            log(f"Using page ID: {page_id}")
            try:
                page_id = int(page_id)
            except ValueError:
                warn(f"Invalid page ID: {page_id}")
                report_error("action", "Page ID must be a number")
            if not is_error():
                page = get_page(page_id=page_id)
                if not page:
                    warn(f"Page {page_id} not found")
                    report_error("action", f"Page {page_id} not found")
        elif page_name or page_link:
            # Use name as alias for link
            search_term = page_name if page_name else page_link
            log(f"Searching for page with name/link: {search_term}")
            page = find_page(link=search_term)
            if not page:
                warn(f"No page found with name/link: {search_term}")
                report_error("action", f"No page found with name/link: {search_term}")
    if not is_error():
        response_data = page.show_page()
        gateway.response.set_action_response(success_payload(response_data))
        # Seed page basics in one combined payload (avoid overwriting)
        resolved_id = getattr(page, 'id', page_id)
        page_block = (response_data or {}).get('page') or {}
        page_title = page_block.get('title') or page_block.get('name')
        seed_payload = {'page': {'id': str(resolved_id)}}
        if page_title:
            seed_payload['page']['title'] = page_title
        gateway.response.add_seed_data(seed_payload)
        if page_id:
            total_children = sum(len(group['children']) for group in response_data['children_by_class'].values())
            log(f"Successfully loaded page {page_id} with {total_children} children")
        else:
            total_children = sum(len(group['children']) for group in response_data['children_by_class'].values())
            log(f"Successfully loaded page '{search_term}' with {total_children} children")
    trace_out()
    return not is_error()
