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

@register_action('add_page')
@register_command('add_page')
def add_page() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.is_set('target_page') and not gateway.is_set('t_page'):
        warn("No target page ID provided")
        report_error("action", "Target page ID is required")
    if not is_error():
        target_page_arg = gateway.get_arg('target_page') or gateway.get_arg('t_page')
        try:
            target_page_id = int(target_page_arg)
        except ValueError:
            warn(f"Invalid target page ID: {target_page_arg}")
            report_error("action", "Target page ID must be a number")
    if not is_error():
        log(f"Loading target page {target_page_id}")
        target_page = get_page(page_id=target_page_id)
    if not is_error():
        # Get optional page class (defaults to 'page')
        page_class = gateway.get_arg('class') or 'page'
        # Check if this page class allows null names before requiring name
        NewPageClass = get_page_class(page_class)
        if not NewPageClass:
            warn(f"Page class '{page_class}' not found")
            report_error("action", f"Page class '{page_class}' not found")
        elif not NewPageClass.allow_null_names():
            # This class requires a name, so check if name is provided
            if not gateway.is_set('name'):
                warn("No page name provided")
                report_error("action", "Page name is required")
    if not is_error():
        name = gateway.get_arg('name')
        log(f"Creating new page '{name}' under target {target_page_id} with class '{page_class}'")
        new_page_id = target_page.add_page(page_class=page_class, name=name)
        page_created = not is_error() and new_page_id is not None
        if not page_created:
            warn("Page creation failed")
            report_error("action", "Page creation failed")
    if not is_error():
        log(f"Loading newly created page {new_page_id}")
        new_page = get_page(page_id=new_page_id)
        if not new_page:
            warn(f"Failed to load newly created page {new_page_id}")
            report_error("action", f"Failed to load newly created page {new_page_id}")
        else:
            # For classes that allow null names, name can be None, so only check if page was loaded
            NewPageClass = get_page_class(page_class)
            if NewPageClass and not NewPageClass.allow_null_names():
                # This class requires a name, so verify it was set
                if new_page.name is None:
                    warn(f"Newly created page {new_page_id} has no name but class '{page_class}' requires one")
                    report_error("action", f"Newly created page {new_page_id} has no name but class '{page_class}' requires one")
    if not is_error():
        response_data = new_page.show_page()
        gateway.response.set_action_response(success_payload(response_data))
        # Calculate total children from children_by_class
        total_children = sum(len(group.get('children', [])) for group in response_data.get('children_by_class', {}).values())
        log(f"Successfully created and loaded page {new_page_id}: {new_page.name} with {total_children} children")
    trace_out()
    return not is_error()
