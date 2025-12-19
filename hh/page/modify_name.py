from __future__ import annotations
from typing import Dict, Any
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway
from hh.gateway.response.json_standard import success_payload
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.page.page_registry import get_page, find_page
from hh.page.page_class_registry import get_page_class
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

@register_action('modify_name')
@register_command('modify_name')
def modify_name() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway.is_set('page_id') and not gateway.is_set('id'):
        warn("No page ID provided")
        report_error("action", "Page ID is required")
    page_id: int = 0
    if not is_error():
        page_id_arg = gateway.get_arg('page_id') or gateway.get_arg('id')
        try:
            page_id = int(page_id_arg)
        except ValueError:
            warn(f"Invalid page ID: {page_id_arg}")
            report_error("action", "Page ID must be a number")
    page = None
    if not is_error():
        log(f"Loading page {page_id}")
        page = get_page(page_id=page_id)
        if not page:
            warn(f"Page {page_id} not found")
            report_error("action", f"Page {page_id} not found")
    new_name: str | None = None
    if not is_error() and page is not None:
        # Get the name argument (could be boolean True, empty string, or actual string)
        name_arg = gateway.get_arg('name') if gateway.is_set('name') else None
        # Check if this page class allows null names
        class_name = page.class_name if page.class_name is not None else "page"
        PageClass = get_page_class(class_name)
        allows_null = PageClass.allow_null_names() if PageClass else False
        
        # Normalize the name: if it's boolean True or empty string, treat as None (if class allows it)
        if name_arg is True or (isinstance(name_arg, str) and len(name_arg.strip()) == 0):
            if allows_null:
                new_name = None  # Will set to NULL in database
            else:
                warn("No new name provided")
                report_error("action", "New name is required")
                new_name = None
        elif name_arg is None or name_arg is False:
            if allows_null:
                new_name = None  # Will set to NULL in database
            else:
                warn("No new name provided")
                report_error("action", "New name is required")
                new_name = None
        else:
            # It's a non-empty string
            new_name = str(name_arg) if not isinstance(name_arg, str) else name_arg
    if not is_error() and page is not None:
        log(f"Modifying page {page_id} name to '{new_name}'")
        success = page.modify_name(new_name)
        if not success:
            warn("Page name modification failed")
            report_error("action", "Page name modification failed")
    if not is_error() and page is not None:
        response_data = page.show_page()
        gateway.response.set_action_response(success_payload(response_data))
        # Calculate total children from children_by_class
        total_children = sum(len(group.get('children', [])) for group in response_data.get('children_by_class', {}).values())
        log(f"Successfully modified page {page_id} name to '{new_name}' with {total_children} children")
    trace_out()
    return not is_error()
